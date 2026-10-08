"""H2-lane interruption recovery (R1 atomic settle + boundaries).

Read-only forensics over the ledger (ledger_index + detect_*) plus
idempotent completion of interrupted settle/fusion/fission through the
SAME host primitives the ops use (transfer/settle/append). Every
completion step is conditional on ledger state, so recovery is itself
crash-safe: a kill during recovery just leaves a smaller partial state,
and re-running recovery converges (proven by the repeated-kill tests).

Scope (see INTERRUPTION-BOUNDARIES.md):
  automated .... birth completion (proposed worlds), fusion completion,
                 fission completion (operator supplies the partition +
                 child names + presets), settle completion.
  detected only  partial quarantine-transfer (LIMITS-3 operator repair),
                 torn ledger lines (disk-loss class), ledgers that fail
                 conservation (fail-closed refusal with operator steps).

Every completion validates EVERYTHING before mutating (the fission
pattern): a refusal leaves zero new partial effects.
"""
from __future__ import annotations

import json
from pathlib import Path

from minihost import ContractViolation, MiniHost, maybe_crash_at
from routing import ChannelRegistry, GRANT_LIMITS, world_record


# ------------------------------------------------------------ forensics

def ledger_index(host: MiniHost) -> dict:
    """Single-pass read-only index of the ledger (no appends)."""
    idx = {"creates": {}, "create_order": [], "grants_to": {},
           "transfers": [], "last_lifecycle": {}, "markers": {},
           "fusions": {}, "fission": {}, "quarantines": {},
           "checkpoints": {}, "n_entries": 0}
    for e in host.ledger_entries():
        idx["n_entries"] += 1
        kind, p = e.get("kind"), e.get("payload", {})
        if kind == "create":
            wid = p.get("world_id", "")
            if wid not in idx["creates"]:
                idx["creates"][wid] = dict(p)
                idx["create_order"].append(wid)
        elif kind == "grant":
            idx["grants_to"].setdefault(p.get("to", ""), []).append(dict(p))
        elif kind == "transfer":
            idx["transfers"].append(e)
        elif kind == "lifecycle":
            idx["last_lifecycle"][p.get("world_id", "")] = p.get("to", "")
        elif kind == "grant_settle":
            wid = p.get("world_id", "")
            idx["markers"][wid] = idx["markers"].get(wid, 0) + 1
        elif kind == "fusion":
            idx["fusions"][p.get("fused_id", "")] = {
                "seq": e.get("seq"), "payload": dict(p)}
        elif kind == "fission":
            idx["fission"][p.get("composite", "")] = {
                "seq": e.get("seq"), "payload": dict(p)}
        elif kind == "quarantine":
            idx["quarantines"][p.get("world_id", "")] = {
                "seq": e.get("seq"), "payload": dict(p)}
        elif kind == "checkpoint":
            idx["checkpoints"].setdefault(
                p.get("world_id", ""), []).append(dict(p))
    return idx


def _fusion_parents_of(create_payload: dict) -> list[str]:
    return [l["world"] for l in create_payload.get("lineage", [])
            if isinstance(l, dict) and l.get("rel") == "derived_from"]


def _has_rel(create_payload: dict, rel: str) -> bool:
    return any(isinstance(l, dict) and l.get("rel") == rel
               for l in create_payload.get("lineage", []))


def detect_partial_fusions(host: MiniHost, idx: dict) -> list[dict]:
    """Composites born by fusion with no ledger `fusion` entry."""
    out = []
    for wid in idx["create_order"]:
        payload = idx["creates"][wid]
        if not _has_rel(payload, "fusion"):
            continue
        if wid in idx["fusions"]:
            continue
        done = [e for e in idx["transfers"]
                if e.get("payload", {}).get("reason") == f"fusion into {wid}"
                and e.get("payload", {}).get("to") == wid]
        out.append({"composite": wid,
                    "parents": _fusion_parents_of(payload),
                    "transfers_done": len(done),
                    "lifecycle": host.worlds[wid].lifecycle
                    if wid in host.worlds else "?",
                    "create_seq": None})
    return out


