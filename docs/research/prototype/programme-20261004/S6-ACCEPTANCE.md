# S6-ACCEPTANCE.md — successor-006 independent acceptance audit

**Verdict: ACCEPT**

Auditor re-ran everything fresh on 2026-10-07 (~13:30 UTC) from the repo
root with `PYTHONDONTWRITEBYTECODE=1`, stdlib-only, offline, $0.
Candidate `prototype/successor-006/` untouched except read; audit state
only under `prototype/successor-006/runs/` (fresh `j1-audit-manual`,
`q-audit-*` dirs) and `/tmp`.

## 1. Docs read

RUNBOOK.md, LIMITS.md (16 items), COUPLING-CONTRACT.md (CC1–CC9),
CONSUMER.md, PROVENANCE.md — all present, mutually consistent, and
matching observed behavior (commands, expect-lines, refusal table).

## 2. Test suites + demo (fresh re-run)

| suite | result |
|---|---|
| test_coupling.py | 10/10 OK |
| test_quarantine_repair.py | 13/13 OK |
| test_j1.py | 6/6 OK |
| test_conformance.py (carried) | 9/9 OK |
| test_fission.py (carried) | 7/7 OK |
| test_procedure_smoke.py | 3/3 OK |
| **total** | **48/48** |
| j1_demo.py | `J1 journey: OK (10/10 PASS)`, rc=0, child_rc=-9 |

Matches builder claim (48/48 + 10/10).

Repro:
```
export PYTHONDONTWRITEBYTECODE=1
for t in test_coupling test_quarantine_repair test_j1 test_conformance test_fission test_procedure_smoke; do python3 prototype/successor-006/$t.py; done
python3 prototype/successor-006/j1_demo.py
```

## 3. Manual CLI journey (RUNBOOK steps 1–9, fresh `runs/j1-audit-manual`)

All 9 steps rc=0; expect-lines hold verbatim:
- s3 `j1-work`: `valid=True quality=4/4 re_executed=0`
- s4 `j1-kill-resume`: `child_rc=-9 valid=True quality=4/4 re_executed=0`
- s5 `j1-status`: conservation `'ok': True`; `--json` parses
- s7 reuse S4/S6: `valid=True` both (5/5, 4/4)
- s8 export bundle written with `derived_from=['PROJ','EXP1']`
- s9 settle: `settled ['EXP1','PROJ','PROJ-FUSED'] ... stranded=0`

## 4. Quarantine repair drill (R11)

- Clean `quarantine` + `recover`: rc=0, silent (no partials).
- Crash-hook (`SUBSTRATE_CRASH_AFTER_APPENDS=4`): rc=42 as documented;
  `recover` detects partial quarantine and names both supported ops.
- `quarantine-complete` after crash: rc=0, `transfers=2`.
- Separate crash dir + `quarantine-rollback`: rc=0, `reversed=1`,
  follow-up `recover` clean. Both directions converge.

## 5. Coupling-contract spot check (CC1, CC9 + CC6)

- CC1: code pin holds — `minihost.py:816 MiniHost.invoke(caller,
  callee, capability, version, args_ref, fn, cost_usd=, time_s=, ...)`;
  `consume` only on success leg (line 893); error leg records `error`
  with no consume. Test passes individually (1/1 OK).
- CC9: `resume.py` sha256 `9283e271…` identical in successor-006 and
  frozen successor-005, matching PROVENANCE.md; test passes (1/1 OK).
- CC6 (extra): `deny(actor, action, reason)` positional pin; test 1/1 OK.

## 6. Frozen predecessors untouched

`find <tree> -newermt "2026-10-07 11:50"` returns ZERO files for:
successor-002 (newest 10-04), successor-003 (10-04), successor-004
(10-04), successor-005 (10-06 11:48), H2-lane (10-04), reuse-demo-001
(10-04), U-execute (10-07 10:52), release-20261004 / release-r2 /
release-r3 (all 10-04). All mtimes predate the 11:50 cutoff.

## 7. Negative checks

- Out-of-envelope: `api.run_tasks(dir, with_sst=True)` → loud
  `RuntimeError: SST leg not carried in successor-006 ...` (LIMITS-7).
- Tamper: garbage line appended to `ledger.jsonl` → `ops recover`
  refuses rc=1: `recovery refused: ledger ... unreadable ... torn
  files are the disk-loss class (LIMITS-2 ...)`; never hand-edit.
- Limit: `ops nest --delegate 99,999,999` → rc=1 `ContractViolation:
  ... exceeds PROJ holdings ... (delegation never manufactures
  resources); zero mutation`.

## Notes (non-blocking)

1. BUILDER-LOG.md still carries a `[PENDING] full suite re-run` line;
   this audit supersedes it (48/48 + 10/10 independently re-observed).
2. No bank/freeze action taken — acceptance only, per brief.
3. Audit artifacts kept for inspection: `prototype/successor-006/runs/
   {j1-audit-manual,q-audit-manual,q-audit-kill,q-audit-rollback,
   q-audit-neg,q-audit-neg2,q-audit-neg3,q-audit-overdeleg}`,
   `j1-20261007T133230Z` (auditor demo run); `/tmp/audit-*.log`.
