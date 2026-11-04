"""`anima` command line: init, doctor, harness list/add/test/use, run, check, verify-log.

Other groups plug in without editing this file: `anima <group> ...` imports
`anima.<group>.cli` and calls its `main(argv)` if that module exists
(for example `anima.memory.cli`).
"""
from __future__ import annotations

import argparse
import importlib
import json
import shutil
import subprocess
import sys
import tempfile
import time
import uuid
from pathlib import Path

from . import chain as chainmod
from . import miniyaml
from .adapters import DETECT_ORDER, KINDS, Adapter, HarnessError, detect_installed, make_adapter
from .ladder import architect_plan, load_task, run_task
from .profile import HEADER, Profile, anima_home, build_default, find_profile, load, save
from .rules import DEFAULT_PACKS, check_command, hook_decision, packs_for

EXIT_NOT_RUN = 2


def out(msg=""):
    print(msg, flush=True)


# ----------------------------------------------------------------- profile io
def open_profile(explicit=None, need=True) -> Profile | None:
    path = find_profile(explicit)
    if path is None or not path.exists():
        if need:
            raise HarnessError("no anima.yaml found. Run `anima init` first (it detects Muse Code, Claude Code and Codex).")
        return None
    return Profile(load(path), path)


def state_file(name: str) -> Path:
    return anima_home() / "state" / f"harness-{name}.json"


def read_state(name: str) -> dict:
    try:
        return json.loads(state_file(name).read_text())
    except (OSError, ValueError):
        return {}


def write_state(name: str, data: dict) -> None:
    f = state_file(name)
    f.parent.mkdir(parents=True, exist_ok=True)
    f.write_text(json.dumps(data, sort_keys=True, indent=1) + "\n")


# ----------------------------------------------------------------- checks
def static_checks(ad: Adapter, login=True) -> list[tuple[str, str, str]]:
    """[(check, PASS|FAIL|NOT RUN, detail)] without any model call."""
    rows = []
    b = ad.resolve_bin()
    if not b:
        rows.append(("binary", "NOT RUN", f"{ad.bin or ad.kind} not found on PATH (install it, or `anima harness add {ad.kind} --bin PATH`)"))
        return rows
    rows.append(("binary", "PASS", b))
    v = ad.version()
    rows.append(("version", "PASS" if v else "FAIL", v or "`--version` gave no answer"))
    missing = ad.check_flags()
    rows.append(("headless flags", "FAIL" if missing else "PASS",
                 ("this CLI no longer shows: " + ", ".join(missing)) if missing else "all required flags present"))
    if login:
        st = ad.login_state()
        rows.append(("login", {"logged-in": "PASS", "not-logged-in": "NOT RUN"}.get(st, "UNKNOWN"),
                     {"logged-in": "the CLI says it is logged in (only the live test proves the token still works)", "not-logged-in": f"not logged in: log in with the {ad.kind} CLI itself",
                      "unknown": "not checked by the CLI; the live test is the real check"}[st]))
    return rows


def live_check(ad: Adapter, role: str, keep=False) -> tuple[str, str, float, list]:
    """One tiny real call. Returns (PASS|FAIL|NOT RUN, detail, seconds, argv)."""
    tmp = Path(tempfile.mkdtemp(prefix=f"anima-test-{ad.name}-"))
    ws = tmp / "ws"
    ws.mkdir()
    pf = tmp / "prompt.txt"
    if role == "worker":
        pf.write_text("Create a file named hello.txt in the current directory whose entire content is exactly: ANIMA-OK\n"
                      "Then reply with the single word: done\n")
    else:
        (ws / "notes.txt").write_text("alpha-bravo\n")
        pf.write_text("Read notes.txt and reply with one line: PLAN: followed by its content. "
                      "Do NOT create, edit or delete any file.\n")
    before = {p.name: p.read_bytes() for p in ws.iterdir()}
    res = ad.run(role, str(ws), str(pf), str(tmp / "run"), job_id=f"anima-test-{ad.name}",
                 timeout_s=min(ad.timeout_s, 420), watch={"packs": DEFAULT_PACKS, "mode": "enforce"})
    after = {p.name: p.read_bytes() for p in ws.iterdir()}
    if not res.ok:
        status = "NOT RUN" if res.failure_class in ("auth_quota", "not_found", "network") else "FAIL"
        detail = f"{res.failure_class}: {res.error}"
    elif role == "worker":
        f = ws / "hello.txt"
        good = f.exists() and f.read_text().strip() == "ANIMA-OK"
        status, detail = ("PASS", "created hello.txt with the exact text") if good else ("FAIL", "ran but hello.txt is missing or wrong")
    else:
        unchanged = before == after
        said = "alpha-bravo" in (res.summary or "")
        status = "PASS" if unchanged and said else "FAIL"
        detail = ("planned read-only; workspace unchanged" if status == "PASS"
                  else f"read-only broken: {not unchanged}; answer had the file content: {said}")
    if not keep:
        shutil.rmtree(tmp, ignore_errors=True)
    return status, detail, res.wall_seconds, res.argv


