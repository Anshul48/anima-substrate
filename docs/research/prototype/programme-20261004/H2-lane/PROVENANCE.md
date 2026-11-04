# PROVENANCE.md — H2-lane copy record

Source: `prototype/successor-003/` (NOT its `runs/` evidence, NOT
`.test-tmp/`).
Method: `tar --exclude='./runs' --exclude='./.test-tmp' -cf - . |
(tar -xf -)` into `prototype/programme-20261004/H2-lane/`, then
per-file sha256 compared source-vs-copy: all 100 files IDENTICAL
(source hashes also match `successor-003/IDENTITY.sha256` for its 45
covered files; `cd prototype/successor-003 && sha256sum -c
IDENTITY.sha256` → 45/45 OK immediately before the copy).
Copy timestamp (UTC): 2026-10-04T15:28Z. `successor-003/` was not
modified during or after the copy (covered by this tree's
`FROZEN-BASELINE.sha256`, which pins the frozen trees, plus the
pre-work snapshot `/tmp/h2-frozen-pre.sha256` — see EVIDENCE.md).

This tree is EXPERIMENTAL (AUTH-1 host-delta build for L2-DESIGN §5).
It is NOT `successor-004` and NOT a release candidate.

## Per-file sha256 at copy time (source == copy; top-level files)

| file | sha256 |
|---|---|
| CONSUMER.md | 98ef59d6539d1f079f21664dd77feebfc9b7c5a654147c7191f8a3990ad1f676 |
| CONTRACT-GAPS.md | 034be5e81ff844903cf32cfbe91abcf5f420e48ea4b0748bdc4bc65fb44169c2 |
| EVIDENCE.md | 991ea38038b57cfac4405ae7e39ef4e910a286edba730082a7ec8480e52828e7 |
| FROZEN-BASELINE.sha256 | 3ab982b59f43a4a34b6ea80560a992ea5d138bea529c914ac12c134eed46dd56 |
| IDENTITY.sha256 | cb5829c2ef779094c83d90d39c5cdd8a1858b65bc7c7aa41a0dc76ebb50c91c1 |
| INTERRUPTION-BOUNDARIES.md | 18500eaadefc6961d10a9fb97eaff626b8089d19ac97643e1e7020e9296deea9 |
| LIMITS.md | 5985a8d4badce38f9f23c636767eaba0235dd7ecbc6027a3322ac483b5e66a96 |
| OBLIGATIONS.md | 578b3219d3dcbd90f1325b9554b648cdc2f2dd5f79c046f9fe0374b1d78e3b1d |
| ORG-OPS.md | 2f0898311cfcfb476f7513c939b3997a0975968a5f1ac4de388c6084fed46873 |
| PROVENANCE.md | 90cf248289b23957194fc276dd7ff7b9f2b48fe6e6a6deb8c8edc4da3b10fe57 |
| REPORT.md | 9d15c16f67f5576d094bac5622fecec366756ac258852097c253680f3600f0bc |
| REPRODUCE.md | 31b9441c28a08e0af6fc04cfe13bac71cad5ed7060cc496e278afdac46e3292d |
| SEPARATION-PATHS.md | 1265b471a14b5111b8f5fa267236bcbcb2c8f697c841f873ad18a91db5bcadda |
| SUCCESSOR-REPORT.md | eecfd3b5cfb60218ed8393be9bbe0fe195c13aa3d40993f1c6f74f557ffefb3c |
| VENDORING.md | 51f7bbb87637b201c39dd1944bee80f8a2bfc09587b4e5ff8ad7677a159994f3 |
| api.py | c52da8ff2d88af0210ecc11f5c911ed458d1029d816e6463e0bb8b4044063fd1 |
| calibrate.py | 5a2e99b2d1b9f1ef86928aeb803638464457c0116d67b2c5238ea67b51d2a51e |
| fusion.py | 6e70fe4772d732042e3fefd8067f27a6beb1b91d850a4ffefb0a5590d5d369d8 |
| make_snapshot_manifest.py | 557fea67b5bb86587ea14c8378959e30f3758a22f75536ce8f98f2fb70c7c519 |
| minihost.py | a2b7ed5925b5a2bb9fedfc81d7ab7ae14bb0bdccd896fc9d95d3aa182ead05d3 |
| pipeline.py | e4aa37a1ebdf89e32e82f1107a37d7248e9ee67671961a1fc16baa4b2e73aa0a |
| recover.py | 9c013ee515752da00fb6e090997e8f0a1bf75ed1e53b0a3d14859f28f7b759f6 |
| release.py | e4d50ac1b4963dadc07f3754c08061f40f57c9c3dc250a61f7a80d0ee89d5768 |
| resume.py | 2cd99df7f53f616724264687be451b23c32ed8a15d44093fd6edb347ebd3cc80 |
| routing.py | 36dd4833b774939f13dadfe5e91847c05af8e1ed1ec59be695f6028cf8efe685 |
| sched_checker.py | 197e684aa64335e461f854a114b409afe9bb0d63fa09c669371533d3c93e1972 |
| sched_domain.py | 091d36299b2258c84c900f096e80d49d615eb483b44505adf00442a7844e5349 |
| sched_inputs.py | 8b2b8a390ddcf436b5e30cc4390fafacb69d24c96567970a563925103225a1bb |
| sst_leg.py | 913fd1c167feb5293396fff3c23dfec5779d1eebf2c436086bf0fe9e17c42fda |
| successor_demo.py | 3b0536f02fcbb44b901b722bde6e5b75c63f37197a121069eb89cdcd746606a0 |
| test_atomicity.py | 770fa1ef356b918b33f8f89c99b7a7ab092f5b9f26536391be8741a876750adf |
| test_conformance.py | 608a61946dcd8dc8c79dc591270cf883ad953b16def615e9d78b792227ea7781 |
| test_fission.py | 7c856512373ae3d1ff7a3415808fc7cbda960dc918de73c173233dedbd61aed6 |
| test_successor.py | c22dc5b31b1169758607ca477d84ecde035cdab575bde6ec836489fe2acb5929 |
| verify_snapshot.py | 13caa2eae3a561952b492f8fa6402af1354f189255fd9413ebd27683b05bea2f |

