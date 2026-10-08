"""Reuse demo runner: drive w1-harden resume_to_verdict through MiniHost.

Exit 0 on success; any failed evidence assertion raises (nonzero exit).
Prints a short evidence summary (one line per check).

Child mode: `reuse_demo.py --child-partial <root>` builds a MiniHost,
runs formulate+propose via the REUSED phase functions, then SIGKILLs
itself (a real crash: no cleanup, no flush beyond per-append closes).
The parent asserts the SIGKILL return code, reopens, and resumes.
"""
from __future__ import annotations

import hashlib
import json
import os
import signal
import subprocess
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from minihost import (CONTRACT_VERSION, ContractViolation, MiniCapability,
                      MiniHost, MiniRepresentation, MiniWorld, MiniWorldRecord)
from w1h_bridge import load_recovery_lib

GRANT_LIMITS = {"max_cost_usd": 1.0, "max_time_s": 120.0, "max_invocations": 20}


def worker_record(state_dir: Path, rl) -> MiniWorldRecord:
    """MiniHost-native worker descriptor (setup is host-shaped: rewritten)."""
    return MiniWorldRecord(
        world_id=rl.WORKER_ID, lineage=[("host", "created", "reuse-demo")],
        code_ref=rl.WORKER_CODE_REF,
        instance_state_dir=str(Path(state_dir) / rl.WORKER_ID),
        custodians={},
        capabilities=[MiniCapability("search.propose", "1.0"),
                      MiniCapability("search.score", "1.0")],
        representations=[MiniRepresentation("minihost-run", "v0")],
        authorities=["search.sst"])


def setup_worker(host: MiniHost, rl) -> MiniWorld:
    host.create_world(worker_record(host.state_dir, rl), "host",
                      grant_limits=dict(GRANT_LIMITS))
    host.transition(rl.WORKER_ID, "active", "host", reason="reuse-demo setup")
    return MiniWorld(Path(host.state_dir) / rl.WORKER_ID)


def sha_of(path: str) -> str:
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def invoke_counts(host: MiniHost) -> dict:
    counts: dict[str, int] = {}
    for e in host.ledger_entries():
        if e.get("kind") == "invoke" and "error" not in e.get("payload", {}):
            cap = e["payload"]["capability"]
            counts[cap] = counts.get(cap, 0) + 1
    return counts


def artifact_shas(world: MiniWorld) -> dict:
    out = {}
    for sub in ("formulations", "candidates", "scores", "verdicts"):
        d = Path(world.state_dir) / sub
        if d.exists():
            for f in sorted(d.glob("*.json")):
                out[f.name] = sha_of(str(f))
    return out


def child_partial(root: str) -> None:
    """Run formulate+propose, then die by real SIGKILL (no cleanup)."""
    rl = load_recovery_lib()
    host = MiniHost(Path(root) / "state", Path(root) / "ledger.jsonl")
    world = setup_worker(host, rl)
    form_ref = rl.phase_formulate(world)          # reused w1-harden code
    rl.phase_propose(host, world, form_ref)       # reused w1-harden code
    with open(Path(root) / "child-done.json", "w", encoding="utf-8") as fh:
        json.dump({"formulation_ref": form_ref}, fh)
    os.kill(os.getpid(), signal.SIGKILL)          # the crash


def variant_drop(root: Path, rl, evidence: list) -> MiniHost:
    """Kill variant 1: drop the host object mid-run, reopen, resume."""
    host = MiniHost(root / "state", root / "ledger.jsonl")
    world = setup_worker(host, rl)
    form_ref = rl.phase_formulate(world)
    rl.phase_propose(host, world, form_ref)
    before_shas = artifact_shas(world)
    before_inv = invoke_counts(host)
    del host, world                               # the "kill": memory gone
    host2 = MiniHost.reopen(
        root / "state", root / "ledger.jsonl",
        records=[worker_record(root / "state", rl)], reason="reuse-demo drop")
    world2 = MiniWorld(root / "state" / rl.WORKER_ID)
    report = rl.resume_to_verdict(host2, world2)  # reused w1-harden code
    assert report["re_executed_invokes"] == 0, report
    assert invoke_counts(host2)["search.propose"] == before_inv["search.propose"]
    assert artifact_shas(world2) == {**before_shas,
                                     **{k: v for k, v in artifact_shas(world2).items()
                                        if k not in before_shas}}, "artifacts changed!"
    for name, digest in before_shas.items():
        assert artifact_shas(world2)[name] == digest, f"{name} not byte-identical"
    assert Path(report["verdict_ref"]).exists()
    evidence.append(f"drop-kill resume: skipped={report['skipped']} "
                    f"executed={report['executed']} re_executed_invokes=0; "
                    f"{len(before_shas)} pre-kill artifacts byte-identical")
    return host2


