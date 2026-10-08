"""Hardened host for the W1 pilot (SUBSTRATE, Alternative C). Stdlib-only.

Adapted copy of prototype/w1/HOST.py (frozen per FREEZE.w1). Behavioral
deltas vs w1, all covered by test_w1_harden.py / test_failures.py /
test_recovery.py:

1. Grant auto-settle: transition() into dissolved/retired first returns all
   unused holdings to each grantor (one grant_return per grant, distributed
   against grant limits) and appends a balance-neutral `grant_settle`
   marker. No more stranded holdings on terminal worlds.
2. Conservation replay honors `grant_settle` (marker only, never
   double-counted; bad envelope refused) and raises
   ContractViolation("unsettled terminal ...") when a world whose last
   lifecycle state is dissolved/retired has no matching marker.
3. Host.reopen(): rebuild a live Host over an existing state dir + ledger
   after a crash/kill, purely by replaying the ledger (no guessing). Full
   capability descriptors are re-supplied by the recovering process and
   verified against the ledger; worlds without supplied descriptors are
   restored ledger-only with authority metadata withheld (non-host invokes
   denied). Edge rule R-REOPEN is documented on reopen() and in
   RECOVERY-REUSE.md.
4. Windows-safe paths: state-dir ownership compares use Path.resolve()
   (symlink/case aliasing) instead of os.path.abspath.

Every refusal is a recorded ledger denial, never silent.
"""
from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path

try:
    from . import contract
    from .contract import (
        CONTRACT_VERSION,
        Capability,
        ContractViolation,
        Relationship,
        Representation,
        WorldRecord,
        check_lifecycle_edge,
        utcnow,
    )
except ImportError:  # running from the package dir (w1-harden/ is not a dotted package)
    import contract
    from contract import (
        CONTRACT_VERSION,
        Capability,
        ContractViolation,
        Relationship,
        Representation,
        WorldRecord,
        check_lifecycle_edge,
        utcnow,
    )

RESOURCE_KEYS = ("max_cost_usd", "max_time_s", "max_invocations")

TERMINAL_STATES = ("dissolved", "retired")

# Authority stamp for ledger-only (descriptor-withheld) capabilities rebuilt
# by reopen() without caller-supplied records. No world holds this authority,
# so non-host invokes against such capabilities are denied (fail closed);
# only the host principal (which bypasses authority checks by design) may
# invoke them, e.g. for inspection during recovery.
WITHHELD_AUTHORITY = "recovery.withheld"


def _zero_holdings() -> dict:
    return {"max_cost_usd": 0.0, "max_time_s": 0.0, "max_invocations": 0}


def _limits_normalized(limits: dict) -> dict:
    out = _zero_holdings()
    for key in RESOURCE_KEYS:
        if key in limits and limits[key] is not None:
            out[key] = limits[key]
    return out