def adapter_for_test(name: str, explicit=None) -> tuple[Adapter, Profile | None]:
    prof = open_profile(explicit, need=False)
    if prof and (name in prof.names()):
        return prof.adapter(name, "worker"), prof
    if name in KINDS and name != "custom":
        return make_adapter(name, {"kind": name}), prof
    raise HarnessError(f"unknown harness {name!r}. Known: {', '.join(prof.names()) if prof else '(no profile)'}; "
                       f"add one with `anima harness add {'|'.join(KINDS)}`")


# ----------------------------------------------------------------- commands
def cmd_init(a) -> int:
    found = detect_installed()
    target = Path("anima.yaml") if a.local else anima_home() / "anima.yaml"
    if a.profile:
        target = Path(a.profile)
    out("anima init: looking for coding-agent CLIs on PATH and in ~/.local/bin (it only looks for the program, never at your logins)")
    for k in DETECT_ORDER:
        out(f"  {k:<7} {'found: ' + found[k] if k in found else 'not found'}")
    if target.exists() and not a.force:
        out(f"profile already exists, kept as it is: {target}  (use --force to rewrite it)")
        return 0
    data = build_default(found)
    save(target, data)
    out(f"wrote {target}")
    if not found:
        out("no harness found. Install Muse Code, Claude Code or Codex, then run `anima init --force`, or `anima harness add custom --argv ...`.")
        return 0
    out(f"main harness: {data['harness']}; ladder after a wrong answer: " + (" -> ".join(
        [s["harness"] for s in data["ladder"] if s.get("do") == "run_with"] or ["(none: only one harness found)"])))
    out("next: `anima doctor` (checks each one), `anima harness test " + data["harness"] + "` (one tiny real call)")
    return 0


def cmd_doctor(a) -> int:
    prof = open_profile(a.profile, need=False)
    if prof is None and not a.no_write:
        out("no anima.yaml yet; running `anima init` first")
        cmd_init(argparse.Namespace(local=False, profile=a.profile, force=False))
        prof = open_profile(a.profile, need=False)
    found = detect_installed()
    names = prof.names() if prof else [k for k in DETECT_ORDER if k in found]
    for k in DETECT_ORDER:  # always show the three, Muse first
        if k not in names:
            names.append(k)
    out(f"anima doctor  (profile: {prof.path if prof else 'none'})")
    worst = 0
    for name in names:
        in_prof = prof is not None and name in prof.names()
        try:
            ad = prof.adapter(name, "worker") if in_prof else make_adapter(name, {"kind": name})
        except HarnessError as exc:
            out(f"  {name:<8} NOT RUN: {exc}")
            continue
        rows = static_checks(ad)
        bad = [r for r in rows if r[1] in ("FAIL", "NOT RUN")]
        recorded = read_state(name)
        live = None
        if a.live and not bad:
            for role in ("worker", "architect"):
                st, detail, secs, _ = live_check(ad, role)
                live = (live or {})
                live[role] = {"status": st, "detail": detail, "seconds": round(secs, 1)}
            write_state(name, {"when": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()), "live": live})
            recorded = read_state(name)
        label = doctor_label(bool(bad), recorded)
        if (bad and bad[0][1] == "FAIL") or label.startswith("FAIL"):
            worst = 1
        out(f"  {name:<8} {label}" + ("" if in_prof else "   [not in profile: `anima harness add " + name + "`]"))
        for chk, st, detail in rows:
            out(f"      {chk:<15} {st:<8} {detail}")
        if recorded.get("live"):
            for role, v in recorded["live"].items():
                out(f"      live {role:<10} {v['status']:<8} {v['detail']} ({v['seconds']}s)")
    if prof:
        ne = prof.not_enforced()
        out("  profile checks:")
        enf = prof.enforce()
        out(f"      enforce          mode={enf['mode']} via={enf['via']}  (wrapper + process watch for every harness; per-action hook: Claude Code only)")
        out(f"      rules            {', '.join(prof.data.get('rules') or []) or '(none)'}")
        out(f"      declared, NOT enforced yet: " + ("; ".join(ne) if ne else "nothing"))
    return worst


