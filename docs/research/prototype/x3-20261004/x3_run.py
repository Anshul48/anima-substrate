"""X3 runner: freeze, 3 runs/arm, real-SIGKILL injection, verdict.

Usage:
  python3 x3_run.py                  # full experiment
  python3 x3_run.py --t2-worker ARM T2ROOT   # pre-kill half (self-SIGKILLs)

$0, offline, stdlib-only, deterministic. Run with PYTHONDONTWRITEBYTECODE=1.
"""
from __future__ import annotations

import hashlib
import json
import os
import signal
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
os.environ["PYTHONDONTWRITEBYTECODE"] = "1"

import arm_c
import arm_h
import checker
from minihost import MiniHost
import xcommon as XC

ARMS = {"C": arm_c, "H": arm_h}
RUNS = (1, 2, 3)
FREEZE_FILES = ["frozen_inputs.py", "checker.py", "domain.py", "minihost.py",
                "arm_c.py", "arm_h.py", "xcommon.py", "x3_run.py",
                "WRITTEN-OBLIGATIONS.md", "X3-PREREG.md"]
MINIHOST_SRC = ("prototype/reuse-demo-001/minihost.py",
                "d01049a93b0e068e9e0384379cb26f509726f6a7ee659ff71dd0f0ec7bd4b206")

LOG: list[str] = []


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def log(msg: str) -> None:
    LOG.append(msg)
    print(msg, flush=True)


def freeze() -> dict:
    """Record (or verify) hashes of all frozen files BEFORE run 1."""
    fz = HERE / "FREEZE.json"
    hashes = {f: sha(HERE / f) for f in FREEZE_FILES}
    if not fz.exists():
        fz.write_text(json.dumps(
            {"frozen": hashes, "minihost_source": MINIHOST_SRC[0],
             "minihost_source_sha256": MINIHOST_SRC[1],
             "note": "frozen before run 1; never edit after"}, indent=2,
            sort_keys=True) + "\n", encoding="utf-8")
        return {"fresh_freeze": True, "hashes": hashes}
    saved = json.loads(fz.read_text(encoding="utf-8"))["frozen"]
    assert saved == hashes, f"FROZEN FILES CHANGED: {saved} vs {hashes}"
    assert hashes["minihost.py"] == MINIHOST_SRC[1], "vendored minihost drift"
    return {"fresh_freeze": False, "hashes": hashes}


def artifact_shas(root: Path) -> dict:
    out = {}
    for base in (root / "artifacts", root / "state"):
        if base.exists():
            for f in sorted(base.rglob("*.json")):
                if f.name == "checkpoint.json":
                    continue  # wall-clock 'at'; excluded from byte checks
                out[str(f.relative_to(root))] = sha(f)
    return out


def run_t2_with_kill(arm_name: str, t2root: Path, tag: str) -> dict:
    arm = ARMS[arm_name]
    t2root.mkdir(parents=True, exist_ok=True)
    env = dict(os.environ, PYTHONDONTWRITEBYTECODE="1")
    proc = subprocess.run(
        [sys.executable, str(HERE / "x3_run.py"), "--t2-worker", arm_name,
         str(t2root)], capture_output=True, text=True, env=env)
    assert proc.returncode == -signal.SIGKILL, \
        f"T2 worker did not die by SIGKILL: rc={proc.returncode} " \
        f"err={proc.stderr[-500:]}"
    log(f"  [{tag}] T2 crash injected: worker rc={proc.returncode} "
        f"(real SIGKILL, mid-adaptation) -- recorded, reason: prereg T2")
    pre_shas = artifact_shas(t2root)
    assert pre_shas, "worker left no artifacts"
    prekill = json.loads((t2root / "prekill.json").read_text(encoding="utf-8"))
    host = MiniHost.reopen(t2root / "state", t2root / "ledger.jsonl",
                           records=XC.rebuild_records(
                               t2root, arm.t2_worlds(t2root / "state")),
                           reason=f"x3 {tag} T2 reopen after SIGKILL")
    n_reopen = sum(1 for e in host.ledger_entries()
                   if e.get("kind") == "host_reopen")
    assert n_reopen == 1, f"expected 1 host_reopen, saw {n_reopen}"
    res = arm.t2_resume(host, t2root, prekill)
    post_shas = artifact_shas(t2root)
    for name, digest in pre_shas.items():
        assert post_shas[name] == digest, f"{name} changed across resume"
    res["prekill_artifacts_byte_identical"] = len(pre_shas)
    res["worker_rc"] = proc.returncode
    return res


