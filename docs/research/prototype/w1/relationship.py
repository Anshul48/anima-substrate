"""Versioned relationships + checked mapping task-spec/v0 <-> formulation/v0.

Stdlib-only. Revision rule (contract section 7): changing the mapping creates
a NEW version; existing runs keep their pinned version. Unmapped fields are
carried as opaque, never silently reinterpreted.
"""
from __future__ import annotations

from contract import ContractViolation, Relationship

REL_ID = "rel-construct-explore"
MAPPING_REF_V1 = "mapping:task-spec/v0<->formulation/v0:1.0"
MAPPING_REF_V2 = "mapping:task-spec/v0<->formulation/v0:2.0"


def v1_record() -> Relationship:
    return Relationship(
        rel_id=REL_ID, version="1.0",
        participants=["E-construct", "E-explore"],
        purpose="construct world requests exploration over a different representation",
        mapping_from="task-spec/v0", mapping_to="formulation/v0",
        mapping_ref=MAPPING_REF_V1,
        losses_declared=["task-spec.acceptance steps beyond goal text are opaque "
                         "to formulation/v0 (carried as opaque_acceptance, not interpreted)",
                         "formulation budget has no task-spec counterpart (defaults)"],
        protocol="construct writes task-spec; host maps to formulation; "
                 "explore searches; scores map back as opaque evidence",
        state="active")


def v2_record() -> Relationship:
    return Relationship(
        rel_id=REL_ID, version="2.0",
        participants=["E-construct", "E-explore"],
        purpose="v1 purpose + explicit assumption field on formulations",
        mapping_from="task-spec/v0", mapping_to="formulation/v0",
        mapping_ref=MAPPING_REF_V2,
        losses_declared=["same as v1",
                         "v1 formulations lack assumptions; v2 readers MUST treat "
                         "a missing assumptions field as opaque, not as 'no assumptions'"],
        protocol="as v1; formulations additionally carry assumptions[]",
        state="active")


def revise_v1_to_v2() -> Relationship:
    """Revision creates a new version; v1 stays valid for pinned runs."""
    return v2_record()


def task_spec_to_formulation(task_spec: dict, version: str) -> dict:
    if version == "1.0":
        return {"representation": "formulation/v0",
                "goal": task_spec["goal"],
                "domain": "code-variant-search",
                "constraints": list(task_spec.get("scope", [])),
                "budget": {"max_iterations": 2},
                "opaque_acceptance": list(task_spec.get("acceptance", []))}
    if version == "2.0":
        form = task_spec_to_formulation(task_spec, "1.0")
        form["assumptions"] = task_spec.get("assumptions", [])
        form["mapping_version"] = "2.0"
        return form
    raise ContractViolation(f"unknown mapping version {version!r}; refusing, not guessing")


def formulation_to_task_spec_evidence(formulation: dict, scores: dict,
                                      version: str) -> dict:
    if version not in ("1.0", "2.0"):
        raise ContractViolation(f"unknown mapping version {version!r}")
    return {"representation": "task-spec-evidence/v0",
            "goal": formulation.get("goal"),
            "champion": scores.get("champion_id"),
            "scores_opaque": scores.get("scores", scores),
            "mapping_version": version}
