"""Arm H: host-local direct negotiation + recovery.

Worlds negotiate DIRECTLY (world-to-world invokes and messages; bytes
counted as direct_bytes, never central). The coordinator sees ONLY
exported commitments and escalations (enforced by HCoordinator, which
refuses anything else). Same recovery machinery as Arm C.

Written obligations (also frozen in WRITTEN-OBLIGATIONS.md):
O1 one fragment per round; O2 proposals cite their basis; O3 authority
conflicts escalate, stale proposals voided only by coordinator ruling;
O4 custody moves direct custodian-to-custodian; O5 each world exports a
terminal commitment for what it agreed to.
"""
from __future__ import annotations

import hashlib
from pathlib import Path

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


class DirectChannel:
    """World-to-world traffic: counted, never shown to the coordinator."""

    def __init__(self) -> None:
        self.direct_bytes = 0
        self.n = 0

    def send(self, msg: dict) -> dict:
        self.direct_bytes += domain.canonical_bytes(msg)
        self.n += 1
        return msg


def _direct_provide(host, caller, callee, cap, payload) -> dict:
    args = host.store_args(callee, cap.replace(".", "-"), payload)
    entry = host.invoke(caller, callee, cap, "1.0", args,
                        lambda: XC.write_json(
                            Path(host.state_dir) / callee / "provided"
                            / f"{cap}.json", payload),
                        cost_usd=0.0, time_s=1.0)
    return {"doc": dict(payload),
            "result_ref": entry["payload"]["result_ref"]}


def _self_solve(host, world, task, name) -> dict:
    args = host.store_args(world, name, {"task": task})
    entry = host.invoke(
        world, world, "sched.solve", "1.0", args,
        lambda: XC.write_json(
            Path(host.state_dir) / world / "solutions" / f"{name}.json",
            {"assignment": domain.solve(task), "task_id": task["task_id"]}),
        cost_usd=0.0, time_s=2.0)
    return {"assignment": domain.solve(task),
            "result_ref": entry["payload"]["result_ref"]}


def run_t1(root: Path) -> dict:
    task = FI.T1
    coord = XC.HCoordinator()
    chan = DirectChannel()
    worlds = t1_worlds(root / "state")
    host = XC.setup_host(root, worlds)
    rounds = 0
    # Direct provides (accountable world-to-world invokes).
    _direct_provide(host, "X3-S", "X3-L", "list.provide",
                    {"task_id": "T1", "list": domain.list_doc(task)})
    _direct_provide(host, "X3-L", "X3-S", "slot.provide",
                    {"task_id": "T1", "slot": domain.slot_doc(task)})
    hold = FI.T1["holdings"]
    ltasks = {t: task["tasks"][t] for t in hold["X3-L"]["req_tasks"]}
    stasks = {t: task["tasks"][t] for t in hold["X3-S"]["req_tasks"]}
    # R1-R3 direct (O1: one fragment per round).
    chan.send(domain.req_fragment("T1", "X3-L", ltasks, task["precedence"]))
    chan.send(domain.req_fragment("T1", "X3-S", stasks, []))
    rounds += 1
    chan.send(domain.pref_fragment(
        "T1", "X3-L", {p: task["prefs"][p] for p in hold["X3-L"]["prefs"]}))
    rounds += 1
    chan.send(domain.pref_fragment(
        "T1", "X3-S", {p: task["prefs"][p] for p in hold["X3-S"]["prefs"]}))
    rounds += 1
    got = _self_solve(host, "X3-L", task, "t1-propose")
    chan.send(domain.proposal("T1", "X3-L", got["assignment"],
                              basis="merged reqs + clarified prefs (O2)"))
    ver = _self_solve(host, "X3-S", task, "t1-verify")
    assert ver["assignment"] == got["assignment"], "direct verify mismatch"
    # O5: export terminal commitments (the ONLY central traffic).
    coord.handle(domain.commitment("T1", "X3-L", got["assignment"],
                                   receipt="O5-L-accept"))
    coord.handle(domain.commitment("T1", "X3-S", got["assignment"],
                                   receipt="O5-S-accept"))
    sol_ref = XC.write_json(root / "artifacts" / "solution.json",
                            {"task_id": "T1", "assignment": got["assignment"],
                             "arm": "H"})
    fin = XC.finish_worlds(host, ["X3-L", "X3-S"], "T1 done")
    rep = checker.check(got["assignment"], task)
    return {"arm": "H", "task": "T1", "central_bytes": coord.central_bytes,
            "direct_bytes": chan.direct_bytes, "direct_messages": chan.n,
            "rounds": rounds, "rework": 0, "escalations": 0,
            "valid": rep["valid"], "quality": rep["quality"],
            "prefs_total": rep["prefs_total"], "solution_ref": sol_ref,
            "finish": fin}


