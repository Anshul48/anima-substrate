"""Transition T end-to-end demo (W1 prototype).

E-construct requests exploration over a different representation ->
E-explore nests an experiment world under a delegated budget -> mapping
revised v1->v2 -> exploration participant assimilated into a composite with
custody transfer + lineage -> suspend/reattach mid-run -> composite
capability (composite.solve) invoked on a follow-up task.

Exits non-zero on any contract violation. Runs under system python3 (stub
search engine) or the project-local .venv (real SST engine); both exit 0.
Usage: python3 demo_T.py --state-dir /tmp/muse-w1-state --ledger /tmp/muse-w1-state/ledger.jsonl
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from HOST import Host
from contract import Capability, ContractViolation, Representation, WorldRecord
from relationship import (REL_ID, formulation_to_task_spec_evidence, revise_v1_to_v2,
                          task_spec_to_formulation, v1_record)
from world_construct import (CAPABILITIES as C_CAPABILITIES,
                             CUSTODIANS as C_CUSTODIANS,
                             REPRESENTATIONS as C_REPS, ConstructWorld)
from world_explore import (CAPABILITIES as E_CAPABILITIES,
                           CUSTODIANS as E_CUSTODIANS,
                           REPRESENTATIONS as E_REPS, ExploreWorld)

COMPOSITE_ID = "C-solve"
EXP_ID = "E-explore-exp1"


def make_host(state_dir: Path, ledger: Path) -> Host:
    return Host(state_dir=state_dir, ledger_path=ledger,
                root_holdings={"max_cost_usd": 10.0, "max_time_s": 600.0,
                               "max_invocations": 1000})


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--state-dir", required=True)
    ap.add_argument("--ledger", required=True)
    args = ap.parse_args()
    state_dir = Path(args.state_dir)
    host = make_host(state_dir, Path(args.ledger))

    c_dir = state_dir / "E-construct"
    e_dir = state_dir / "E-explore"
    construct = ConstructWorld(c_dir)
    explore = ExploreWorld(e_dir)

    # 1. Two distinct worlds + coalition record.
    host.create_world(WorldRecord(
        world_id="E-construct", lineage=[("host", "created", "demo_T")],
        code_ref="w1/world_construct.py", instance_state_dir=str(c_dir),
        custodians=dict(C_CUSTODIANS), capabilities=list(C_CAPABILITIES),
        representations=list(C_REPS),
        authorities=["execute.local", "artifact.read", "custody.transfer"]), "host",
        grant_limits={"max_cost_usd": 2.0, "max_time_s": 200.0, "max_invocations": 200})
    host.create_world(WorldRecord(
        world_id="E-explore", lineage=[("host", "created", "demo_T")],
        code_ref="w1/world_explore.py", instance_state_dir=str(e_dir),
        custodians=dict(E_CUSTODIANS), capabilities=list(E_CAPABILITIES),
        representations=list(E_REPS),
        authorities=["search.sst", "world.create", "grant.delegate",
                     "custody.transfer"]), "host",
        grant_limits={"max_cost_usd": 2.0, "max_time_s": 200.0, "max_invocations": 200})
    host.create_world(WorldRecord(
        world_id="coalition-T", lineage=[("host", "created", "demo_T")],
        code_ref="w1/demo_T.py:coalition", instance_state_dir=str(state_dir / "coalition-T"),
        custodians={"membership": "coalition-T"}), "host")
    for wid in ("E-construct", "E-explore", "coalition-T"):
        host.transition(wid, "active", "host", reason="demo_T start")

    # 2. E-construct does real work: task-spec -> run -> verify.
    spec_T1 = {"goal": "write a greeting file hello.txt",
               "acceptance": ["hello.txt exists", "contains greeting"],
               "scope": ["hello.txt"]}
    spec_T1_ref = construct.write_task_spec(**spec_T1)
    run_args = host.store_args("E-construct", "run-hello",
                               {"argv": ["python3", "-c",
                                         "open('hello.txt','w').write('hello from E-construct\\n')"],
                                "timeout_s": 30})
    run_entry = host.invoke(
        "E-construct", "E-construct", "build.run", "1.0", run_args,
        lambda: json.dumps(construct.build_run(
            ["python3", "-c", "open('hello.txt','w').write('hello from E-construct\\n')"],
            timeout_s=30)),
        cost_usd=0.01, time_s=1.0)
    run_out = json.loads(run_entry["payload"]["result_ref"])
    assert run_out["exit_code"] == 0, run_out
    verify_args = host.store_args("E-construct", "verify-hello",
                                  {"receipt_ref": run_out["receipt_ref"],
                                   "assertions": {"exit_code": 0,
                                                  "files_exist": ["hello.txt"]}})
    verify_entry = host.invoke(
        "E-construct", "E-construct", "build.verify", "1.0", verify_args,
        lambda: json.dumps(construct.build_verify(
            run_out["receipt_ref"], {"exit_code": 0, "files_exist": ["hello.txt"]})))
    assert json.loads(verify_entry["payload"]["result_ref"])["passed"]
    print("construct work: hello.txt built + verified", flush=True)

    # 3. Cross-representation request via relationship v1.
    host.declare_relationship(v1_record(), actor="host")
    form_F1 = task_spec_to_formulation(spec_T1, "1.0")
    form_F1_ref = explore.write_formulation(
        goal=form_F1["goal"], domain=form_F1["domain"],
        constraints=form_F1["constraints"], budget=form_F1["budget"])
    print(f"relationship {REL_ID} v1 declared; formulation {form_F1_ref}", flush=True)

    # 4. Nested experiment world with a delegated grant from E-explore's holding.
    holding_before = dict(host.holdings["E-explore"])
    exp_dir = state_dir / EXP_ID
    host.create_world(WorldRecord(
        world_id=EXP_ID, lineage=[("E-explore", "created", "demo_T nested experiment")],
        code_ref="w1/world_explore.py", instance_state_dir=str(exp_dir),
        custodians={"search-state": EXP_ID, "formulations": EXP_ID},
        capabilities=list(E_CAPABILITIES), representations=list(E_REPS),
        authorities=["search.sst"]), "E-explore")
    host.grant("E-explore", EXP_ID,
               {"max_cost_usd": 0.5, "max_time_s": 60.0, "max_invocations": 20},
               authority=["search.sst"], grant_id="g-explore-exp1")
    host.transition(EXP_ID, "active", "E-explore", reason="nested experiment start")
    holding_after = host.holdings["E-explore"]
    assert holding_after["max_cost_usd"] < holding_before["max_cost_usd"], \
        "parent holding must decrease on delegation"
    print(f"nested {EXP_ID}: E-explore holding {holding_before['max_cost_usd']} -> "
          f"{holding_after['max_cost_usd']}", flush=True)
    exp_world = ExploreWorld(exp_dir, engine=explore.engine)

    # 5. Suspend/reattach mid-run: identity, versions, accounted effects preserved.
    ids_before = sorted(host.worlds)
    vers_before = {w: [c.name + "@" + c.version for c in host.worlds[w].capabilities]
                   for w in ids_before}
    holds_before = {w: dict(h) for w, h in host.holdings.items()}
    host.suspend("E-explore", "host", reason="demo_T interruption",
                 pending_effects=["exp1 search_propose"])
    assert (e_dir / "checkpoint.json").exists()
    host.reattach("E-explore", "host", reason="demo_T reattachment")
    assert sorted(host.worlds) == ids_before
    for w in ids_before:
        assert [c.name + "@" + c.version for c in host.worlds[w].capabilities] == vers_before[w]
    assert {w: dict(h) for w, h in host.holdings.items()} == holds_before
    print("suspend/reattach: identities, versions, holdings unchanged", flush=True)

    # 6. Nested experiment runs the search under its delegated budget.
    propose_args = host.store_args(
        EXP_ID, "propose-F1",
        {"formulation_ref": form_F1_ref,
         "policy": {"max_iterations": 2, "max_depth": 2, "branching": 1},
         "rel": REL_ID, "rel_version": "1.0"})
    propose_entry = host.invoke(
        EXP_ID, "E-explore", "search.propose", "1.0", propose_args,
        lambda: json.dumps(exp_world.search_propose(
            form_F1_ref, {"max_iterations": 2, "max_depth": 2, "branching": 1})),
        cost_usd=0.0, time_s=5.0)
    run1 = json.loads(propose_entry["payload"]["result_ref"])
    assert run1["champion_id"], run1
    assert run1["cost_usd"] == 0.0, "SST spend must be $0"
    host.get_relationship(REL_ID, "1.0").evidence.append(
        propose_entry["payload"]["invoke_id"])
    score_args = host.store_args(EXP_ID, "score-F1",
                                 {"candidate_refs": run1["candidate_refs"]})
    score_entry = host.invoke(
        EXP_ID, "E-explore", "search.score", "1.0", score_args,
        lambda: json.dumps(exp_world.search_score(run1["candidate_refs"])))
    scores1 = json.loads(score_entry["payload"]["result_ref"])
    assert scores1["evaluator"] == "world-local"
    print(f"nested search: engine={run1['engine']} champion={run1['champion_id']} "
          f"termination={run1['termination']}", flush=True)

    # 6b. One intentional refusal: exp1 lacks execute.local -> recorded denial.
    try:
        host.invoke(EXP_ID, "E-construct", "build.run", "1.0", "denied-args",
                    lambda: "never", cost_usd=0.0)
        raise AssertionError("expected authority refusal")
    except ContractViolation:
        pass
    assert host.ledger_entries()[-1]["kind"] == "deny"
    print("authority refusal recorded as ledger denial", flush=True)

    # 7. Mapping revised v1 -> v2; old run stays pinned to v1 and still verifies.
    host.declare_relationship(revise_v1_to_v2(), actor="host")
    form_F1_again = task_spec_to_formulation(spec_T1, "1.0")
    for key in ("goal", "domain", "constraints", "budget", "opaque_acceptance"):
        assert form_F1_again.get(key) == form_F1.get(key), key
    spec_T2 = {"goal": "variant search with stated assumptions",
               "acceptance": ["champion selected"],
               "scope": ["toy.py"], "assumptions": ["toy source is trusted"]}
    form_F2 = task_spec_to_formulation(spec_T2, "2.0")
    assert form_F2["assumptions"] == ["toy source is trusted"]
    assert form_F2["mapping_version"] == "2.0"
    print("mapping v2 declared; v1 re-derivation identical (old run pinned)", flush=True)

    # 8. Assimilation: exp1 merges into composite C-solve with custody transfer.
    c_dir = state_dir / COMPOSITE_ID
    composite_world = ExploreWorld(c_dir, engine=explore.engine)
    host.create_world(WorldRecord(
        world_id=COMPOSITE_ID,
        lineage=[("E-construct", "fused", "demo_T assimilation"),
                 (EXP_ID, "fused", "demo_T assimilation")],
        code_ref="w1/demo_T.py:composite+solve",
        instance_state_dir=str(c_dir),
        custodians={"solutions": COMPOSITE_ID},
        capabilities=[Capability(
            name="composite.solve", version="1.0",
            inputs="task-spec ref", outputs="champion + world-local score",
            side_effects="runs bounded search under composite state dir",
            cost_model="cost_usd=0.01/invocation", applicability="any task-spec/v0",
            failure_modes="no champion (budget exhausted)",
            required_authority="execute.local")],
        representations=[Representation(name="solution/v0", version="1.0",
                                        schema_ref="composite:solution/v0",
                                        meaning_note="champion + verdict + lineage")],
        authorities=["execute.local", "artifact.read"]), "host",
        grant_limits={"max_cost_usd": 1.0, "max_time_s": 120.0, "max_invocations": 50})

    def composite_solve(task_spec: dict) -> str:
        form = task_spec_to_formulation(task_spec, "2.0")
        form_ref = composite_world.write_formulation(
            goal=form["goal"], domain=form["domain"],
            constraints=form["constraints"], budget=form["budget"])
        run = composite_world.search_propose(
            form_ref, {"max_iterations": 2, "max_depth": 2, "branching": 1})
        scored = composite_world.search_score(run["candidate_refs"])
        solution = formulation_to_task_spec_evidence(form, run, "2.0")
        solution["scores"] = scored
        solution["derived_from"] = [
            {"world_id": "E-construct", "version": "1.0",
             "what_inherited": "task-spec + acceptance", "what_reacquired": "nothing"},
            {"world_id": EXP_ID, "version": "1.0",
             "what_inherited": "search procedure + engine",
             "what_reacquired": "fresh search run (no state copied)"}]
        sol_ref = composite_world._write_json("solutions", solution)
        return json.dumps({"solution_ref": sol_ref,
                           "champion_id": run["champion_id"],
                           "engine": run["engine"]})

    host.transfer_custody("search-state", EXP_ID, COMPOSITE_ID, EXP_ID,
                          reason="assimilation into composite",
                          continuity=f"{EXP_ID} dissolved; records preserved; "
                                     f"{COMPOSITE_ID} continues search-state")
    host.transition(COMPOSITE_ID, "active", "host", reason="composite ready")
    host.transition(EXP_ID, "dissolved", EXP_ID, reason="assimilated into composite")
    host.transition(EXP_ID, "retired", "host", reason="assimilation complete")
    print(f"assimilation: {EXP_ID} retired; custody search-state -> {COMPOSITE_ID}",
          flush=True)

    # 9. Composite capability reuse on a follow-up task.
    spec_T3 = {"goal": "follow-up: greet a file variant",
               "acceptance": ["champion selected"], "scope": ["hello.txt"],
               "assumptions": ["reuse composite procedure"]}
    spec_T3_ref = construct.write_task_spec(
        goal=spec_T3["goal"], acceptance=spec_T3["acceptance"], scope=spec_T3["scope"])
    solve_args = host.store_args("E-construct", "composite-solve-T3",
                                 {"task_spec_ref": spec_T3_ref, "rel_version": "2.0"})
    solve_entry = host.invoke(
        "E-construct", COMPOSITE_ID, "composite.solve", "1.0", solve_args,
        lambda: composite_solve(spec_T3), cost_usd=0.01, time_s=5.0)
    solved = json.loads(solve_entry["payload"]["result_ref"])
    assert solved["champion_id"], solved
    print(f"composite.solve: champion={solved['champion_id']} engine={solved['engine']}",
          flush=True)

    # 10. Close the coalition; verify conservation; summarize.
    host.transition("coalition-T", "dissolved", "host",
                    reason="T complete; records preserved")
    report = host.verify_conservation()
    assert report["ok"]
    kinds: dict[str, int] = {}
    for e in host.ledger_entries():
        kinds[e["kind"]] = kinds.get(e["kind"], 0) + 1
    print(f"ledger kinds: {json.dumps(kinds, sort_keys=True)}", flush=True)
    print(f"conservation OK; ledger={args.ledger}", flush=True)
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except ContractViolation as exc:
        print(f"CONTRACT VIOLATION: {exc}", file=sys.stderr)
        sys.exit(1)
