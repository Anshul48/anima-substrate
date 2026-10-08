"""relcheck step program (S5 vehicle bundle binary; stdlib-only).

Executed by the procedure host, one `proc.exec` invoke per step::

    python3 inputs/relcheck.py --step NAME        (cwd = step scratch)

Inputs (staged by the caller under ``inputs/``):
  relcheck.py  these bytes (executed; hash recorded in proc_begin).
  pins.json    bundle pins (identity maps, suite expects, surface
               minimums, artifact filenames). Static per bundle.
  params.json  per-run params (mode, nonce, run paths, frozen roots,
               bundle sha). Varies per run.

Every step writes its declared outputs to the cwd and exits 0 on
success. Any verification failure is LOUD (stderr + ``ok: false``
output where one was writable + nonzero exit); silence is never
success. No sleeps, no network, no shell: subprocess use is
list-form ``[sys.executable, file]`` for frozen-suite children only.
"""

from __future__ import annotations

import ast
import hashlib
import json
import os
import shutil
import subprocess
import sys
import time
from pathlib import Path

STEP_NAMES = ("identity", "suite-r1", "suite-r2", "suite-r3",
              "compat", "package")

# Outer bound for one suite child. The manifest step timeout (600 s)
# is the host-enforced ceiling; children get slightly less so a hung
# suite fails the step loudly with margin left to finalize.
CHILD_TIMEOUT_S = 580.0


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()


def load_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path: Path, obj: dict) -> None:
    path.write_text(json.dumps(obj, indent=2, sort_keys=True) + "\n",
                    encoding="utf-8")


def copy_frozen(src: Path, dst: Path, ignore_top: list[str]) -> int:
    """Copy a frozen tree to dst, skipping top-level scratch names.

    Returns the copied file count. Refuses symlinks (loud) — a
    symlink in supposedly-frozen bytes is not copied silently.
    """
    ignored = set(ignore_top)
    count = 0
    for root, dirs, files in os.walk(src):
        root_p = Path(root)
        if root_p == src:
            dirs[:] = sorted(d for d in dirs if d not in ignored)
            files = sorted(f for f in files if f not in ignored)
        else:
            dirs.sort()
            files.sort()
        for name in files:
            src_p = root_p / name
            if src_p.is_symlink():
                raise ValueError(f"refusing to copy symlink {src_p}")
            rel = src_p.relative_to(src)
            dst_p = dst / rel
            dst_p.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(src_p, dst_p)
            count += 1
    return count


def run_child(argv: list[str], cwd: Path, timeout_s: float) -> tuple:
    """Run one child (list form, no shell). Returns (rc, out, err, dt).

    A timeout kills the whole process group (SIGKILL class on POSIX;
    child.kill() fallback) and reports rc=-9. Grandchildren that
    outlive the kill are reaped by communicate(); nothing here sleeps
    or polls: one blocking communicate with a timeout.
    """
    cwd = Path(os.path.abspath(cwd))
    env = {"PATH": os.environ.get("PATH", ""),
           "PYTHONDONTWRITEBYTECODE": "1",
           "HOME": str(cwd), "TMPDIR": str(cwd)}
    # Forward the venv override this bundle step received (host manifest
    # env_extra under proc.exec; the caller's export under direct runs):
    # suite children run from scratch copies that lack the relative
    # w1/.venv path, so without the absolute override their SST legs
    # refuse loudly. Forwarded ONLY when non-empty (sst_leg treats a
    # missing var as "use default"; an empty string would poison it).
    venv = os.environ.get("SST_VENV_PY", "")
    if venv.strip():
        env["SST_VENV_PY"] = venv
    child = subprocess.Popen(
        argv, cwd=str(cwd), env=env, stdin=subprocess.DEVNULL,
        stdout=subprocess.PIPE, stderr=subprocess.PIPE,
        start_new_session=True)
    t0 = time.monotonic()
    try:
        out, err = child.communicate(timeout=timeout_s)
    except subprocess.TimeoutExpired:
        try:
            if os.name == "posix":
                import signal
                os.killpg(child.pid, signal.SIGKILL)
            else:  # pragma: no cover - best effort on Windows
                child.kill()
        finally:
            out, err = child.communicate()
        return -9, out or b"", err or b"", timeout_s
    return child.returncode, out or b"", err or b"", \
        time.monotonic() - t0


