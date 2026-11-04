# PROVENANCE.md — successor-006 copy-forward record

successor-006 is a NEW tree (2026-10-07). Nothing under
`prototype/successor-002/`, `successor-003/`, `successor-004/`,
`programme-20261004/H2-lane/`, `successor-005/`, `release-*`,
`reuse-demo-001/`, or `programme-20261004/U-execute/` was modified;
all of those were read-only sources. Copy-forward source for code:
the frozen `prototype/successor-005/` tree.

## Carried files (sha256 of the successor-005 source bytes)

Byte-identical at copy time; per-file adaptation edits are listed in
the next section (adapted files DIVERGE from these hashes by exactly
the listed edits — nothing else).

```
4cb3c1dd8d27233818b6005ff23b33b20bd65bc893199209fb156238758095a4 minihost.py
9283e2712c1926c5eac71e670da839eb4733480b0eb87c9a4895b8513a2714db resume.py
791ac4e6cf8cd329a16d4334cdc4b9c4c7ebe32a8254b0a4533e7b1367e697e0 routing.py
7c3ce792196b859cabc3fe49d1f4ea65aa84a8e1669d4f1443c66649a7feeae5 pipeline.py
a2211a5de56c9553edac2dbe09c73c3ceb842549429bfb9b56f0e821b3031910 fusion.py
8b3ed5af2f4d64a50a70109079575ab98a55ddd3f90b4f0f16abf267b6a1979a recover.py
ec4962ca8bbe92bbf48d97a6015fc46cbb506347ed6d269ec005f2cbd8f561d2 api.py
559c56451e1b59669887e65ee24a97e6f2660629960b201951fdbece2172ba6e release.py
465f8edc99cfd7b76d78a034c15acc1385e2e7777100be37ab8cd394ee18f244 sched_checker.py
55a4ad9cdfef35afad33fd9592726e06f35b6f330cfcbdd09a282c7a72bb8a6f sched_domain.py
b3bdbfafe8d97bf32d619fc250a7461f998d01c3eaa17a73ac98078f8c07f15b sched_inputs.py
87a9cff3bb1cf0aeea7c7289526a0c09e6760131908a8886580830c639b7136e successor_demo.py
98d134d19e3fe35f3312de12749504b09b10fe8f7c3020d29eb6439fdbd57e73 procedure.py
96acde7e05149dd396ee84438c4bb615e057fd9dee55b062bd4d5af662b01d8f calibrate.py
9dd329488432833eff6eb524ac58caa9187d6b9ed2abb29c57d2fc62674a90a9 test_conformance.py
022b3b8f9bf34c4c50dd978523b0b25f70c06da1f1dafdc8c9e7063b17275cb9 test_fission.py
53a4bf67653760783370c8d95822cd20d4e2a752496e3b811c825f2dee1d6093 accept/EXPECTED.json
52eb737d3d1e37373f188bf55ef6e928f1005420c8d2d6520181c1de8855f94f accept/README.md
bdf1e38407fc501527e11e907fc3a95a2b5af81a7c66b2904524b4676829a883 accept/S1.json
fc32edeea1737db96298f1dd0482d009db75a29ed75b1c3164f1fe006aa110ff accept/S2.json
0847e159bcc1418e608b5379afe2f0c24b9522355d868fe015cb1da6ffad1157 accept/S3.json
af81bdcdf8b77686f5fae2eec33bf8aa902e15533fac4f31038dad7b299e688b accept/S4-followup.json
0b794b8b5a596e143e4668910e6cb27cc07d4b9b81258d856447f617b20682b8 accept/S5.json
ce42d0353bfe6cd89b2f8d871cbb64522feefca154553b8c5639d188d15dc5d3 accept/S6-followup.json
```

Tests pin the byte-identity that matters: `test_coupling.py::CC9`
(resume.py) and `test_procedure_smoke.py::test_carried_bytes`
(procedure.py).

## Adaptation edits to the copies (exact list)

- `routing.py`: `CODE_REF` + default lineage string bumped
  `successor-005` -> `successor-006` (new-tree identity; all state is
  fresh, no cross-tree ledger compat is claimed).