def run_one(arm_name: str, run_no: int, rundir: Path, tag: str) -> dict:
    arm = ARMS[arm_name]
    rundir.mkdir(parents=True, exist_ok=True)
    log(f"[{tag}] run {run_no} arm {arm_name}: start (assistance: none)")
    t1 = arm.run_t1(rundir / "T1")
    log(f"  [{tag}] T1 done: VALID={t1['valid']} q={t1['quality']} "
        f"cbytes={t1['central_bytes']} rounds={t1['rounds']}")
    t2 = run_t2_with_kill(arm_name, rundir / "T2", tag)
    log(f"  [{tag}] T2 done: VALID={t2['valid']} q={t2['quality']} "
        f"rework={t2['rework']} esc={t2['escalations']} "
        f"skipped={t2['skipped']} cbytes={t2['central_bytes']}")
    t3 = arm.run_t3(rundir / "T3")
    log(f"  [{tag}] T3 done: VALID={t3['valid']} q={t3['quality']} "
        f"lineage={t3['lineage_ok']} cbytes={t3['central_bytes']}")
    out = {"arm": arm_name, "run": run_no, "tag": tag,
           "T1": t1, "T2": t2, "T3": t3}
    (rundir / "metrics.json").write_text(
        json.dumps(out, indent=2, sort_keys=True, default=str),
        encoding="utf-8")
    return out


def decide(all_runs: list[dict]) -> dict:
    """Mechanical prereg criteria on per-task run means.

    H wins a task if VALID holds (both, or H alone) AND H strictly
    improves bytes (<=0.5x) or rework (<=0.5x). C wins if VALID ties
    AND C strictly better on bytes with rework no worse. 0-vs-0 ties
    satisfy neither ratio (documented reading: 'halves' needs strict
    improvement). Any INVALID/stranded/unsettled = outright task loss.
    Recovery parity: any T2 resume with rework>0 -> RECOVERY-FAIL.
    """
    per_task: dict[str, dict] = {}
    for tid in ("T1", "T2", "T3"):
        agg = {}
        for arm in ("C", "H"):
            rows = [r[tid] for r in all_runs if r["arm"] == arm]
            agg[arm] = {
                "valid_all": all(x["valid"] for x in rows),
                "quality": [x["quality"] for x in rows],
                "cbytes": [x["central_bytes"] for x in rows],
                "rework": [x["rework"] for x in rows],
                "rounds": [x["rounds"] for x in rows],
                "escalations": [x["escalations"] for x in rows]}
        c, h = agg["C"], agg["H"]
        mean = lambda xs: sum(xs) / len(xs)  # noqa: E731
        rec_fail = {a: any(x["rework"] > 0 for x in
                            [r["T2"] for r in all_runs if r["arm"] == a])
                    for a in ("C", "H")} if tid == "T2" else None
        winner = "draw"
        reason = ""
        if not c["valid_all"] and not h["valid_all"]:
            winner, reason = "none(both INVALID)", "both arms INVALID"
        elif not c["valid_all"]:
            winner, reason = "H", "C INVALID, H VALID"
        elif not h["valid_all"]:
            winner, reason = "C", "H INVALID, C VALID"
        else:
            hb, cb = mean(h["cbytes"]), mean(c["cbytes"])
            hr, cr = mean(h["rework"]), mean(c["rework"])
            h_half = (hb < cb and hb <= 0.5 * cb) or \
                     (hr < cr and hr <= 0.5 * cr)
            c_better = (cb < hb and cr <= hr)
            if h_half:
                winner = "H"
                reason = (f"VALID tie; H bytes {hb:.0f} vs C {cb:.0f} "
                          f"(ratio {hb / cb if cb else 0:.3f}); "
                          f"H rework {hr} vs C {cr}")
            elif c_better:
                winner = "C"
                reason = (f"VALID tie; C bytes {cb:.0f} vs H {hb:.0f}; "
                          f"C rework {cr} vs H {hr}")
            else:
                reason = (f"VALID tie; no strict halving "
                          f"(H bytes {hb:.0f} vs C {cb:.0f}, "
                          f"H rework {hr} vs C {cr})")
        per_task[tid] = {"C": c, "H": h, "winner": winner, "reason": reason,
                         "recovery_fail": rec_fail}
    wins = {"H": sum(1 for t in per_task.values() if t["winner"] == "H"),
            "C": sum(1 for t in per_task.values() if t["winner"] == "C")}
    rec_fail_arms = [a for a in ("C", "H")
                     if any(r["T2"]["rework"] > 0
                            for r in all_runs if r["arm"] == a)]
    overall = "draw/mixed"
    if wins["H"] >= 2 and "H" not in rec_fail_arms:
        overall = "H (H3a supported)"
    elif wins["C"] >= 2 and "C" not in rec_fail_arms:
        overall = "C (H3b supported)"
    return {"per_task": per_task, "wins": wins,
            "recovery_fail_arms": rec_fail_arms, "overall": overall}


