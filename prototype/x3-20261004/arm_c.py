"""Arm C: central orchestrator + recovery.

All cross-world traffic flows through the central Coordinator (every
fragment relay counted in central-context-bytes). Fixed versioned
adapters (list2slot/v1, list2slot/v2). Accountable invokes are issued
centrally (caller=host). Recovery machinery shared with Arm H.
"""
from __future__ import annotations

from pathlib import Path

from minihost import MiniHost

import checker
import domain
import frozen_inputs as FI
import xcommon as XC

L_CAPS = [("list.provide", "1.0"), ("sched.solve", "1.0"),
          ("sched.assign", "1.0")]
S_CAPS = [("slot.provide", "1.0"), ("sched.solve", "1.0"),
          ("slot.assign", "1.0")]
T_CAPS = [("sched.solve", "1.0"), ("sched.reuse", "1.0")]


def t1_worlds(state_dir: Path):
    return [XC.world_record(state_dir, "X3-L", L_CAPS, [("sched-list", "v1")]),
            XC.world_record(state_dir, "X3-S", S_CAPS, [("sched-slot", "v1")])]


def t2_worlds(state_dir: Path):
    return [XC.world_record(state_dir, "X3-L", L_CAPS, [("sched-list", "v2")]),
            XC.world_record(state_dir, "X3-S", S_CAPS, [("sched-slot", "v2")])]


def t3_worlds(state_dir: Path):
    return [XC.world_record(state_dir, "X3-L", L_CAPS, [("sched-list", "v1")]),
            XC.world_record(state_dir, "X3-S", S_CAPS, [("sched-slot", "v1")],
                            custodians={"sched.composite": "X3-S"}),
            XC.world_record(state_dir, "X3-T", T_CAPS, [("sched-slot", "v1")])]


def _provide(host: MiniHost, world: str, cap: str, payload: dict,
             coord: XC.Coordinator) -> dict:
    args = host.store_args(world, cap.replace(".", "-"), payload)
    entry = host.invoke("host", world, cap, "1.0", args,
                        lambda: XC.write_json(
                            Path(host.state_dir) / world / "provided"
                            / f"{cap}.json", payload),
                        cost_usd=0.0, time_s=1.0)
    doc = dict(payload)
    coord.handle({"kind": "fetch", "task_id": payload.get("task_id"),
                  "from": world, "capability": cap, "doc": doc})
    return {"doc": doc, "result_ref": entry["payload"]["result_ref"]}


def _solve(host: MiniHost, world: str, task: dict, name: str) -> dict:
    args = host.store_args(world, name, {"task": task})
    entry = host.invoke(
        "host", world, "sched.solve", "1.0", args,
        lambda: XC.write_json(
            Path(host.state_dir) / world / "solutions" / f"{name}.json",
            {"assignment": domain.solve(task), "task_id": task["task_id"]}),
        cost_usd=0.0, time_s=2.0)
    return {"assignment": domain.solve(task),
            "result_ref": entry["payload"]["result_ref"]}


def run_t1(root: Path) -> dict:
    task = FI.T1
    coord = XC.Coordinator()
    worlds = t1_worlds(root / "state")
    host = XC.setup_host(root, worlds)
    rounds = 0
    # Central fetches both worlds' docs through itself.
    ldoc = _provide(host, "X3-L", "list.provide",
                    {"task_id": "T1", "list": domain.list_doc(task)}, coord)
    sdoc = _provide(host, "X3-S", "slot.provide",
                    {"task_id": "T1", "slot": domain.slot_doc(task)}, coord)
    # Fixed versioned adapter, central-side.
    sdoc_v, loss = domain.translate_list2slot(ldoc["doc"]["list"],
                                              FI.T1["adapter"])
    coord.handle({"kind": "translation", "task_id": "T1",
                  "adapter": FI.T1["adapter"], "doc": sdoc_v, "loss": loss})
    hold = FI.T1["holdings"]
    ltasks = {t: task["tasks"][t] for t in hold["X3-L"]["req_tasks"]}
    stasks = {t: task["tasks"][t] for t in hold["X3-S"]["req_tasks"]}
    # R1: requirements exchange (relayed).
    coord.handle(domain.req_fragment("T1", "X3-L", ltasks, task["precedence"]))
    coord.handle(domain.req_fragment("T1", "X3-S", stasks, []))
    rounds += 1
    # R2: clarification 1 (L prefs -> S, relayed).
    coord.handle(domain.pref_fragment(
        "T1", "X3-L", {p: task["prefs"][p] for p in hold["X3-L"]["prefs"]}))
    rounds += 1
    # R3: clarification 2 (S prefs -> L, relayed) + central solve.
    coord.handle(domain.pref_fragment(
        "T1", "X3-S", {p: task["prefs"][p] for p in hold["X3-S"]["prefs"]}))
    rounds += 1
    full = dict(task)
    got = _solve(host, "X3-L", full, "t1-propose")
    coord.handle(domain.proposal("T1", "central", got["assignment"],
                                 basis="merged reqs + clarified prefs"))
    ver = _solve(host, "X3-S", full, "t1-verify")
    assert ver["assignment"] == got["assignment"], "central verify mismatch"
    sol_ref = XC.write_json(root / "artifacts" / "solution.json",
                            {"task_id": "T1", "assignment": got["assignment"],
                             "arm": "C"})
    fin = XC.finish_worlds(host, ["X3-L", "X3-S"], "T1 done")
    rep = checker.check(got["assignment"], task)
    return {"arm": "C", "task": "T1", "central_bytes": coord.central_bytes,
            "direct_bytes": 0, "rounds": rounds, "rework": 0,
            "escalations": 0, "valid": rep["valid"],
            "quality": rep["quality"], "prefs_total": rep["prefs_total"],
            "solution_ref": sol_ref, "finish": fin}