def cmd_harness(a) -> int:
    sub = a.hsub
    if sub == "list":
        prof = open_profile(a.profile, need=False)
        found = detect_installed()
        out("name      kind    role(s)               binary / version / login")
        names = prof.names() if prof else []
        for name in names:
            ad = prof.adapter(name, "worker")
            roles = []
            if prof.main == name:
                roles.append("main")
            for r in ("architect", "worker"):
                if prof.role_harness(r) == name:
                    roles.append(r)
            b, v = ad.resolve_bin(), (ad.version() if ad.resolve_bin() else None)
            login = ad.login_state() if (b and not a.fast) else "-"
            out(f"{name:<9} {ad.kind:<7} {','.join(roles) or '-':<21} {b or 'NOT FOUND'} / {v or '-'} / login: {login}")
        for k in DETECT_ORDER:
            if k not in names and k in found:
                out(f"{k:<9} {k:<7} {'-':<21} {found[k]}  (found, not in profile: `anima harness add {k}`)")
        if not names and not found:
            out("(none found) install Muse Code, Claude Code or Codex, or `anima harness add custom --argv ...`")
        if not prof:
            out("no anima.yaml yet: run `anima init`")
        return 0
    if sub == "add":
        kind = a.kind
        name = a.name or kind
        cfg = {"kind": kind}
        if kind == "custom":
            if not a.argv:
                raise HarnessError("custom needs --argv '[\"mytool\", \"--prompt-file\", \"{prompt_file}\"]' (placeholders: {prompt_file} {workspace} {job_id} {model} {out_file} {role})")
            cfg["argv"] = _json_argv("--argv", a.argv)
            if a.architect_argv:
                cfg["architect_argv"] = _json_argv("--architect-argv", a.architect_argv)
            if a.stdin:
                cfg["stdin"] = a.stdin
            if a.result:
                cfg["result"] = a.result
        else:
            path = a.bin or detect_installed().get(kind)
            if not path:
                raise HarnessError(f"{kind} not found on PATH or in ~/.local/bin. Install it, or pass --bin /full/path/to/{kind}")
            cfg["bin"] = path
        for key in ("model", "effort"):
            if getattr(a, key):
                cfg[key] = getattr(a, key)
        if a.yolo:
            cfg["yolo"] = True
        make_adapter(name, cfg)  # validates templates
        path = find_profile(a.profile) or (anima_home() / "anima.yaml")
        data = load(path) if path.exists() else build_default({})
        hs = data.setdefault("harnesses", {})
        changed = hs.get(name) != cfg
        hs[name] = cfg
        if not data.get("harness"):
            data["harness"] = name
        if changed:
            save(path, data)
        out(f"{'added' if changed else 'already present, unchanged'}: harness {name!r} ({kind}) in {path}")
        for chk, st, detail in static_checks(make_adapter(name, cfg), login=False):
            out(f"  {chk:<15} {st:<8} {detail}")
        out(f"next: `anima harness test {name}`")
        return 0
    if sub == "use":
        prof = open_profile(a.profile)
        for role, val in (("architect", a.architect), ("worker", a.worker)):
            if val:
                if val not in prof.names():
                    raise HarnessError(f"{val!r} is not in the profile; add it first")
                prof.data.setdefault("roles", {}).setdefault(role, {})["harness"] = val
        if a.main:
            if a.main not in prof.names():
                raise HarnessError(f"{a.main!r} is not in the profile; add it first")
            prof.data["harness"] = a.main
        save(prof.path, prof.data)
        out(f"updated {prof.path}: main={prof.main} architect={prof.role_harness('architect')} worker={prof.role_harness('worker')}")
        return 0
    if sub == "test":
        ad, prof = adapter_for_test(a.name, a.profile)
        out(f"anima harness test {a.name}  ({ad.kind})")
        rows = static_checks(ad)
        for chk, st, detail in rows:
            out(f"  {chk:<15} {st:<8} {detail}")
        roles = ["worker", "architect"] if a.role == "both" else [a.role]
        for role in roles:
            out(f"  argv ({role}):    " + " ".join(ad.describe(role)))
        if any(r[1] != "PASS" for r in rows if r[0] in ("binary", "version", "headless flags")):
            out("RESULT NOT RUN: static checks failed, no model call made")
            return EXIT_NOT_RUN
        if any(r[0] == "login" and r[1] == "NOT RUN" for r in rows):
            out("RESULT NOT RUN: not logged in. " + next(r[2] for r in rows if r[0] == "login"))
            return EXIT_NOT_RUN
        if a.dry_run:
            out("RESULT NOT RUN (dry run: command lines shown, no model call made)")
            return EXIT_NOT_RUN
        results = {}
        for role in roles:
            out(f"  live {role}: one tiny real call ...")
            st, detail, secs, _ = live_check(ad, role, keep=a.keep)
            results[role] = {"status": st, "detail": detail, "seconds": round(secs, 1)}
            out(f"  live {role:<9} {st:<8} {detail} ({secs:.0f}s)")
        prior = read_state(a.name).get("live") or {}
        write_state(a.name, {"when": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()), "live": {**prior, **results}})
        statuses = {v["status"] for v in results.values()}
        verdict = "PASS" if statuses == {"PASS"} else ("NOT RUN" if "NOT RUN" in statuses and "FAIL" not in statuses else "FAIL")
        out(f"RESULT {verdict}")
        return 0 if verdict == "PASS" else (EXIT_NOT_RUN if verdict == "NOT RUN" else 1)
    raise HarnessError("usage: anima harness list|add|use|test")