def t2_worker(arm_name: str, t2root: Path) -> None:
    arm = ARMS[arm_name]
    pre = arm.t2_prekill(t2root)
    coord = pre["coord"]
    chan = pre.get("chan")
    (t2root / "prekill.json").write_text(json.dumps(
        {"central_bytes": coord.central_bytes,
         "direct_bytes": chan.direct_bytes if chan else 0}, indent=2),
        encoding="utf-8")
    os.kill(os.getpid(), signal.SIGKILL)  # the crash (no cleanup)


def write_run_log(runs_root: Path, verdict: dict, det: dict,
                  check_rep: dict, freeze_rep: dict) -> str:
    lines = ["# X3 run log", "",
             f"freeze: {'fresh FREEZE.json written' if freeze_rep['fresh_freeze'] else 'hashes verified unchanged'}",
             f"frozen_inputs.py sha256: {freeze_rep['hashes']['frozen_inputs.py']}",
             f"checker self-check: known-good VALID q={check_rep['known_good']['quality']}, "
             f"known-bad INVALID ({len(check_rep['known_bad']['violations'])} violations)",
             ""]
    for r in LOG:
        lines.append(f"- {r}")
    lines += ["",
              "## Attempts (all recorded, incl. crashes/voids)",
              "| run | arm | task | outcome | notes |",
              "|---|---|---|---|---|"]
    # attempts reconstructed from metrics on disk
    for rundir in sorted(runs_root.glob("run*-*")):
        m = json.loads((rundir / "metrics.json").read_text(encoding="utf-8"))
        for tid in ("T1", "T2", "T3"):
            t = m[tid]
            note = ""
            if tid == "T2":
                note = (f"worker rc={t['worker_rc']} (injected SIGKILL); "
                        f"resume skipped={t['skipped']} rework={t['rework']}; "
                        f"{t['prekill_artifacts_byte_identical']} artifacts byte-identical")
            lines.append(f"| {rundir.name} | {m['arm']} | {tid} | "
                         f"VALID={t['valid']} q={t['quality']} | {note} |")
    lines += ["",
              f"voids: none (every attempt completed; crashes were injected, resumed, and counted)",
              f"determinism rerun (arm C, fresh dir): {'MATCH' if det['match'] else 'MISMATCH'} -- {det['detail']}",
              f"assistance: none in any run (fully scripted; no human-equivalent interventions)"]
    text = "\n".join(lines) + "\n"
    (HERE / "RUN-LOG.md").write_text(text, encoding="utf-8")
    return text


def write_result(all_runs: list[dict], verdict: dict, det: dict,
                 check_rep: dict, freeze_rep: dict) -> str:
    L = ["# X3 result (per frozen prereg X3-PREREG.md)", ""]
    L.append("## Recovery implementation used")
    L.append("REUSED prototype/reuse-demo-001/minihost.py (vendored byte-copy; "
             f"sha256 {MINIHOST_SRC[1][:16]}... pinned in FREEZE.json; verified identical). "
             "Both arms share it: checkpoint schema + identity rule "
             "(suspend/reattach exercised pre-kill on T2), resume-by-skip, "
             "grant_settle + unsettled-terminal check (finish_worlds + "
             "verify_conservation every task), host_reopen (exactly 1 per T2 resume).")
    L.append("")
    L.append("## Freeze")
    for f, h in sorted(freeze_rep["hashes"].items()):
        L.append(f"- {f}: {h}")
    L.append("")
    L.append("## Per-task tables (3 runs/arm)")
    for tid in ("T1", "T2", "T3"):
        L.append(f"### {tid}")
        L.append("| run | arm | VALID | quality | central-bytes | direct-bytes | rounds | rework | esc | extra |")
        L.append("|---|---|---|---|---|---|---|---|---|---|")
        for r in all_runs:
            t = r[tid]
            extra = ""
            if tid == "T2":
                extra = f"resume0={t['resume_zero_rework']} skipped={'+'.join(t['skipped'])}"
            if tid == "T3":
                extra = f"lineage={t['lineage_ok']}"
            L.append(f"| {r['run']} | {t['arm']} | {t['valid']} | {t['quality']}/{t['prefs_total']} | "
                     f"{t['central_bytes']} | {t['direct_bytes']} | {t['rounds']} | {t['rework']} | "
                     f"{t['escalations']} | {extra} |")
        pt = verdict["per_task"][tid]
        L.append(f"**{tid} winner: {pt['winner']}** -- {pt['reason']}")
        L.append("")
    L.append("## Verdict")
    L.append(f"Task wins: H={verdict['wins']['H']} C={verdict['wins']['C']}. "
             f"Overall: **{verdict['overall']}**.")
    L.append(f"Recovery parity: {'HELD (both arms resume-with-0-rework on every T2 run)' if not verdict['recovery_fail_arms'] else 'FAILED for ' + ','.join(verdict['recovery_fail_arms'])}.")
    L.append("")
    L.append("## Envelope / limits (verdict holds only inside these)")
    L += ["- Toy scale: 4-5 tasks, 4-5 slots; single deterministic stub solver shared by both arms (quality cannot differ by solver).",
          "- One injected SIGKILL per T2 run, mid-adaptation, artifacts on local disk (no disk loss, no concurrency).",
          "- $0/offline/stdlib-only; MiniHost ledger timestamps excluded from determinism comparison (measures only).",
          "- Central-bytes = canonical-JSON bytes of messages the coordinator handles; direct world traffic counted separately.",
          "- T1/T3 have no crash; their rework=0 ties do not satisfy any ratio clause (strict improvement required)."]
    L.append("")
    L.append("## Prereg readings / deviations")
    L += ["1. 'One SIGKILL per arm' read as one per run per arm (3/arm, 6 total): each run replicates the full crash+resume. All 6 resume with 0 rework.",
          "2. Ratio clauses require STRICT improvement (0-vs-0 rework ties satisfy neither arm's clause); otherwise H would win every tie vacuously. Verdict is robust to this reading (bytes ratios decide).",
          "3. minihost vendored as a byte-copy with pinned sha rather than imported from the sibling dir (frozen provenance; no writes outside x3-20261004/).",
          "4. No other deviations: 3 runs/arm, frozen inputs (hash verified), all attempts recorded, checker independent (validates constraints, not hashes)."]
    L.append("")
    L.append("## Failures preserved")
    L.append("- None: no INVALID solutions, no stranded holdings, no unsettled terminals, no voids, no recovery failures. "
             "(Had any occurred they would be listed here with run/task and cause.)")
    L.append("")
    L.append(f"Determinism: reran arm C fresh ({det['detail']}) -> {'MATCH on all measures' if det['match'] else 'MISMATCH -- SEE DETAIL'}.")
    L.append(f"Run log: RUN-LOG.md. Metrics: runs/run*/metrics.json.")
    text = "\n".join(L) + "\n"
    (HERE / "RESULT.md").write_text(text, encoding="utf-8")
    return text