def detect_partial_fissions(host: MiniHost, idx: dict) -> list[dict]:
    """Composites with fission progress but no ledger `fission` entry."""
    out = []
    candidates: dict[str, dict] = {}
    for e in idx["transfers"]:
        reason = e.get("payload", {}).get("reason", "")
        if reason.startswith("fission of ") and ":" in reason:
            comp = reason[len("fission of "):reason.index(":")]
            candidates.setdefault(comp, {"done": []})["done"].append(e)
    for wid in idx["create_order"]:
        payload = idx["creates"][wid]
        for l in payload.get("lineage", []):
            if isinstance(l, dict) and l.get("rel") == "fission-of":
                comp = l.get("fusion", "")
                if comp:
                    candidates.setdefault(comp, {"done": []})
    for comp, info in candidates.items():
        if comp in idx["fission"]:
            continue
        children = sorted({c for c in idx["create_order"]
                           if any(isinstance(l, dict)
                                  and l.get("rel") == "fission-of"
                                  and l.get("fusion") == comp
                                  for l in idx["creates"][c]
                                  .get("lineage", []))})
        out.append({"composite": comp,
                    "children_created": children,
                    "transfers_done": len(info["done"]),
                    "lifecycle": host.worlds[comp].lifecycle
                    if comp in host.worlds else "?"})
    return out


def detect_partial_quarantines(host: MiniHost, idx: dict) -> list[dict]:
    """Suspended/transferred worlds with no ledger `quarantine` entry.

    Detection keys on quarantine-shaped evidence ONLY (quarantine-reason
    transfers, or suspended + non-empty pending_effects): a plain
    suspend/reattach probe is NOT a partial quarantine.
    """
    out = []
    moved: dict[str, list] = {}
    for e in idx["transfers"]:
        p = e.get("payload", {})
        if str(p.get("reason", "")).startswith("quarantine transfer"):
            moved.setdefault(p.get("from", ""), []).append(e)
    suspects = set(moved)
    for wid, ckpts in idx["checkpoints"].items():
        if wid in host.worlds \
                and host.worlds[wid].lifecycle == "suspended" \
                and ckpts and ckpts[-1].get("pending_effects"):
            suspects.add(wid)
    for wid in sorted(suspects):
        if wid in idx["quarantines"]:
            continue
        pend = idx["checkpoints"].get(wid, [{}])[-1].get(
            "pending_effects", [])
        out.append({"world": wid,
                    "lifecycle": host.worlds[wid].lifecycle
                    if wid in host.worlds else "?",
                    "pending_effects": pend,
                    "transfers_done": [
                        {"state_class": e["payload"].get("state_class"),
                         "to": e["payload"].get("to")}
                        for e in moved.get(wid, [])]})
    return out


def quarantine_operator_steps(partial: dict) -> str:
    w = partial["world"]
    pend = partial["pending_effects"] or []
    standby = pend[0].get("to", "<standby>") if pend else "<standby>"
    done = {t["state_class"] for t in partial["transfers_done"]}
    missing = [c.get("commitment") for c in pend
               if c.get("commitment") not in done]
    return (
        f"partial quarantine of {w}: {len(done)} transfer(s) recorded, "
        f"{len(missing)} pending {missing}, no quarantine entry. "
        f"OPERATOR REPAIR (LIMITS-3; automation out of scope): "
        f"inspect lifecycles/custody via `release.py inspect`, then "
        f"either COMPLETE (transfer remaining {missing} {w}->{standby} "
        f"with actor host + append the quarantine entry) or ROLL BACK "
        f"(transfer {sorted(done)} {standby}->{w} with actor {standby}, "
        f"then reattach {w}); exact recipes in "
        f"INTERRUPTION-BOUNDARIES.md. Recovery will not settle {w} "
        f"until the quarantine entry exists.")


# ------------------------------------------------------ birth completion

def plan_births(host: MiniHost, idx: dict,
                skip: set[str]) -> list[dict]:
    """Plan grant+activate for proposed worlds outside partial ops.

    Pure validation (no mutation): raises ContractViolation when a
    birth cannot be completed (host cannot fund the initial grant).
    """
    plans = []
    for wid in idx["create_order"]:
        if wid in skip or wid not in host.worlds:
            continue
        if host.worlds[wid].lifecycle != "proposed":
            continue
        need_grant = not idx["grants_to"].get(wid)
        if need_grant:
            avail = host.holdings.get("host", {})
            short = [k for k in GRANT_LIMITS
                     if GRANT_LIMITS[k] > avail.get(k, 0) + 1e-9]
            if short:
                raise ContractViolation(
                    f"recovery refused: cannot fund initial grant "
                    f"for proposed world {wid!r} (host short on "
                    f"{short}); operator repair required")
        plans.append({"world": wid, "need_grant": need_grant})
    return plans