class Host:
    """Registry + ledger + accountable invocation. All state under state_dir."""

    def __init__(self, state_dir: str | os.PathLike, ledger_path: str | os.PathLike,
                 root_holdings: dict | None = None) -> None:
        self.state_dir = Path(state_dir)
        self.state_dir.mkdir(parents=True, exist_ok=True)
        self.ledger_path = Path(ledger_path)
        self.ledger_path.parent.mkdir(parents=True, exist_ok=True)
        if not self.ledger_path.exists():
            self.ledger_path.write_text("", encoding="utf-8")
        self.worlds: dict[str, WorldRecord] = {}
        self.holdings: dict[str, dict] = {}  # world_id -> current holding
        self.holdings_initial: dict[str, dict] = {}
        self.grants_out: dict[str, list[dict]] = {}  # parent -> grant dicts
        self.consumed: dict[str, dict] = {}  # world_id -> consumed totals
        self.relationships: dict[str, dict[str, Relationship]] = {}  # rel_id -> version -> rel
        self._seq = 0
        self._retired_ids: set[str] = set()
        # Root principal holds the initial budget everything else delegates from.
        root = dict(_zero_holdings())
        root.update(root_holdings or {"max_cost_usd": 10.0, "max_time_s": 600.0,
                                      "max_invocations": 1000})
        self.holdings["host"] = dict(root)
        self.holdings_initial["host"] = dict(root)
        self.consumed["host"] = _zero_holdings()
        self._append("host_init", {"root_holdings": root}, actor="host")

    # -- ledger ------------------------------------------------------------
    def _append(self, kind: str, payload: dict, actor: str) -> dict:
        self._seq += 1
        entry = {"seq": self._seq, "at": utcnow(), "kind": kind,
                 "contract_version": CONTRACT_VERSION, "actor": actor,
                 "payload": payload}
        with open(self.ledger_path, "a", encoding="utf-8") as fh:
            fh.write(json.dumps(entry, sort_keys=True) + "\n")
        return entry

    def ledger_entries(self) -> list[dict]:
        out = []
        with open(self.ledger_path, encoding="utf-8") as fh:
            for line in fh:
                line = line.strip()
                if line:
                    out.append(json.loads(line))
        return out

    def deny(self, actor: str, action: str, reason: str, detail: dict | None = None) -> dict:
        payload = {"action": action, "reason": reason}
        if detail:
            payload.update(detail)
        return self._append("deny", payload, actor=actor)

    # -- worlds ------------------------------------------------------------
    def create_world(self, record: WorldRecord, creator: str,
                     grant_limits: dict | None = None) -> WorldRecord:
        record.validate()
        if record.world_id in self.worlds or record.world_id in self._retired_ids:
            self.deny(creator, "world.create",
                      f"world_id {record.world_id!r} already used (ids never reused)")
            raise ContractViolation(f"world_id {record.world_id!r} already used")
        for other in self.worlds.values():
            if (Path(other.instance_state_dir).resolve()
                    == Path(record.instance_state_dir).resolve()):
                self.deny(creator, "world.create",
                          "state dir already owned by " + other.world_id)
                raise ContractViolation("distinct worlds MUST NOT share a state dir")
        if creator != "host":
            parent = self.worlds.get(creator)
            if parent is None:
                self.deny(creator, "world.create", f"unknown creator {creator!r}")
                raise ContractViolation(f"unknown creator {creator!r}")
            if "world.create" not in parent.authorities:
                self.deny(creator, "world.create",
                          f"{creator!r} lacks world.create authority")
                raise ContractViolation(f"{creator!r} lacks world.create authority")
        Path(record.instance_state_dir).mkdir(parents=True, exist_ok=True)
        self.worlds[record.world_id] = record
        self.holdings[record.world_id] = _zero_holdings()
        self.holdings_initial[record.world_id] = _zero_holdings()
        self.consumed[record.world_id] = _zero_holdings()
        self._append("create", {
            "world_id": record.world_id, "creator": creator,
            "code_ref": record.code_ref,
            "instance_state_dir": record.instance_state_dir,
            "custodians": record.custodians,
            "authorities": record.authorities,
            "capabilities": [c.name + "@" + c.version for c in record.capabilities],
            "representations": [r.name + "@" + r.version for r in record.representations],
            "lineage": record.lineage,
        }, actor=creator)
        if grant_limits:
            self.grant(creator, record.world_id, grant_limits,
                       authority=list(record.authorities), grant_id=f"g-init-{record.world_id}")
        return record

    @classmethod
    def reopen(cls, state_dir: str | os.PathLike, ledger_path: str | os.PathLike,
               records: list[WorldRecord] | None = None,
               actor: str = "host", reason: str = "reopen after interruption") -> "Host":
        """Rebuild a live Host over an existing state dir + ledger.

        Used after a crash/kill: the recovering process calls reopen() on the
        SAME state_dir/ledger_path instead of constructing a fresh Host (which
        would append a second host_init and corrupt conservation replay).

        Edge rule R-REOPEN (recovery contract):
        - Registry, holdings, consumed totals, grants, custodians, lifecycle
          states, and retired ids are rebuilt PURELY by replaying the ledger
          in seq order. Nothing is guessed; no lifecycle edge is traversed
          (reopen appends no lifecycle entries — worlds simply resume at
          their last ledger-recorded state).
        - There is NO active->active "resume" edge and reopen does not need
          one: a world whose last ledger state is `active` is already active
          and continues by reusing on-disk artifacts + ledger proof of
          completed steps (see recovery_lib.resume_to_verdict). A world whose
          last ledger state is `suspended` continues via the ordinary
          contract edge suspended->active through reattach(), which still
          requires a verified on-disk checkpoint (identity: world_id +
          code_ref + contract_version).
        - Full capability/representation descriptors are NOT in the ledger
          (create entries carry name@version only). The recovering process
          re-supplies them via `records` (the same code constants that
          created the worlds); each supplied record is VERIFIED against the
          ledger (world_id known, code_ref equal, capability and
          representation name@version sets equal) and adopted with its
          replayed lifecycle + custodians. Mismatch -> recorded deny +
          ContractViolation.
        - Worlds with no supplied record are restored ledger-only (names +
          versions known, authority metadata WITHHELD): their capabilities
          carry required_authority="recovery.withheld", so non-host invokes
          are denied fail-closed until the world is reopened with descriptors.
        - A balance-neutral `host_reopen` marker is appended (seq continues
          past the replayed max; conservation replay ignores it). Reopen is
          re-runnable: each call replays from scratch and appends one marker.
        """
        obj = cls.__new__(cls)
        obj.state_dir = Path(state_dir)
        obj.ledger_path = Path(ledger_path)
        if not obj.ledger_path.exists():
            raise ContractViolation(f"reopen: missing ledger {obj.ledger_path}")
        obj.worlds = {}
        obj.holdings = {}
        obj.holdings_initial = {}
        obj.grants_out = {}
        obj.consumed = {}
        obj.relationships = {}
        obj._seq = 0
        obj._retired_ids = set()
        creates: dict[str, dict] = {}
        last_lifecycle: dict[str, str] = {}
        custodians: dict[str, dict] = {}
        n_replayed = 0
        for e in obj.ledger_entries():
            n_replayed += 1
            obj._seq = max(obj._seq, int(e.get("seq", 0)))
            kind, payload = e.get("kind"), e.get("payload", {})
            if kind == "host_init":
                root = _limits_normalized(payload.get("root_holdings", {}))
                obj.holdings["host"] = dict(root)
                obj.holdings_initial["host"] = dict(root)
                obj.consumed.setdefault("host", _zero_holdings())
            elif kind == "create":
                wid = payload.get("world_id", "")
                creates[wid] = dict(payload)
                custodians[wid] = dict(payload.get("custodians", {}))
                obj.holdings.setdefault(wid, _zero_holdings())
                obj.holdings_initial.setdefault(wid, _zero_holdings())
                obj.consumed.setdefault(wid, _zero_holdings())
            elif kind == "lifecycle":
                wid = payload.get("world_id", "")
                last_lifecycle[wid] = payload.get("to", "")
                if payload.get("to") == "retired":
                    obj._retired_ids.add(wid)
            elif kind == "grant":
                frm, to = payload.get("from", ""), payload.get("to", "")
                limits = _limits_normalized(payload.get("limits", {}))
                for key in RESOURCE_KEYS:
                    obj.holdings.setdefault(frm, _zero_holdings())[key] -= limits[key]
                    obj.holdings.setdefault(to, _zero_holdings())[key] += limits[key]
                obj.grants_out.setdefault(frm, []).append({
                    "grant_id": payload.get("grant_id", ""), "from": frm,
                    "to": to, "limits": limits,
                    "authority": payload.get("authority", []),
                    "at": payload.get("at", ""),
                    "expires": payload.get("expires")})
            elif kind == "grant_return":
                frm, to = payload.get("from", ""), payload.get("to", "")
                amounts = _limits_normalized(payload.get("amounts", {}))
                for key in RESOURCE_KEYS:
                    obj.holdings.setdefault(frm, _zero_holdings())[key] -= amounts[key]
                    obj.holdings.setdefault(to, _zero_holdings())[key] += amounts[key]
            elif kind == "consume":
                wid = payload.get("world_id", "")
                for key in RESOURCE_KEYS:
                    use = payload.get(key, 0)
                    obj.holdings.setdefault(wid, _zero_holdings())[key] -= use
                    obj.consumed.setdefault(wid, _zero_holdings())[key] += use
            elif kind == "transfer":
                frm, to = payload.get("from", ""), payload.get("to", "")
                state_class = payload.get("state_class", "")
                if frm in custodians:
                    custodians[frm].pop(state_class, None)
                if to != "host" and to in custodians:
                    custodians[to][state_class] = to
            elif kind == "relationship":
                mapping = payload.get("mapping", {})
                rel = Relationship(
                    rel_id=payload.get("rel_id", ""),
                    version=payload.get("version", ""),
                    participants=list(payload.get("participants", [])),
                    purpose=payload.get("purpose", ""),
                    mapping_from=mapping.get("from", ""),
                    mapping_to=mapping.get("to", ""),
                    mapping_ref=mapping.get("ref", ""),
                    losses_declared=list(mapping.get("losses", [])),
                    protocol=payload.get("protocol", ""),
                    authority_granted=list(payload.get("authority_granted", [])),
                    state=payload.get("state", "proposed"))
                obj.relationships.setdefault(rel.rel_id, {})[rel.version] = rel
            # grant_settle / host_reopen / checkpoint / reattach / invoke /
            # deny / create: balance-neutral or already handled; ignored.
        obj.holdings.setdefault("host", _zero_holdings())
        obj.holdings_initial.setdefault("host", _zero_holdings())
        obj.consumed.setdefault("host", _zero_holdings())

        def _names(items: list[str]) -> set[str]:
            return set(items)

        supplied = {r.world_id: r for r in (records or [])}
        for wid in supplied:
            if wid not in creates:
                obj.deny(actor, "reopen",
                         f"supplied record for unknown world {wid!r} "
                         f"(never created in this ledger)")
                raise ContractViolation(
                    f"reopen: {wid!r} was never created in this ledger; "
                    f"refusing, not guessing")
        for wid, payload in creates.items():
            if wid in supplied:
                rec = supplied[wid]
                rec.validate()
                problems = []
                if rec.code_ref != payload.get("code_ref"):
                    problems.append(
                        f"code_ref ledger={payload.get('code_ref')!r} "
                        f"supplied={rec.code_ref!r}")
                ledger_caps = _names(payload.get("capabilities", []))
                supplied_caps = _names(
                    [c.name + "@" + c.version for c in rec.capabilities])
                if ledger_caps != supplied_caps:
                    problems.append(
                        f"capabilities ledger={sorted(ledger_caps)} "
                        f"supplied={sorted(supplied_caps)}")
                ledger_reps = _names(payload.get("representations", []))
                supplied_reps = _names(
                    [r.name + "@" + r.version for r in rec.representations])
                if ledger_reps != supplied_reps:
                    problems.append(
                        f"representations ledger={sorted(ledger_reps)} "
                        f"supplied={sorted(supplied_reps)}")
                if problems:
                    obj.deny(actor, "reopen",
                             f"record mismatch for {wid!r}: " + "; ".join(problems))
                    raise ContractViolation(
                        f"reopen: supplied record for {wid!r} does not match "
                        f"ledger (" + "; ".join(problems) + "); refusing, not guessing")
                rec.lifecycle = last_lifecycle.get(wid, "proposed")
                rec.custodians = dict(custodians.get(wid, {}))
                obj.worlds[wid] = rec
            else:
                skel_caps = []
                for item in payload.get("capabilities", []):
                    name, _, version = item.partition("@")
                    skel_caps.append(Capability(
                        name=name, version=version,
                        required_authority=WITHHELD_AUTHORITY))
                skel_reps = []
                for item in payload.get("representations", []):
                    name, _, version = item.partition("@")
                    skel_reps.append(Representation(name=name, version=version))
                obj.worlds[wid] = WorldRecord(
                    world_id=wid, lineage=list(payload.get("lineage", [])),
                    code_ref=payload.get("code_ref", ""),
                    instance_state_dir=payload.get("instance_state_dir", ""),
                    custodians=dict(custodians.get(wid, {})),
                    capabilities=skel_caps, representations=skel_reps,
                    lifecycle=last_lifecycle.get(wid, "proposed"),
                    authorities=list(payload.get("authorities", [])))
        obj._append("host_reopen", {"reason": reason,
                                   "ledger_entries_replayed": n_replayed,
                                   "worlds": sorted(obj.worlds),
                                   "descriptors_supplied": sorted(supplied),
                                   "descriptors_withheld": sorted(
                                       set(obj.worlds) - set(supplied))},
                    actor=actor)
        return obj

    # -- grants / conservation ---------------------------------------------
    def grant(self, frm: str, to: str, limits: dict, authority: list,
              grant_id: str, expires: str | None = None) -> dict:
        if frm != "host" and frm not in self.worlds:
            self.deny(frm, "grant", f"unknown grantor {frm!r}")
            raise ContractViolation(f"unknown grantor {frm!r}")
        if to not in self.worlds:
            self.deny(frm, "grant", f"unknown grantee {to!r}")
            raise ContractViolation(f"unknown grantee {to!r}")
        if frm != "host" and "grant.delegate" not in self.worlds[frm].authorities:
            self.deny(frm, "grant", f"{frm!r} lacks grant.delegate authority")
            raise ContractViolation(f"{frm!r} lacks grant.delegate authority")
        norm = _limits_normalized(limits)
        avail = self.holdings.get(frm, _zero_holdings())
        for key in RESOURCE_KEYS:
            if norm[key] > avail[key] + 1e-9:
                self.deny(frm, "grant",
                          f"grant {grant_id} exceeds holding: {key} {norm[key]} > {avail[key]}",
                          {"grant_id": grant_id, "to": to})
                raise ContractViolation("delegation never manufactures resources: "
                                        f"{key} {norm[key]} > available {avail[key]}")
        for key in RESOURCE_KEYS:
            self.holdings[frm][key] -= norm[key]
            self.holdings[to][key] += norm[key]
        rec = {"grant_id": grant_id, "from": frm, "to": to, "limits": norm,
               "authority": authority, "at": utcnow(), "expires": expires}
        self.grants_out.setdefault(frm, []).append(rec)
        self._append("grant", dict(rec, parent_holding_after=dict(self.holdings[frm]),
                                   child_holding_after=dict(self.holdings[to])), actor=frm)
        return rec

    def return_grant(self, grant_id: str, frm: str, amounts: dict, reason: str) -> dict:
        """Return unused granted resources from child back to parent (host extension)."""
        found = None
        for parent, grants in self.grants_out.items():
            for g in grants:
                if g["grant_id"] == grant_id and g["to"] == frm:
                    found = (parent, g)
        if found is None:
            self.deny(frm, "grant_return", f"unknown grant {grant_id!r}")
            raise ContractViolation(f"unknown grant {grant_id!r}")
        parent, _g = found
        norm = _limits_normalized(amounts)
        for key in RESOURCE_KEYS:
            if norm[key] > self.holdings[frm][key] + 1e-9:
                self.deny(frm, "grant_return", f"return exceeds holding for {key}")
                raise ContractViolation("cannot return more than held")
        for key in RESOURCE_KEYS:
            self.holdings[frm][key] -= norm[key]
            self.holdings[parent][key] += norm[key]
        return self._append("grant_return", {"grant_id": grant_id, "from": frm,
                                             "to": parent, "amounts": norm,
                                             "reason": reason}, actor=frm)

    def settle_grants(self, world_id: str, actor: str, reason: str) -> list[str]:
        """Return ALL unused holdings of world_id to its grantors.

        Called automatically by transition() before any move into dissolved /
        retired. Emits one grant_return per grant that still has funds to move
        (amounts distributed against each grant's limits, so multi-grantor
        worlds return each grantor's share), then a balance-neutral
        `grant_settle` marker. Worlds with no grants or zero holdings emit
        the marker only. Conservation replay MUST treat the marker as opaque
        (funds move in the grant_return entries, never in the marker).
        """
        grants_to = [g for grants in self.grants_out.values() for g in grants
                     if g["to"] == world_id]
        settled = [g["grant_id"] for g in grants_to]
        totals = _zero_holdings()
        for g in grants_to:
            held = self.holdings.get(world_id, _zero_holdings())
            if not any(held[key] > 1e-9 for key in RESOURCE_KEYS):
                break
            amounts = {key: min(held[key], g["limits"].get(key, 0))
                       for key in RESOURCE_KEYS}
            if any(amounts[key] > 1e-9 for key in RESOURCE_KEYS):
                self.return_grant(g["grant_id"], world_id, amounts,
                                  reason=f"settle-on-terminal: {reason}")
                for key in RESOURCE_KEYS:
                    totals[key] += amounts[key]
        residual = self.holdings.get(world_id, _zero_holdings())
        if any(residual[key] > 1e-6 for key in RESOURCE_KEYS):
            self.deny(actor, "grant_settle",
                      f"settle left residual holdings on {world_id!r}",
                      {"world_id": world_id, "residual": dict(residual)})
            raise ContractViolation(
                f"settle left residual holdings on {world_id!r}; refusing "
                f"terminal transition, not stranding funds")
        self._append("grant_settle",
                     {"world_id": world_id, "grants": settled,
                      "reason": reason, "amounts_total": totals},
                     actor=actor)
        return settled

    def consume(self, world_id: str, cost_usd: float = 0.0, time_s: float = 0.0,
                invocations: int = 0, evidence_ref: str = "") -> dict:
        use = {"max_cost_usd": cost_usd, "max_time_s": time_s,
               "max_invocations": invocations}
        avail = self.holdings.get(world_id)
        if avail is None:
            self.deny(world_id, "consume", f"unknown world {world_id!r}")
            raise ContractViolation(f"unknown world {world_id!r}")
        for key in RESOURCE_KEYS:
            if use[key] > avail[key] + 1e-9:
                self.deny(world_id, "consume",
                          f"would exceed grant: {key} {use[key]} > {avail[key]}")
                raise ContractViolation(f"grant exceeded for {world_id}: {key}")
        for key in RESOURCE_KEYS:
            self.holdings[world_id][key] -= use[key]
            self.consumed[world_id][key] += use[key]
        return self._append("consume", dict(use, world_id=world_id,
                                            evidence_ref=evidence_ref), actor=world_id)

    def verify_conservation(self) -> dict:
        """Replay the ledger; every world balance must stay >= 0 (no manufacture).

        Hardened vs w1: `grant_settle` markers are honored as balance-neutral
        (bad envelope or malformed payload refused), and every world whose
        LAST lifecycle state is dissolved/retired must have a matching
        `grant_settle` entry, else ContractViolation("unsettled terminal").
        NOTE: this intentionally rejects pre-settle ledgers (e.g. w1 demo
        ledgers) — that is the invariant doing its job, not a bug.
        """
        bal: dict[str, dict] = {}
        consumed: dict[str, dict] = {}
        last_lifecycle: dict[str, str] = {}
        settled: set[str] = set()

        def B(w: str) -> dict:
            return bal.setdefault(w, _zero_holdings())

        def C(w: str) -> dict:
            return consumed.setdefault(w, _zero_holdings())

        for e in self.ledger_entries():
            k, p = e["kind"], e["payload"]
            if k == "host_init":
                for key in RESOURCE_KEYS:
                    B("host")[key] = p["root_holdings"].get(key, 0)
            elif k == "grant":
                for key in RESOURCE_KEYS:
                    B(p["from"])[key] -= p["limits"][key]
                    B(p["to"])[key] += p["limits"][key]
            elif k == "grant_return":
                for key in RESOURCE_KEYS:
                    B(p["from"])[key] -= p["amounts"][key]
                    B(p["to"])[key] += p["amounts"][key]
            elif k == "consume":
                for key in RESOURCE_KEYS:
                    B(p["world_id"])[key] -= p[key]
                    C(p["world_id"])[key] += p[key]
            elif k == "grant_settle":
                if e.get("contract_version") != CONTRACT_VERSION:
                    raise ContractViolation(
                        f"grant_settle at seq {e['seq']}: bad envelope; "
                        f"refusing, not guessing")
                for field in ("world_id", "grants", "reason"):
                    if field not in p:
                        raise ContractViolation(
                            f"grant_settle at seq {e['seq']}: missing {field!r}")
                settled.add(p["world_id"])
            elif k == "host_reopen":
                if e.get("contract_version") != CONTRACT_VERSION:
                    raise ContractViolation(
                        f"host_reopen at seq {e['seq']}: bad envelope; "
                        f"refusing, not guessing")
            elif k == "lifecycle":
                last_lifecycle[p["world_id"]] = p["to"]
            for w, b in bal.items():
                for key in RESOURCE_KEYS:
                    if b[key] < -1e-9:
                        raise ContractViolation(
                            f"conservation violated at seq {e['seq']}: {w}.{key}={b[key]}")
        for wid, state in last_lifecycle.items():
            if state in TERMINAL_STATES and wid not in settled:
                raise ContractViolation(
                    f"unsettled terminal: world {wid!r} ended in {state!r} "
                    f"with no grant_settle marker; holdings may be stranded")
        total_held = {key: sum(b[key] for b in bal.values()) for key in RESOURCE_KEYS}
        total_consumed = {key: sum(c[key] for c in consumed.values()) for key in RESOURCE_KEYS}
        total_initial = dict(self.holdings_initial.get("host", _zero_holdings()))
        for key in RESOURCE_KEYS:
            if abs(total_held[key] + total_consumed[key] - total_initial[key]) > 1e-6:
                raise ContractViolation(f"global conservation failed for {key}")
        return {"balances": bal, "consumed": consumed, "ok": True,
                "settled_terminals": sorted(settled)}

    # -- invoke --------------------------------------------------------------
    def invoke(self, caller: str, callee: str, capability: str, version: str,
               args_ref: str, fn, cost_usd: float = 0.0, time_s: float = 0.0) -> dict:
        """Accountable cross-world call. fn() performs the work; this records it."""
        if caller != "host" and caller not in self.worlds:
            self.deny(caller, "invoke", f"unknown caller {caller!r}")
            raise ContractViolation(f"unknown caller {caller!r}")
        target = self.worlds.get(callee)
        if target is None:
            self.deny(caller, "invoke", f"unknown callee {callee!r}")
            raise ContractViolation(f"unknown callee {callee!r}")
        if target.lifecycle != "active":
            self.deny(caller, "invoke",
                      f"callee {callee!r} not active (state={target.lifecycle})")
            raise ContractViolation(f"callee {callee!r} not active")
        cap = next((c for c in target.capabilities
                    if c.name == capability and c.version == version), None)
        if cap is None:
            self.deny(caller, "invoke",
                      f"{callee!r} does not advertise {capability}@{version}")
            raise ContractViolation(f"{callee!r} does not advertise {capability}@{version}")
        if cap.required_authority:
            held = [] if caller == "host" else self.worlds[caller].authorities
            if caller != "host" and cap.required_authority not in held:
                self.deny(caller, "invoke",
                          f"{caller!r} lacks {cap.required_authority} for {capability}")
                raise ContractViolation(f"{caller!r} lacks {cap.required_authority}")
        avail = self.holdings.get(caller, _zero_holdings())
        need = {"max_cost_usd": cost_usd, "max_time_s": time_s,
                "max_invocations": 1}
        for key in RESOURCE_KEYS:
            if need[key] > avail[key] + 1e-9:
                self.deny(caller, "invoke",
                          f"would exceed grant: {key} {need[key]} > {avail[key]}")
                raise ContractViolation(f"grant exceeded for {caller}: {key}")
        invoke_id = f"inv-{self._seq + 1:06d}"
        try:
            result_ref = fn()
        except Exception as exc:  # noqa: BLE001 - recorded, then re-raised
            self._append("invoke", {"invoke_id": invoke_id, "caller": caller,
                                    "callee": callee, "capability": capability,
                                    "version": version, "args_ref": args_ref,
                                    "error": f"{type(exc).__name__}: {exc}",
                                    "cost": {"cost_usd": cost_usd, "time_s": time_s}},
                         actor=caller)
            raise
        self.consume(caller, cost_usd=cost_usd, time_s=time_s, invocations=1,
                     evidence_ref=invoke_id)
        return self._append("invoke", {"invoke_id": invoke_id, "caller": caller,
                                       "callee": callee, "capability": capability,
                                       "version": version, "args_ref": args_ref,
                                       "result_ref": result_ref,
                                       "cost": {"cost_usd": cost_usd, "time_s": time_s}},
                            actor=caller)

    # -- lifecycle -----------------------------------------------------------
    def transition(self, world_id: str, to_state: str, actor: str, reason: str) -> dict:
        world = self.worlds.get(world_id)
        if world is None:
            self.deny(actor, "lifecycle", f"unknown world {world_id!r}")
            raise ContractViolation(f"unknown world {world_id!r}")
        try:
            check_lifecycle_edge(world.lifecycle, to_state, world_id)
        except ContractViolation as exc:
            self.deny(actor, "lifecycle", str(exc))
            raise
        if to_state in TERMINAL_STATES:
            # Settle-before-terminal: funds move while the world is still in
            # its pre-terminal state, so the ledger order is grant_return(s),
            # grant_settle, then lifecycle. A settle failure refuses the
            # transition (no lifecycle entry) rather than stranding funds.
            self.settle_grants(world_id, actor, reason)
        frm = world.lifecycle
        world.lifecycle = to_state
        if to_state == "retired":
            self._retired_ids.add(world_id)
        return self._append("lifecycle", {"world_id": world_id, "from": frm,
                                          "to": to_state, "reason": reason}, actor=actor)

    def suspend(self, world_id: str, actor: str, reason: str,
                pending_effects: list | None = None) -> dict:
        world = self.worlds.get(world_id)
        if world is None:
            self.deny(actor, "suspend", f"unknown world {world_id!r}")
            raise ContractViolation(f"unknown world {world_id!r}")
        checkpoint = {
            "contract_version": CONTRACT_VERSION,
            "world_id": world_id,
            "code_ref": world.code_ref,
            "capability_versions": [c.name + "@" + c.version for c in world.capabilities],
            "representation_versions": [r.name + "@" + r.version
                                        for r in world.representations],
            "ledger_position": self._seq,
            "pending_effects": pending_effects or [],
            "at": utcnow(),
        }
        ckpt_path = Path(world.instance_state_dir) / "checkpoint.json"
        ckpt_path.write_text(json.dumps(checkpoint, indent=2, sort_keys=True),
                             encoding="utf-8")
        self.transition(world_id, "suspended", actor, reason)
        return self._append("checkpoint", {"world_id": world_id,
                                           "checkpoint_ref": str(ckpt_path),
                                           "ledger_position": self._seq - 1,
                                           "pending_effects": pending_effects or []},
                            actor=actor)

    def reattach(self, world_id: str, actor: str, reason: str) -> dict:
        world = self.worlds.get(world_id)
        if world is None:
            self.deny(actor, "reattach", f"unknown world {world_id!r}")
            raise ContractViolation(f"unknown world {world_id!r}")
        if world.lifecycle != "suspended":
            self.deny(actor, "reattach", f"{world_id!r} not suspended")
            raise ContractViolation(f"{world_id!r} not suspended")
        ckpt_path = Path(world.instance_state_dir) / "checkpoint.json"
        if not ckpt_path.exists():
            self.deny(actor, "reattach", "missing checkpoint")
            raise ContractViolation("missing checkpoint")
        checkpoint = json.loads(ckpt_path.read_text(encoding="utf-8"))
        contract.require_contract_version(checkpoint.get("contract_version", "?"),
                                          f"checkpoint {world_id}")
        if checkpoint["world_id"] != world_id or checkpoint["code_ref"] != world.code_ref:
            self.deny(actor, "reattach", "checkpoint identity mismatch")
            raise ContractViolation("checkpoint identity mismatch")
        self.transition(world_id, "active", actor, reason)
        return self._append("reattach", {"world_id": world_id,
                                         "checkpoint_ref": str(ckpt_path),
                                         "restored_ledger_position":
                                             checkpoint["ledger_position"],
                                         "pending_effects_replayed":
                                             checkpoint["pending_effects"]},
                            actor=actor)

    # -- relationships ---------------------------------------------------------
    def declare_relationship(self, rel: Relationship, actor: str) -> Relationship:
        rel.validate()
        versions = self.relationships.setdefault(rel.rel_id, {})
        if rel.version in versions:
            self.deny(actor, "relationship.declare",
                      f"{rel.rel_id} v{rel.version} already declared")
            raise ContractViolation(f"{rel.rel_id} v{rel.version} already declared")
        for pid in rel.participants:
            if pid != "host" and pid not in self.worlds:
                self.deny(actor, "relationship.declare", f"unknown participant {pid!r}")
                raise ContractViolation(f"unknown participant {pid!r}")
        versions[rel.version] = rel
        self._append("relationship", {
            "rel_id": rel.rel_id, "version": rel.version,
            "participants": rel.participants, "purpose": rel.purpose,
            "mapping": {"from": rel.mapping_from, "to": rel.mapping_to,
                        "ref": rel.mapping_ref, "losses": rel.losses_declared},
            "protocol": rel.protocol, "authority_granted": rel.authority_granted,
            "state": rel.state}, actor=actor)
        return rel

    def get_relationship(self, rel_id: str, version: str) -> Relationship:
        versions = self.relationships.get(rel_id, {})
        if version not in versions:
            raise ContractViolation(f"unknown relationship {rel_id} v{version}")
        return versions[version]

    # -- custody -----------------------------------------------------------------
    def transfer_custody(self, state_class: str, frm: str, to: str, actor: str,
                         reason: str, continuity: str) -> dict:
        if frm not in self.worlds or (to != "host" and to not in self.worlds):
            self.deny(actor, "custody.transfer", "unknown world in transfer")
            raise ContractViolation("unknown world in transfer")
        if self.worlds[frm].custodians.get(state_class) != frm:
            self.deny(actor, "custody.transfer",
                      f"{frm!r} is not custodian of {state_class!r}")
            raise ContractViolation(f"{frm!r} is not custodian of {state_class!r}")
        if actor != "host" and actor != frm:
            held = self.worlds.get(actor)
            if held is None or "custody.transfer" not in held.authorities:
                self.deny(actor, "custody.transfer",
                          f"{actor!r} lacks custody.transfer authority")
                raise ContractViolation(f"{actor!r} lacks custody.transfer authority")
        del self.worlds[frm].custodians[state_class]
        if to != "host":
            self.worlds[to].custodians[state_class] = to
        return self._append("transfer", {"state_class": state_class, "from": frm,
                                         "to": to, "reason": reason,
                                         "continuity": continuity}, actor=actor)

    # -- helpers -------------------------------------------------------------------
    def store_args(self, world_id: str, name: str, payload: dict) -> str:
        world = self.worlds.get(world_id)
        base = self.state_dir if world is None else Path(world.instance_state_dir)
        path = base / "args" / f"{name}.json"
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")
        return str(path)

    @staticmethod
    def sha256_file(path: str) -> str:
        h = hashlib.sha256()
        with open(path, "rb") as fh:
            for chunk in iter(lambda: fh.read(65536), b""):
                h.update(chunk)
        return h.hexdigest()
