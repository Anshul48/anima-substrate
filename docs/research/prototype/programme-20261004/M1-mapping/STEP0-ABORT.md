# M1 STEP-0 — observation budget: ABORT (frozen host yields 2–3, need ~20)

- Date (UTC): 2026-10-04
- Work dir: `prototype/programme-20261004/M1-mapping/`
- Host: `prototype/successor-003/` (FROZEN), consumed ONLY via `release.py` CLI
  (black-box subprocess, `PYTHONDONTWRITEBYTECODE=1`). No host imports, no host
  modification. All probe state dirs under `t0-throwaway/` in this work dir
  (NOT inside successor-003/ — experiment probes, not release runs; frozen
  tree untouched takes precedence per the M1 brief; same placement precedent
  as L1-transfer).
- Probe IDs: `M1-T0-*` (throwaway, pre-prereg, never to be reused as train/test).

## Verdict

**ABORT — do not proceed to DESIGN/PREREG/execution.** The frozen host can yield
at most **2 same-class (feature → LEDGER/ARTIFACT-recorded `central_bytes`)**
observations, **3** counting the different-class S3 kill-resume point — far below
the ~20 needed. This is a complete, publishable result: the M1 estimand
(per-lane coordinator cost on held-out lane descriptors) is unmeasurable on the
frozen host by consumer-interface construction.

## Observation budget (measured, throwaway)

| # | Probe | Result |
|---|---|---|
| P1 | `init` + `run --tasks S1,S2` | S1: lane=central central=**655** direct=0; S2: lane=local central=**310** direct=500. Matches `accept/EXPECTED.json`. Bytes exist ONLY here. |
| P2 | `run --tasks M1-NOVEL` | LOUD refusal, rc=1: `ValueError: run_tasks supports ['S1', 'S2']; got ['M1-NOVEL']`. Novel lane descriptors CANNOT be executed. |
| P3 | `explain-route --task-json novel-desc.json` (rounds=5, split=true) | Returns lane=local + rule text ONLY. Predicted lane, not cost; no execution, no bytes. |
| P4 | Fresh dir, re-run S1,S2 | Byte-IDENTICAL (655/310); `solution-S1/S2.json` diff-clean. Deterministic: reruns are NOT distinct observations. |
| P5 | `fuse` → `reuse` × 2 distinct followups (F1 vs label-permuted+machine-swapped F2, both VALID 5/5) | Reuse returns valid/quality/prefs/lineage ONLY — **no byte fields**. Ledger lines 55=55 with IDENTICAL kind histograms (invoke 13=13, …). Even the fallback cost unit is task-content-independent on successor-003. |
| P6 | `fission` → `split-pair` (VALID 5/5) | Returns valid/quality/prefs/refs ONLY — **no bytes** (host docstring: "no lane bytes are claimed here"). |

## Upper-bound accounting (by construction + probes)

1. `run` allowlist = {S1, S2} (P2 + `api.LANE_TASKS`): exactly **2** fixed
   (feature → `central_bytes`) points. Determinism (P4) means no more.
2. `explain-route` accepts novel JSON but predicts lanes only (P3): **0** costs.
3. `reuse` / `split-pair` accept novel followups but emit no byte metrics
   (P5/P6 + return-shape code): **0** costs. Fallback units (ledger entries,
   invokes) are content-independent (P5: 55=55 identical histograms), so they
   cannot support "features predict cost beating baselines" — a constant
   predictor ties at best, and they are not the `central_bytes` estimand.
4. S3 via `ops kill-resume` (fixed FI.S3 input, EXPECTED `central_bytes_ref`
   685): at most **+1**, and a DIFFERENT measurement class (kill-resume
   adaptation flow: revise+revoke+ruling+void+re-propose), not a plain lane
   execution of a held-out descriptor. Not executed (kill drill unnecessary
   for the bound; 2 vs 3 changes nothing against ~20).
5. `calibrate.py` S2-both-lanes uses host INTERNALS (`routing`, `pipeline`
   imports) — not a consumer interface, excluded by the brief. Wall-clock is
   excluded as a primary by the brief (non-replayable). Host-state mutations
   (revise/revoke before `run`) vary authority state, not grid+holdings
   descriptor features — wrong estimand, not counted.

**Total: 2 (same-class) / 3 (counting S3). Abort threshold: ~20. → ABORT.**

## Why no PREREG/DESIGN follows

Fitting or evaluating any grid+holdings → cost predictor needs ≥~20 distinct
measured costs with held-out descriptors; the host yields 2–3 with NO executable
held-out lane task. Any "prediction" built here would be fit on S1/S2 and tested
on unmeasurable descriptors — untestable, hence not an experiment. L1 lesson
holds on successor-003: bytes exist only where executed (P1 vs P2/P3).

## What would unblock M1 (not requested, no host change made)

A host affordance that executes NOVEL lane descriptors through the metered
coordinator path (e.g. `run --task-json` executing fragment/clarify dialogue
with recomputed `central_bytes`), i.e. new-builder work outside the frozen
host. Out of scope for this frozen-host experiment.

## Frozen-tree integrity

- No writes into `successor-003/` or any other programme/neighbour dir: all
  probe state under `prototype/programme-20261004/M1-mapping/t0-throwaway/`.
- Post-step-0 check: `cd prototype/successor-003 && sha256sum -c IDENTITY.sha256`
  → 45/45 OK (see report). `runs/` dir listing unchanged (2 demo dirs only);
  no `__pycache__` / `.test-tmp` created (BYTECODE disabled; calibrate/tests
  never run).

## Reproduction (all under this work dir)

```
export PYTHONDONTWRITEBYTECODE=1
M=prototype/programme-20261004/M1-mapping/t0-throwaway
python3 prototype/successor-003/release.py init --state-dir $M/<d>
python3 prototype/successor-003/release.py run --state-dir $M/<d> --tasks S1,S2
python3 prototype/successor-003/release.py run --state-dir $M/<d> --tasks M1-NOVEL   # expect rc=1 ValueError
python3 prototype/successor-003/release.py explain-route --task-json $M/novel-desc.json --json
# reuse/split-pair: ops fuse [--reason ...] → ops reuse --composite SC-FUSED --followup $M/f1.json
#                   ops fission --composite SC-FUSED --left SC-L2 --right SC-S2 \
#                     --partition sched.requirements=SC-L2,sched.composite=SC-L2,sched.slots=SC-S2 \
#                     --reason ... → ops split-pair --left SC-L2 --right SC-S2 --followup $M/f1.json
```