- `api.py`: `RELEASE` bumped; `sst_leg` import replaced by a loud
  `RuntimeError` stub (SST leg NOT carried — see below); `open_run`
  additionally restores creation-fixed `authorities` from the ledger
  `create` payloads (same pattern as lineage/procedures; sched
  worlds restore `[]`, byte-identical behavior); NEW J1 ops
  (`j1_init`, `nest_op`, `j1_work_op`, `j1_kill_resume_op`,
  `j1_status_op`, `j1_export_op`) + NEW quarantine repair ops
  (`quarantine_complete_op`, `quarantine_rollback_op`); docstring
  tree-name updates.
- `recover.py`: `ledger_index` checkpoints now carry seq +
  `rollbacks` index added; `detect_partial_quarantines` extended
  (rollback resolutions, seq comparison, side-file fallback);
  operator-steps text now points at the supported ops; NEW
  `complete_quarantine` / `rollback_quarantine` (the R11 repair).
- `release.py`: CLI for the new ops (`j1-init`, `ops nest`,
  `ops j1-work`, `ops j1-kill-resume`, `ops j1-status`,
  `ops j1-export`, `ops quarantine-complete`,
  `ops quarantine-rollback`); docstring tree-name updates.
- `successor_demo.py`: `sst_leg` import replaced by a loud stub
  (`run_demo` is not supported in this tree; `main_worlds` /
  `child_partial` helpers intact for carried tests); tree-name
  updates.
- `calibrate.py`, `test_conformance.py`, `test_fission.py`:
  docstring tree-name updates ONLY (no behavior change).
- `minihost.py`, `resume.py`, `pipeline.py`, `fusion.py`,
  `sched_checker.py`, `sched_domain.py`, `sched_inputs.py`,
  `procedure.py`, `accept/*`: NO edits (byte-identical to source).

## NOT carried (deliberate, recorded)

- `sst_leg.py`, `verify_snapshot.py`, `make_snapshot_manifest.py`,
  `vendor/`: the SST leg needs a venv interpreter with pinned
  pydantic — incompatible with this tree's stdlib-only constraint.
  `run_tasks(..., with_sst=True)` and `run_demo` refuse loudly.
- `vehicle/`: the s5-readiness vehicle is not re-run here.
- `test_successor.py`, `test_atomicity.py`: import the SST/vendor
  surface; not carried. Regression cover for carried behavior comes
  from `test_conformance.py` (9) + `test_fission.py` (7), which pass
  unmodified in this tree.
- `test_procedure.py` (57 tests): not carried; the procedure
  participant is covered by byte-identity + `test_procedure_smoke.py`
  (3). Full procedure re-verification is out of scope for the
  R11/J1 brief (see LIMITS.md).

## New files (authored in successor-006)

`COUPLING-CONTRACT.md`, `test_coupling.py`,
`test_quarantine_repair.py`, `test_j1.py`, `test_procedure_smoke.py`,
`j1_demo.py`, `RUNBOOK.md`, `CONSUMER.md`, `LIMITS.md`,
`BUILDER-LOG.md`, this file.

## Concept provenance (non-code sources)

- The 8 coupling items: `reuse-demo-001/REUSE-REPORT.md`
  §"Interface gaps" + `closeout-20261004/REUSE-CALIBRATION.md`
  (Q3 DEMONSTRATED-WITH-COUPLING-LIST); clause pins from
  `successor-contract/WORLD-CONTRACT-v1.md` C1–C6.
- The owed-item list: `programme-20261004/COMPLETION-MAP.md` R9/Q3
  rows (resume-coupling list) and R11 row (quarantine-transfer
  operator repair); execution order from
  `programme-20261004/SUBSTRATE-COMPLETION-PROPOSAL.md` §5
  (repair-first, then J1).
- J1 journey shape: SUBSTRATE-COMPLETION-PROPOSAL.md §2 (J1 Builder)
  + §3 acceptance row (worlds/reuse); kill/resume + fusion/fission/
  quarantine mechanics from the carried successor-005 code.