Plus `accept/` (8 files) and `vendor/` (57 files: 3 docs + 54-file
SST snapshot), all identical at copy time (see this tree's
`IDENTITY.sha256` for the carried accept/vendor doc hashes; the
snapshot still verifies `MATCH hash=5f1f3789...`).

Excluded: `successor-003/runs/` (evidence outputs, not source),
`successor-003/.test-tmp/` (scratch; empty at copy time).

## Post-copy evolution (H2: content-derived routing + open lane execution + lane-override hook)

Only the L2-DESIGN §5 delta (H2.1/H2.2/H2.3, three additive items)
plus tree-name rebrands. Non-goals byte-identical to successor-003:
solver, grants, capabilities, representations, settle/fuse/fission/
quarantine semantics, SST leg, cross-host (none).

- `routing.py`: + `validate_lane_task` (H2.1 schema: required keys;
  holdings must partition exactly the grid's tasks/prefs, both
  worlds present), + `derive_routing_inputs` (H2.2:
  `derived_rounds = len(fragment_rounds(task))` via the SAME
  pipeline function, `derived_split` = both holdings sides hold
  something), `route()` takes lane tasks down the derived path
  (rule form unchanged; declared fields ignored-but-recorded;
  `inputs_derived_from: holdings`) with optional `lane_override`
  (H2.3; records `{rule_lane, override, final_lane}`, inert when
  unset); non-lane descriptors keep the legacy declared-field path
  (S3/S4/S6 routing unchanged); `CODE_REF` + lineage default
  rebranded.
- `api.py`: `run_tasks` gains `task_json` (one path or list; unknown
  task NAMES still raise) + `lane_override` (None | lane |
  {task: lane|None} map); all files loaded+validated, ids
  de-duplicated, and overrides resolved BEFORE any run work
  (loud, no partials); `RELEASE` rebranded.
- `release.py`: `run` gains repeatable `--task-json` + repeatable
  `--lane-override` (bare LANE or TASK=LANE, not mixed); rebrand.
- `test_lane_tasks.py` (NEW): 18 builder tests proving the §5 bar —
  schema refusals (loud + no partials), pinned hand-computed
  derivation, S1/S2-by-JSON == S1/S2-by-name (byte-exact lanes +
  655/0 + 310/500 + 2.61x), override recording/execution,
  unset-hook byte-identity, conservation + settle + clean inspect
  on novel tasks, kill-resume convergence on a novel lane task,
  legacy S3/S4/S6 routing unchanged.
- `test_successor.py` / `test_conformance.py` / `test_fission.py` /
  `test_atomicity.py`: rebrand only (17/17, 9/9, 7/7, 27/27 pass).
- `pipeline.py`, `resume.py`, `fusion.py`, `recover.py`,
  `sched_*.py`, `sst_leg.py`, `verify_snapshot.py`,
  `calibrate.py`, `make_snapshot_manifest.py`,
  `successor_demo.py`: docstring/print/path rebrand only
  (clean-path behavior unchanged; demo evidence structurally
  identical to successor-003 — see EVIDENCE.md).
- `minihost.py`: byte-identical (still pinned
  `a2b7ed59...05d3`, asserted by `test_successor.py`).
- `SUCCESSOR-REPORT.md`, `REPORT.md`: kept byte-identical as the
  successor-001/002 base records. `OBLIGATIONS.md`, `VENDORING.md`,
  `CONTRACT-GAPS.md`, `SEPARATION-PATHS.md`,
  `INTERRUPTION-BOUNDARIES.md`: base text kept + a short H2-lane
  carry note each. `REPRODUCE.md` / `LIMITS.md` / `CONSUMER.md` /
  `ORG-OPS.md`: updated for the H2 delta (copy-time hashes above
  are the before record). `accept/`: FROZEN, byte-identical
  (inputs never edited to make a run pass). `vendor/`: all 57
  files byte-identical.
- New docs: `EVIDENCE.md` (this build: commands, test output,
  accept comparison, §5 bar), `test_lane_tasks.py` (above).
- `IDENTITY.sha256` + `FROZEN-BASELINE.sha256` (regenerated for
  this tree; the baseline pins the frozen trees, run from
  `prototype/`).
