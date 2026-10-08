# STEP0-ABORT — L2-execute DOES NOT PROCEED (frozen criterion fired)

- Date: 2026-10-04. Lane: L2-execute (AUTH-2), step 0 only.
- Host: ACCEPTED H2-lane, consumed ONLY via `release.py` CLI.
- Pre-commit: `step0/STEP0-PROBES.md`
  (sha256 `9d4411dc38ad436e193e6a761c3b0136f0ef44488b248557519832a5541ea8d5`),
  written BEFORE any probe run; 8 probes, no additions/removals/re-rolls.
- Results: `step0/STEP0-RESULTS.json`
  (sha256 `23914c6b3c4bf60c22e2bb43742aa2848ed5908c11b3283d66d45c39a3752adf`);
  full CLI transcript `step0/logs/step0.log`; run dirs `step0/runs/`.
- Guard batch (same phase): S1 rule-lane 655/0, S2 rule-lane 310/500 —
  both EXPECT MATCH (phase valid, host behaving to spec).
- Frozen trees untouched: H2-lane IDENTITY 46/46 OK before AND after;
  successor-003 IDENTITY 45/45 OK before AND after; no new files in
  H2-lane/runs (only the as-accepted demo dir); all L2 state under
  `prototype/programme-20261004/L2-transfer/`.

## Probe table (per probe x lane, fresh dirs, VALID all 16 runs)

Derived inputs below are authoritative `explain-route --task-json`
values (they match the pre-committed hand counts exactly).

| probe | size | rounds | split | rule  | central-lane central_B | local-lane central_B | cheaper lane | entries C/L | invokes C/L |
|-------|------|--------|-------|-------|------------------------|----------------------|--------------|-------------|-------------|
| L2P-01 | 4 | 4 | T | local   | 834 | 318 | local | 25/25 | 7/7 |
| L2P-02 | 4 | 2 | F | central | 671 | 318 | local | 21/21 | 5/5 |
| L2P-03 | 4 | 3 | T | local   | 761 | 318 | local | 23/23 | 6/6 |
| L2P-04 | 5 | 4 | T | local   | 892 | 340 | local | 25/25 | 7/7 |
| L2P-05 | 5 | 3 | T | local   | 819 | 340 | local | 23/23 | 6/6 |
| L2P-06 | 5 | 3 | T | local   | 802 | 340 | local | 23/23 | 6/6 |
| L2P-07 | 6 | 4 | T | local   | 962 | 362 | local | 25/25 | 7/7 |
| L2P-08 | 6 | 2 | T | local   | 799 | 362 | local | 21/21 | 5/5 |

Direct bytes (for the record): equal to central-minus-local per probe
(516/353/443/552/479/462/600/437) — i.e. `central_B(central) =
central_B(local) + direct_B(local)` exactly, every probe.

## Criterion evaluation (no discretion)

Frozen abort criterion (L2-DESIGN §6): proceed ONLY if some probe is
cheaper-central AND some (other) probe is cheaper-local in
central_bytes, both VALID.

- Cheaper-central probes: **0 of 8**. Cheaper-local probes: **8 of 8**.
- All 16 runs VALID (quality full marks; settlement clean).
- Guard MATCH (host nominal) — this is a finding about the cost
  structure, not a method failure.

**Result: NO CROSSOVER → ABORT.** L2-execute ends here per the frozen
rule. No DESIGN.md / PREREG.md / extraction / transfer runs were
produced or started; L2P-* IDs are retired as throwaway. This is a
complete result (L2-DESIGN §6: "a second clean negative arrived at for
the price of probes, not a full experiment").

## Reasoning (why no crossover can appear — mechanism, confirmed)

The probe data show the lane choice only RE-ROUTES a fixed byte mass:
for every probe, `central_B(central) = central_B(local) +
direct_B(local)` to the byte, with `central_B(local)` constant per
grid size (318/340/362 = the two terminal commitments, which are
lane-independent). Central-lane central bytes additionally carry every
clarify fragment; local-lane central bytes carry none. Every lane task
has >= 1 non-empty holdings part (>= 2 here: non-empty tasks AND
prefs), hence a strictly positive fragment mass, hence for EVERY
generatable task:

    central_bytes(central, t) > central_bytes(local, t).

A cheaper-central probe is therefore not merely absent from this
sample — it is ungeneratable under the H2 byte model. The X3 "central
wins small" cut the design hoped to re-discover compares DIFFERENT
tasks across lanes (S1-central 655 vs S2-local 310), not the same task
across lanes; within-task, in the §6 primary unit (central_bytes), the
local lane wins everywhere by construction. Ledger entries/invokes are
additionally lane-invariant (identical counts both lanes, all probes),
confirming L2-DESIGN §3-A-(b).

Consequence for the design: the H2 delta as accepted provides a lane
*hook* but not a lane *trade-off* — there is no task-conditional
surface in central_bytes (or entries/invokes) for any recipe to grip.
A recipe fitted here would be `always-local`, degenerate exactly as
L1's `always-reuse`. The honest next bets are the ones L2-DESIGN §9-10
already named for this branch: kill L2-execute, pivot learning budget
to vector-13 mapping work on the frozen host (concurrent-safe, no host
change), and re-examine any H2-dependent vector-15 sequencing, since
the surface H2 was built to provide does not exist in the primary
unit. No re-probing or family re-sizing can change a strict
per-task inequality; per the brief, no tuning was attempted.

## Reproduction (from the repo root, $0, offline, stdlib-only)

    cd prototype/programme-20261004/L2-transfer/step0
    PYTHONDONTWRITEBYTECODE=1 python3 gen_probes_step0.py --out probes
    PYTHONDONTWRITEBYTECODE=1 python3 run_step0.py
    # compares guard vs EXPECTED inline; writes STEP0-RESULTS.json

All host contact is via `release.py` CLI subprocess calls; probe grids
are authored bytes in `step0/probes/` (L2P-* throwaway).