def parse_unittest_log(data: bytes) -> dict:
    """Parse unittest counts from combined child output.

    unittest writes its summary to stderr; callers concatenate both
    streams. Returns {ran, ok, skipped}. ``ok`` requires the exact
    ``OK`` line (``OK (skipped=N)`` counts, with skipped parsed);
    any ``FAILED`` marker fails.
    """
    text = data.decode("utf-8", errors="replace")
    ran = None
    for line in text.splitlines():
        s = line.strip()
        if s.startswith("Ran ") and " test" in s:
            try:
                ran = int(s.split()[1])
            except (ValueError, IndexError):
                pass
    failed = any(ln.strip().startswith("FAILED")
                 for ln in text.splitlines())
    ok_line = any(ln.strip() == "OK" or
                  (ln.strip().startswith("OK (") and
                   ln.strip().endswith(")"))
                  for ln in text.splitlines())
    skipped = 0
    for ln in text.splitlines():
        s = ln.strip()
        if "skipped=" in s:
            frag = s.split("skipped=", 1)[1]
            num = "".join(ch for ch in frag if ch.isdigit())
            if num:
                skipped = int(num)
    return {"ran": ran, "ok": bool(ok_line) and not failed,
            "skipped": skipped}


def scan_ledger_kinds(root: Path) -> list[str]:
    """Collect entry kinds observed in fresh ledger outputs.

    Globs ``*.jsonl`` under root (suite copies write their run
    ledgers there), parses JSON lines, collects string ``kind``
    values. Malformed lines are skipped, never fatal: this reports
    what was observed; absence is ``[]`` with no verdict weight
    (ledger kinds are reported, not gated — see the compat rule).
    """
    kinds: set[str] = set()
    files = sorted(root.rglob("*.jsonl"))
    for path in files[:200]:
        try:
            text = path.read_text(encoding="utf-8")
        except (OSError, ValueError):
            continue
        for line in text.splitlines()[:50000]:
            line = line.strip()
            if not line:
                continue
            try:
                obj = json.loads(line)
            except ValueError:
                continue
            if isinstance(obj, dict) and isinstance(obj.get("kind"),
                                                   str):
                kinds.add(obj["kind"])
    return sorted(kinds)


# Surface algorithm (CONTRACT — verdict_relcheck.py duplicates it
# exactly; make_vehicle_pins.py imports it from here). Purpose is
# regression detection (same algorithm at pin time and run time),
# not Platonic CLI truth: cli_verbs is the union of (a) string
# literals compared with == against args.op / args.cmd and (b)
# first-argument literals of .add_parser(...) calls; api_functions
# is the sorted top-level def names of api.py. Missing files yield
# [] plus an absent flag (recorded, not fatal).
def cli_verbs_of(release_py: Path) -> list[str]:
    tree = ast.parse(release_py.read_text(encoding="utf-8"))
    verbs: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Compare) and len(node.ops) == 1 \
                and isinstance(node.ops[0], ast.Eq):
            sides = [node.left, *node.comparators]
            for attr_side, lit_side in (sides, sides[::-1]):
                if isinstance(attr_side, ast.Attribute) \
                        and attr_side.attr in ("op", "cmd") \
                        and isinstance(lit_side, ast.Constant) \
                        and isinstance(lit_side.value, str):
                    verbs.add(lit_side.value)
        elif isinstance(node, ast.Call) \
                and isinstance(node.func, ast.Attribute) \
                and node.func.attr == "add_parser" and node.args \
                and isinstance(node.args[0], ast.Constant) \
                and isinstance(node.args[0].value, str):
            verbs.add(node.args[0].value)
    return sorted(verbs)


def api_functions_of(api_py: Path) -> list[str]:
    tree = ast.parse(api_py.read_text(encoding="utf-8"))
    return sorted(n.name for n in tree.body
                  if isinstance(n, ast.FunctionDef))