def variant_sigkill(root: Path, rl, evidence: list) -> MiniHost:
    """Kill variant 2: real subprocess SIGKILL mid-run, reopen, resume."""
    if not hasattr(signal, "SIGKILL"):
        evidence.append("sigkill variant: SKIPPED (no SIGKILL on this platform)")
        return variant_drop(root, rl, evidence)
    proc = subprocess.run(
        [sys.executable, str(Path(__file__).resolve()),
         "--child-partial", str(root)],
        capture_output=True, text=True)
    assert proc.returncode == -signal.SIGKILL, \
        f"child did not die by SIGKILL: rc={proc.returncode} err={proc.stderr[-300:]}"
    # Pre-kill artifact bytes, read straight off disk (child is dead):
    wdir = root / "state" / rl.WORKER_ID
    pre = {f.name: sha_of(str(f))
           for sub in ("formulations", "candidates")
           for f in sorted((wdir / sub).glob("*.json"))}
    assert pre, "child left no artifacts"
    host = MiniHost.reopen(
        root / "state", root / "ledger.jsonl",
        records=[worker_record(root / "state", rl)], reason="reuse-demo sigkill")
    world = MiniWorld(wdir)
    report = rl.resume_to_verdict(host, world)
    assert report["re_executed_invokes"] == 0, report
    assert set(report["skipped"]) >= {"formulate", "propose"}, report
    post = artifact_shas(world)
    for name, digest in pre.items():
        assert post[name] == digest, f"{name} not byte-identical after SIGKILL"
    evidence.append(f"SIGKILL resume: child rc={proc.returncode} "
                    f"skipped={report['skipped']} executed={report['executed']} "
                    f"re_executed_invokes=0; {len(pre)} artifacts byte-identical")
    return host


