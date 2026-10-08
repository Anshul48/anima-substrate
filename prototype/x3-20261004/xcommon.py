"""X3 shared harness: coordinators, MiniHost setup, resume, finish.

Both arms use identical recovery machinery (MiniHost vendored from
reuse-demo-001, sha pinned in FREEZE.json): checkpoint schema + identity
rule, resume-by-skip, grant_settle + unsettled-terminal check,
host_reopen. Recovery parity is structural, not aspirational.
"""
from __future__ import annotations

import json
from pathlib import Path

from minihost import (MiniCapability, MiniHost, MiniRepresentation,
                      MiniWorldRecord)

import domain

GRANT_LIMITS = {"max_cost_usd": 1.0, "max_time_s": 60.0,
                "max_invocations": 100}

CODE_REF = "x3-20261004/xcommon.py"


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
    """Host-local coordinator: sees ONLY commitments and escalations.

    Any other payload is refused (mechanism guard: local state stays
    local; direct world traffic bypasses this object entirely).
    """

    ALLOWED = ("commitment", "escalation", "resolution")

    def handle(self, msg: dict) -> dict:
        if msg.get("kind") not in self.ALLOWED:
            raise ValueError(f"coordinator refused non-export payload "
                             f"{msg.get('kind')!r}: local state stays local")
        return super().handle(msg)


def world_record(state_dir: Path, world_id: str, caps: list[tuple[str, str]],
                 reps: list[tuple[str, str]], custodians: dict | None = None,
                 authorities: list | None = None) -> MiniWorldRecord:
    return MiniWorldRecord(
        world_id=world_id, lineage=[("host", "created", "x3")],
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
        host.transition(rec.world_id, "active", "host", reason="x3 setup")
    return host


def rebuild_records(root: Path, worlds: list[MiniWorldRecord]) -> list[MiniWorldRecord]:
    """Fresh descriptors for reopen (same bytes as setup: verifiable)."""
    return [world_record(root / "state", r.world_id,
                         [(c.name, c.version) for c in r.capabilities],
                         [(x.name, x.version) for x in r.representations],
                         dict(r.custodians), list(r.authorities))
            for r in worlds]


def write_json(path: Path, obj: dict) -> str:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(obj, indent=2, sort_keys=True) + "\n",
                    encoding="utf-8")
    return str(path)


def successful_invokes(entries: list[dict], capability: str) -> list[dict]:
    return [e for e in entries
            if e.get("kind") == "invoke"
            and e.get("payload", {}).get("capability") == capability
            and "error" not in e.get("payload", {})]


def args_match(args_ref: str, key: str, want) -> bool:
    try:
        got = json.loads(Path(args_ref).read_text(encoding="utf-8")).get(key)
    except (OSError, ValueError):
        return False
    return got == want


def finish_worlds(host: MiniHost, world_ids: list[str], reason: str) -> dict:
    """Settle-then-dissolve every world; verify conservation + 0 stranded."""
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
