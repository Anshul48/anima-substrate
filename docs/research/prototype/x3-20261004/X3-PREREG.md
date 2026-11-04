# X3 Preregistration: local responsibility vs capable central WITH recovery (FROZEN 2026-10-04)

## Question

Does local responsibility + direct local negotiation beat a capable
central orchestrator when BOTH have comparable crash-recovery support,
on tasks built to expose central-reconstruction cost? X1/X2/X1H showed
central winning at toy scale with recovery as the host's only win; X3
holds recovery constant so any difference attributes to the
coordination mechanism, not to recovery presence.

## Arms (both $0, offline, stdlib-only, deterministic)

- **Arm C (central+recovery):** central orchestrator; all cross-world
  traffic flows through it; fixed versioned adapters; checkpoint/resume
  via the retained machinery (recovery_lib conventions: checkpoint
  schema + identity rule, resume-by-skip, grant_settle +
  unsettled-terminal check, host_reopen).
- **Arm H (host-local):** worlds negotiate directly under explicit
  written obligations + escalation rules; local state stays local;
  the coordinator sees only exported commitments and escalations.
  Same recovery machinery as Arm C.

Both arms share: task inputs, domain checker, crash-injection
procedure, run count, measurement definitions.

## Domain (valid, independent checker)

Constrained scheduling: place N tasks into slots subject to
machine-exclusive + precedence + window constraints. Two frozen
representations: LIST-form (task→requirements) and SLOT-form
(slot→occupancy). Translation LIST→SLOT drops preferences (DECLARED
loss); recovering them needs clarification rounds. The checker
validates solutions against the constraints (not a hash self-gate):
a solution is VALID iff all hard constraints hold; quality =
preferences satisfied (count, higher better).

## Frozen tasks (inputs frozen before run 1; never edited after)

- **T1 incompatible representations:** LIST-world and SLOT-world must
  co-produce a valid schedule; ≥2 clarification rounds required by
  construction (preferences split across worlds). Measures:
  central-context-bytes (all bytes the coordinator handles),
  rounds, VALID + quality.
- **T2 changed condition + crash:** after partial progress, the
  representation revises v1→v2 (declared loss) AND one capability is
  revoked (ownership change); mid-adaptation one SIGKILL is injected
  per arm. Measures: rework (re-executed invokes), adaptation VALID,
  escalations, resume 0-rework check.
- **T3 transfer + subsequent reuse:** transfer sub-result custody to a
  third world, dissolve the coalition (settle, 0 stranded), then reuse
  the composite on a FOLLOW-UP task elsewhere. Measures: rework,
  lineage completeness (derived_from present + resolvable),
  stranded-holdings check.

## Prospective decision criteria

- H wins a task if VALID ties (or H alone VALID) AND (central-bytes(H)
  ≤ 0.5 × central-bytes(C) OR rework(H) ≤ 0.5 × rework(C)).
- C wins a task if VALID ties AND effort+bytes favor C (replicating
  H1b/H2b under harder conditions).
- Either arm loses a task outright on INVALID solution, stranded
  holdings, or unsettled terminal.
- Overall: 3 runs/arm; majority of tasks decides; all attempts
  recorded incl. crashes/voids. Recovery parity required: any arm
  failing resume-with-0-rework on T2 is marked RECOVERY-FAIL and
  cannot win overall.

## Hypotheses (competing, pre-committed)

- H3a (local wins): T1+T2 expose central shuttling; H halves central
  bytes/rework with equal VALID.
- H3b (central still wins): even with clarification rounds, central
  bookkeeping stays cheaper; C matches or beats H on effort+bytes.
  A H3b outcome is ACCEPTED as evidence, not a failure.

## Out of scope

Live models, learned mappings (hand-written v1/v2 as in W1),
multi-writer concurrency, disk loss. Assistance accounting: every
human-equivalent intervention logged per run.
