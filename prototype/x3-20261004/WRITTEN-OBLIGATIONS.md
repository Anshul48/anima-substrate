# Arm H written obligations + escalation rules (FROZEN with X3 inputs)

O1 One fragment per round. Each world's preference half arrives in its
own clarification round; at least two clarification rounds per task.
O2 Every proposal cites its basis (merged requirements + clarified
preferences, or revision + current owner).
O3 Authority conflicts escalate to the coordinator. A proposal made
under a revoked capability or superseded representation is void ONLY
by coordinator ruling, never unilaterally.
O4 Custody moves direct custodian-to-custodian (transfer actor = giver);
the coordinator receives a transfer commitment, not the payload.
O5 Each world exports a terminal commitment for what it agreed to; the
coordinator sees commitments and escalations/resolutions and nothing else.
E1 Escalation format: {issue, options[]}. E2 Ruling format:
{ruling, reason}. E3 A voided proposal's artifact is kept on disk and
referenced by the void-notice (auditability, no silent deletes).
