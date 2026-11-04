# Copyright 2026 Anshul48
# SPDX-License-Identifier: Apache-2.0
"""Build the A/B bug tasks in the format `anima run --task` reads (stdlib only).

For every entry in tasks.json it creates   <out>/<id>/{task.json, repo/, hidden/}

  repo/    the project exactly as it was at the BASE commit, with no git history
           (so the agent cannot read the fix out of `git log`).
  hidden/  the tests folder as it is at the FIX commit. The checker copies it into
           the workspace only AFTER the agent has finished. The agent never sees it.
  gate     pytest over the test files that the fix commit changed.

Then `--check` proves the gate is sound: it must FAIL on the base code and PASS once
the fix commit's non-test changes are applied. A task that does not satisfy both is
reported and left out of the A/B.

  python3 -m anima.memory.ab.build_tasks --out DIR [--source DIR_OF_CLONES] [--check --python PY]

--source lets you reuse local clones named like the repos (cachetools, click, ...);
without it each repo is cloned (blob-filtered, no checkout) from GitHub.
"""
from __future__ import annotations

import argparse
import json
import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

HERE = Path(__file__).resolve().parent
TESTISH = re.compile(r"(^|/)(tests?|testing)(/|$)|(^|/)test_[^/]*\.py$|(^|/)[^/]*_test\.py$")


def git(repo, *args, check=True, text=True, input=None):
    r = subprocess.run(["git", "-C", str(repo), *args], capture_output=True, text=text, input=input)
    if check and r.returncode:
        raise RuntimeError(f"git {' '.join(args)} failed in {repo}: {(r.stderr or '')[:300]}")
    return r.stdout


def get_repo(task, source, cache):
    name = task.get("_local") or task["repo"].rsplit("/", 1)[-1].removesuffix(".git")
    if source and (Path(source) / name).is_dir():
        return Path(source) / name
    dest = Path(cache) / name
    if not dest.exists():
        subprocess.run(["git", "clone", "--quiet", "--no-checkout", "--filter=blob:none", task["repo"], str(dest)], check=True)
    return dest


def archive(repo, rev, dest, paths=()):
    dest.mkdir(parents=True, exist_ok=True)
    p = subprocess.Popen(["git", "-C", str(repo), "archive", rev, *paths], stdout=subprocess.PIPE)
    subprocess.run(["tar", "-x", "-C", str(dest)], stdin=p.stdout, check=True)
    p.stdout.close()
    if p.wait():
        raise RuntimeError(f"git archive {rev} {paths} failed")


def split_changes(repo, base, fix):
    names = git(repo, "diff", "--name-only", f"{base}", f"{fix}").split()
    tests = [n for n in names if n.endswith(".py") and TESTISH.search(n)]
    code = [n for n in names if n not in tests and n.endswith(".py")]  # docs / changelog entries are not needed to fix the bug
    return tests, code


def gate_argv(targets):
    code = ("import sys, pytest; sys.path[:0] = ['src', '.']; "
            "sys.exit(pytest.main(['-q', '-p', 'no:cacheprovider', '--rootdir=.', '-o', 'addopts='] + sys.argv[1:]))")
    return ["{python}", "-c", code, *targets]


