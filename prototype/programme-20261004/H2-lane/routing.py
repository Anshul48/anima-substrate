"""H2-lane hybrid coordination (successor-003 lineage + H2 delta).

Central default + explicit logged routing rule: multi-round dialogue
over split state goes to the local-negotiation lane; everything else
stays central. Routing decisions are recorded per task (ledger
`routing` entries + a run-local routing log).

X3 evidence incorporated: central wins small (S1-shape), local wins
dialogue-heavy (S2-shape). The rule below encodes exactly that cut.

H2 delta (L2-DESIGN §5, three additive items): lane-task routing
inputs are DERIVED from holdings content (H2.2, rule form unchanged);
an optional per-task lane_override hook (H2.3, inert-when-unset)
forces the final lane; novel lane-task JSON is schema-validated
(H2.1, see validate_lane_task). Non-lane descriptors (S3 wrappers,
follow-up sentinels) keep the legacy declared-field path.
"""
from __future__ import annotations

import copy
import json
from pathlib import Path

from minihost import (ContractViolation, MiniCapability, MiniHost,
                      MiniRepresentation, MiniWorldRecord)

import sched_domain as domain

GRANT_LIMITS = {"max_cost_usd": 1.0, "max_time_s": 60.0,
                "max_invocations": 100}

CODE_REF = "H2-lane/routing.py"

# ---------------------------------------------------------------- rule
# H2.2/H2.3: derived routing inputs + lane-override hook. The rule FORM
# (local iff rounds>=2 AND split else central) is unchanged; only the
# input source changes (derived from holdings for lane tasks).

LOCAL_MIN_ROUNDS = 2

LANE_TASK_REQUIRED_KEYS = ("task_id", "slots", "tasks", "precedence",
                           "prefs", "holdings", "adapter")
LANE_WORLDS = ("SC-L", "SC-S")
LANE_ADAPTERS = ("list2slot/v1", "list2slot/v2")
LANE_OVERRIDES = ("central", "local")

DERIVED_RULE = "local iff rounds>=2 AND split else central"
LEGACY_RULE = "local iff expected_rounds>=2 AND split_state else central"


def is_lane_task(task: dict) -> bool:
    """True when the descriptor carries a sched grid (lane-task shape).

    Lane tasks always carry `tasks` (the grid); revision wrappers such
    as S3 carry base/revised/holdings but no grid `tasks` and stay on
    the legacy declared-field path (S3/S4/S6 routing unchanged).
    """
    return isinstance(task, dict) and "tasks" in task


