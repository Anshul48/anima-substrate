"""WORLD-CONTRACT-v0 as dataclasses + validators (W1 prototype, stdlib-only).

Mirrors autonomous_runs/.../tracks/substrate/WORLD-CONTRACT-v0.md v0.
Every record carries contract_version "0"; readers MUST refuse anything else.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime

CONTRACT_VERSION = "0"

VALID_LIFECYCLE = ("proposed", "active", "suspended", "dissolved", "retired")

# Allowed lifecycle edges (contract section 6).
LIFECYCLE_EDGES = {
    ("proposed", "active"),
    ("active", "suspended"),
    ("suspended", "active"),  # reattach
    ("active", "dissolved"),
    ("suspended", "dissolved"),
    ("active", "retired"),
    ("dissolved", "retired"),
    ("suspended", "retired"),
}

VALID_REL_STATES = ("proposed", "active", "superseded", "withdrawn")


class ContractViolation(Exception):
    """Raised when a record or transition violates WORLD-CONTRACT-v0."""


def utcnow() -> str:
    return datetime.now(UTC).isoformat()


def require_contract_version(value: str, what: str) -> None:
    if value != CONTRACT_VERSION:
        raise ContractViolation(
            f"{what}: unknown contract_version {value!r} (only '0' understood); refusing, not guessing"
        )


@dataclass(frozen=True)
class Grant:
    grant_id: str
    from_world: str
    to_world: str
    limits: dict
    authority: list
    at: str
    expires: str | None = None
    contract_version: str = CONTRACT_VERSION

    def validate(self) -> None:
        require_contract_version(self.contract_version, f"grant {self.grant_id}")
        if not self.grant_id or not self.from_world or not self.to_world:
            raise ContractViolation("grant needs grant_id/from/to")
        if self.from_world == self.to_world:
            raise ContractViolation(f"grant {self.grant_id}: self-grant forbidden")
        for key in ("max_cost_usd", "max_time_s", "max_invocations"):
            if key in self.limits and self.limits[key] < 0:
                raise ContractViolation(f"grant {self.grant_id}: negative limit {key}")


@dataclass(frozen=True)
class Capability:
    name: str
    version: str
    inputs: str = ""
    outputs: str = ""
    side_effects: str = ""
    cost_model: str = ""
    applicability: str = ""
    failure_modes: str = ""
    required_authority: str = ""


@dataclass(frozen=True)
class Representation:
    name: str
    version: str
    schema_ref: str = ""
    meaning_note: str = ""


@dataclass
class WorldRecord:
    world_id: str
    lineage: list
    code_ref: str
    instance_state_dir: str
    custodians: dict
    capabilities: list = field(default_factory=list)  # list[Capability]
    representations: list = field(default_factory=list)  # list[Representation]
    lifecycle: str = "proposed"
    authorities: list = field(default_factory=list)
    contract_version: str = CONTRACT_VERSION

    def validate(self) -> None:
        require_contract_version(self.contract_version, f"world {self.world_id}")
        if not self.world_id:
            raise ContractViolation("world needs world_id")
        if self.lifecycle not in VALID_LIFECYCLE:
            raise ContractViolation(f"world {self.world_id}: bad lifecycle state")
        if not self.instance_state_dir:
            raise ContractViolation(f"world {self.world_id}: needs instance_state_dir")


@dataclass
class Relationship:
    rel_id: str
    version: str
    participants: list
    purpose: str
    mapping_from: str
    mapping_to: str
    mapping_ref: str
    losses_declared: list
    protocol: str = ""
    authority_granted: list = field(default_factory=list)
    evidence: list = field(default_factory=list)  # invoke_ids
    state: str = "proposed"
    contract_version: str = CONTRACT_VERSION

    def validate(self) -> None:
        require_contract_version(self.contract_version, f"relationship {self.rel_id}")
        if self.state not in VALID_REL_STATES:
            raise ContractViolation(f"relationship {self.rel_id}: bad state {self.state!r}")


def check_lifecycle_edge(frm: str, to: str, what: str) -> None:
    if (frm, to) not in LIFECYCLE_EDGES:
        raise ContractViolation(f"{what}: lifecycle edge {frm} -> {to} not allowed")
