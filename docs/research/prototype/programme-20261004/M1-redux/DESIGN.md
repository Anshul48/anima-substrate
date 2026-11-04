# M1-redux DESIGN — grid+holdings → per-lane central_bytes on held-out descriptors

- Date (UTC): 2026-10-04. Work dir: `prototype/programme-20261004/M1-redux/`.
- Host: frozen ACCEPTED H2-lane, consumed ONLY via `release.py` CLI
  (black-box subprocess, `PYTHONDONTWRITEBYTECODE=1`). No host imports,
  no host modification. No `--with-sst` (SST leg not needed).
- Step-0: `STEP0-RESULTS.md` — PROCEED with 26 counted observations;
  structure notes below are step-0-calibrated (pre-prereg, allowed).

## 1. Question + estimand

Can grid+holdings features predict per-lane coordinator cost
(`central_bytes`, LEDGER/ARTIFACT-recorded) on HELD-OUT lane descriptors,
beating a constant predictor AND a host-rule-derived predictor — on H2?

Estimand: for a held-out lane-task descriptor d and exec lane l ∈
{central, local}, predict central_bytes(d, l) as metered by the host's
`lane_bytes` recomputation (clarify receipts + commitment payloads).

## 2. Task family (frozen by `gen_main.py`, pins in `main/task-pins.sha256`)

- Bases: frozen H2 accept S2 grid (4 tasks), S4-followup grid (5 tasks),
  T6 extension (6 tasks, L1-precedent shape). Solvability-preserving
  transforms only (label permutation + machine swap, seeded) or identity.
- TRAIN: 18 tasks `M1R-TR-01..18` (plain grids, canonical splits).
- TEST: 18 tasks `M1R-TE-01..18`, disjoint descriptors (even cells:
  permuted grids seeds 900+idx; odd cells: plain grids, complementary
  splits). Test shapes ⊆ train shapes (18 matched count-cells; stratum
  coverage, not descriptor overlap — verified pre-prereg from JSON).
- All IDs 9 chars (task_id length enters fragment bytes — controlled).
- Train/test/T0 IDs pairwise disjoint by construction (asserted in harness).
- 6 shapes × 3 sizes: ALL_L, ALL_S, HALVES, REQL_PREFS, SPLIT3, ONEVREST
  (see `gen_main.py` for exact index splits).

## 3. Features (ALL computable from the task JSON WITHOUT execution)

Per (descriptor d, exec lane l) item, `features(d, l)` in `harness.py`:

- Grid: `n_tasks`, `n_slots`, `n_prec` (recorded; covary with size in-family).
- Holdings counts: `nL_req, nS_req, nL_pref, nS_pref`.
- Derived (own reimplementation of the DOCUMENTED rule, no host import):
  `derived_rounds` = #non-empty among the 4 holdings lists;
  `derived_split` = both sides hold (reqs or prefs);
  `rule_lane` = local iff rounds>=2 and split else central.
- Exec lane: `lane` ∈ {central, local} (the lane being predicted).

EXCLUDED (with step-0 evidence): `adapter` (B: v1==v2 bytes); label
identities — counts only (07: permutation byte-identical); exact
fragment-byte oracle (reimplementing canonical lengths would be
re-derivation of the meter, not a feature mapping — explicitly out);
wall-clock (recorded, non-binding covariate only).

## 4. Model class (deliberately simple)

Per-group-mean over partition features. Group key:
`(n_tasks, nL_req, nS_req, nL_pref, nS_pref, lane)`.
Fit = group means on train items (36). Predict = group mean.
Fallback (pre-committed): train lane-conditional global mean; expected
uses = 0 (coverage by construction); ANY use → VOID (method failure).

Rationale: step-0 shows truth is ~(fragment-pattern, size, lane)-
determined with identity-invariance; the fine count-key nests the pattern
(multiple count-cells may share a mean — e.g. T0-01==T0-04 — which
per-group-mean handles without forcing). Linear would mis-specify the
within-pattern count-invariance; group-mean does not assume a form.

## 5. Baselines (fit on train only)

- CONSTANT: train global mean (single number for all test items).
- HOST-RULE: train mean per `(rule_lane(task), exec_lane)` (4 groups).
  The host rule assigns lanes, not bytes; this is its natural byte
  predictor (conflates patterns within a rule lane — strictly weaker
  than pattern features by step-0 construction).

## 6. Metric + thresholds (exact predicates in `predicates.py` / PREREG.md)

- Metric: MAE over the 36 test items (18 tasks × 2 lanes) in central_bytes.
- P1 = (mae_model < 0.5 * mae_const): model at least halves constant error.
- P2 = (mae_model < 0.5 * mae_rule): model at least halves host-rule error.
- 0.5× is a substantiality bar (not epsilon-hunting), scaled by step-0:
  central bytes span ~324–980 with pattern gaps O(50–200); constant/rule
  residuals are O(50–100) while pattern-group residuals are O(0–30)
  (placement residual in 6/18 size-5/6 cells only).
- Validity gate (→ VOID, not NEGATIVE, if failed): 36/36 test items
  present + VALID; fallback_uses == 0; both phase guards reproduce the
  S1/S2 EXPECTED pins exactly (655/0 + 310/500); ID disjointness holds.
- OVERALL = PASS iff valid and P1 and P2; VOID iff invalid; else NEGATIVE.

## 7. Runs (74 total, one task per fresh state dir under `main/runs/`)

- Train: 18 tasks × {override central, override local} = 36 runs.
- Test: 18 tasks × {override central, override local} = 36 runs.
- Guards: S1,S2-by-name once per phase (train-phase, test-phase) = 2 runs.
- Per run: VALID (CLI + artifact), lane, central/direct bytes, ledger
  entries, invokes, wall-clock (covariate). Runner: `run_main.py`.

## 8. Analysis rules

Single evaluation run of `harness.py` after ALL executions (no
peeking-and-tuning); verdict imports `predicates.py` (never reimplements);
no task replacement/re-rolls; secondaries advisory only (per-size MAE,
plain-vs-permuted MAE, max-abs-err, entries/invokes invariance re-check,
direct_bytes descriptives). A clean negative is complete.

## 9. Non-claims (carried to EVIDENCE)

Prediction quality is not transfer; bytes exist only where executed; the
mapping rides the host's mechanical (pattern, size, lane)-determinism
(step-0 §Structure) — a calibrated cost map, not discovered knowledge.
