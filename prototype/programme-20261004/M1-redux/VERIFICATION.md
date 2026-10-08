# M1-redux VERIFICATION — independent acceptance record

- Verdict: **ACCEPT-WITH-NOTES** (PASS stands).
- Verifier: independent lane (strictly read-only; probe script in
  /tmp; no new H2 executions — all evidence re-derived from on-disk
  ledgers/artifacts).
- Date: 2026-10-04. Builder files untouched by verification.

## Independent confirmation (re-derived, not trusted)

- Pins 7/7 + task pins 36/36 match; predicates quoted verbatim;
  PREREG-LOG chain verified from both files (genesis → af809304…,
  entry → e077d5e4…).
- Ordering monotonic: PROBE-SET → t0 runs → STEP0-RESULTS → tasks →
  DESIGN → predicates → runner → harness → PREREG → ENTRY (14s
  before first main run) → 74 runs → verdict → EVIDENCE →
  countersign. Zero main runs predate PREREG.
- Isolation: TR/TE/T0 18/18/15 pairwise disjoint; 0 TE in t0/train;
  0/18 test files byte-equal to any train file.
- Full recomputation from RAW run dirs (reimplemented lane_bytes
  over frozen canonical_bytes): 0 mismatches on all 72 runs;
  72 distinct ledger timestamps (fresh executions, not copies);
  72/72 VALID; refit MAEs exactly 0.0000/233.2500/38.0694;
  frozen predicates.verdict → PASS; guards exact both phases;
  0 fallback uses.
- Step-0 recounted 26 > ~20 → PROCEED correct; T0 IDs retired.
- H2 IDENTITY 46/46; successor-003 45/45; no writes into H2.
- Scope honesty: "transfer"/"discovery" appear only as explicit
  non-claims; wall-clock non-binding only; secondaries re-verified.

## Notes (record-only, accepted; dispositions)

1. Weak-novelty subset: 6 test tasks differ from train donors only
   by task_id characters (verified by diff). IMMATERIAL: on the 24
   genuinely-novel items alone the verdict still passes with huge
   margin (0.00 vs 253.38/34.59). Disclosure gap noted (DESIGN §2
   vs gen docstring; pre-freeze pinned). No action.
2. Post-hoc countersign: coordinator LOG append came after execution,
   against the log's as-written rule — under the brief's explicit
   exception procedure. Trail sound (ENTRY predated first run;
   hashes immutable; PREREG §5 expectation was wrong — strong
   anti-post-hoc signal). Disposition: PREREG-LOG rules amended
   (RULES-AMENDMENT-1) to admit the exception procedure explicitly
   with conditions.
3. Lookup-table legitimate: 36 size-1 groups = single-donor lookup,
   but a legitimate held-out prediction (key carries no byte info;
   all bytes freshly executed; descriptors disjoint; strata
   pre-disclosed). No action.
4. H2 FROZEN-BASELINE "failures" are scope artifacts of the
   verifier's environment (absent trees), not baseline corruption;
   the file is intact per IDENTITY. No action.

## Acceptance mapping (M1-redux brief)

Pre-registered mapping evaluation: yes. Held-out descriptors with
stated baselines: yes. Honest result (PASS with exact mechanism +
binding non-claims): yes. Independently verified: yes (this file +
verifier report in coordinator session log). H2 + frozen intact: yes.

**M1-redux status: ACCEPTED as a calibrated cost mapping.**
Finding: (fragment-pattern, size, lane)-determinism makes per-lane
coordinator cost exactly predictable from no-execution features on
held-out descriptors. NOT transfer, NOT discovery (binding).
