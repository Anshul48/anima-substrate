# Written obligations + escalation rules (carried into successor-003 unchanged)

> H2-lane carry note (2026-10-04): base text below is the byte-identical successor-003 record; only this note was added. The H2 delta (task-JSON lane path, derived routing inputs, lane-override hook) does not change the behaviors documented here.

Successor-002 note: all obligations below hold as written. Fission
(`fusion.fission_worlds`) is O4-conformant: custody back-transfers
carry actor = the composite (the giver), continuity
`fission-partition`. No new obligations; see ORG-OPS.md for the
consumer clauses.

Successor-003 note: obligations unchanged. R1 recovery completions
are O4-conformant by construction (fusion completion transfers carry
actor = giver; fission completion actor = composite; spec repair
moves no custody). Settle atomicity adds no new obligation (same
O2/O5 shapes, fail-closed earlier).

# Successor-001 written obligations + escalation rules (base text)

Lineage: `x3-20261004/WRITTEN-OBLIGATIONS.md` (obligations O1–O5,
escalation rules E1–E3), adapted to the unified hybrid pipeline. The
successor enforces these structurally (see the cited code), not by
convention alone.

## Obligations

O1 One fragment per clarify step. Each world's preference half arrives
in its own step; tasks with preferences split across worlds therefore
need >= 2 clarification rounds by construction. Enforced:
`pipeline.fragment_rounds` emits one fragment per step and
`LaneCtx.carry_fragment` carries exactly that step's fragment
(`pipeline.py`).

O2 Every proposal cites its basis: merged requirements + clarified
preferences, or revision + current owner. Enforced:
`pipeline.check_basis` raises on any basis citing neither
(`pipeline.py:check_basis`; test_03/09 exercise it).

O3 Authority conflicts escalate to the coordinator. A proposal made
under a revoked capability or a superseded representation is void ONLY
by coordinator ruling, never unilaterally: the host still executes the
invoke (it cannot judge staleness), and the ruling voids it afterwards.
Enforced by flow: `s3_resume_flow` steps 2–7 (`pipeline.py`).

O4 Custody moves direct custodian-to-custodian (transfer actor = giver);
the coordinator receives commitments, not payloads. Enforced:
`transfer_custody(..., actor=giver, ...)` in `fusion.fuse_worlds` and
`fusion.quarantine_world` (quarantine uses actor=host only because the
giver is suspended — documented in the code).

O5 Each world exports a terminal commitment for what it agreed to; the
local-lane coordinator sees commitments and escalations/resolutions and
nothing else. Enforced: `HCoordinator` refuses any other payload, and
`pipeline.export_commitments` emits one commitment per world
(`routing.py`, `pipeline.py`).

## Escalation rules

E1 Escalation format: {issue, options[]}.
E2 Ruling format: {ruling, reason}.
E3 A voided proposal's artifact is kept on disk and referenced by the
void-notice (auditability, no silent deletes). Enforced:
`pipeline.void_proposal` asserts the artifact exists and records its
ref (`pipeline.py`).