def surface_of(tree_dir: Path) -> dict:
    rel = tree_dir / "release.py"
    api = tree_dir / "api.py"
    if rel.is_file() and not rel.is_symlink():
        verbs: list[str] = cli_verbs_of(rel)
        rel_present = True
    else:
        verbs = []
        rel_present = False
    if api.is_file() and not api.is_symlink():
        funcs: list[str] = api_functions_of(api)
        api_present = True
    else:
        funcs = []
        api_present = False
    return {"cli_verbs": verbs, "api_functions": funcs,
            "release_present": rel_present,
            "api_present": api_present}


def verdict_rule(ident_ok: bool, suites_ok: bool,
                 surface_ok: bool) -> str:
    """Frozen ACCEPT/PARTIAL/FAIL mapping (checker duplicates it)."""
    if ident_ok and suites_ok and surface_ok:
        return "ACCEPT"
    if ident_ok and suites_ok:
        return "PARTIAL"
    return "FAIL"


def _verify_against(base: Path, expected: dict[str, str]) -> list[str]:
    """Hash every pinned relpath under base. Returns bad-rel list."""
    bad = []
    for rel, want in sorted(expected.items()):
        path = base / rel
        if path.is_symlink() or not path.is_file():
            bad.append(f"{rel}: missing")
        elif sha256_file(path) != want:
            bad.append(f"{rel}: mismatch")
    return bad


def _find_extras(base: Path, expected: dict[str, str]) -> list[str]:
    """Every file under base must be pinned. Returns extra-rel list."""
    extras = []
    for path in sorted(base.rglob("*")):
        if path.is_dir():
            continue
        rel = path.relative_to(base).as_posix()
        if path.is_symlink():
            extras.append(f"{rel}: symlink")
        elif rel not in expected:
            extras.append(rel)
    return extras


def step_identity(pins: dict, params: dict, pins_sha: str) -> int:
    """Verify frozen identities + scratch copies. Loud on mismatch."""
    ignore_top = pins["ignore_top"]
    tags: dict = {}
    all_ok = True
    for tag in sorted(pins["identity"]):
        expected = pins["identity"][tag]
        frozen = Path(params["frozen"][tag])
        copied = Path(f"frozen-{tag}")
        try:
            n_files = copy_frozen(frozen, copied, ignore_top)
        except (OSError, ValueError) as exc:
            print(f"identity {tag}: copy refused: {exc}",
                  file=sys.stderr)
            tags[tag] = {"files": 0, "match": False,
                         "error": f"copy refused: {exc}"}
            all_ok = False
            continue
        frozen_bad = _verify_against(frozen, expected)
        copy_bad = _verify_against(copied, expected)
        extras = _find_extras(copied, expected)
        ok = not frozen_bad and not copy_bad and not extras
        all_ok = all_ok and ok
        tags[tag] = {"files": len(expected), "copied_files": n_files,
                     "match": ok, "frozen_bad": frozen_bad,
                     "copy_bad": copy_bad, "extras": extras}
        print(f"identity {tag}: files={len(expected)} "
              f"match={ok}", flush=True)
    out = {"pins_sha256": pins_sha, "tags": tags, "ok": all_ok}
    write_json(Path("IDENTITY-RESULT.json"), out)
    if not all_ok:
        print("identity: MISMATCH (see IDENTITY-RESULT.json)",
              file=sys.stderr)
        return 1
    return 0


def run_suite_program(copy: Path, spec: dict, pins: dict) -> dict:
    """Run one pinned suite program fresh on a scratch copy.

    Expects, when present in the spec, must match; when absent
    (pin generation), ok means rc 0 + parsed-OK (+ demo marker).
    """
    argv = [sys.executable, spec["file"]]
    if spec["kind"] == "demo":
        argv += spec.get("args", [])
    rc, out, err, dt = run_child(argv, copy, CHILD_TIMEOUT_S)
    combined = (b"=== stdout ===\n" + out + b"\n=== stderr ===\n"
                + err + b"\n")
    Path(spec["log"]).write_bytes(combined)
    rec: dict = {"file": spec["file"], "kind": spec["kind"],
                 "rc": rc, "elapsed_s": round(dt, 3),
                 "log": spec["log"],
                 "log_sha256": hashlib.sha256(combined).hexdigest(),
                 "log_bytes": len(combined)}
    if spec["kind"] == "unittest":
        parsed = parse_unittest_log(combined)
        rec.update(parsed)
        exp_t, exp_s = spec.get("expect_tests"), \
            spec.get("expect_skipped")
        rec["ok"] = (rc == 0 and parsed["ok"]
                     and (exp_t is None or parsed["ran"] == exp_t)
                     and (exp_s is None
                          or parsed["skipped"] == exp_s))
    else:
        text = combined.decode("utf-8", errors="replace")
        marker = pins["demo_marker"]
        rec["marker_found"] = marker in text
        rec["ok"] = rc == 0 and marker in text
    return rec


