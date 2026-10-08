"""S5-A12 lane-owned tamper legs (independent byte-flip sites).

Against a clean readiness host run (--root under lane scratch):
  T0 clean control -> RELCHECK-VALID, rc=0
  T1 frozen-bytes tamper (own site: s004 release.py, 1 byte, in a
     scratch copy; pins copy re-points that tree) -> INVALID naming
     the identity axis
  T2 suite-log tamper (own site: suite-r2 log byte, artifacts copy)
     -> INVALID naming the artifact axis
  T3 ledger argv-skew (own step: compat proc_begin, ledger copy)
     -> INVALID naming the ledger axis
  T4a report verdict flip (ACCEPT->FAIL, report copy) -> INVALID
     naming the verdict-rule axis
  T4b report bundle-sha flip (report copy) -> INVALID naming the
     bundle-binding axis

Usage: lane_tamper.py <readiness-root>
All mutations hit lane-scratch copies; frozen trees and the original
run outputs are never touched. stdlib-only. Exit 0 iff the control
is VALID and every tamper leg refuses (rc=1) with its axis named.
"""
from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
from pathlib import Path

LANE = Path(__file__).resolve().parent
SCRATCH = LANE / "scratch" / "lane-tamper"
S005 = (Path(__file__).resolve().parents[3] / "prototype"
        / "successor-005")
CHECKER = S005 / "vehicle" / "verdict_relcheck.py"
PINS = S005 / "vehicle" / "relcheck-pins.json"


def run_checker(report: Path, ledger: Path, artifacts: Path,
                pins: Path) -> tuple[int, str]:
    env = dict(os.environ)
    env["PYTHONDONTWRITEBYTECODE"] = "1"
    proc = subprocess.run(
        [sys.executable, str(CHECKER), str(report), str(ledger),
         str(artifacts), str(pins)],
        cwd=str(S005), env=env, stdout=subprocess.PIPE,
        stderr=subprocess.PIPE, text=True)
    return proc.returncode, proc.stdout.strip()


def flip_one_byte(path: Path) -> None:
    data = bytearray(path.read_bytes())
    assert len(data) > 64, path
    data[17] ^= 0x01
    path.write_bytes(bytes(data))


def main() -> int:
    root = Path(sys.argv[1])
    key = "s5a10readiness"
    report = root / "artifacts" / f"proc-{key}" / "package" \
        / "RELCHECK-REPORT.json"
    ledger = root / "ledger.jsonl"
    artifacts = root / "artifacts" / f"proc-{key}"
    for p in (report, ledger, artifacts):
        assert p.exists(), p
    if SCRATCH.exists():
        shutil.rmtree(SCRATCH)
    SCRATCH.mkdir(parents=True)

    # T0: clean control
    rc, line = run_checker(report, ledger, artifacts, PINS)
    print(f"T0 clean control: rc={rc} line={line!r}", flush=True)
    assert rc == 0 and line == "RELCHECK-VALID", (rc, line)

    # T1: frozen-bytes tamper at an own site (s004 release.py)
    pins = json.loads(PINS.read_text(encoding="utf-8"))
    frozen_s004 = Path(pins["frozen"]["s004"])
    copy_s004 = SCRATCH / "s004tampered"
    shutil.copytree(frozen_s004, copy_s004, symlinks=True)
    target = copy_s004 / "release.py"
    target.chmod(0o644)
    flip_one_byte(target)
    pins_copy = dict(pins)
    frozen_copy = dict(pins["frozen"])
    frozen_copy["s004"] = str(copy_s004)
    pins_copy["frozen"] = frozen_copy
    pins_t1 = SCRATCH / "pins-t1.json"
    pins_t1.write_text(json.dumps(pins_copy, indent=2, sort_keys=True))
    rc, line = run_checker(report, ledger, artifacts, pins_t1)
    print(f"T1 frozen tamper: rc={rc} line={line!r}", flush=True)
    assert rc == 1 and line.startswith("RELCHECK-INVALID: "), line
    assert "identity" in line and "release.py" in line, line

    # T2: suite-log tamper at an own site (suite-r2 first log).
    # Keep the proc-<key> basename: the checker derives the ledger
    # idem_key from it, and a renamed dir refuses on naming instead
    # of reaching the artifact-skew leg.
    art_t2 = SCRATCH / "proc-s5a10readiness"
    shutil.copytree(artifacts, art_t2, symlinks=True)
    suite_logs = sorted((art_t2 / "suite-r2").glob("*.log"))
    assert suite_logs, "no suite-r2 logs"
    flip_one_byte(suite_logs[0])
    rc, line = run_checker(report, ledger, art_t2, PINS)
    print(f"T2 suite-log tamper: rc={rc} line={line!r}", flush=True)
    assert rc == 1 and line.startswith("RELCHECK-INVALID: "), line
    assert "suite-r2" in line and "skews" in line, line

    # T3: ledger argv-skew at an own step (compat proc_begin)
    ledger_t3 = SCRATCH / "ledger-t3.jsonl"
    lines = (ledger.read_text(encoding="utf-8")).splitlines(keepends=True)
    skewed = False
    out = []
    for ln in lines:
        if ln.strip():
            obj = json.loads(ln)
            if obj.get("kind") == "proc_begin" \
                    and obj.get("payload", {}).get("step") == "compat":
                obj["payload"]["argv_sha256"] = "0" * 64
                skewed = True
                ln = json.dumps(obj, sort_keys=True) + "\n"
        out.append(ln)
    assert skewed, "no compat proc_begin found"
    ledger_t3.write_text("".join(out), encoding="utf-8")
    rc, line = run_checker(report, ledger_t3, artifacts, PINS)
    print(f"T3 ledger argv-skew: rc={rc} line={line!r}", flush=True)
    assert rc == 1 and line.startswith("RELCHECK-INVALID: "), line
    assert "compat" in line and "argv skews" in line, line

    # T4a: report verdict flip (ACCEPT -> FAIL, both verdict fields)
    rep = json.loads(report.read_text(encoding="utf-8"))
    assert rep["verdict"] == "ACCEPT", rep["verdict"]
    rep["verdict"] = "FAIL"
    rep["compat"]["verdict"] = "FAIL"
    report_t4a = SCRATCH / "report-t4a.json"
    report_t4a.write_text(json.dumps(rep, indent=2, sort_keys=True))
    rc, line = run_checker(report_t4a, ledger, artifacts, PINS)
    print(f"T4a verdict flip: rc={rc} line={line!r}", flush=True)
    assert rc == 1 and line.startswith("RELCHECK-INVALID: "), line
    assert "verdict rule recomputes ACCEPT" in line, line

    # T4b: report bundle-sha flip
    rep = json.loads(report.read_text(encoding="utf-8"))
    rep["bundle_sha256"] = "f" * 64
    report_t4b = SCRATCH / "report-t4b.json"
    report_t4b.write_text(json.dumps(rep, indent=2, sort_keys=True))
    rc, line = run_checker(report_t4b, ledger, artifacts, PINS)
    print(f"T4b bundle flip: rc={rc} line={line!r}", flush=True)
    assert rc == 1 and line.startswith("RELCHECK-INVALID: "), line
    assert "foreign bundle sha" in line, line

    print("lane tamper: CONTROL VALID + 5/5 TAMPER LEGS REFUSED LOUD")
    return 0


if __name__ == "__main__":
    sys.exit(main())
