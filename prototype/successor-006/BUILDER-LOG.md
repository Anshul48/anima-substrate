# BUILDER-LOG.md — successor-006 builder log (running)

Constraints honored throughout: stdlib-only, offline, $0, no pip,
`PYTHONDONTWRITEBYTECODE=1` on every command. Frozen trees were
never written (verified by read-only comparison + final status
check); all work is in `prototype/successor-006/`.

## 2026-10-07 — setup + carry-forward

- Located the owed items: Q3 8-item list in
  `reuse-demo-001/REUSE-REPORT.md` §"Interface gaps" (+ Q3/R9 rows
  in `programme-20261004/COMPLETION-MAP.md`); R11 owed
  quarantine-transfer repair in COMPLETION-MAP R11 row +
  `successor-005/INTERRUPTION-BOUNDARIES.md` §6 (operator-manual
  recipes); J1 shape in `SUBSTRATE-COMPLETION-PROPOSAL.md` §2/§3/§5.
- Created `prototype/successor-006/`; copied 16 `.py` modules +
  `accept/` from successor-005 (hashes in PROVENANCE.md).
- Minimal adaptations: tree-identity strings, SST-leg loud stubs
  (not carried: needs a venv), `open_run` authority restore (for
  nest delegation; sched behavior unchanged).
- Carried regression: test_conformance 9/9 + test_fission 7/7 green
  in the new tree before any new behavior.

## 2026-10-07 — R11 quarantine-transfer repair

- `recover.py`: seq-aware partial-quarantine detection (rollback
  resolutions, side-file fallback for the lifecycle/checkpoint
  split), `complete_quarantine` + `rollback_quarantine`
  (validate-before-mutate, ledger-conditional, direction-mixing
  refused), operator steps point at the supported ops.
- `api.py` + `release.py`: `quarantine_complete_op` /
  `quarantine_rollback_op`, CLI `ops quarantine-complete` /
  `ops quarantine-rollback`.
- Debug: ordered the rollback-in-progress refusal AHEAD of the
  generic custody-moved check (precise message wins).
- `test_quarantine_repair.py`: 13/13 (kill at every boundary x both
  directions, kill-during-repair convergence, refusal battery,
  silence checks, re-quarantine after rollback).

## 2026-10-07 — Q3 coupling contract

- `COUPLING-CONTRACT.md`: CC1–CC8 formalized (promise + code pin +
  test pin each) + CC9 unmodified-engine reuse.
- `test_coupling.py`: 10/10 (signature pins, matcher checks,
  real-SIGKILL byte-compat, engine byte-identity vs frozen
  successor-005, contract-file cross-check).

## 2026-10-07 — J1 journey

- `api.py`: `j1_init`, `nest_op` (never-manufactured delegation),
  `j1_work_op`, `j1_kill_resume_op` (real kill, byte-identity +
  ledger-prefix asserts), `j1_status_op`, `j1_export_op`
  (verify-before-write); CLI + `j1_demo.py` single-command demo
  (also serves as the kill child).
- Debug: ledger-prefix comparison used `split(b"\n")` (trailing
  empty element broke the equality) → `splitlines()`; J1 demo then
  10/10 PASS with child_rc=-9.
- `test_j1.py`: 6/6 (full journey incl. unmodified-reuse snapshot
  equality, RUNBOOK CLI smoke, nest/export refusal battery).
- `test_procedure_smoke.py`: 3/3 (carried-bytes pin + advertise/
  run/skip + table-miss deny). Debug: step argv must be
  `[python, -c, code]` (bundle files are not on the step cwd —
  matches s005 test convention); `re_executed_steps` is a list.

## 2026-10-07 — docs + self-test

- Wrote PROVENANCE.md, CONSUMER.md, RUNBOOK.md, LIMITS.md (16
  items, 5 new), this log. Verified RUNBOOK quarantine drill uses
  init-shipped worlds (fixed an early draft naming a nonexistent
  world).
- [DONE by coordinator after builder session break] full suite
  re-run 48/48 + demo 10/10 + frozen-tree untouched check (zero
  files newer than 11:50 in all frozen trees); independent audit
  S6-ACCEPTANCE.md supersedes (ACCEPT).

## Totals (builder-observed, this session)

- New tests: coupling 10 + quarantine-repair 13 + J1 6 + proc-smoke
  3 = 32/32. Carried: conformance 9 + fission 7 = 16/16.
  Combined: 48/48. Demo: 10/10 stages.
- No bank/freeze claimed; no acceptance claimed (auditor follows).