def step_suite(suite_tag: str, pins: dict, params: dict,
               pins_sha: str) -> int:
    """Freshly re-execute one release's pinned suites. Loud on fail."""
    spec = pins["suites"][suite_tag]
    tree = Path(params["frozen"][spec["tree"]])
    copy = Path(f"suite-{suite_tag}")
    try:
        copy_frozen(tree, copy, pins["ignore_top"])
    except (OSError, ValueError) as exc:
        print(f"{suite_tag}: copy refused: {exc}", file=sys.stderr)
        return 1
    results = []
    for prog in spec["programs"]:
        rec = run_suite_program(copy, prog, pins)
        results.append(rec)
        print(f"{suite_tag} {prog['file']}: rc={rec['rc']} "
              f"ok={rec['ok']} elapsed={rec['elapsed_s']}s",
              flush=True)
    kinds = scan_ledger_kinds(copy)
    ok = all(r["ok"] for r in results)
    out = {"pins_sha256": pins_sha, "suite": suite_tag,
           "tree": spec["tree"], "results": results,
           "ledger_kinds": kinds, "ok": ok}
    summary_name = pins["artifacts"][f"suite-{suite_tag}"][0]
    write_json(Path(summary_name), out)
    if not ok:
        print(f"{suite_tag}: SUITE FAILURE (see {summary_name})",
              file=sys.stderr)
        return 1
    return 0


def step_compat(pins: dict, params: dict, pins_sha: str) -> int:
    """Emit COMPAT-REPORT.json from collected step artifacts.

    Reads (never writes) the run artifact store via the absolute
    params path. Always exits 0 once the report is written — even a
    FAIL verdict is a successfully reported verdict; the checker,
    not this step, is the decider. Missing/corrupt inputs refuse
    loudly (exit 1).
    """
    artifacts = Path(params["artifacts_dir"])
    art = pins["artifacts"]
    try:
        ident = load_json(artifacts / "identity" / art["identity"][0])
        suites = {}
        for stag in ("r1", "r2", "r3"):
            suites[stag] = load_json(
                artifacts / f"suite-{stag}" / art[f"suite-{stag}"][0])
    except (OSError, ValueError) as exc:
        print(f"compat: cannot read step artifacts: {exc}",
              file=sys.stderr)
        return 1
    surface: dict = {}
    surface_ok = True
    for stag in ("r1", "r2", "r3"):
        tree = Path(params["frozen"][pins["surface_trees"][stag]])
        try:
            observed = surface_of(tree)
        except (OSError, ValueError) as exc:
            print(f"compat: surface read refused for {stag}: {exc}",
                  file=sys.stderr)
            return 1
        minimum = pins["surface_min"][stag]
        verbs_ok = set(minimum["cli_verbs"]) <= set(
            observed["cli_verbs"])
        funcs_ok = set(minimum["api_functions"]) <= set(
            observed["api_functions"])
        ok = verbs_ok and funcs_ok
        surface_ok = surface_ok and ok
        surface[stag] = {
            "tree": pins["surface_trees"][stag],
            "cli_verbs": observed["cli_verbs"],
            "api_functions": observed["api_functions"],
            "release_present": observed["release_present"],
            "api_present": observed["api_present"],
            "ledger_kinds": suites[stag].get("ledger_kinds", []),
            "minimum_ok": ok, "verbs_ok": verbs_ok,
            "funcs_ok": funcs_ok}
    ident_ok = bool(ident.get("ok"))
    suites_ok = all(s.get("ok") for s in suites.values())
    verdict = verdict_rule(ident_ok, suites_ok, surface_ok)
    out = {"pins_sha256": pins_sha,
           "identities": {t: {"match": v.get("match"),
                              "files": v.get("files")}
                          for t, v in ident.get("tags", {}).items()},
           "suites": {t: {"ok": s.get("ok"),
                          "results": [
                              {"file": r.get("file"),
                               "rc": r.get("rc"),
                               "ran": r.get("ran"),
                               "skipped": r.get("skipped"),
                               "ok": r.get("ok")}
                              for r in s.get("results", [])]}
                      for t, s in suites.items()},
           "surface": surface, "verdict": verdict}
    write_json(Path("COMPAT-REPORT.json"), out)
    print(f"compat: verdict={verdict}", flush=True)
    return 0


