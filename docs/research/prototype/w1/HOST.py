"""Minimal host for the W1 prototype (SUBSTRATE, Alternative C). Stdlib-only.

Implements WORLD-CONTRACT-v0 for the W1 worlds: world registry, grant /
delegation ledger (append-only JSONL), accountable invoke, lifecycle
transitions, suspend/reattach checkpoints, custody transfer.

Every refusal is a recorded ledger denial, never silent.
"""
from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path

import contract
from contract import (
    CONTRACT_VERSION,
    Capability,
    ContractViolation,
    Relationship,
    WorldRecord,
    check_lifecycle_edge,
    utcnow,
)

RESOURCE_KEYS = ("max_cost_usd", "max_time_s", "max_invocations")


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
            if os.path.abspath(other.instance_state_dir) == os.path.abspath(record.instance_state_dir):
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
        """Replay the ledger; every world balance must stay >= 0 (no manufacture)."""
        bal: dict[str, dict] = {}
        consumed: dict[str, dict] = {}

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
            for w, b in bal.items():
                for key in RESOURCE_KEYS:
                    if b[key] < -1e-9:
                        raise ContractViolation(
                            f"conservation violated at seq {e['seq']}: {w}.{key}={b[key]}")
        total_held = {key: sum(b[key] for b in bal.values()) for key in RESOURCE_KEYS}
        total_consumed = {key: sum(c[key] for c in consumed.values()) for key in RESOURCE_KEYS}
        total_initial = dict(self.holdings_initial.get("host", _zero_holdings()))
        for key in RESOURCE_KEYS:
            if abs(total_held[key] + total_consumed[key] - total_initial[key]) > 1e-6:
                raise ContractViolation(f"global conservation failed for {key}")
        return {"balances": bal, "consumed": consumed, "ok": True}

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