def build_one(task, out, source, cache):
    repo = get_repo(task, source, cache)
    base, fix = task["base"], task["fix"]
    tests, code = split_changes(repo, base, fix)
    if not tests or not code:
        raise RuntimeError(f"{task['id']}: fix commit must change both tests ({tests}) and code ({code})")
    d = Path(out) / task["id"]
    if d.exists():
        shutil.rmtree(d)
    archive(repo, base, d / "repo")
    roots = sorted({t.split("/")[0] for t in tests if "/" in t})  # e.g. "tests"
    troot = roots[0] if roots and roots[0] in ("tests", "test") else None
    if troot:
        archive(repo, fix, d / "_fix_tests", [troot])
        shutil.move(str(d / "_fix_tests" / troot), str(d / "hidden"))
        shutil.rmtree(d / "_fix_tests")
        targets = [f"hidden/{t[len(troot) + 1:]}" for t in tests if t.startswith(troot + "/")]
    else:  # tests next to the code (e.g. test_x.py in the root)
        (d / "hidden").mkdir()
        for t in tests:
            (d / "hidden" / Path(t).name).write_bytes(subprocess.run(["git", "-C", str(repo), "show", f"{fix}:{t}"], capture_output=True, check=True).stdout)
        targets = [f"hidden/{Path(t).name}" for t in tests]
    card = {
        "id": task["id"], "title": task["id"].replace("-", " "),
        "issue_text": task["issue_text"].rstrip() + "\nFix the bug in the repository. Do not edit anything under tests/. Finish with a one-line summary.",
        "workspace_seed": "repo", "hidden_dir": "hidden", "protected_roots": [troot or "tests"],
        "gate_argv": gate_argv(targets), "timeout_s": 1500, "gate_timeout_s": 240,
        "provenance": {"repo": task["repo"], "base": base, "fix": fix, "flagship": bool(task.get("flagship")),
                       "tests_changed_by_fix": tests, "code_changed_by_fix": code},
    }
    (d / "task.json").write_text(json.dumps(card, indent=1) + "\n")
    # the fix's code changes, kept OUTSIDE the task folder (used only by --check, never shown to an agent)
    gold = git(repo, "diff", base, fix, "--", *code)
    gdir = Path(out) / "_gold"
    gdir.mkdir(exist_ok=True)
    (gdir / f"{task['id']}.patch").write_text(gold)
    return d, card


def run_gate(card, seed_dir, hidden_dir, python, apply_patch=None):
    with tempfile.TemporaryDirectory() as td:
        ev = Path(td) / "ev"
        shutil.copytree(seed_dir, ev, ignore=shutil.ignore_patterns(".git", "__pycache__"))
        if apply_patch:
            subprocess.run(["git", "apply", "--whitespace=nowarn", str(apply_patch)], cwd=ev, check=True)
        shutil.copytree(hidden_dir, ev / "hidden", ignore=shutil.ignore_patterns("__pycache__"))
        argv = [python if a == "{python}" else a for a in card["gate_argv"]]
        r = subprocess.run(argv, cwd=ev, capture_output=True, text=True, timeout=card["gate_timeout_s"])
        tail = [ln for ln in (r.stdout + r.stderr).strip().splitlines() if ln.strip()][-1:] or [""]
        return r.returncode, tail[0]


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("--out", required=True)
    ap.add_argument("--source", help="folder holding local clones named cachetools, click, ...")
    ap.add_argument("--only", action="append", help="build only this task id (repeatable)")
    ap.add_argument("--check", action="store_true", help="prove the gate FAILS on base and PASSES with the fix")
    ap.add_argument("--python", default=sys.executable, help="interpreter with pytest (and the test dependencies) for --check")
    a = ap.parse_args(argv)
    spec = json.loads((HERE / "tasks.json").read_text())
    cache = Path(a.out) / "_clones"
    Path(a.out).mkdir(parents=True, exist_ok=True)
    report = {}
    for t in spec["tasks"]:
        if a.only and t["id"] not in a.only:
            continue
        try:
            d, card = build_one(t, a.out, a.source, cache)
        except Exception as e:  # noqa: BLE001
            print(f"BUILD-FAIL {t['id']}: {e}")
            report[t["id"]] = {"built": False, "why": str(e)}
            continue
        row = {"built": True}
        if a.check:
            rc0, l0 = run_gate(card, d / "repo", d / "hidden", a.python)
            rc1, l1 = run_gate(card, d / "repo", d / "hidden", a.python, Path(a.out) / "_gold" / f"{t['id']}.patch")
            ok = rc0 != 0 and rc1 == 0
            row.update(base_exit=rc0, base_last_line=l0, fixed_exit=rc1, fixed_last_line=l1, sound=ok)
            print(f"{'SOUND ' if ok else 'UNSOUND'} {t['id']:32s} base: exit {rc0} [{l0[:60]}]  with fix: exit {rc1} [{l1[:50]}]")
        else:
            print(f"built {t['id']} -> {d}")
        report[t["id"]] = row
    (Path(a.out) / "build-report.json").write_text(json.dumps(report, indent=1) + "\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())