def validate_lane_task(task: dict, source: str = "task") -> dict:
    """Schema-validate a novel lane-task descriptor (H2.1).

    Required keys: task_id, slots, tasks, precedence, prefs, holdings,
    adapter. Holdings must name exactly worlds SC-L + SC-S and must
    partition EXACTLY the grid's tasks/prefs (every task/pref held
    once, nothing missing, nothing extra, nothing unknown).

    Raises ValueError naming every defect (loud, before any run work).
    Returns the task unchanged on success.
    """
    if not isinstance(task, dict):
        raise ValueError(f"invalid lane task {source}: not a JSON object")
    missing = [k for k in LANE_TASK_REQUIRED_KEYS if k not in task]
    if missing:
        raise ValueError(f"invalid lane task {source}: missing required "
                         f"key(s) {missing}")
    defects: list[str] = []
    tid = task.get("task_id")
    if not isinstance(tid, str) or not tid:
        defects.append("task_id must be a non-empty string")
    slots = task.get("slots")
    if not isinstance(slots, dict) or not slots:
        defects.append("slots must be a non-empty object")
        slots = {}
    else:
        for sid, spec in slots.items():
            if not isinstance(spec, dict) or "machine" not in spec \
                    or "time" not in spec:
                defects.append(
                    f"slot {sid!r} must define machine+time")
    grid = task.get("tasks")
    if not isinstance(grid, dict) or not grid:
        defects.append("tasks must be a non-empty object")
        grid = {}
    else:
        for name, req in grid.items():
            win = req.get("window") if isinstance(req, dict) else None
            if not isinstance(win, list) or not win:
                defects.append(f"task {name!r} must have a non-empty "
                               f"window list")
            else:
                for sid in win:
                    if sid not in slots:
                        defects.append(
                            f"task {name!r} window references unknown "
                            f"slot {sid!r}")
    prec = task.get("precedence")
    if not isinstance(prec, list):
        defects.append("precedence must be a list of [a, b] pairs")
    else:
        for pair in prec:
            if not isinstance(pair, (list, tuple)) or len(pair) != 2 \
                    or pair[0] not in grid or pair[1] not in grid:
                defects.append(f"precedence pair {pair!r} must name two "
                               f"known tasks")
    prefs = task.get("prefs")
    if not isinstance(prefs, dict):
        defects.append("prefs must be an object")
        prefs = {}
    else:
        for p, m in prefs.items():
            if p not in grid:
                defects.append(f"pref {p!r} names an unknown task")
            if not isinstance(m, str):
                defects.append(f"pref {p!r} machine must be a string")
    if task.get("adapter") not in LANE_ADAPTERS:
        defects.append(f"adapter must be one of {list(LANE_ADAPTERS)}")
    hold = task.get("holdings")
    if not isinstance(hold, dict) or set(hold) != set(LANE_WORLDS):
        defects.append(f"holdings must hold exactly worlds "
                       f"{list(LANE_WORLDS)}")
    else:
        seen_req: list[str] = []
        seen_pref: list[str] = []
        for side in LANE_WORLDS:
            part = hold.get(side)
            if not isinstance(part, dict):
                defects.append(f"holdings.{side} must be an object")
                continue
            reqs = part.get("req_tasks")
            prfs = part.get("prefs")
            if not isinstance(reqs, list) or not isinstance(prfs, list):
                defects.append(f"holdings.{side} must define req_tasks "
                               f"+ prefs lists")
                continue
            for t in reqs:
                if t not in grid:
                    defects.append(
                        f"holdings.{side} req_tasks references unknown "
                        f"task {t!r}")
            for p in prfs:
                if p not in prefs:
                    defects.append(
                        f"holdings.{side} prefs references unknown "
                        f"pref {p!r}")
            seen_req.extend(reqs)
            seen_pref.extend(prfs)
        if sorted(seen_req) != sorted(grid):
            defects.append("holdings req_tasks must partition exactly "
                           "the grid tasks")
        if sorted(seen_pref) != sorted(prefs):
            defects.append("holdings prefs must partition exactly the "
                           "grid prefs")
        if len(set(seen_req)) != len(seen_req):
            defects.append("holdings req_tasks holds a task more than "
                           "once")
        if len(set(seen_pref)) != len(seen_pref):
            defects.append("holdings prefs holds a pref more than once")
    if defects:
        raise ValueError(
            f"invalid lane task {source} "
            f"({tid if isinstance(tid, str) and tid else '?'}): "
            + "; ".join(defects))
    return task


def derive_routing_inputs(task: dict) -> dict:
    """Derive routing inputs from validated lane-task content (H2.2).

    derived_rounds = number of clarify rounds the holdings partition
    yields (pipeline.fragment_rounds — the SAME function the pipeline
    executes, so derivation cannot drift from execution);
    derived_split = both holdings sides hold something (req_tasks OR
    prefs non-empty on each side).
    """
    from pipeline import fragment_rounds  # deferred: pipeline imports routing
    validate_lane_task(task)
    hold = task["holdings"]

    def _held(side: str) -> bool:
        return bool(hold[side].get("req_tasks")) \
            or bool(hold[side].get("prefs"))

    return {"derived_rounds": len(fragment_rounds(task)),
            "derived_split": bool(_held("SC-L") and _held("SC-S"))}


