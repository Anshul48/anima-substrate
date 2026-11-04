# L1 DESIGN — held-out recipe transfer on the frozen r1 envelope

- Written: 2026-10-04T14:14:10Z (BEFORE extraction / transfer / baseline runs)
- Author role: L1 transfer-experiment researcher
- Work dir: `prototype/programme-20261004/L1-transfer/`
- Consumes: `prototype/successor-002/` (r1) ONLY via `release.py` CLI
  (black-box subprocess; `PYTHONDONTWRITEBYTECODE=1`). No r1 imports,
  no r1 modification. r1 identity at design time: `IDENTITY.sha256`
  41/41 OK (checked 2026-10-04T14:12Z).

## 1. Question

Do procedures (recipes: routing / split / reuse decisions) extracted
from completed r1 runs improve HELD-OUT task performance vs a competent
cold baseline, net of acquisition cost?

## 2. Envelope findings that shape the design (pre-prereg probes)

Pre-prereg feasibility probes (2026-10-04T14:12–14:13Z, dir `probes/`,
throwaway IDs `PROBE-*`, never reused as train/test) established:

1. `run_tasks` (CLI `run`) executes ONLY frozen S1/S2. Novel lane tasks
   CANNOT be executed through the consumer interface, so r1's
   canonical-bytes lane metric is NOT measurable on held-out tasks.
   This is an envelope boundary, recorded as a finding (see §7).
2. Novel follow-up tasks CAN be executed via `ops reuse --followup FILE`
   (fused composite, 1 invoke) and `ops split-pair --followup FILE`
   (fission children, 3 invokes). Both share r1's deterministic solver,
   so success/quality are solver-determined; per-task COST (ledger
   entries, invokes) is the transferable dimension.
3. Modest scale-up IS supported by the host: a 6-task/6-slot grid ran
   VALID 6/6 via split-pair (`probes/pb-reuse` log).
4. Label-permutation + machine-swap (applied consistently) preserves
   solvability (`PROBE-4B` VALID 4/4). A hand-edited grid that broke
   precedence/time consistency failed loudly with `no valid schedule`
   (`PROBE-4`) — failures are loud, never silent.
5. `explain-route --task-json FILE` returns routing decisions for novel
   descriptors (prediction only; no execution, no bytes).
6. All L1 state dirs live under the L1 work dir (NOT inside
   `successor-002/`); probes wrote nothing into r1 (verified with
   `find -newer`, empty).

## 3. Task family (frozen by `gen_tasks.py`)

Scheduling grids in the successor envelope, generated ONLY by
solvability-preserving transforms (see `gen_tasks.py` header) from r1's
own proven grids. Sizes 4/5/6 tasks-slots (4 = r1 scale, 5 = S4 scale,
6 = modest scale-up per probe 3).

- TRAIN (extraction only): L1-TR-01..06 — 2× size-4 (seeds 101,102),
  2× size-5 (seeds 103,104), 2× size-6 (seeds 105,106).
- TEST (held-out, never executed before the transfer test): L1-TE-01..12
  — 4× size-4 (seeds 201–204), 4× size-5 (seeds 205–208),
  4× size-6 (seeds 209–212).
- Files: `tasks/L1-TR-*.json`, `tasks/L1-TE-*.json`; sha256 pins in
  PREREG.md. Generator pin: `gen_tasks.py` sha256
  `e579da25c723d007a771f31d74023d4c9394aeeead048650edad98bf1747b7eb`.
- Any r1-reported failure on any task×arm is PRESERVED and reported;
  tasks are never replaced or re-rolled.

## 4. Recipe representation + extraction procedure

Primary recipe R-path (org-path selection): a JSON decision list
mapping task features `{n_tasks, n_slots, shape}` (shape ∈
{fresh-4, extension-5, extension-6}) to an org path ∈ {reuse,
split-pair}, plus a `default` path. Frozen as `recipe.json`.