def cmd_run(a) -> int:
    prof = open_profile(a.profile)
    task = load_task(a.task)
    runs_dir = Path(a.runs_dir) if a.runs_dir else anima_home() / "runs"
    if a.role == "architect":
        name = a.harness or prof.role_harness("architect")
        run_dir = runs_dir / f"{time.strftime('%Y%m%dT%H%M%SZ', time.gmtime())}-{task.id}-plan-{uuid.uuid4().hex[:6]}"
        run_dir.mkdir(parents=True, exist_ok=True)
        ch = chainmod.Chain(run_dir / "decisions.jsonl", mode="REAL")
        ch.append("heartbeat", "", status="plan only", for_task=task.id)
        plan, res = architect_plan(prof, name, task, run_dir, ch, out, dry_run=a.dry_run)
        if a.dry_run:
            return EXIT_NOT_RUN
        ch.write_head()
        if plan:
            out("---- plan ----\n" + plan + "\n--------------")
            out(f"PLAN OK  (run dir: {run_dir})")
            return 0
        out(f"PLAN NOT RUN/FAILED: {res.error if res else 'no result'}")
        return EXIT_NOT_RUN
    memory = {"store": a.memory_store, "k": a.memory_k, "exclude_self": a.memory_exclude_self} if a.memory == "trace" else None
    res = run_task(prof, task, runs_dir, harness=a.harness, ladder=a.ladder, plan_first=a.plan_first, dry_run=a.dry_run, say=out,
                   memory=memory)
    if a.dry_run:
        return EXIT_NOT_RUN
    if memory and not a.memory_no_record:
        from .ladder import _memory_cmd, _memory_env
        try:
            r = subprocess.run(_memory_cmd("ingest", str(res.run_dir), "--task", str(task.dir), "--store", a.memory_store),
                               capture_output=True, text=True, timeout=300, env=_memory_env())
            tail = (r.stdout.strip().splitlines() or [""])[-1] if r.returncode == 0 else ((r.stderr or r.stdout).strip().splitlines() or ["failed"])[-1]
            out(f"memory: {'recorded this run -> ' if r.returncode == 0 else 'NOT recorded: '}{tail[:160]}")
        except (OSError, subprocess.SubprocessError) as exc:
            out(f"memory: NOT recorded: {exc}")
    ok, why, n, digest = chainmod.verify(res.chain_path)
    f = res.final
    if res.verdict == "PASS":
        out(f"VERDICT PASS  (task {task.id}; rung {f.rung}, harness {f.harness})")
    elif res.verdict == "FAIL":
        out(f"VERDICT FAIL  (task {task.id}; last rung {f.rung} {f.harness}: rule {f.failed_rule}: {f.digest[:100]})")
    else:
        out(f"VERDICT NOT RUN  (task {task.id}: {f.note if f else 'nothing ran'})")
    out(f"{'CHAIN OK' if ok else 'CHAIN BROKEN'} - {n} records, {why}")
    out(f"run dir: {res.run_dir}")
    return {"PASS": 0, "FAIL": 1}.get(res.verdict, EXIT_NOT_RUN)