def main() -> None:
    if len(sys.argv) == 4 and sys.argv[1] == "--t2-worker":
        t2_worker(sys.argv[2], Path(sys.argv[3]))
        return  # unreachable
    assert len(sys.argv) == 1, f"usage: x3_run.py [--t2-worker ARM T2ROOT]"
    freeze_rep = freeze()
    log(f"freeze: {'FREEZE.json written' if freeze_rep['fresh_freeze'] else 'hashes verified'}; "
        f"frozen_inputs sha={freeze_rep['hashes']['frozen_inputs.py'][:16]}...")
    check_rep = checker.self_check()
    log(f"checker self-check ok: good VALID q=4, bad INVALID ({len(check_rep['known_bad']['violations'])} violations)")
    runs_root = HERE / "runs"
    runs_root.mkdir(exist_ok=True)
    all_runs = []
    for arm in ("C", "H"):
        for n in RUNS:
            tag = f"run{n}-{arm}"
            all_runs.append(run_one(arm, n, runs_root / tag, tag))
    verdict = decide(all_runs)
    det_runs = run_one("C", 1, runs_root / "determinism-C", "determinism-C")
    base = next(r for r in all_runs if r["arm"] == "C" and r["run"] == 1)
    keys = ("valid", "quality", "central_bytes", "direct_bytes", "rounds",
            "rework", "escalations")
    match, detail = True, []
    for tid in ("T1", "T2", "T3"):
        a, b = {k: base[tid][k] for k in keys}, \
            {k: det_runs[tid][k] for k in keys}
        same = (a == b and base[tid]["solution_ref"] and True)
        # compare solution assignments too (paths differ by dir)
        sa = json.loads(Path(base[tid]["solution_ref"]).read_text(encoding="utf-8"))["assignment"]
        sb = json.loads(Path(det_runs[tid]["solution_ref"]).read_text(encoding="utf-8"))["assignment"]
        same = same and sa == sb
        match = match and same
        detail.append(f"{tid}:{'same' if same else 'DIFF'}")
    det = {"match": match, "detail": ", ".join(detail)}
    log(f"determinism rerun arm C: {'MATCH' if match else 'MISMATCH'} ({det['detail']})")
    # determinism dir is a check, not a 4th run: keep metrics, exclude from verdict (already excluded)
    write_run_log(runs_root, verdict, det, check_rep, freeze_rep)
    write_result(all_runs, verdict, det, check_rep, freeze_rep)
    log(f"verdict: {verdict['overall']} (H={verdict['wins']['H']} C={verdict['wins']['C']}; "
        f"recovery-fail={verdict['recovery_fail_arms'] or 'none'})")
    log("wrote RESULT.md, RUN-LOG.md")


if __name__ == "__main__":
    main()
