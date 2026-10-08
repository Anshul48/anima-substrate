# PROVENANCE.md — successor-004 copy record

Source: `prototype/successor-003/` (NOT its `runs/` evidence, NOT
`.test-tmp/`).
Method: `cp -rp` per file/directory (bytes + mtimes preserved),
then per-file sha256 compared source-vs-copy: all 100 files
IDENTICAL (source hashes also match
`successor-003/IDENTITY.sha256` for its 45 covered files).
Copy timestamp (UTC): 2026-10-04T17:52Z (pre-work marker
`/tmp/r3-prework-marker`; copy completed the same minute).
`successor-003/` was not modified during or
after the copy (covered by this tree's `FROZEN-BASELINE.sha256`,
which pins the whole frozen r2 tree, plus the pre-work snapshot
`/tmp/r3-frozen-pre-004.sha256` — see EVIDENCE.md).

## Per-file sha256 at copy time (source == copy; top-level files)

| file | sha256 |
|---|---|
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
| CONSUMER.md | 98ef59d6539d1f079f21664dd77feebfc9b7c5a654147c7191f8a3990ad1f676 |
| CONTRACT-GAPS.md | 034be5e81ff844903cf32cfbe91abcf5f420e48ea4b0748bdc4bc65fb44169c2 |
| EVIDENCE.md | 991ea38038b57cfac4405ae7e39ef4e910a286edba730082a7ec8480e52828e7 |
| INTERRUPTION-BOUNDARIES.md | 18500eaadefc6961d10a9fb97eaff626b8089d19ac97643e1e7020e9296deea9 |
| LIMITS.md | 5985a8d4badce38f9f23c636767eaba0235dd7ecbc6027a3322ac483b5e66a96 |
| OBLIGATIONS.md | 578b3219d3dcbd90f1325b9554b648cdc2f2dd5b79c046f9fe0374b1d78e3b1d |
| ORG-OPS.md | 2f0898311cfcfb476f7513c939b3997a0975968a5f1ac4de388c6084fed46873 |
| PROVENANCE.md | 90cf248289b23957194fc276dd7ff7b9f2b48fe6e6a6deb8c8edc4da3b10fe57 |
| REPORT.md | 9d15c16f67f5576d094bac5622fecec366756ac258852097c253680f3600f0bc |
| REPRODUCE.md | 31b9441c28a08e0af6fc04cfe13bac71cad5ed7060cc496e278afdac46e3292d |
| SEPARATION-PATHS.md | 1265b471a14b5111b8f5fa267236bcbcb2c8f697c841f873ad18a91db5bcadda |
| SUCCESSOR-REPORT.md | eecfd3b5cfb60218ed8393be9bbe0fe195c13aa3d40993f1c6f74f557ffefb3c |
| VENDORING.md | 51f7bbb87637b201c39dd1944bee80f8a2bfc09587b4e5ff8ad7677a159994f3 |

Plus `accept/` (8 files) and `vendor/` (57 files: 3 docs + 54-file
SST snapshot), all identical at copy time (see this tree's
`IDENTITY.sha256` for the carried accept/vendor doc hashes; the
snapshot still verifies `MATCH hash=5f1f3789...`).

Excluded: `successor-003/runs/` (evidence outputs, not source),
`successor-003/.test-tmp/` (scratch; empty at copy time).

## Post-copy evolution (R3: atomic side writes + F1/F2 doc precision)

- `FROZEN-BASELINE.sha256` REPLACED (see EVIDENCE.md §Frozen
  verification): pins the frozen r2 tree (`successor-002/` incl.
  its `runs/` evidence, `successor-003/` incl. its `runs/`
  evidence, `release-20261004/`, `release-r2/`) plus neighboring
  tracks. Live sibling dirs excluded (see EVIDENCE.md).
- `minihost.py`: + `atomic_write_text` (same-dir temp +
  `os.replace`; crash guarantee in its docstring; uses only
  os/pathlib — no new imports, stdlib-only pin holds); its four
  whole-file writes (ledger-init, `checkpoint.json`, `store_args`,
  `MiniWorld._write`) route through it; + test-only
  write-interior hooks (`SUBSTRATE_CRASH_MID_APPEND`,
  `SUBSTRATE_CRASH_MID_SIDE_WRITE`; unset = zero behavior change);
  unreadable checkpoint now refuses classified (`deny` +
  `ContractViolation`, disk-loss class) instead of a raw decode
  error. Re-pinned in `test_successor.py`
  (`8551ed92...d5757`; R1 `a2b7ed59...05d3` above).