def cmd_check(a) -> int:
    packs = packs_for(a.pack or DEFAULT_PACKS)
    if a.hook:
        code, msg = hook_decision(sys.stdin.read(), packs)
        if code and a.mode != "enforce":
            print(f"ANIMA (warn mode, allowed) {msg}", file=sys.stderr)
            return 0
        if msg:
            print(msg, file=sys.stderr)
        return code
    if a.cmd is None:
        raise HarnessError("usage: anima check --cmd '<command line>'   or   --hook (reads Claude Code hook JSON on stdin)")
    v = check_command(a.cmd, packs)
    if v.allowed:
        out("allow")
        return 0
    out(f"block {v.rule}: {v.explain}")
    return 3


def cmd_verify(a) -> int:
    p = Path(a.path) if a.path else None
    if p is None:
        runs = list((anima_home() / "runs").glob("*/decisions.jsonl"))
        if not runs:
            raise HarnessError("no runs yet; pass a decisions.jsonl path")
        p = max(runs, key=lambda r: r.stat().st_mtime)
    if p.is_dir():
        p = p / "decisions.jsonl"
    ok, why, n, digest = chainmod.verify(p)
    out(f"{'CHAIN OK' if ok else 'CHAIN BROKEN'} - {n} records, {why}")
    out(f"  file fingerprint (SHA-256): {digest}")
    out(f"  file: {p}")
    return 0 if ok else 1


# ----------------------------------------------------------------- parser
def build_parser():
    ap = argparse.ArgumentParser(prog="anima", description="ANIMA: plug into the coding agent you already have (Muse Code, Claude Code, Codex).")
    ap.add_argument("--profile", help="path to anima.yaml (default: ./anima.yaml, then ~/.anima/anima.yaml)")
    sub = ap.add_subparsers(dest="command", required=True)
    s = sub.add_parser("init", help="detect Muse Code / Claude Code / Codex and write anima.yaml")
    s.add_argument("--force", action="store_true")
    s.add_argument("--local", action="store_true", help="write ./anima.yaml instead of ~/.anima/anima.yaml")
    s = sub.add_parser("doctor", help="check each harness; prints PASS / READY / NOT RUN honestly")
    s.add_argument("--live", action="store_true", help="also make one tiny real call per role (uses your CLI login)")
    s.add_argument("--no-write", action="store_true")
    h = sub.add_parser("harness", help="list / add / use / test harnesses")
    hs = h.add_subparsers(dest="hsub", required=True)
    hs.add_parser("list").add_argument("--fast", action="store_true", help="skip login checks")
    t = hs.add_parser("add", help="add muse | claude | codex | custom to anima.yaml")
    t.add_argument("kind", choices=KINDS)
    t.add_argument("--name"); t.add_argument("--bin"); t.add_argument("--model"); t.add_argument("--effort")
    t.add_argument("--argv", help="custom: JSON list, e.g. '[\"mytool\",\"--prompt-file\",\"{prompt_file}\"]'")
    t.add_argument("--architect-argv"); t.add_argument("--stdin", choices=["prompt_file"]); t.add_argument("--result", choices=["out_file"])
    t.add_argument("--yolo", action="store_true", help="muse: run without approval or sandbox (what the recorded ladder used; process watch still applies)")
    t = hs.add_parser("use", help="choose which harness plays which role")
    t.add_argument("--main"); t.add_argument("--architect"); t.add_argument("--worker")
    t = hs.add_parser("test", help="static checks, then one tiny real call per role")
    t.add_argument("name")
    t.add_argument("--role", choices=["worker", "architect", "both"], default="worker")
    t.add_argument("--dry-run", action="store_true", help="show the command lines, make no model call")
    t.add_argument("--keep", action="store_true")
    s = sub.add_parser("run", help="run a task through a harness (or the ladder) and judge it with the hidden checker")
    s.add_argument("--task", required=True, help="folder with task.json, a task.json, or a built-in name (tiny-bug)")
    s.add_argument("--harness", help="pin one harness for this run (no escalation unless --ladder)")
    s.add_argument("--role", choices=["worker", "architect"], default="worker", help="architect = read-only plan, no checker")
    s.add_argument("--ladder", action="store_true", help="with --harness: also follow the ladder from anima.yaml")
    s.add_argument("--plan-first", action="store_true", help="ask the architect role for a plan, hand it to the worker")
    s.add_argument("--dry-run", action="store_true", help="print the command lines that would run; start nothing")
    s.add_argument("--runs-dir")
    s.add_argument("--memory", choices=["off", "trace"], default="off",
                   help="trace: put similar past fixes from the local TRACE memory in front of the worker's prompt, and record this run afterwards (see docs/MEMORY.md)")
    s.add_argument("--memory-store", default=".anima/trace", help="memory folder (default .anima/trace)")
    s.add_argument("--memory-k", type=int, default=3, help="how many past jobs to recall")
    s.add_argument("--memory-no-record", action="store_true", help="recall only; do not add this run to the memory")
    s.add_argument("--memory-exclude-self", action="store_true", help="never recall this same task's own earlier jobs (used for the A/B)")
    s = sub.add_parser("check", help="would this command be blocked? (exit 3 = block)")
    s.add_argument("--cmd"); s.add_argument("--hook", action="store_true"); s.add_argument("--pack", action="append")
    s.add_argument("--mode", default="enforce", choices=["warn", "enforce"])
    s = sub.add_parser("verify-log", help="check a decision chain (default: the newest run)")
    s.add_argument("path", nargs="?")
    return ap