def route(task: dict, lane_override: str | None = None) -> dict:
    """Apply the hybrid routing rule. Central default; local iff the task
    needs multi-round dialogue (>=2 clarification rounds) over state
    split across worlds.

    H2: lane tasks (grid descriptors) route on DERIVED inputs (see
    derive_routing_inputs); declared expected_rounds/split_state are
    ignored (never trusted, never an error) and recorded under
    declared_ignored. lane_override in {central, local, None} (H2.3):
    None (default) = the rule decides (inert-when-unset); otherwise
    the final lane is forced and the decision records {rule_lane,
    override, final_lane}. Non-lane descriptors keep the legacy
    declared-field rule (S3/S4/S6 routing unchanged).
    """
    if lane_override is not None and lane_override not in LANE_OVERRIDES:
        raise ValueError(f"lane_override must be one of "
                         f"{list(LANE_OVERRIDES)} or None, got "
                         f"{lane_override!r}")
    if is_lane_task(task):
        derived = derive_routing_inputs(task)
        rounds, split = derived["derived_rounds"], derived["derived_split"]
        if rounds >= LOCAL_MIN_ROUNDS and split:
            rule_lane = "local"
            reason = (f"multi-round dialogue (derived_rounds={rounds}>=2) "
                      f"over split holdings -> local-negotiation lane "
                      f"(X3 H3a cut; inputs derived from holdings)")
        else:
            rule_lane = "central"
            reason = (f"default central (derived_rounds={rounds}, "
                      f"derived_split={split}; local requires >=2 rounds "
                      f"AND split holdings; inputs derived from holdings)")
        decision = {
            "task_id": task.get("task_id", "?"), "rule": DERIVED_RULE,
            "inputs": dict(derived), "inputs_derived_from": "holdings",
            "declared_ignored": {
                k: task[k] for k in ("expected_rounds", "split_state")
                if k in task},
            "reason": reason}
    else:
        rounds = int(task.get("expected_rounds", 1))
        split = bool(task.get("split_state", False))
        if rounds >= LOCAL_MIN_ROUNDS and split:
            rule_lane = "local"
            reason = (f"multi-round dialogue ({rounds}>=2 rounds) over "
                      f"split state -> local-negotiation lane (X3 H3a cut)")
        else:
            rule_lane = "central"
            reason = (f"default central (rounds={rounds}, split={split}; "
                      f"local requires >=2 rounds AND split state)")
        decision = {
            "task_id": task.get("task_id", "?"), "rule": LEGACY_RULE,
            "inputs": {"expected_rounds": rounds, "split_state": split},
            "reason": reason}
    final_lane = lane_override if lane_override is not None else rule_lane
    decision.update({"lane": final_lane, "rule_lane": rule_lane,
                     "override": lane_override is not None,
                     "final_lane": final_lane})
    if lane_override is not None:
        decision["reason"] += (f" [caller lane_override={lane_override} "
                               f"-> final_lane={final_lane}]")
    return decision


def record_routing(host: MiniHost, decision: dict, log_path: Path) -> dict:
    """Ledger the routing decision AND append to the run routing log."""
    entry = host.append("routing", dict(decision), actor="host")
    log_path.parent.mkdir(parents=True, exist_ok=True)
    with open(log_path, "a", encoding="utf-8") as fh:
        fh.write(json.dumps(decision, sort_keys=True) + "\n")
    return entry


# ------------------------------------------------------- coordinators

class Coordinator:
    """Central context meter: every message the coordinator handles counts."""

    def __init__(self) -> None:
        self.central_bytes = 0
        self.handled: list[dict] = []

    def handle(self, msg: dict) -> dict:
        n = domain.canonical_bytes(msg)
        self.central_bytes += n
        self.handled.append({"kind": msg.get("kind"), "bytes": n})
        return msg


class HCoordinator(Coordinator):
    """Local-lane coordinator: sees ONLY commitments, escalations and
    resolutions. Any other payload is refused (mechanism guard: local
    state stays local; direct world traffic bypasses this object)."""

    ALLOWED = ("commitment", "escalation", "resolution")

    def handle(self, msg: dict) -> dict:
        if msg.get("kind") not in self.ALLOWED:
            raise ValueError(f"coordinator refused non-export payload "
                             f"{msg.get('kind')!r}: local state stays local")
        return super().handle(msg)


class DirectChannel:
    """World-to-world traffic: counted, never shown to the coordinator."""

    def __init__(self, name: str) -> None:
        self.name = name
        self.direct_bytes = 0
        self.n = 0
        self.removed = False

    def send(self, msg: dict) -> dict:
        if self.removed:
            raise RuntimeError(f"direct channel {self.name} was removed "
                               f"(fused pair communicates internally now)")
        self.direct_bytes += domain.canonical_bytes(msg)
        self.n += 1
        return msg