def main() -> None:
    if len(sys.argv) == 3 and sys.argv[1] == "--child-partial":
        child_partial(sys.argv[2])
        return  # unreachable (SIGKILLed)
    rl = load_recovery_lib()
    evidence: list[str] = []
    tmp = Path(tempfile.mkdtemp(prefix="reuse-demo-001-"))

    host = variant_drop(tmp / "drop", rl, evidence)
    host = variant_sigkill(tmp / "sigkill", rl, evidence)

    # Steady-state: a second resume skips everything.
    world = MiniWorld(tmp / "sigkill" / "state" / rl.WORKER_ID)
    again = rl.resume_to_verdict(host, world)
    assert again["executed"] == [] and again["re_executed_invokes"] == 0, again
    evidence.append(f"second resume: executed={again['executed']} "
                    f"(verdict {Path(again['verdict_ref']).name} reused)")

    # Suspend/reattach roundtrip on the worker (checkpoint path works).
    host.suspend(rl.WORKER_ID, "host", "demo suspend",
                 pending_effects=["score", "verdict"])
    ckpt = json.loads((Path(world.state_dir) / "checkpoint.json")
                      .read_text(encoding="utf-8"))
    assert ckpt["contract_version"] == CONTRACT_VERSION
    host.reattach(rl.WORKER_ID, "host", "demo reattach")
    evidence.append("suspend/reattach roundtrip: checkpoint schema + identity ok")

    # Refusal paths on a scratch world (each raising with a recorded deny).
    scratch = MiniWorldRecord(
        world_id="scratch", lineage=[], code_ref="reuse-demo/scratch",
        instance_state_dir=str(tmp / "sigkill" / "state" / "scratch"),
        capabilities=[], representations=[], authorities=[])
    host.create_world(scratch, "host")
    host.transition("scratch", "active", "host", reason="demo")
    host.suspend("scratch", "host", "demo", pending_effects=[])
    ckpt_path = Path(scratch.instance_state_dir) / "checkpoint.json"
    saved = ckpt_path.read_text(encoding="utf-8")
    ckpt_path.unlink()
    try:
        host.reattach("scratch", "host", "demo")
        raise AssertionError("missing checkpoint was NOT refused")
    except ContractViolation as exc:
        assert "missing checkpoint" in str(exc)
    ckpt_path.write_text(saved.replace("reuse-demo/scratch", "evil/fork"),
                         encoding="utf-8")
    try:
        host.reattach("scratch", "host", "demo")
        raise AssertionError("identity mismatch was NOT refused")
    except ContractViolation as exc:
        assert "identity mismatch" in str(exc)
    denies = [e for e in host.ledger_entries()
              if e.get("kind") == "deny"
              and e.get("payload", {}).get("action") == "reattach"]
    assert len(denies) >= 2, "refusals were not recorded"
    ckpt_path.write_text(saved, encoding="utf-8")  # restore honesty
    host.reattach("scratch", "host", "demo")
    evidence.append("refusals: missing-checkpoint + identity-mismatch both raised "
                    f"with recorded deny (reattach denies={len(denies)})")
    host.transition("scratch", "dissolved", "host", reason="demo cleanup")

    # Terminal settle: zero stranded holdings + conservation clean.
    host.transition(rl.WORKER_ID, "dissolved", "host", reason="demo done")
    held = host.holdings[rl.WORKER_ID]
    assert all(v == 0 for v in held.values()), f"stranded: {held}"
    rep = host.verify_conservation()
    assert rep["ok"] and rl.WORKER_ID in rep["settled_terminals"]
    n_settle = sum(1 for e in host.ledger_entries()
                   if e.get("kind") == "grant_settle")
    evidence.append(f"terminal settle: holdings={held} stranded=0 "
                    f"grant_settle markers={n_settle} conservation ok")

    # Hand-written unsettled-terminal ledger is rejected.
    bad = tmp / "bad-ledger.jsonl"
    rows = [
        {"seq": 1, "at": "t", "kind": "host_init",
         "contract_version": "0", "actor": "host",
         "payload": {"root_holdings": {"max_cost_usd": 1.0, "max_time_s": 10.0,
                                       "max_invocations": 5}}},
        {"seq": 2, "at": "t", "kind": "create",
         "contract_version": "0", "actor": "host",
         "payload": {"world_id": "w", "creator": "host", "code_ref": "x",
                     "instance_state_dir": str(tmp / "badstate" / "w"),
                     "custodians": {}, "authorities": [], "capabilities": [],
                     "representations": [], "lineage": []}},
        {"seq": 3, "at": "t", "kind": "lifecycle",
         "contract_version": "0", "actor": "host",
         "payload": {"world_id": "w", "from": "active", "to": "dissolved",
                     "reason": "hand-written, no settle"}},
    ]
    bad.write_text("".join(json.dumps(r, sort_keys=True) + "\n" for r in rows),
                   encoding="utf-8")
    badhost = MiniHost.reopen(tmp / "badstate", bad, reason="demo bad ledger")
    try:
        badhost.verify_conservation()
        raise AssertionError("unsettled terminal was NOT rejected")
    except ContractViolation as exc:
        assert "unsettled terminal" in str(exc)
    evidence.append("hand-written unsettled-terminal ledger: rejected "
                    "('unsettled terminal')")

    print("reuse-demo-001 evidence (MiniHost + reused w1-harden resume):")
    for line in evidence:
        print(f"  ok: {line}")
    print(f"  state kept at: {tmp}")
    print("RESULT: PASS (exit 0)")


if __name__ == "__main__":
    main()
