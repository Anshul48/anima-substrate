"""Resumable formulate -> propose -> score -> verdict pipeline (recovery focus).

Engine-agnostic: resume decisions use ONLY on-disk artifacts + the ledger
(formulation/candidate/score refs + successful invoke entries), never
in-memory state, so they survive a kill-mid-run. Works with the stub engine
or real SST (artifacts + ledger are the interface); the exercises pin the
stub for determinism.

Resume rule (idempotent-by-skip, never restart):
- each phase is skipped only when a ledger-successful invoke for the CURRENT
  inputs exists AND all of its output artifacts exist on disk;
- otherwise the phase executes (first execution, or re-execution when
  outputs were lost — the latter is counted honestly in the report);
- resume NEVER wipes state and never re-runs a provably complete phase.

Refusal convention: resume-time refusals (nothing to resume, propose output
missing with no way forward) are recorded via host.deny, never silent.
"""
from __future__ import annotations

import json
from pathlib import Path

try:
    from .HOST import Host
    from .contract import ContractViolation, WorldRecord
    from .world_explore import (CAPABILITIES as E_CAPABILITIES,
                                CUSTODIANS as E_CUSTODIANS,
                                REPRESENTATIONS as E_REPS, ExploreWorld,
                                SearchEngine)
except ImportError:  # running from the package dir
    from HOST import Host
    from contract import ContractViolation, WorldRecord
    from world_explore import (CAPABILITIES as E_CAPABILITIES,
                               CUSTODIANS as E_CUSTODIANS,
                               REPRESENTATIONS as E_REPS, ExploreWorld,
                               SearchEngine)

WORKER_ID = "R-worker"
WORKER_CODE_REF = "w1-harden/recovery_lib.py:R-worker"
POLICY = {"max_iterations": 2, "max_depth": 2, "branching": 1}
GOAL = "recovery exercise: search toy variants, then survive a kill"
VERDICT_NAME = "verdict.json"


def worker_record(state_dir: Path) -> WorldRecord:
    """Deterministic worker descriptor (same bytes pre-kill and post-reopen)."""
    return WorldRecord(
        world_id=WORKER_ID, lineage=[("host", "created", "recovery")],
        code_ref=WORKER_CODE_REF,
        instance_state_dir=str(Path(state_dir) / WORKER_ID),
        custodians=dict(E_CUSTODIANS),
        capabilities=list(E_CAPABILITIES),
        representations=list(E_REPS),
        authorities=["search.sst"])


def setup(host: Host, engine: SearchEngine | None = None) -> ExploreWorld:
    """Create + fund + activate the worker. Returns the world handle."""
    host.create_world(
        worker_record(host.state_dir), "host",
        grant_limits={"max_cost_usd": 1.0, "max_time_s": 120.0,
                      "max_invocations": 20})
    host.transition(WORKER_ID, "active", "host", reason="recovery setup")
    return ExploreWorld(Path(host.state_dir) / WORKER_ID, engine=engine)


def phase_formulate(world: ExploreWorld) -> str:
    """Phase 1 (world-local setup): write the formulation. Returns its ref."""
    return world.write_formulation(
        goal=GOAL, domain="code-variant-search",
        constraints=["toy.py"], budget={"max_iterations": 2})


def phase_propose(host: Host, world: ExploreWorld, form_ref: str) -> dict:
    """Phase 2 (accountable): search.propose under the worker's budget."""
    args_ref = host.store_args(WORKER_ID, "r-propose",
                               {"formulation_ref": form_ref, "policy": POLICY})
    entry = host.invoke(
        WORKER_ID, WORKER_ID, "search.propose", "1.0", args_ref,
        lambda: json.dumps(world.search_propose(form_ref, dict(POLICY))),
        cost_usd=0.0, time_s=5.0)
    return json.loads(entry["payload"]["result_ref"])


def phase_score(host: Host, world: ExploreWorld, run: dict) -> dict:
    """Phase 3 (accountable): search.score over the run's candidates."""
    args_ref = host.store_args(WORKER_ID, "r-score",
                               {"candidate_refs": run["candidate_refs"]})
    entry = host.invoke(
        WORKER_ID, WORKER_ID, "search.score", "1.0", args_ref,
        lambda: json.dumps(world.search_score(run["candidate_refs"])))
    return json.loads(entry["payload"]["result_ref"])


def phase_verdict(world: ExploreWorld, run: dict, scored: dict) -> str:
    """Phase 4 (host-side aggregation): write the fixed-name verdict file."""
    wdir = Path(world.state_dir)
    (wdir / "verdicts").mkdir(parents=True, exist_ok=True)
    verdict = {"contract_version": "0", "representation": "recovery-verdict/v0",
               "candidate_refs": run["candidate_refs"],
               "champion_id": run["champion_id"], "engine": run["engine"],
               "scores": scored["scores"], "evaluator": scored["evaluator"]}
    ref = wdir / "verdicts" / VERDICT_NAME
    ref.write_text(json.dumps(verdict, indent=2, sort_keys=True), encoding="utf-8")
    return str(ref)