def run_births(host: MiniHost, idx: dict, plans: list[dict]) -> list[str]:
    """Execute birth plans (grant-if-missing, then activate)."""
    done = []
    for plan in plans:
        wid = plan["world"]
        if plan["need_grant"]:
            authorities = list(idx["creates"][wid].get("authorities", []))
            host.grant("host", wid, dict(GRANT_LIMITS),
                       authority=authorities, grant_id=f"g-init-{wid}")
        host.transition(wid, "active", "host",
                        reason="recovery: complete interrupted birth")
        done.append(wid)
    return done


# ---------------------------------------------------- fusion completion

def _fusion_done(host: MiniHost, idx: dict, composite: str) -> list[dict]:
    return [{"state_class": e["payload"].get("state_class"),
             "from": e["payload"].get("from"),
             "to": e["payload"].get("to")}
            for e in idx["transfers"]
            if e.get("payload", {}).get("reason") == f"fusion into {composite}"
            and e.get("payload", {}).get("to") == composite]


def complete_fusion(host: MiniHost, composite: str, actor: str = "host",
                    reason: str = "recover") -> dict:
    """Complete an interrupted fusion (validates all, then mutates).

    Parents come from the composite's recorded derived_from lineage;
    remaining transfers/dissolves are derived from ledger state, so the
    completion is deterministic and idempotent (re-running after a kill
    during recovery just finishes a smaller remainder).
    """
    idx = ledger_index(host)
    if composite in idx["fusions"]:
        raise RuntimeError(f"fusion of {composite} already recorded: "
                           f"nothing to complete")
    if composite not in idx["creates"]:
        raise RuntimeError(f"no interrupted fusion of {composite}: "
                           f"never created (nothing to complete)")
    parents = _fusion_parents_of(idx["creates"][composite])
    if len(parents) != 2 or parents[0] == parents[1]:
        raise ContractViolation(
            f"recovery refused: {composite} has no clean 2-parent "
            f"fusion lineage {parents}; operator repair required")
    a, b = parents
    for p in (a, b):
        if p not in host.worlds:
            raise ContractViolation(
                f"recovery refused: fusion parent {p!r} unknown in "
                f"ledger; operator repair required")
    state = host.worlds[composite].lifecycle
    if state not in ("active", "proposed"):
        raise ContractViolation(
            f"recovery refused: composite {composite} is {state}; "
            f"operator repair required")
    done = _fusion_done(host, idx, composite)
    done_sc = {t["state_class"] for t in done}
    if state == "proposed" and done:
        raise ContractViolation(
            f"recovery refused: proposed {composite} already has "
            f"fusion transfers (ledger inconsistent); operator repair")
    need_grant = not idx["grants_to"].get(composite)
    if need_grant:
        avail = host.holdings.get("host", {})
        short = [k for k in GRANT_LIMITS
                 if GRANT_LIMITS[k] > avail.get(k, 0) + 1e-9]
        if short:
            raise ContractViolation(
                f"recovery refused: host cannot fund the initial "
                f"grant for {composite} (short on {short}); "
                f"operator repair required")
    remaining: dict[str, list[str]] = {}
    for giver in (a, b):
        gstate = host.worlds[giver].lifecycle
        if gstate not in ("active", "dissolved"):
            raise ContractViolation(
                f"recovery refused: parent {giver} is {gstate}; "
                f"operator repair required")
        if gstate == "dissolved" and not idx["markers"].get(giver):
            raise ContractViolation(
                f"recovery refused: parent {giver} dissolved with no "
                f"grant_settle marker (fail-closed); operator repair")
        pre = set(host.worlds[giver].custodians) | {
            t["state_class"] for t in done if t["from"] == giver}
        rest = sorted(pre - done_sc)
        if gstate == "dissolved" and rest:
            raise ContractViolation(
                f"recovery refused: dissolved parent {giver} still "
                f"owes transfers {rest} (ledger inconsistent)")
        for sc in rest:
            if host.worlds[giver].custodians.get(sc) != giver:
                raise ContractViolation(
                    f"recovery refused: {sc} not held by {giver} "
                    f"(custody moved since the kill); operator repair")
        remaining[giver] = rest
        if gstate == "active":
            host.check_settleable(giver)  # raises before ANY mutation
    # ---- execute (all validation passed)
    if need_grant:
        authorities = list(idx["creates"][composite]
                           .get("authorities", []))
        host.grant("host", composite, dict(GRANT_LIMITS),
                   authority=authorities,
                   grant_id=f"g-init-{composite}")
    if state == "proposed":
        host.transition(composite, "active", actor,
                        reason="recovery: activate interrupted composite")
    fresh: list[dict] = []
    for giver in (a, b):
        for sc in remaining[giver]:
            host.transfer_custody(sc, giver, composite, actor=giver,
                                  reason=f"fusion into {composite}",
                                  continuity="sha256-of-composite")
            fresh.append({"state_class": sc, "from": giver,
                          "to": composite})
    for giver in (a, b):
        if host.worlds[giver].lifecycle == "active":
            host.transition(giver, "dissolved", actor,
                            reason=f"fused into {composite} "
                                   f"(recovery completion)")
    transfers = done + fresh
    host.append("fusion", {"fused_id": composite, "parents": [a, b],
                           "transfers": transfers,
                           "removed_mechanism": "direct-channel:" +
                           ChannelRegistry.key(a, b),
                           "reason": reason}, actor=actor)
    return {"fused_id": composite, "parents": [a, b],
            "transfers": transfers,
            "removed_mechanism": "direct-channel:" +
            ChannelRegistry.key(a, b),
            "reason": reason, "recovered": True}