def step_package(pins: dict, params: dict, pins_sha: str) -> int:
    """Relocate the verdict: single-file RELCHECK-REPORT.json.

    Re-hashes every collected artifact file itself (never trusting
    RESULT claims — skew refuses loudly) and embeds the compat
    report. This is the deliverable step: its declared output is the
    file the checker validates and the lane files.
    """
    artifacts = Path(params["artifacts_dir"])
    try:
        compat = load_json(artifacts / "compat" / "COMPAT-REPORT.json")
    except (OSError, ValueError) as exc:
        print(f"package: cannot read compat report: {exc}",
              file=sys.stderr)
        return 1
    if compat.get("verdict") not in ("ACCEPT", "PARTIAL", "FAIL"):
        print("package: compat verdict missing/corrupt",
              file=sys.stderr)
        return 1
    manifest = []
    for step in pins["steps"]:
        if step == "package":
            continue
        step_dir = artifacts / step
        result_path = step_dir / "RESULT.json"
        try:
            result = load_json(result_path)
        except (OSError, ValueError) as exc:
            print(f"package: cannot read {step}/RESULT.json: {exc}",
                  file=sys.stderr)
            return 1
        claimed = {a["relpath"]: a for a in result.get("artifacts",
                                                       [])}
        for name in pins["artifacts"][step]:
            path = step_dir / name
            if path.is_symlink() or not path.is_file():
                print(f"package: {step}/{name} missing",
                      file=sys.stderr)
                return 1
            data = path.read_bytes()
            entry = {"step": step, "relpath": name,
                     "sha256": hashlib.sha256(data).hexdigest(),
                     "bytes": len(data)}
            want = claimed.get(name)
            if want is None or want.get("sha256") != entry["sha256"] \
                    or want.get("bytes") != entry["bytes"]:
                print(f"package: {step}/{name} skews vs RESULT "
                      f"claim (refusing)", file=sys.stderr)
                return 1
            manifest.append(entry)
    out = {"vehicle": "relcheck", "vehicle_version": 1,
           "verdict": compat["verdict"], "nonce": params["nonce"],
           "run_id": params["run_id"], "mode": params["mode"],
           "bundle_sha256": params["bundle_sha256"],
           "pins_sha256": pins_sha,
           "compat": compat, "artifacts": manifest}
    write_json(Path("RELCHECK-REPORT.json"), out)
    print(f"package: relocated verdict={compat['verdict']} "
          f"artifacts={len(manifest)}", flush=True)
    return 0


def main(argv: list[str]) -> int:
    if len(argv) != 3 or argv[1] != "--step" \
            or argv[2] not in STEP_NAMES:
        print(f"usage: relcheck.py --step "
              f"{{{'|'.join(STEP_NAMES)}}}", file=sys.stderr)
        return 2
    step = argv[2]
    try:
        pins_raw = Path("inputs/pins.json").read_bytes()
        pins = json.loads(pins_raw.decode("utf-8"))
        params = load_json(Path("inputs/params.json"))
    except (OSError, ValueError) as exc:
        print(f"{step}: cannot load inputs: {exc}", file=sys.stderr)
        return 1
    pins_sha = hashlib.sha256(pins_raw).hexdigest()
    try:
        if step == "identity":
            return step_identity(pins, params, pins_sha)
        if step.startswith("suite-"):
            return step_suite(step[len("suite-"):], pins, params,
                              pins_sha)
        if step == "compat":
            return step_compat(pins, params, pins_sha)
        return step_package(pins, params, pins_sha)
    except Exception as exc:  # loud failure, never silent
        import traceback
        traceback.print_exc()
        print(f"{step}: INTERNAL FAILURE: {type(exc).__name__}: "
              f"{exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main(sys.argv))