- `api.py`: `_write_specs` (THE F2 window), both `CONFIG.json`
  writes, fusion/fission artifact writes, and `_recovery_note`
  route through `atomic_write_text` (clean-path bytes unchanged);
  `RELEASE` rebranded.
- `recover.py`: `repair_specs` spec write routes through
  `atomic_write_text` (bytes unchanged); rebrand.
- `routing.py`: `write_json` routes through `atomic_write_text`
  (bytes unchanged); `CODE_REF` + lineage default rebranded.
  `ROUTING-LOG.jsonl` append kept byte-identical (append-only).
- `resume.py` (`SchedWorld._write`), `pipeline.py` (2 verdict
  copies), `fusion.py` (1 verdict copy), `sst_leg.py` (parent-side
  `SNAPSHOT-CHECK.json` + child-script writes), `successor_demo.py`
  (`child.READY`, `EVIDENCE.json`), `calibrate.py` (report),
  `make_snapshot_manifest.py` (manifest): all route through
  `atomic_write_text` (bytes unchanged); rebrand.
- Ledger `append()` kept byte-identical (append-only prefix
  property preserved); the R1 hook comment's unproven no-tear
  claim narrowed (a kill inside an append MAY tear the tail;
  specified landing = loud disk-loss refusal, tested).
- `test_atomicity.py`: + `TestAtomicConstruction` (4: helper is
  temp+replace shared by all 11 writer modules; AST proof of zero
  direct whole-file writes in shipped code; 59-write runtime
  routing proof with `Path.write_text` never touched; old-or-new
  semantics), + `TestSpecWindowKillLoop` (50 real SIGKILLs across
  the fission op tail: zero torn side files, every landing
  converged), + `TestWriteInterior` (7: mid-append crash →
  torn tail → loud disk-loss refusal; 0-byte/truncated
  `worlds.json` fixtures → loud refusal; mid-write crashes for
  specs/artifact/CONFIG/checkpoint → old bytes + convergence;
  torn checkpoint → classified refusal). 27 → 39 tests.
- `test_successor.py`: minihost re-pin (above) + rebrand only;
  all 17 tests pass unchanged. `test_conformance.py`,
  `test_fission.py`: rebrand only (9/9, 7/7 pass).
- `release.py`, `verify_snapshot.py`, `sched_*.py`: rebrand only
  (no file writes in these modules).
- `SUCCESSOR-REPORT.md`, `REPORT.md`: kept byte-identical as the
  base records. `OBLIGATIONS.md`, `VENDORING.md`,
  `CONTRACT-GAPS.md`, `SEPARATION-PATHS.md`: base text + s003
  notes kept, short successor-004 carry note each. `accept/` (all
  8 frozen files), `vendor/` (all 57 files): byte-identical.
- `INTERRUPTION-BOUNDARIES.md`: rebrand + F2 precision ("all
  landings converge" → ledger-prefix landings converge + side
  files old-or-new; torn-side-file landing closed) + F1 warning
  kept and scoped (direct settle stays custody-orthogonal; only
  `recover_op`'s targeted settle withholds; recover path named) +
  ledger no-tear claim narrowed (mid-append tear specified +
  tested) + R3 guarantees.
- `LIMITS.md`: item 2 narrowed (side-file kill-tear exposure
  zero; ledger explicitly NOT covered; multi-writer/disk-loss/
  no-fsync stay out of scope).
- `CONSUMER.md` / `ORG-OPS.md` / `REPRODUCE.md`: rebrand + R3
  clauses (atomic side files, torn-side-file row, F1 warning,
  39/72 counts). `EVIDENCE.md`: rewritten (this build's F2 red
  log, survey, kill-loop numbers, suite results). `IDENTITY.sha256`
  + `FROZEN-BASELINE.sha256`: regenerated.
