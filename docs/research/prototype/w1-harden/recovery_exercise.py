"""Recovery exercise runner: scripted kill-mid-run + failure paths, with evidence.

Two modes:
1. --child --state-dir X --ledger Y
   Run setup + formulate + propose, suspend with pending effects, print
   "READY form=<ref>" (flushed), then sleep. The parent kills this process
   mid-run (SIGKILL) and resumes from the checkpoint + ledger. Stub engine
   pinned for determinism.
2. (default) --evidence-dir D
   Drive all four recovery scenarios with persistent state and copy each
   run's ledger + a summary report into D:
     R1 kill-resume : spawn --child, SIGKILL it, reopen, reattach, resume.
     R2 missing checkpoint : suspend, delete checkpoint, reopen, reattach
        must refuse (raise + deny).
     R3 identity mismatch : suspend, tamper checkpoint world_id, reopen,
        reattach must refuse (raise + deny).
     R4 settle-on-terminal : fund, consume partial, dissolve + retire;
        assert grant_settle markers + zero stranded holdings + replay assert.

Usage: python3 recovery_exercise.py --evidence-dir /tmp/substrate-h1-001/evidence
"""
from __future__ import annotations

import argparse
import json
import os
import shutil
import signal
import subprocess
import sys
import tempfile
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

try:
    from .HOST import Host
    from .contract import ContractViolation, WorldRecord
    from .recovery_lib import (WORKER_ID, ExploreWorld, phase_formulate,
                               phase_propose, resume_to_verdict, setup,
                               successful_invokes, worker_record)
    from .world_explore import StubSearchEngine
except ImportError:  # running from the package dir
    from HOST import Host
    from contract import ContractViolation, WorldRecord
    from recovery_lib import (WORKER_ID, ExploreWorld, phase_formulate,
                              phase_propose, resume_to_verdict, setup,
                              successful_invokes, worker_record)
    from world_explore import StubSearchEngine

ROOT_HOLDINGS = {"max_cost_usd": 10.0, "max_time_s": 600.0, "max_invocations": 1000}
EXCERPT_KINDS = ("host_init", "host_reopen", "checkpoint", "reattach",
                 "grant_settle", "grant_return", "invoke", "deny", "lifecycle")


def child_main(state_dir: str, ledger: str) -> int:
    host = Host(state_dir=state_dir, ledger_path=ledger,
                root_holdings=dict(ROOT_HOLDINGS))
    world = setup(host, StubSearchEngine())
    form_ref = phase_formulate(world)
    run = phase_propose(host, world, form_ref)
    assert run["champion_id"], run
    host.suspend(WORKER_ID, "host", reason="exercise kill point",
                 pending_effects=["score", "verdict"])
    print(f"READY form={form_ref}", flush=True)
    time.sleep(120)  # killed mid-run; never returns normally
    return 0


def _excerpt_ledger(ledger: Path, dest: Path) -> list[dict]:
    rows = [json.loads(line) for line in ledger.read_text(encoding="utf-8").splitlines()
            if line.strip()]
    excerpt = [e for e in rows if e.get("kind") in EXCERPT_KINDS]
    dest.write_text("".join(json.dumps(e, sort_keys=True) + "\n" for e in excerpt),
                    encoding="utf-8")
    return rows


