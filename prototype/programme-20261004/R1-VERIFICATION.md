# R1 VERIFICATION — independent acceptance record

- Verdict: **ACCEPT-WITH-NOTES** (all 8 checks PASS on observed evidence).
- Verifier: independent lane (read + execute only; no source modified;
  /tmp scratch removed; successor-003/IDENTITY 45/45 before AND after).
- Date: 2026-10-04. successor-003/ bytes are exactly as the verifier
  checked them — this record lives here so the tree stays frozen.

## Independent confirmation (observed, not trusted)

- Regression: 9/9 + 7/7 + 17/17 (incl. SST $0/MATCH legs) + 8
  atomicity spots (refusal, side-effect-freedom, bare-recover default,
  wrong-partition, settle matrix N=1..8, SIGKILL settle, fuse 15/15,
  fission 15/15). Demo spine exit 0, line-identical to builder log.
  calibrate 2.61x, snapshot MATCH 54/5f1f3789, self-check OK.
- Own kill landings (verifier-chosen N): settle N=5, fuse N=9,
  fission pre-spec, kill-during-recovery — every landing converged,
  no silent partials, conservation held everywhere.
- Atomicity: refusal probe → lifecycles/holdings unchanged, fresh
  kinds `['deny']`, zero grant_return/grant_settle. Clean-path settle
  growth identical to r1 modulo seq/at; phase-2 is byte-for-byte r1
  logic. Fail-closed-earlier weakens nothing (r1 LIMITS-11 disclaimed
  atomicity; the removed partials were never a guarantee).
- Hooks inert: unset/blank/garbage env → rc=0, conservative asserts
  hold; 3 named points + 1 counter (exhaustive); documented test-only.
- Rebrand: 12 files docstring/path-only; minihost re-pin verified
  against actual sha256; accept/ 8/8 + vendor/ 57/57 identical.
- Frozen: r1 41/41 OK; FROZEN-BASELINE 3639 OK + 1 expected miss
  (Note E); ../sst porcelain clean; no sibling writes by verifier.

## Notes (record-only, accepted; dispositions)

- A (frozen-evidence hash 61f523a5 vs 5f1f3789): confirmed
  record-only — EXPECTED.json pins MATCH only; r1 acceptance stands.
  No action.
- B (unpinned runs/demo-* in successor-003): evidence per r1
  convention (r1 ships 3 unpinned runs; both IDENTITYs pin 0 runs/
  lines). No action — deliberate convention, now explicit.
- C (README 8/8 vs actual 9/9; S4-followup.lane/S5.lane unmappable;
  REPRODUCE "~44s" vs 59.5s): pre-existing r1 doc nits carried
  byte-identical (accept/ frozen by policy) + machine-dependent
  timing. No tree edit (would break carried-byte identity for a nit).
- D ("every exact field" slightly overstated): builder claim-precision;
  verifier mapped-compare 47 PASS / 0 FAIL + the 2 noted fields; r1
  and R1 agree exactly. No action beyond this record.
- E (FROZEN-BASELINE 1 FAILED = CONTINUING-PROGRAMME.md): expected
  drift — the baseline pinned a live coordinator log; current bytes
  differ by my own L1/R1 log appends (14:59Z, pre-verifier-session).
  Disposition: interpret the baseline as 3639/3639 over frozen paths
  + 1 live file; future checks exclude or tolerate that line. The
  baseline is NOT regenerated (would invalidate the verifier's
  checked artifact).

## Acceptance mapping (CONTINUING-PROGRAMME R1)

Settle all-or-nothing: yes. Kill-during-settle/fusion/fission defined
+ recovery-exercised: yes. Operator-repair explicit where declared:
yes. Tests pass: yes. No partial states demonstrable: yes
(verifier probed for them). Independently verified: yes. r1 intact: yes.

**R1 status: ACCEPTED. successor-003/ FROZEN as-verified (45/45).**
Closes r1 LIMITS-11; narrows r1 LIMITS-3 to quarantine-transfer only.
Remaining interruption scope: quarantine-transfer operator-repair,
multi-writer, disk-loss (torn ledger refuses loudly), cross-host.