# --------------------------------------------------- fission completion

def _fission_done(host: MiniHost, idx: dict, composite: str) -> dict:
    done: dict[str, str] = {}
    for e in idx["transfers"]:
        p = e.get("payload", {})
        if str(p.get("reason", "")).startswith(f"fission of {composite}:") \
                and p.get("from") == composite:
            done[p.get("state_class", "")] = p.get("to", "")
    return done


def _split_nv(items: list[str]) -> list[tuple[str, str]]:
    out = []
    for item in items:
        name, _, version = item.partition("@")
        out.append((name, version))
    return out


def complete_fission(host: MiniHost, state_dir: Path | str,
                     composite: str, left: str, right: str,
                     partition: dict[str, str], left_caps, left_reps,
                     right_caps, right_reps, actor: str = "host",
                     reason: str = "recover") -> dict:
    """Complete an interrupted fission (validates all, then mutates).

    The operator supplies the partition (+ child names + cap/rep specs,
    normally via api presets): they are the partition of record and
    MUST agree with pre-crash progress (recorded transfers, created
    children's lineage) or recovery refuses loudly -- never silently
    diverging from what the kill interrupted.
    """
    idx = ledger_index(host)
    if left == right:
        raise ValueError(f"fission needs two distinct children, "
                         f"got {left!r} twice")
    if composite in idx["fission"]:
        raise RuntimeError(f"fission of {composite} already recorded: "
                           f"nothing to complete")
    if composite not in idx["creates"]:
        raise RuntimeError(f"no interrupted fission of {composite}: "
                           f"never created (nothing to complete)")
    if composite not in idx["fusions"]:
        raise ContractViolation(
            f"recovery refused: {composite} is not a recorded fusion "
            f"composite; operator repair required")
    fusion_parents = list(idx["fusions"][composite]["payload"]
                          .get("parents", []))
    if composite not in host.worlds:
        raise ContractViolation(
            f"recovery refused: {composite} unknown; operator repair")
    cstate = host.worlds[composite].lifecycle
    done = _fission_done(host, idx, composite)
    expected = set(host.worlds[composite].custodians) | set(done)
    # ---- partition validation (mirrors fission_worlds + progress match)
    pkeys = set(partition)
    if pkeys != expected:
        raise ValueError(
            f"recovery partition must cover exactly the composite's "
            f"remaining + transferred classes {sorted(expected)}: "
            f"missing {sorted(expected - pkeys)}, "
            f"unknown {sorted(pkeys - expected)}")
    sides = {left, right}
    bad = {sc: owner for sc, owner in partition.items()
           if owner not in sides}
    if bad:
        raise ValueError(f"recovery partition assigns outside {left}, "
                         f"{right}: {bad}")
    if set(partition.values()) != sides:
        raise ValueError(f"recovery partition must split across BOTH "
                         f"children, got one-sided {partition}")
    for sc, owner in done.items():
        if partition.get(sc) != owner:
            raise RuntimeError(
                f"recovery refused: recorded transfer {sc}->"
                f"{owner} contradicts the supplied partition "
                f"({sc}->{partition.get(sc)}); re-run with the "
                f"partition matching recorded progress")
    # ---- children validation (created children must match the args)
    specs = {left: (left_caps, left_reps, "left"),
             right: (right_caps, right_reps, "right")}
    for child, (caps, reps, side) in specs.items():
        want_side_classes = sorted(sc for sc, o in partition.items()
                                   if o == child)
        if child in idx["creates"]:
            payload = idx["creates"][child]
            named = [l for l in payload.get("lineage", [])
                     if isinstance(l, dict)
                     and l.get("rel") == "fission-of"
                     and l.get("fusion") == composite]
            if not named:
                raise RuntimeError(
                    f"recovery refused: existing world {child} is not "
                    f"a recorded child of {composite}; pass the "
                    f"original child names")
            if named[0].get("side") != side:
                raise RuntimeError(
                    f"recovery refused: {child} was created as side "
                    f"{named[0].get('side')!r}, now passed as {side!r}; "
                    f"pass the original --left/--right assignment")
            if sorted(named[0].get("partition", [])) != want_side_classes:
                raise RuntimeError(
                    f"recovery refused: {child} was created for side "
                    f"{named[0].get('partition')} but the supplied "
                    f"partition gives {want_side_classes}; pass the "
                    f"original partition")
            have_caps = set(payload.get("capabilities", []))
            want_caps = {n + "@" + v for n, v in caps}
            if have_caps != want_caps:
                raise RuntimeError(
                    f"recovery refused: {child} was created with "
                    f"capabilities {sorted(have_caps)}, not the "
                    f"supplied preset {sorted(want_caps)}; pass the "
                    f"original presets")
            if child not in host.worlds:
                raise ContractViolation(
                    f"recovery refused: {child} created but unknown "
                    f"after reopen; operator repair required")
            if host.worlds[child].lifecycle not in ("active", "proposed"):
                raise ContractViolation(
                    f"recovery refused: child {child} is "
                    f"{host.worlds[child].lifecycle}; operator repair")
        else:
            if child in host.worlds:
                raise ContractViolation(
                    f"recovery refused: {child} live but never "
                    f"created in-ledger; operator repair required")
            sdir = (Path(state_dir) / "state" / child).resolve()
            for other in host.worlds.values():
                if Path(other.instance_state_dir).resolve() == sdir:
                    raise ContractViolation(
                        f"recovery refused: state dir for {child} "
                        f"already owned by {other.world_id}")
    # ---- composite end-state validation
    if cstate == "active":
        host.check_settleable(composite)  # raises before ANY mutation
        for sc in sorted(expected - set(done)):
            if host.worlds[composite].custodians.get(sc) != composite:
                raise ContractViolation(
                    f"recovery refused: {sc} not held by "
                    f"{composite} (custody moved since the kill)")
    elif cstate == "dissolved":
        if not idx["markers"].get(composite):
            raise ContractViolation(
                f"recovery refused: {composite} dissolved with no "
                f"grant_settle marker (fail-closed); operator repair")
        if expected - set(done) or host.worlds[composite].custodians:
            raise ContractViolation(
                f"recovery refused: dissolved {composite} still "
                f"holds custody (ledger inconsistent)")
    else:
        raise ContractViolation(
            f"recovery refused: composite {composite} is {cstate}; "
            f"operator repair required")
    missing = [c for c in (left, right) if c not in idx["creates"]]
    if missing:
        avail = host.holdings.get("host", {})
        short = [k for k in GRANT_LIMITS
                 if len(missing) * GRANT_LIMITS[k] > avail.get(k, 0) + 1e-9]
        if short:
            raise ContractViolation(
                f"recovery refused: host cannot fund {len(missing)} "
                f"child grant(s) (short on {short}); operator repair")
    # ---- execute (all validation passed)
    for child, (caps, reps, side) in specs.items():
        if child in idx["creates"]:
            if not idx["grants_to"].get(child):
                authorities = list(idx["creates"][child]
                                   .get("authorities", []))
                host.grant("host", child, dict(GRANT_LIMITS),
                           authority=authorities,
                           grant_id=f"g-init-{child}")
            if host.worlds[child].lifecycle == "proposed":
                host.transition(child, "active", actor,
                                reason="recovery: activate child")
        else:
            side_classes = sorted(sc for sc, o in partition.items()
                                  if o == child)
            rec = world_record(Path(state_dir) / "state", child,
                               list(caps), list(reps))
            rec.lineage = [
                {"rel": "derived_from", "world": composite},
                {"rel": "fission-of", "fusion": composite,
                 "fusion_parents": fusion_parents, "side": side,
                 "partition": side_classes},
                {"rel": "fission", "actor": actor, "reason": reason}]
            host.create_world(rec, "host",
                              grant_limits=dict(GRANT_LIMITS))
            host.transition(child, "active", actor,
                            reason="recovery: fission birth completion")
    fresh: list[dict] = []
    for sc in sorted(expected - set(done)):
        host.transfer_custody(sc, composite, partition[sc],
                              actor=composite,
                              reason=f"fission of {composite}: {reason}",
                              continuity="fission-partition")
        fresh.append({"state_class": sc, "from": composite,
                      "to": partition[sc]})
    if host.worlds[composite].lifecycle == "active":
        host.transition(composite, "dissolved", actor,
                        reason=f"fissioned into {left}+{right} "
                               f"(recovery completion)")
    done_list = [{"state_class": sc, "from": composite, "to": owner}
                 for sc, owner in
                 sorted(done.items(), key=lambda kv: kv[0])]
    transfers = done_list + fresh
    host.append("fission", {"composite": composite,
                            "children": [left, right],
                            "partition": dict(partition),
                            "fusion": {"fused_id": composite,
                                       "parents": fusion_parents},
                            "transfers": transfers,
                            "restored_mechanism": "direct-channel:" +
                            ChannelRegistry.key(left, right),
                            "reason": reason}, actor=actor)
    return {"composite": composite, "children": [left, right],
            "partition": dict(partition),
            "fusion": {"fused_id": composite,
                       "parents": fusion_parents},
            "transfers": transfers,
            "restored_mechanism": "direct-channel:" +
            ChannelRegistry.key(left, right),
            "reason": reason, "recovered": True}