def latest_artifact(world_dir: Path, subdir: str) -> Path | None:
    files = sorted((Path(world_dir) / subdir).glob("*.json")) if (
        Path(world_dir) / subdir).exists() else []
    return files[-1] if files else None


def successful_invokes(entries: list[dict], capability: str) -> list[dict]:
    return [e for e in entries
            if e.get("kind") == "invoke"
            and e.get("payload", {}).get("capability") == capability
            and "error" not in e.get("payload", {})]


def _artifacts_exist(refs: list[str]) -> bool:
    return bool(refs) and all(Path(r).exists() for r in refs)


def _args_formulation_ref(args_ref: str) -> str | None:
    try:
        return json.loads(Path(args_ref).read_text(encoding="utf-8")).get(
            "formulation_ref")
    except (OSError, ValueError):
        return None


def _args_candidate_refs(args_ref: str) -> list | None:
    try:
        return json.loads(Path(args_ref).read_text(encoding="utf-8")).get(
            "candidate_refs")
    except (OSError, ValueError):
        return None


def resume_to_verdict(host: Host, world: ExploreWorld) -> dict:
    """Resume the pipeline to a verdict without restarting.

    Skips each phase with ledger proof + surviving artifacts; executes the
    rest. Returns {"verdict_ref", "champion_id", "formulation_ref",
    "candidate_refs", "skipped", "executed", "re_executed_invokes"} where
    re_executed_invokes counts accountable invokes executed for a phase that
    already had a ledger-successful invoke (output loss case; 0 in the
    scripted kill exercises).
    """
    if host.worlds.get(WORKER_ID) is None:
        host.deny("host", "resume", f"unknown worker {WORKER_ID!r}")
        raise ContractViolation(f"resume: unknown worker {WORKER_ID!r}")
    if host.worlds[WORKER_ID].lifecycle != "active":
        host.deny("host", "resume",
                  f"worker not active (state={host.worlds[WORKER_ID].lifecycle})")
        raise ContractViolation("resume: worker not active (reattach first)")
    wdir = Path(world.state_dir)
    entries = host.ledger_entries()
    skipped: list[str] = []
    executed: list[str] = []
    re_executed = 0

    form_file = latest_artifact(wdir, "formulations")
    if form_file is None:
        form_ref = phase_formulate(world)
        executed.append("formulate")
    else:
        form_ref = str(form_file)
        skipped.append("formulate")

    run: dict | None = None
    propose_ok = successful_invokes(entries, "search.propose")
    for inv in reversed(propose_ok):  # latest proof first
        try:
            candidate = json.loads(inv["payload"]["result_ref"])
        except (KeyError, ValueError):
            continue
        if (_args_formulation_ref(inv["payload"].get("args_ref", "")) == form_ref
                and _artifacts_exist(candidate.get("candidate_refs", []))):
            run = candidate
            break
    if run is None:
        if propose_ok:
            re_executed += 1  # ledger says propose ran; outputs unusable
        run = phase_propose(host, world, form_ref)
        executed.append("propose")
    else:
        skipped.append("propose")
    if not run.get("champion_id"):
        host.deny("host", "resume", "propose yielded no champion; cannot score")
        raise ContractViolation("resume: propose yielded no champion")

    scored: dict | None = None
    score_ok = successful_invokes(entries, "search.score")
    for inv in reversed(score_ok):
        try:
            candidate = json.loads(inv["payload"]["result_ref"])
        except (KeyError, ValueError):
            continue
        score_refs = [s.get("score_ref") for s in candidate.get("scores", [])]
        if (_args_candidate_refs(inv["payload"].get("args_ref", ""))
                == run["candidate_refs"]
                and _artifacts_exist([r for r in score_refs if r])):
            scored = candidate
            break
    if scored is None:
        if score_ok:
            re_executed += 1
        scored = phase_score(host, world, run)
        executed.append("score")
    else:
        skipped.append("score")

    verdict_path = wdir / "verdicts" / VERDICT_NAME
    verdict_ok = False
    if verdict_path.exists():
        try:
            existing = json.loads(verdict_path.read_text(encoding="utf-8"))
            verdict_ok = (existing.get("candidate_refs") == run["candidate_refs"]
                          and existing.get("champion_id") == run["champion_id"])
        except ValueError:
            verdict_ok = False
    if verdict_ok:
        skipped.append("verdict")
        verdict_ref = str(verdict_path)
    else:
        verdict_ref = phase_verdict(world, run, scored)
        executed.append("verdict")

    return {"verdict_ref": verdict_ref, "champion_id": run["champion_id"],
            "formulation_ref": form_ref, "candidate_refs": run["candidate_refs"],
            "skipped": skipped, "executed": executed,
            "re_executed_invokes": re_executed}