def doctor_label(static_bad: bool, recorded: dict) -> str:
    """One word for a harness in `anima doctor`. NOT RUN (could not try: login, network, missing binary) is
    never shown as FAIL; FAIL means a live check ran and gave a wrong result."""
    live = recorded.get("live") or {}
    if static_bad:
        return "NOT RUN"
    if not live:
        return "READY (not live-tested)"
    states = {v["status"] for v in live.values()}
    when = recorded.get("when")
    if "FAIL" in states:
        return f"FAIL (live, {when})"
    if states == {"PASS"}:
        return f"PASS (live, {when})"
    return f"NOT RUN (live, {when})"


def _json_argv(flag: str, text: str) -> list:
    """--argv must be a JSON list of strings; say so plainly instead of a traceback."""
    try:
        val = json.loads(text)
    except ValueError:
        val = None
    if not (isinstance(val, list) and val and all(isinstance(x, str) for x in val)):
        raise HarnessError(f"{flag} must be a JSON list of strings, e.g. {flag} '[\"mytool\", \"--prompt-file\", \"{{prompt_file}}\"]' (got {text!r})")
    return val


def main(argv=None) -> int:
    argv = list(sys.argv[1:] if argv is None else argv)
    known = {"init", "doctor", "harness", "run", "check", "verify-log", "-h", "--help", "--profile"}
    if argv and argv[0] not in known and not argv[0].startswith("-"):
        try:
            mod = importlib.import_module(f"anima.{argv[0].replace('-', '_')}.cli")
        except ModuleNotFoundError:
            print(f"anima: unknown command {argv[0]!r}. Known: init, doctor, harness, run, check, verify-log "
                  f"(other groups appear when installed: anima.<group>.cli)", file=sys.stderr)
            return 64
        return int(mod.main(argv[1:]) or 0)
    a = build_parser().parse_args(argv)
    try:
        return {"init": cmd_init, "doctor": cmd_doctor, "harness": cmd_harness, "run": cmd_run,
                "check": cmd_check, "verify-log": cmd_verify}[a.command](a)
    except HarnessError as exc:
        print(f"anima: {exc}", file=sys.stderr)
        return 2
    except miniyaml.YamlError as exc:
        print(f"anima: bad anima.yaml: {exc}", file=sys.stderr)
        return 2
    except KeyboardInterrupt:
        print("anima: interrupted", file=sys.stderr)
        return 130


if __name__ == "__main__":
    sys.exit(main())