# ---------------------------------------------------------- spec repair

def spec_for_create(payload: dict, custodians: dict) -> dict:
    """Rebuild a worlds.json spec from a ledger `create` payload."""
    return {"world_id": payload["world_id"],
            "caps": [[n, v] for n, v in
                     _split_nv(payload.get("capabilities", []))],
            "reps": [[n, v] for n, v in
                     _split_nv(payload.get("representations", []))],
            "custodians": dict(custodians)}


def missing_specs(host: MiniHost, idx: dict,
                  specs: list[dict]) -> list[str]:
    known = {s["world_id"] for s in specs}
    return [wid for wid in idx["create_order"] if wid not in known]


def repair_specs(root: Path, host: MiniHost, idx: dict,
                 specs: list[dict]) -> list[str]:
    """Append specs for ledger-known worlds missing from worlds.json.

    The ledger `create` payloads are authoritative (code_ref/caps/reps
    match by construction, so the next open_run verifies). Crash point
    `recover:pre-spec` fires before the write (kill-during-recovery
    boundary: re-running repair is idempotent).
    """
    miss = missing_specs(host, idx, specs)
    if not miss:
        return []
    maybe_crash_at("recover:pre-spec")
    for wid in miss:
        specs.append(spec_for_create(
            idx["creates"][wid],
            host.worlds[wid].custodians if wid in host.worlds else {}))
    (root / "worlds.json").write_text(
        json.dumps(specs, indent=2, sort_keys=True) + "\n",
        encoding="utf-8")
    return miss