def t2_prekill(root: Path) -> dict:
    """T2 pre-kill half (runs in the worker that will be SIGKILLed)."""
    task = FI.T2["revised"]
    coord = XC.Coordinator()
    worlds = t2_worlds(root / "state")
    host = XC.setup_host(root, worlds)
    form_ref = XC.write_json(
        root / "artifacts" / "formulation.json",
        {"task_id": "T2", "base_tasks": FI.T2["base"]["tasks"],
         "precedence": FI.T2["base"]["precedence"], "adapter": "list2slot/v1"})
    # Checkpoint + identity exercise before the revision.
    for wid in ("X3-L", "X3-S"):
        host.suspend(wid, "host", "T2 pre-revision checkpoint",
                     pending_effects=["adapt-propose"])
    for wid in ("X3-L", "X3-S"):
        host.reattach(wid, "host", "T2 resume after checkpoint")
    # Revision v1 -> v2 (declared loss) + capability revocation.
    host.append("revision", {"task_id": "T2", **FI.T2["revision"]}, actor="host")
    host.append("capability_revoked", {"task_id": "T2", **FI.T2["revocation"]},
                actor="host")
    coord.handle({"kind": "revision", "task_id": "T2",
                  "change": FI.T2["revision"],
                  "revocation": FI.T2["revocation"]})
    # Central adapts: re-fetch both worlds' revised docs through itself
    # (central reconstruction after a lossy revision), re-translate via
    # the v2 adapter, relay req + pref re-clarification, solve via L.
    hold = FI.T2["holdings"]
    ldoc = _provide(host, "X3-L", "list.provide",
                    {"task_id": "T2-v2",
                     "list": domain.list_doc({**task, "task_id": "T2-v2"})},
                    coord)
    _provide(host, "X3-S", "slot.provide",
             {"task_id": "T2-v2",
              "slot": domain.slot_doc({**task, "task_id": "T2-v2"})}, coord)
    sdoc_v, loss = domain.translate_list2slot(ldoc["doc"]["list"],
                                              FI.T2["revision"]["to"])
    coord.handle({"kind": "translation", "task_id": "T2-v2",
                  "adapter": FI.T2["revision"]["to"],
                  "doc": sdoc_v, "loss": loss})
    coord.handle(domain.req_fragment(
        "T2", "X3-L", {t: task["tasks"][t] for t in hold["X3-L"]["req_tasks"]},
        task["precedence"]))
    coord.handle(domain.req_fragment(
        "T2", "X3-S", {t: task["tasks"][t] for t in hold["X3-S"]["req_tasks"]},
        []))
    coord.handle(domain.pref_fragment(
        "T2", "X3-L", {p: task["prefs"][p] for p in hold["X3-L"]["prefs"]}))
    coord.handle(domain.pref_fragment(
        "T2", "X3-S", {p: task["prefs"][p] for p in hold["X3-S"]["prefs"]}))
    args = host.store_args("X3-L", "t2-adapt-propose",
                           {"formulation_ref": form_ref,
                            "task_version": "v2", "task": task})
    entry = host.invoke(
        "host", "X3-L", "sched.solve", "1.0", args,
        lambda: XC.write_json(
            Path(host.state_dir) / "X3-L" / "solutions" / "t2-propose.json",
            {"assignment": domain.solve(task), "task_id": "T2-v2"}),
        cost_usd=0.0, time_s=2.0)
    coord.handle(domain.proposal("T2", "central", domain.solve(task),
                                 basis="v2 revision, owner X3-L"))
    return {"host": host, "coord": coord, "form_ref": form_ref,
            "propose_ref": entry["payload"]["result_ref"], "task": task}