class ChannelRegistry:
    """Named direct channels between world pairs. Fusion removes the
    channel between the fused pair (the now-redundant mechanism)."""

    def __init__(self) -> None:
        self.channels: dict[str, DirectChannel] = {}

    @staticmethod
    def key(a: str, b: str) -> str:
        return "<->".join(sorted([a, b]))

    def get(self, a: str, b: str) -> DirectChannel:
        k = self.key(a, b)
        if k not in self.channels:
            self.channels[k] = DirectChannel(k)
        return self.channels[k]

    def remove(self, a: str, b: str) -> DirectChannel:
        k = self.key(a, b)
        chan = self.channels.pop(k)
        chan.removed = True
        return chan

    def inventory(self) -> dict:
        return {k: {"direct_bytes": c.direct_bytes, "messages": c.n}
                for k, c in sorted(self.channels.items())}


# ------------------------------------------------------------- setup

def world_record(state_dir: Path, world_id: str, caps: list[tuple[str, str]],
                 reps: list[tuple[str, str]], custodians: dict | None = None,
                 authorities: list | None = None,
                 lineage: list | None = None) -> MiniWorldRecord:
    return MiniWorldRecord(
        world_id=world_id, lineage=list(lineage or [("host", "created",
                                                     "H2-lane")]),
        code_ref=f"{CODE_REF}:{world_id}",
        instance_state_dir=str(Path(state_dir) / world_id),
        custodians=dict(custodians or {}),
        capabilities=[MiniCapability(n, v) for n, v in caps],
        representations=[MiniRepresentation(n, v) for n, v in reps],
        authorities=list(authorities or []))


def setup_host(root: Path, worlds: list[MiniWorldRecord]) -> MiniHost:
    host = MiniHost(root / "state", root / "ledger.jsonl")
    for rec in worlds:
        host.create_world(rec, "host", grant_limits=dict(GRANT_LIMITS))
        host.transition(rec.world_id, "active", "host", reason="setup")
    return host


def rebuild_records(root: Path,
                    worlds: list[MiniWorldRecord]) -> list[MiniWorldRecord]:
    """Fresh descriptors for reopen (same bytes as setup: verifiable)."""
    return [world_record(root / "state", r.world_id,
                         [(c.name, c.version) for c in r.capabilities],
                         [(x.name, x.version) for x in r.representations],
                         dict(r.custodians), list(r.authorities),
                         copy.deepcopy(r.lineage))
            for r in worlds]


def write_json(path: Path, obj: dict) -> str:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(obj, indent=2, sort_keys=True) + "\n",
                    encoding="utf-8")
    return str(path)


def finish_worlds(host: MiniHost, world_ids: list[str], reason: str) -> dict:
    """Settle-then-dissolve every world; verify conservation + 0 stranded.

    Successor-003 (R1): ATOMIC on refusal. Phase 1 validates the whole
    batch before ANY dissolve: the ledger must already conserve (a
    pre-existing unsettled terminal refuses here instead of stranding
    fresh dissolves), and every world must pass check_settleable
    (known, active/suspended, reattachable, zero residual). A refusal
    raises ContractViolation with ZERO partial dissolves -- only a
    `deny` entry is recorded. Phase 2 executes. Single-machine /
    no-multi-writer (LIMITS-2) means no TOCTOU between the phases;
    kill-during-execution is the defined interruption boundary (see
    INTERRUPTION-BOUNDARIES.md; recovery via api.recover_op).
    """
    try:
        host.verify_conservation()
    except ContractViolation as exc:
        host.deny("host", "settle",
                  f"settle refused batch {list(world_ids)}: {exc}")
        raise ContractViolation(
            f"settle refused: ledger not conserving before settle "
            f"({exc}); zero worlds dissolved") from exc
    for wid in world_ids:
        try:
            host.check_settleable(wid)
        except ContractViolation as exc:
            host.deny("host", "settle",
                      f"settle refused batch {list(world_ids)}: {exc}")
            raise ContractViolation(
                f"settle refused: {exc}; zero worlds dissolved") from exc
    for wid in world_ids:
        if host.worlds[wid].lifecycle == "suspended":
            host.reattach(wid, "host", reason="finish reattach")
        host.transition(wid, "dissolved", "host", reason=reason)
    stranded = {w: dict(host.holdings[w]) for w in world_ids}
    assert all(v == 0 for h in stranded.values() for v in h.values()), \
        f"stranded holdings: {stranded}"
    rep = host.verify_conservation()
    assert rep["ok"]
    n_settle = sum(1 for e in host.ledger_entries()
                   if e.get("kind") == "grant_settle")
    return {"stranded": stranded, "settled_terminals": rep["settled_terminals"],
            "grant_settle_markers": n_settle, "conservation_ok": True}
