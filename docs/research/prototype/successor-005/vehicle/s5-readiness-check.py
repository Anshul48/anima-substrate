"""s5-readiness-check.py — THROWAWAY S5-A10 readiness aid (NOT release).

One clean host run of the relcheck bundle + direct baseline + the
§2.3 checker on both + honest-expense gate + bundle hygiene scan +
frozen both-ends re-check. Prints READINESS-PASS/READINESS-FAIL and
exits 0/1. State roots are throwaway (default under /tmp) and
disclosed; NOTHING here runs before its time — this is the S5-A10
readiness the design (§7.2) explicitly permits pre-prereg.

Usage::

    s5-readiness-check.py [--root DIR] [--world W] [--key K]
        [--nonce N] [--run-id R] [--skip-direct]

--skip-direct runs the host arm only (the direct baseline is a
separate S5-A10 conjunct; skipping it cannot PASS readiness — the
flag exists for diagnosing the host arm alone and always reports
FAIL with the skipped conjunct named).
"""

from __future__ import annotations

import ast
import hashlib
import json
import os
import subprocess
import sys
import time
from datetime import UTC, datetime
from pathlib import Path

HERE = Path(__file__).resolve().parent
S005 = HERE.parent

EXPENSE_FLOOR_S = 60.0


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()


def frozen_check(baseline_path: Path, proto_dir: Path,
                 only_tags: dict[str, str]) -> tuple[bool, int, list]:
    """Re-verify frozen bytes vs the in-tree FROZEN-BASELINE.

    only_tags maps vehicle tag -> tree dirname; entries outside
    those trees are skipped (the full-baseline re-check is the
    separate S5-A9 leg). Returns (ok, n_checked, bad_list).
    """
    # Baseline relpaths are prototype/-relative (no prefix).
    wanted = {d for d in only_tags.values()}
    bad, n = [], 0
    for line in baseline_path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line:
            continue
        digest, _, rel = line.partition("  ")
        top = rel.split("/", 1)[0] if "/" in rel else rel
        if top not in wanted:
            continue
        path = proto_dir / rel
        n += 1
        if not path.is_file() or path.is_symlink():
            bad.append(f"{rel}: missing")
        elif sha256_file(path) != digest:
            bad.append(f"{rel}: MISMATCH")
    return (not bad, n, bad)


def scan_bundle_hygiene(bundle_bin: Path) -> tuple[bool, dict]:
    """AST scan: no sleep/burn/network/shell in shipped bundle bytes.

    Forbids: calls to *.sleep* (any receiver), imports of socket /
    urllib* / http* / sched, shell=True, os.system/os.popen. Loops
    are NOT flagged (hashing/copy loops are the work); the manual
    padding review lives in EVIDENCE.md alongside this scan.
    """
    tree = ast.parse(bundle_bin.read_text(encoding="utf-8"))
    hits: list[str] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Call):
            func = node.func
            name = ""
            if isinstance(func, ast.Attribute):
                name = func.attr
            elif isinstance(func, ast.Name):
                name = func.id
            if "sleep" in name:
                hits.append(f"sleep-call: line "
                            f"{getattr(node, 'lineno', '?')}")
            for kw in node.keywords:
                if kw.arg == "shell" and not (
                        isinstance(kw.value, ast.Constant)
                        and kw.value.value is False):
                    hits.append("shell= truthy/non-False: line "
                                f"{getattr(node, 'lineno', '?')}")
            if isinstance(func, ast.Attribute) \
                    and func.attr in ("system", "popen") \
                    and isinstance(func.value, ast.Name) \
                    and func.value.id == "os":
                hits.append(f"os.{func.attr}: line "
                            f"{getattr(node, 'lineno', '?')}")
        elif isinstance(node, ast.Import):
            for alias in node.names:
                top = alias.name.split(".")[0]
                if top in ("socket", "urllib", "http", "sched"):
                    hits.append(f"import {alias.name}: line "
                                f"{getattr(node, 'lineno', '?')}")
        elif isinstance(node, ast.ImportFrom) and node.module:
            top = node.module.split(".")[0]
            if top in ("socket", "urllib", "http", "sched"):
                hits.append(f"from-import {node.module}: line "
                            f"{getattr(node, 'lineno', '?')}")
    info = {"calls_scanned": sum(isinstance(n, ast.Call)
                                 for n in ast.walk(tree)),
            "hits": hits}
    return (not hits, info)


