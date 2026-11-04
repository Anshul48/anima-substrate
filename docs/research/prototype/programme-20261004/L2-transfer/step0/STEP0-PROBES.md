# STEP-0 PRE-COMMIT — probe grid list (frozen before any probe run)

- Written: 2026-10-04, BEFORE any L2P execution. This file fixes the probe
  set; no additions, removals, replacements, or re-rolls after first run.
- IDs `L2P-*` are throwaway: never reused as train/test in any later phase.
- Host: ACCEPTED H2-lane (46/46 baseline), consumed ONLY via `release.py`
  CLI. State dirs under `step0/runs/` (this work dir; L1 precedent —
  frozen H2-lane/ stays untouched).
- Grids: L1 solvability-preserving transforms (task-label permutation +
  machine swap, fixed seeds) applied to T4 (S2 grid) / T5 (S4-followup
  grid) / T6 (T5 + S5{M0,t3} + F{[S5]} + [E,F], L1-proven VALID 6/6).
  Adapter `list2slot/v1` for all probes (proven; holdings split is the
  varied dimension, not adapter).
- Holdings partitions pre-registered below to span derived_rounds {2,3,4}
  x split {True, False} x rule lanes {central, local} x sizes {4,5,6},
  per L2-DESIGN §6 step-0 (1 round is ungeneratable: non-empty tasks AND
  non-empty prefs force >= 2 non-empty holdings parts).
- Expected derived values below are hand counts (non-empty parts among
  req-L/req-S/pref-L/pref-S; split = both sides hold something); the
  AUTHORITATIVE values come from `release.py explain-route --task-json`
  (prediction-only, no execution) recorded at run time.
- Abort criterion (frozen, L2-DESIGN §6 verbatim): if no probe pair shows
  a lane crossover (some probe cheaper-central AND some probe cheaper-local
  in central_bytes, both VALID), L2-execute DOES NOT PROCEED.

## Probe list (8 probes, pre-committed)

| probe   | size | seed | req L / S        | pref L / S       | exp rounds | exp split | exp rule lane |
|---------|------|------|------------------|------------------|------------|-----------|---------------|
| L2P-01  | 4    | 901  | A,B / C,D        | A,B / C,D        | 4          | True      | local         |
| L2P-02  | 4    | 902  | A,B,C,D / --     | A,B,C,D / --     | 2          | False     | central       |
| L2P-03  | 4    | 903  | A,B / C,D        | A,B,C,D / --     | 3          | True      | local         |
| L2P-04  | 5    | 904  | A,B,C / D,E      | A,B,C / D,E      | 4          | True      | local         |
| L2P-05  | 5    | 905  | A,B / C,D,E      | A,B,C,D,E / --   | 3          | True      | local         |
| L2P-06  | 5    | 906  | A,B,C,D,E / --   | A,B / C,D,E      | 3          | True      | local         |
| L2P-07  | 6    | 907  | A,B,C / D,E,F    | A,B,C / D,E,F    | 4          | True      | local         |
| L2P-08  | 6    | 908  | A,B,C,D,E,F / -- | -- / A,B,C,D,E,F | 2          | True      | local         |

Notes:
- Labels above are pre-permutation; the generator applies the seeded
  permutation consistently to tasks/precedence/prefs/holdings (holdings
  reference permuted labels; partition SHAPE unchanged, so expected
  derived values hold under any permutation).
- L2P-02 is the §6 "tiny unsplit holdings central corner".
- L2P-08 is the minimal-rounds split (2 rounds, split True).
- Partition-shape coverage: even split (01/04/07), unsplit (02),
  reqs-split/prefs-together (03/05), reqs-together/prefs-split (06),
  crossed (08). Q1a-style scheme variety recorded per probe.

## Procedure (fixed)

Per probe x lane in {central, local}: fresh dir `step0/runs/<probe>-<lane>`:
`init` -> `run --task-json <probe>.json --lane-override <lane>` ->
record VALID/central_bytes/direct_bytes (stdout) + ledger entries/invokes
(parsed from OUR ledger.jsonl) -> `ops settle --worlds SC-L,SC-S`.
Guard batch (same phase, non-probe): fresh dir `step0/runs/guard-S1S2`:
`init` -> `run --tasks S1,S2` (rule lanes) -> must reproduce EXPECTED
(S1 central 655/0, S2 local 310/500); any deviation voids the phase.
Driver: `step0/run_step0.py` (stdlib-only, subprocess CLI calls only).
Logs: `step0/logs/`. Results: `step0/STEP0-RESULTS.json`.
