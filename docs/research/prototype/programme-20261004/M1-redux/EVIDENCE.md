# M1-redux EVIDENCE — fit→evaluate on held-out descriptors (H2)

- Date (UTC): 2026-10-04. Host: frozen ACCEPTED H2-lane via `release.py`
  CLI only. $0, offline, stdlib-only; `PYTHONDONTWRITEBYTECODE=1`.
- Frozen inputs: `PREREG.md` (`cfe4f633…`), `predicates.py` (`a1089fb5…`),
  `DESIGN.md` (`89c0f0d9…`), 36 task pins (`main/task-pins.sha256`
  `96aa3a91…`). Log-entry text: `PREREG-LOG-ENTRY.md`
  (entry_hash `e077d5e4…`, file `cd07714c…`; coordinator appends).
- Single evaluation run (no peeking/tuning); verdict imports frozen
  `predicates.verdict`.

## 1. Commands (from the repo root)

```
export PYTHONDONTWRITEBYTECODE=1
cd prototype/programme-20261004/M1-redux
python3 gen_main.py --out main/tasks            # pre-freeze (deterministic)
python3 run_main.py 2>&1 | tee main/run.log     # 74 runs post-freeze
python3 harness.py 2>&1 | tee main/eval.log     # single evaluation
```

Raw records: `main/run.log`, `main/train-results.json`,
`main/test-results.json`, `main/verdict.json`, `main/eval.log`;
per-run dirs under `main/runs/` (74: `tr-*`, `te-*`, 2 guards).

## 2. Result vs thresholds (primary)

```
model MAE=0.00 const MAE=233.25 rule MAE=38.07
P1=True P2=True valid=True OVERALL=PASS
items=36 valid=36 fallback=0 guards=True disjoint=True
```

- P1 (mae_model < 0.5 × mae_const): 0.00 < 116.63 → TRUE.
- P2 (mae_model < 0.5 × mae_rule): 0.00 < 19.04 → TRUE.
- Validity: 36/36 test items present + VALID (CLI True + artifact True,
  quality n/n); 0 fallback uses (coverage held); both phase guards
  reproduce S1 655/0 + S2 310/500 exactly; TR/TE/T0 IDs pairwise disjoint.
- **OVERALL = PASS.** Grid+holdings partition features predict per-lane
  `central_bytes` on held-out descriptors, beating both baselines.

## 3. Why exact (mechanism, pre-registered in step-0 §Structure)

Every test item equals its train cell mean (max|err| = 0.0) because metered
bytes are (fragment-pattern, size, lane)-determined with fixed ID lengths:
fragment totals = per-fragment overheads + total grid content, so E/F
placement and label-identity variations cancel in the sum (the 6
placement-divergent cells and all 9 permuted-identity cells confirm it).
The PREREG §5 expectation was "near-exact, residual O(0–30)"; actual 0.

## 4. Secondaries (advisory, no thresholds)

- Per-size model MAE: 0.00 / 0.00 / 0.00 (n=12 each).
- Permuted-identity test MAE 0.00 (n=18); plain-complementary MAE 0.00
  (n=18) — identity-invariance holds across 9 novel grids, not one probe.
- Max|err|: model 0.0, const 400.8, rule 169.8.
- Entries/invokes: lane-INVARIANT both phases (r2: 21/5 ×9/lane;
  r3: 23/6 ×3/lane; r4: 25/7 ×6/lane) — overhead guards, not the estimand.
- direct_bytes: central lane always 0; local lane 12 distinct values
  (337–612, pattern×size-determined clarify bytes). Recorded only.
- Wall-clock 1.5–4.3s/run, non-binding covariate only.

## 5. Non-claims (binding)

PASS is a calibrated cost mapping, NOT transfer and NOT discovery: the
mapping rides the host's mechanical (pattern, size, lane)-determinism.
Bytes exist only where executed (all 36 test bytes are LEDGER/ARTIFACT-
recorded from fresh H2 executions). No tuning was performed (single
evaluation; predicates byte-identical pre/post: `a1089fb5…`).

## 6. Integrity

- H2-lane IDENTITY post-run: 46/46 OK; `runs/` = demo dir only (no probe
  state entered the frozen tree; all state under this work dir).
- Frozen prereg bytes unchanged post-freeze (PREREG.md `cfe4f633…`,
  predicates.py `a1089fb5…` re-verified at evaluation).