def normalize_for_diff(obj):
    """Strip run-varying leaves so host/direct claims can be diffed.

    Dropped: nonce/run_id/mode (differ by construction), elapsed and
    byte/hash leaves (timings embed in logs), at/stamp fields, and
    ledger_kinds (kill-timing-varying; reported, not gated). What
    remains — verdicts, counts, identities, surfaces, ok flags, pins
    and bundle shas — must compare EQUAL: the host may add no
    content beyond accounting.
    """
    drop = {"nonce", "run_id", "mode", "elapsed_s", "elapsed",
            "at", "stamp", "log_sha256", "log_bytes", "sha256",
            "bytes", "log", "stdout_total_bytes",
            "stderr_total_bytes", "ledger_kinds"}
    if isinstance(obj, dict):
        return {k: normalize_for_diff(v) for k, v in obj.items()
                if k not in drop}
    if isinstance(obj, list):
        return [normalize_for_diff(v) for v in obj]
    return obj


def diff_claims(host_report: dict, direct_report: dict) -> list[str]:
    a = normalize_for_diff(host_report)
    b = normalize_for_diff(direct_report)
    diffs: list[str] = []

    def walk(x, y, path: str) -> None:
        if isinstance(x, dict) and isinstance(y, dict):
            for key in sorted(set(x) | set(y)):
                if key not in x:
                    diffs.append(f"{path}.{key}: host-missing")
                elif key not in y:
                    diffs.append(f"{path}.{key}: direct-missing")
                else:
                    walk(x[key], y[key], f"{path}.{key}")
        elif isinstance(x, list) and isinstance(y, list):
            if len(x) != len(y):
                diffs.append(f"{path}: len {len(x)} != {len(y)}")
            for i, (u, v) in enumerate(zip(x, y)):
                walk(u, v, f"{path}[{i}]")
        elif x != y:
            diffs.append(f"{path}: {x!r} != {y!r}")

    walk(a, b, "report")
    return diffs


def run_cmd(argv: list[str], cwd: Path) -> subprocess.CompletedProcess:
    return subprocess.run(
        argv, cwd=str(cwd), stdout=subprocess.PIPE,
        stderr=subprocess.PIPE, text=True)


