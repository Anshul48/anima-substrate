# M1-redux STEP-0 results: PROCEED (26 observations, content-sensitive bytes)

- Date (UTC): 2026-10-04. Host: frozen H2-lane via `release.py` CLI only.
- Pre-commitment: `PROBE-SET.md` (hand derivations, run plan, counting rule).
  Raw log: `t0-throwaway/step0-run.log`; machine record:
  `t0-throwaway/step0-results.json`. Runs: 33/33 rc=0.

## Observation table (sweep A: per-task x lane)

central_bytes / direct_bytes; entries/invokes per run dir (one task each).

| Probe | Shape L=(req,pref) | central lane | local lane | entries/inv |
|---|---|---|---|---|
| T0-01 (4) | (4,4) | 683 / 0 | 324 / 359 | 21 / 5 |
| T0-02 (4) | (0,0) | 661 / 0 | 324 / 337 | 21 / 5 |
| T0-03 (4) | (2,2) | 852 / 0 | 324 / 528 | 25 / 7 |
| T0-04 (4) | (4,0) | 683 / 0 | 324 / 359 | 21 / 5 |
| T0-05 (4) | (2,4) | 776 / 0 | 324 / 452 | 23 / 6 |
| T0-06 (4) | (1,1) | 852 / 0 | 324 / 528 | 25 / 7 |
| T0-07 (4 perm) | (2,2) | 852 / 0 | 324 / 528 | 25 / 7 |
| T0-09 (5) | (5,5) | 741 / 0 | 346 / 395 | 21 / 5 |
| T0-10 (5) | (2,2) | 910 / 0 | 346 / 564 | 25 / 7 |
| T0-11 (5) | (5,0) | 741 / 0 | 346 / 395 | 21 / 5 |
| T0-12 (5) | (3,5) | 834 / 0 | 346 / 488 | 23 / 6 |
| T0-13 (6) | (6,6) | 811 / 0 | 368 / 443 | 21 / 5 |
| T0-14 (6) | (3,3) | 980 / 0 | 368 / 612 | 25 / 7 |
| T0-15 (6) | (1,1) | 980 / 0 | 368 / 612 | 25 / 7 |

All sweep items VALID (CLI True + solution artifact True), quality n/n.

## Method checks (B–E, never counted)

- B adapter: T0-08 (v2 dup of 03) central = 852 = 03-central. Adapter excluded
  from features (clarify/commitment payloads never touch it).
- C determinism: 03-central rerun = 852, entries/invokes identical. Reruns
  are not distinct observations (counted once).
- D ruleequiv: 01-rule = central 683 = 01-central; 03-rule = local 324/528 =
  03-local. Rule lane duplicates the matching override byte-wise.
- E guard: S1 655/0 + S2 310/500 — matches `accept/EXPECTED.json`.
- Isomorphism: T0-07 (label-permuted + machine-swapped halves) = 03 bytes
  exactly, both lanes. Label identity carries no byte signal (same-length
  names); same-shape task correctly excluded from the count.
- Routing: all 15 hand-derived rule_lanes match ledger records (0 mismatches);
  override flags + derived inputs recorded as accepted.

## Structure found (sizes the main experiment)

- central_bytes (central lane): 9 distinct values across shapes x sizes;
  (Lr,Lp)==(Lr,Sp) (01==04: 683) — pref-fragment side doesn't matter
  ("SC-L"/"SC-S" equal length); (2,2)==(1,1) within size (03==06: 852,
  14==15: 980) — within-pattern req/pref COUNTS don't matter, only which
  of the 4 fragment slots are non-empty (L-req always carries full
  precedence; S-req none). Truth is ~(pattern, size, lane)-determined.
- central_bytes (local lane): size-determined only (324/346/368:
  2 x commitments; clarify goes direct). Partition-invariant within size.
- Ledger entries/invokes: rounds-determined (21/5, 23/6, 25/7),
  lane-INVARIANT — overhead guards, not the estimand (L2-DESIGN expectation
  confirmed). Wall-clock 1.9–4.2s, recorded as non-binding covariate only.

## Count vs abort criterion

- Counted: 13 distinct shape vectors (01–06, 09–15) x 2 lanes = **26**,
  all VALID with LEDGER/ARTIFACT-recorded central_bytes. (Even under
  coarse pattern-counting: 12 patterns x 2 = 24.)
- Variation: 9 distinct central-lane + 3 local-lane values — content-
  sensitive, not constant (no M1-mapping-P5 invariance trap).
- Abort threshold ~20: **exceeded → PROCEED to DESIGN.md + PREREG.md.**
- Caveat carried forward: bytes are mechanically (pattern, size,
  lane)-determined (07/B isomorphisms); prediction quality here is NOT
  transfer and NOT discovery of unknown structure — it is a calibrated
  cost mapping. Size-5/6 E/F (1-slot windows) placement adds honest
  within-shape residual the main experiment must span (see DESIGN.md).