def t2_prekill(root: Path) -> dict:
    task = FI.T2["revised"]
    coord = XC.HCoordinator()
    chan = DirectChannel()
    worlds = t2_worlds(root / "state")
    host = XC.setup_host(root, worlds)
    form_ref = XC.write_json(
        root / "artifacts" / "formulation.json",
        {"task_id": "T2", "base_tasks": FI.T2["base"]["tasks"],
         "precedence": FI.T2["base"]["precedence"], "adapter": "list2slot/v1"})
    for wid in ("X3-L", "X3-S"):
        host.suspend(wid, "host", "T2 pre-revision checkpoint",
                     pending_effects=["adapt-propose"])
    for wid in ("X3-L", "X3-S"):
        host.reattach(wid, "host", "T2 resume after checkpoint")
    # S's in-flight v1 opening proposal (SLOT-view bid, pre-revision).
    stale = XC.write_json(
        root / "artifacts" / "v1-opening-proposal.json",
        {"task_id": "T2", "from": "X3-S", "adapter": "list2slot/v1",
         "bid": {"A": "S0", "B": "S1", "C": "S1", "D": "S2"}})
    # Revision + revocation observed directly by the worlds.
    host.append("revision", {"task_id": "T2", **FI.T2["revision"]}, actor="host")
    host.append("capability_revoked", {"task_id": "T2", **FI.T2["revocation"]},
                actor="host")
    # O3: S's in-flight v1 bid vs L's v2 authority is an authority
    # conflict -> escalate; coordinator ruling voids the stale bid.
    esc = domain.escalation("T2", "X3-S",
                            issue="in-flight v1 bid under revoked slot.assign",
                            options=["honor v1 bid", "void; L re-plans under v2"])
    coord.handle(esc)
    rul = domain.resolution("T2", ruling="void v1 bid; L re-plans under v2",
                            reason="O3: revocation wins; v1 bid predates v2")
    coord.handle(rul)
    chan.send({"kind": "void-notice", "task_id": "T2", "from": "X3-S",
               "voided_ref": str(Path(stale).relative_to(root)),
               "ruling": rul["ruling"]})
    # Direct v2 adaptation, then L (new owner) proposes accountably.
    hold = FI.T2["holdings"]
    chan.send(domain.req_fragment(
        "T2", "X3-L", {t: task["tasks"][t] for t in hold["X3-L"]["req_tasks"]},
        task["precedence"]))
    chan.send(domain.req_fragment(
        "T2", "X3-S", {t: task["tasks"][t] for t in hold["X3-S"]["req_tasks"]},
        []))
    # Worlds apply the revision to local state and re-confirm prefs
    # directly (no central re-fetch: they already hold their own state).
    chan.send(domain.pref_fragment(
        "T2", "X3-L", {p: task["prefs"][p] for p in hold["X3-L"]["prefs"]}))
    chan.send(domain.pref_fragment(
        "T2", "X3-S", {p: task["prefs"][p] for p in hold["X3-S"]["prefs"]}))
    args = host.store_args("X3-L", "t2-adapt-propose",
                           {"formulation_ref": form_ref,
                            "task_version": "v2", "task": task})
    entry = host.invoke(
        "X3-L", "X3-L", "sched.solve", "1.0", args,
        lambda: XC.write_json(
            Path(host.state_dir) / "X3-L" / "solutions" / "t2-propose.json",
            {"assignment": domain.solve(task), "task_id": "T2-v2"}),
        cost_usd=0.0, time_s=2.0)
    chan.send(domain.proposal("T2", "X3-L", domain.solve(task),
                              basis="v2 revision, owner X3-L (O2)"))
    return {"host": host, "coord": coord, "chan": chan, "form_ref": form_ref,
            "propose_ref": entry["payload"]["result_ref"], "task": task}