def t2_resume(host: MiniHost, root: Path, prekill: dict) -> dict:
    """T2 post-reopen half: resume-by-skip, then verify + finish."""
    task = FI.T2["revised"]
    coord = XC.Coordinator()
    coord.central_bytes = prekill["central_bytes"]
    entries = host.ledger_entries()
    skipped, executed = [], []
    re_executed = 0
    form_ref = str(root / "artifacts" / "formulation.json")
    assert Path(form_ref).exists(), "formulation lost across kill"
    skipped.append("formulate")
    run = None
    for inv in reversed(XC.successful_invokes(entries, "sched.solve")):
        if XC.args_match(inv["payload"].get("args_ref", ""),
                         "task_version", "v2") and Path(
                inv["payload"]["result_ref"]).exists():
            run = {"assignment": domain.solve(task),
                   "result_ref": inv["payload"]["result_ref"]}
            break
    if run is None:
        if XC.successful_invokes(entries, "sched.solve"):
            re_executed += 1
        args = host.store_args("X3-L", "t2-adapt-propose",
                               {"formulation_ref": form_ref,
                                "task_version": "v2", "task": task})
        ent = host.invoke(
            "host", "X3-L", "sched.solve", "1.0", args,
            lambda: XC.write_json(
                Path(host.state_dir) / "X3-L" / "solutions" / "t2-propose.json",
                {"assignment": domain.solve(task), "task_id": "T2-v2"}),
            cost_usd=0.0, time_s=2.0)
        run = {"assignment": domain.solve(task),
               "result_ref": ent["payload"]["result_ref"]}
        executed.append("adapt-propose")
    else:
        skipped.append("adapt-propose")
    ver = _solve(host, "X3-S", task, "t2-verify")
    executed.append("verify")
    assert ver["assignment"] == run["assignment"], "T2 verify mismatch"
    sol_ref = XC.write_json(root / "artifacts" / "solution.json",
                            {"task_id": "T2", "task_version": "v2",
                             "assignment": run["assignment"], "arm": "C"})
    fin = XC.finish_worlds(host, ["X3-L", "X3-S"], "T2 done")
    rep = checker.check(run["assignment"], task)
    return {"arm": "C", "task": "T2", "central_bytes": coord.central_bytes,
            "direct_bytes": 0, "rounds": 3, "rework": re_executed,
            "escalations": 0, "valid": rep["valid"],
            "quality": rep["quality"], "prefs_total": rep["prefs_total"],
            "solution_ref": sol_ref, "skipped": skipped,
            "executed": executed, "resume_zero_rework": re_executed == 0,
            "finish": fin}


def run_t3(root: Path) -> dict:
    comp_task = FI.T3["composite_task"]
    fol_task = FI.T3["followup"]
    coord = XC.Coordinator()
    worlds = t3_worlds(root / "state")
    host = XC.setup_host(root, worlds)
    # Coalition produces the composite through the central.
    got = _solve(host, "X3-L", comp_task, "t3-composite")
    composite = {"task_id": "T3-composite", "assignment": got["assignment"],
                 "derived_from": {"task": "T1", "inputs": "frozen"},
                 "arm": "C"}
    comp_ref = XC.write_json(root / "artifacts" / "composite.json", composite)
    comp_rel = str(Path(comp_ref).relative_to(root))  # run-dir independent
    coord.handle({"kind": "composite", "task_id": "T3",
                  "from": "X3-L", "doc": composite})
    # Central moves custody to the third world, then dissolves coalition.
    host.transfer_custody(FI.T3["transfer"]["state_class"],
                          FI.T3["transfer"]["from"], FI.T3["transfer"]["to"],
                          "host", reason="T3 transfer",
                          continuity=f"sha256:{MiniHost.sha256_file(comp_ref)}")
    coord.handle({"kind": "transfer", "task_id": "T3",
                  "transfer": FI.T3["transfer"], "composite_ref": comp_rel})
    fin1 = XC.finish_worlds(host, ["X3-L", "X3-S"], "T3 coalition dissolved")
    # Follow-up reuse elsewhere, still centrally mediated.
    coord.handle({"kind": "fetch", "task_id": "T3-followup",
                  "from": "X3-T", "capability": "sched.reuse",
                  "doc": {"composite_ref": comp_rel}})
    args = host.store_args("X3-T", "t3-reuse", {"task": fol_task,
                                               "derived_from": comp_ref})
    host.invoke("host", "X3-T", "sched.reuse", "1.0", args,
                lambda: XC.write_json(
                    Path(host.state_dir) / "X3-T" / "solutions" / "t3-reuse.json",
                    {"assignment": domain.solve(fol_task)}),
                cost_usd=0.0, time_s=2.0)
    fol = {"task_id": "T3-followup", "assignment": domain.solve(fol_task),
           "derived_from": comp_ref, "arm": "C"}
    fol_ref = XC.write_json(root / "artifacts" / "solution.json", fol)
    coord.handle({"kind": "solution", "task_id": "T3-followup",
                  "doc": {**fol, "derived_from": comp_rel}})
    fin2 = XC.finish_worlds(host, ["X3-T"], "T3 followup done")
    rep = checker.check(fol["assignment"], fol_task)
    lineage_ok = bool(fol.get("derived_from")) and Path(fol["derived_from"]).exists()
    return {"arm": "C", "task": "T3", "central_bytes": coord.central_bytes,
            "direct_bytes": 0, "rounds": 2, "rework": 0,
            "escalations": 0, "valid": rep["valid"],
            "quality": rep["quality"], "prefs_total": rep["prefs_total"],
            "solution_ref": fol_ref, "lineage_ok": lineage_ok,
            "finish": {"coalition": fin1, "followup": fin2}}