Mechanical extraction (no hand-tuning; `harness.py extract`):
1. For each TRAIN task, run BOTH arms on FRESH state dirs:
   - setup (both arms): `init` → `run --tasks S1,S2` → `ops fuse`
     (mirrors the r1 demo path; S1/S2 byte observations also feed §6).
   - reuse arm: `ops reuse --followup <task>` → `ops settle`.
   - split arm: `ops fission` (partition
     `sched.requirements+sched.composite→SC-L2, sched.slots→SC-S2`,
     the r1 partition) → `ops split-pair --followup <task>` →
     `ops settle`.
2. Per task×arm record: VALID (from `artifacts/solution-<id>.json`),
   quality/prefs_total, ledger entries (lines of `ledger.jsonl`),
   invoke entries (`kind==invoke` count), ledger bytes, wall seconds.
3. Fit: for each feature-value group, the cheaper arm subject to VALID
   wins the group (majority over group members); ties → globally
   cheaper arm; groups with any failure → the successful arm, or
   `default` if both fail (reported, never hidden).
4. Emit `recipe.json` + `extraction-log.json`. Acquisition cost =
   ledger entries + invokes summed over ALL training runs (both arms,
   setup included).

Secondary recipe R-route (routing prediction, NO performance claim):
hypothesis class = {`local iff rounds>=k AND split` k∈1..5,
`local iff rounds>=k` k∈1..5, `local iff split`, always-central,
always-local}. Fit mechanically on the S1/S2 lane decisions observed
during extraction setup runs: keep rules consistent with ALL
observations; tie-break = fewest literals, then lexicographic rule
name. Predict lanes for the 8 frozen descriptors in
`tasks/secondary-descriptors.json` (novel rounds×split combos on
held-out grids); ground truth = r1 `explain-route`. This tests
few-shot predictive transfer ONLY (bytes need execution, which the
consumer interface refuses for novel lane tasks).

## 5. Held-out split + cold competent baseline

- Held-out: L1-TE-01..12 (pins in PREREG.md). No test task is executed,
  routed, or inspected for content before the transfer test begins
  (existence + hashes only).
- Transfer test (`harness.py transfer`): for each TEST task, run the
  recipe-prescribed arm on a FRESH state dir (same setup + settle as §4).
- Cold competent baseline (`harness.py baseline`): FIXED split-pair arm
  for every TEST task (fresh dirs, same setup + settle). Competent:
  same-solver 100%-success path on solvable tasks, the documented
  post-fission cooperation pattern (r1 S6), zero training knowledge,
  fixed BEFORE extraction results exist. A fixed always-reuse reference
  cost line is reported for context but is NOT the baseline.

## 6. Metrics + acquisition-cost accounting

Per task×arm (read from OUR run dirs only): VALID, quality,
ledger entries (PRIMARY cost unit), invokes (secondary cost unit),
ledger bytes + wall time (recorded, non-binding).
NOT measurable on held-out tasks by consumer-interface construction:
r1 canonical JSON lane bytes, clarify rounds (follow-up paths have no
dialogue). S1/S2 byte observations are reproduced as a calibration
check only (must match EXPECTED.json: 655/0, 310/500).
Acquisition cost (§4 step 4) is charged IN FULL against held-out gains:
recipe total = acquisition + transfer-arm cost; baseline total =
baseline-arm cost on the same 12 tasks. No amortization tricks, no
per-task averaging that hides the training bill.

## 7. Predicted outcome (design-time expectation, NOT a result)

Both follow-up paths share r1's deterministic solver and fixed
pipelines (1 vs 3 invokes, task-content-independent), so the expected
finding is: identical success/quality on both arms, a task-INDEPENDENT
cost gap, hence a recipe with NO task-conditional content — a clean
honest NEGATIVE on transfer (predicted: P1 FAIL, P2 PASS, P3 FAIL;
see PREREG.md). The experiment is still capable of detecting
conditionality if it exists (per-task both-arms measurement would show
it), so the negative would be informative, not vacuous: it maps the
envelope boundary where recipe transfer has no surface.