def scenario_R1_kill_resume(scratch: Path, evidence: Path) -> dict:
    state_dir = scratch / "R1" / "state"
    ledger = state_dir / "ledger.jsonl"
    proc = subprocess.Popen(
        [sys.executable, str(Path(__file__).resolve()), "--child",
         "--state-dir", str(state_dir), "--ledger", str(ledger)],
        stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
    assert proc.stdout is not None
    line = proc.stdout.readline().strip()
    if not line.startswith("READY "):
        _, stderr = proc.communicate(timeout=60)
        raise RuntimeError(f"child failed before READY: {line} {stderr}")
    form_ref = line.split("form=", 1)[1].split()[0]
    os.kill(proc.pid, signal.SIGKILL)
    rc = proc.wait(timeout=60)
    proc.communicate(timeout=60)
    assert rc not in (None, 0), "child must die by kill, not exit 0"

    host = Host.reopen(state_dir, ledger, records=[worker_record(state_dir)],
                       reason="R1 exercise resume after SIGKILL")
    host.reattach(WORKER_ID, "host", reason="R1 exercise resume")
    world = ExploreWorld(state_dir / WORKER_ID, engine=StubSearchEngine())
    report = resume_to_verdict(host, world)
    assert report["formulation_ref"] == form_ref
    assert report["re_executed_invokes"] == 0
    entries = host.ledger_entries()
    assert len(successful_invokes(entries, "search.propose")) == 1
    assert len(successful_invokes(entries, "search.score")) == 1
    assert host.verify_conservation()["ok"]
    rows = _excerpt_ledger(ledger, evidence / "R1-ledger-excerpt.jsonl")
    summary = {"scenario": "R1 kill-mid-run -> resume-to-verdict",
               "child_returncode": rc, "skipped": report["skipped"],
               "executed": report["executed"],
               "re_executed_invokes": report["re_executed_invokes"],
               "champion_id": report["champion_id"],
               "ledger_entries": len(rows),
               "conservation": "ok", "spend_usd": 0.0}
    (evidence / "R1-summary.json").write_text(
        json.dumps(summary, indent=2, sort_keys=True), encoding="utf-8")
    return summary


def _suspended_pair(scratch: Path, name: str) -> tuple[Path, Path]:
    state_dir = scratch / name / "state"
    ledger = state_dir / "ledger.jsonl"
    host = Host(state_dir=state_dir, ledger_path=ledger,
                root_holdings=dict(ROOT_HOLDINGS))
    world = setup(host, StubSearchEngine())
    phase_propose(host, world, phase_formulate(world))
    host.suspend(WORKER_ID, "host", reason=f"{name} fixture",
                 pending_effects=["score", "verdict"])
    return state_dir, ledger


def scenario_R2_missing_checkpoint(scratch: Path, evidence: Path) -> dict:
    state_dir, ledger = _suspended_pair(scratch, "R2")
    (state_dir / WORKER_ID / "checkpoint.json").unlink()
    host = Host.reopen(state_dir, ledger, records=[worker_record(state_dir)],
                       reason="R2 probe")
    try:
        host.reattach(WORKER_ID, "host", reason="R2 probe")
        raise AssertionError("expected missing-checkpoint refusal")
    except ContractViolation as exc:
        assert "missing checkpoint" in str(exc), exc
    last = host.ledger_entries()[-1]
    assert last["kind"] == "deny" and "missing checkpoint" in last["payload"]["reason"]
    rows = _excerpt_ledger(ledger, evidence / "R2-ledger-excerpt.jsonl")
    summary = {"scenario": "R2 missing-checkpoint reattach refusal",
               "raised": "ContractViolation(missing checkpoint)",
               "ledger_tail": {"kind": last["kind"],
                               "reason": last["payload"]["reason"]},
               "ledger_entries": len(rows)}
    (evidence / "R2-summary.json").write_text(
        json.dumps(summary, indent=2, sort_keys=True), encoding="utf-8")
    return summary


def scenario_R3_identity_mismatch(scratch: Path, evidence: Path) -> dict:
    state_dir, ledger = _suspended_pair(scratch, "R3")
    ckpt_path = state_dir / WORKER_ID / "checkpoint.json"
    ckpt = json.loads(ckpt_path.read_text(encoding="utf-8"))
    ckpt["world_id"] = "R-impostor"
    ckpt_path.write_text(json.dumps(ckpt, indent=2, sort_keys=True), encoding="utf-8")
    host = Host.reopen(state_dir, ledger, records=[worker_record(state_dir)],
                       reason="R3 probe")
    try:
        host.reattach(WORKER_ID, "host", reason="R3 probe")
        raise AssertionError("expected identity-mismatch refusal")
    except ContractViolation as exc:
        assert "checkpoint identity mismatch" in str(exc), exc
    last = host.ledger_entries()[-1]
    assert last["kind"] == "deny" and "identity mismatch" in last["payload"]["reason"]
    rows = _excerpt_ledger(ledger, evidence / "R3-ledger-excerpt.jsonl")
    summary = {"scenario": "R3 checkpoint identity-mismatch refusal",
               "raised": "ContractViolation(checkpoint identity mismatch)",
               "ledger_tail": {"kind": last["kind"],
                               "reason": last["payload"]["reason"]},
               "ledger_entries": len(rows)}
    (evidence / "R3-summary.json").write_text(
        json.dumps(summary, indent=2, sort_keys=True), encoding="utf-8")
    return summary


def scenario_R4_settle_on_terminal(scratch: Path, evidence: Path) -> dict:
    state_dir = scratch / "R4" / "state"
    ledger = state_dir / "ledger.jsonl"
    host = Host(state_dir=state_dir, ledger_path=ledger,
                root_holdings=dict(ROOT_HOLDINGS))
    parent = WorldRecord(world_id="parent", lineage=[], code_ref="t",
                         instance_state_dir=str(state_dir / "parent"),
                         custodians={},
                         authorities=["grant.delegate", "world.create"])
    host.create_world(parent, "host",
                      grant_limits={"max_cost_usd": 4.0, "max_time_s": 200.0,
                                    "max_invocations": 40})
    host.transition("parent", "active", "host", reason="R4 setup")
    child = WorldRecord(world_id="child", lineage=[], code_ref="t",
                        instance_state_dir=str(state_dir / "child"), custodians={})
    host.create_world(child, "parent")
    host.transition("child", "active", "parent", reason="R4 setup")
    host.grant("parent", "child",
               {"max_cost_usd": 1.0, "max_time_s": 60.0, "max_invocations": 10},
               authority=[], grant_id="g-parent-child")
    host.consume("child", cost_usd=0.25, invocations=3, evidence_ref="work")
    host.transition("child", "dissolved", "parent", reason="R4 done")
    host.transition("child", "retired", "host", reason="R4 archived")
    entries = host.ledger_entries()
    settles = [e for e in entries if e["kind"] == "grant_settle"]
    assert len(settles) == 2, len(settles)
    assert all(v == 0 for v in host.holdings["child"].values())
    report = host.verify_conservation()
    assert report["ok"] and "child" in report["settled_terminals"]
    assert all(abs(v) < 1e-9 for v in report["balances"]["child"].values())
    rows = _excerpt_ledger(ledger, evidence / "R4-ledger-excerpt.jsonl")
    summary = {"scenario": "R4 settle-on-terminal, zero stranded holdings",
               "grant_settle_markers": len(settles),
               "child_holdings_final": dict(host.holdings["child"]),
               "child_replay_balance": report["balances"]["child"],
               "ledger_entries": len(rows),
               "conservation": "ok"}
    (evidence / "R4-summary.json").write_text(
        json.dumps(summary, indent=2, sort_keys=True), encoding="utf-8")
    return summary


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--child", action="store_true")
    ap.add_argument("--state-dir", default="")
    ap.add_argument("--ledger", default="")
    ap.add_argument("--evidence-dir", default="")
    args = ap.parse_args()
    if args.child:
        return child_main(args.state_dir, args.ledger)
    evidence = Path(args.evidence_dir) if args.evidence_dir else Path(
        tempfile.mkdtemp(prefix="substrate-h1-evidence-"))
    evidence.mkdir(parents=True, exist_ok=True)
    scratch = evidence / "run-state"
    if scratch.exists():
        shutil.rmtree(scratch)
    scratch.mkdir(parents=True, exist_ok=True)
    summaries = [
        scenario_R1_kill_resume(scratch, evidence),
        scenario_R2_missing_checkpoint(scratch, evidence),
        scenario_R3_identity_mismatch(scratch, evidence),
        scenario_R4_settle_on_terminal(scratch, evidence),
    ]
    (evidence / "ALL-summary.json").write_text(
        json.dumps(summaries, indent=2), encoding="utf-8")
    for s in summaries:
        print(json.dumps(s, sort_keys=True), flush=True)
    print(f"evidence: {evidence}", flush=True)
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except ContractViolation as exc:
        print(f"CONTRACT VIOLATION: {exc}", file=sys.stderr)
        sys.exit(1)