def main(argv: list[str]) -> int:
    stamp = datetime.now(UTC).strftime("%Y%m%dT%H%M%SZ")
    root = Path(f"/tmp/s5readiness-{stamp}")
    world, key = "RELCHECK", "s5a10readiness"
    nonce, run_id = f"readiness-{stamp}", f"host-{stamp}"
    skip_direct = False
    toks = list(argv[1:])
    while toks:
        tok = toks.pop(0)
        if tok == "--root" and toks:
            root = Path(toks.pop(0))
        elif tok == "--world" and toks:
            world = toks.pop(0)
        elif tok == "--key" and toks:
            key = toks.pop(0)
        elif tok == "--nonce" and toks:
            nonce = toks.pop(0)
        elif tok == "--run-id" and toks:
            run_id = toks.pop(0)
        elif tok == "--skip-direct":
            skip_direct = True
        else:
            print(f"readiness: unknown option {tok}",
                  file=sys.stderr)
            return 2
    root = Path(os.path.abspath(root))
    bundle = HERE / "relcheck"
    pins_file = HERE / "relcheck-pins.json"
    pins = json.loads(pins_file.read_text(encoding="utf-8"))
    proto_dir = S005.parent
    baseline = S005 / "FROZEN-BASELINE.sha256"
    failures: list[str] = []

    def note(ok: bool, label: str) -> None:
        print(f"[{'PASS' if ok else 'FAIL'}] {label}", flush=True)
        if not ok:
            failures.append(label)

    # 1. Frozen both-ends pre-check (vehicle trees only; the
    # full-baseline S5-A9 leg is separate EVIDENCE).
    ok, n, bad = frozen_check(baseline, proto_dir, pins["trees"])
    note(ok, f"frozen-pre: {n} files re-verified "
              f"({'; '.join(bad[:3]) if bad else 'clean'})")
    if not ok:
        print("READINESS-FAIL")
        return 1

    # 2. Bundle hygiene scan (no sleep/burn/network/shell).
    scan_ok, scan_info = scan_bundle_hygiene(
        bundle / "bin" / "relcheck.py")
    note(scan_ok, f"hygiene-scan: {scan_info['calls_scanned']} "
                  f"calls scanned "
                  f"({'; '.join(scan_info['hits'][:3]) if scan_info['hits'] else 'clean'})")
    if not scan_ok:
        print("READINESS-FAIL")
        return 1

    # 3. Advertise + one clean host run.
    sys.path.insert(0, str(S005))
    import api  # noqa: E402
    try:
        created = api.create_proc_world(
            root, world, bundle,
            reason="S5-A10 readiness (throwaway state, disclosed)")
    except ValueError as exc:
        note(False, f"advertise refused: {exc}")
        print("READINESS-FAIL")
        return 1
    note(created["bundle_sha256"] == pins["bundle_sha256"],
         f"advertise: bundle sha matches pins "
         f"({created['bundle_sha256'][:16]}...)")
    params = {"params_format": 1, "mode": "host", "nonce": nonce,
              "run_id": run_id, "idem_key": key,
              "run_root": str(root),
              "artifacts_dir": str(root / "artifacts" / f"proc-{key}"),
              "bundle_sha256": created["bundle_sha256"],
              "frozen": pins["frozen"]}
    inputs = {
        "relcheck.py": (bundle / "bin" / "relcheck.py").read_bytes(),
        "pins.json": (bundle / "pins.json").read_bytes(),
        "params.json": (json.dumps(params, indent=2, sort_keys=True)
                        + "\n").encode("utf-8")}
    t0 = time.monotonic()
    try:
        rep = api.run_procedure(root, world, "relcheck", key, inputs)
    except Exception as exc:
        note(False, f"host run raised {type(exc).__name__}: {exc}")
        print("READINESS-FAIL")
        return 1
    wall = time.monotonic() - t0
    note(len(rep.get("executed", [])) == 6
         and rep.get("skipped") == []
         and rep.get("re_executed_steps") == [],
         f"host run: executed={len(rep.get('executed', []))} "
         f"skipped={len(rep.get('skipped', []))} "
         f"re_executed={len(rep.get('re_executed_steps', []))} "
         f"wall={wall:.1f}s")

    # 4. Checker on the host report.
    report = root / "artifacts" / f"proc-{key}" / "package" \
        / "RELCHECK-REPORT.json"
    ledger = root / "ledger.jsonl"
    artifacts = root / "artifacts" / f"proc-{key}"
    proc = run_cmd([sys.executable, str(HERE / "verdict_relcheck.py"),
                    str(report), str(ledger), str(artifacts),
                    str(pins_file)], S005)
    host_valid = proc.returncode == 0 and proc.stdout.strip() == \
        "RELCHECK-VALID"
    note(host_valid, f"checker(host): {proc.stdout.strip() or proc.returncode} "
                      f"{proc.stderr.strip()[:200]}")
    host_report = json.loads(report.read_text(encoding="utf-8")) \
        if report.is_file() else {}

    # 5. Honest expense gate (measured, never padded).
    note(wall >= EXPENSE_FLOOR_S,
         f"expense: host wall {wall:.1f}s "
         f"(floor {EXPENSE_FLOOR_S:.0f}s, no padding)")

    # 6. Direct baseline from identical bytes + checker.
    direct_report_path = None
    if skip_direct:
        note(False, "direct baseline SKIPPED (--skip-direct)")
    else:
        direct_out = root.parent / (root.name + "-direct")
        proc = run_cmd(
            [sys.executable, str(HERE / "direct_relcheck.py"),
             str(bundle), str(pins_file), str(direct_out),
             "--nonce", f"direct-{nonce}", "--run-id",
             f"direct-{run_id}"], S005)
        note(proc.returncode == 0,
             f"direct run rc={proc.returncode} "
             f"{proc.stderr.strip()[:200]}")
        direct_report_path = direct_out / "artifacts" / "package" \
            / "RELCHECK-REPORT.json"
        proc = run_cmd(
            [sys.executable, str(HERE / "verdict_relcheck.py"),
             str(direct_report_path),
             str(direct_out / "direct-ledger.jsonl"),
             str(direct_out / "artifacts"), str(pins_file),
             "--direct"], S005)
        note(proc.returncode == 0
             and proc.stdout.strip() == "RELCHECK-VALID",
             f"checker(direct): {proc.stdout.strip() or proc.returncode} "
             f"{proc.stderr.strip()[:200]}")

    # 7. Host-vs-direct claims diff (host adds no content).
    if direct_report_path is not None and direct_report_path.is_file() \
            and host_report:
        direct_report = json.loads(
            direct_report_path.read_text(encoding="utf-8"))
        diffs = diff_claims(host_report, direct_report)
        note(not diffs, f"claims-diff: {len(diffs)} differences "
                        f"({'; '.join(diffs[:5]) if diffs else 'identical claims'})")

    # 8. Frozen both-ends post-check.
    ok, n, bad = frozen_check(baseline, proto_dir, pins["trees"])
    note(ok, f"frozen-post: {n} files re-verified "
              f"({'; '.join(bad[:3]) if bad else 'clean'})")

    summary = {"root": str(root), "world": world, "key": key,
               "wall_s": round(wall, 1),
               "failures": failures,
               "verdict": "READINESS-PASS" if not failures
               else "READINESS-FAIL"}
    print(json.dumps(summary, indent=2, sort_keys=True), flush=True)
    print(summary["verdict"])
    return 0 if not failures else 1


if __name__ == "__main__":
    sys.exit(main(sys.argv))