def t2_resume(host, root: Path, prekill: dict) -> dict:
    task = FI.T2["revised"]
    coord = XC.HCoordinator()
    coord.central_bytes = prekill["central_bytes"]
    chan = DirectChannel()
    chan.direct_bytes = prekill["direct_bytes"]
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
            "X3-L", "X3-L", "sched.solve", "1.0", args,
            lambda: XC.write_json(
                Path(host.state_dir) / "X3-L" / "solutions" / "t2-propose.json",
                {"assignment": domain.solve(task), "task_id": "T2-v2"}),
            cost_usd=0.0, time_s=2.0)
        run = {"assignment": domain.solve(task),
               "result_ref": ent["payload"]["result_ref"]}
        executed.append("adapt-propose")
    else:
        skipped.append("adapt-propose")
    ver = _self_solve(host, "X3-S", task, "t2-verify")
    executed.append("verify")
    assert ver["assignment"] == run["assignment"], "T2 verify mismatch"
    coord.handle(domain.commitment("T2", "X3-L", run["assignment"],
                                   receipt="O5-L-adapt-accept"))
    coord.handle(domain.commitment("T2", "X3-S", run["assignment"],
                                   receipt="O5-S-adapt-accept"))
    sol_ref = XC.write_json(root / "artifacts" / "solution.json",
                            {"task_id": "T2", "task_version": "v2",
                             "assignment": run["assignment"], "arm": "H"})
    fin = XC.finish_worlds(host, ["X3-L", "X3-S"], "T2 done")
    rep = checker.check(run["assignment"], task)
    return {"arm": "H", "task": "T2", "central_bytes": coord.central_bytes,
            "direct_bytes": chan.direct_bytes, "rounds": 3,
            "rework": re_executed, "escalations": 1,
            "valid": rep["valid"], "quality": rep["quality"],
            "prefs_total": rep["prefs_total"], "solution_ref": sol_ref,
            "skipped": skipped, "executed": executed,
            "resume_zero_rework": re_executed == 0, "finish": fin}


def run_t3(root: Path) -> dict:
    comp_task = FI.T3["composite_task"]
    fol_task = FI.T3["followup"]
    coord = XC.HCoordinator()
    chan = DirectChannel()
    worlds = t3_worlds(root / "state")
    host = XC.setup_host(root, worlds)
    got = _self_solve(host, "X3-L", comp_task, "t3-composite")
    composite = {"task_id": "T3-composite", "assignment": got["assignment"],
                 "derived_from": {"task": "T1", "inputs": "frozen"},
                 "arm": "H"}
    comp_ref = XC.write_json(root / "artifacts" / "composite.json", composite)
    # O4: direct custodian-to-custodian custody move (actor = giver).
    chan.send({"kind": "handoff", "task_id": "T3", "from": "X3-S",
               "to": "X3-T",
               "composite_ref": str(Path(comp_ref).relative_to(root))})
    host.transfer_custody(FI.T3["transfer"]["state_class"],
                          FI.T3["transfer"]["from"], FI.T3["transfer"]["to"],
                          FI.T3["transfer"]["from"], reason="T3 direct transfer",
                          continuity="sha256:" + hashlib.sha256(
                              Path(comp_ref).read_bytes()).hexdigest())
    coord.handle(domain.commitment("T3", "X3-S", got["assignment"],
                                   receipt="O5-S-transfer-complete"))
    fin1 = XC.finish_worlds(host, ["X3-L", "X3-S"], "T3 coalition dissolved")
    # Follow-up reuse elsewhere; coordinator sees only the commitment.
    args = host.store_args("X3-T", "t3-reuse", {"task": fol_task,
                                               "derived_from": comp_ref})
    host.invoke("X3-T", "X3-T", "sched.reuse", "1.0", args,
                lambda: XC.write_json(
                    Path(host.state_dir) / "X3-T" / "solutions" / "t3-reuse.json",
                    {"assignment": domain.solve(fol_task)}),
                cost_usd=0.0, time_s=2.0)
    fol = {"task_id": "T3-followup", "assignment": domain.solve(fol_task),
           "derived_from": comp_ref, "arm": "H"}
    fol_ref = XC.write_json(root / "artifacts" / "solution.json", fol)
    coord.handle(domain.commitment("T3-followup", "X3-T", fol["assignment"],
                                   receipt="O5-T-reuse-complete"))
    fin2 = XC.finish_worlds(host, ["X3-T"], "T3 followup done")
    rep = checker.check(fol["assignment"], fol_task)
    lineage_ok = bool(fol.get("derived_from")) and Path(fol["derived_from"]).exists()
    return {"arm": "H", "task": "T3", "central_bytes": coord.central_bytes,
            "direct_bytes": chan.direct_bytes, "rounds": 2, "rework": 0,
            "escalations": 0, "valid": rep["valid"],
            "quality": rep["quality"], "prefs_total": rep["prefs_total"],
            "solution_ref": fol_ref, "lineage_ok": lineage_ok,
            "finish": {"coalition": fin1, "followup": fin2}}
