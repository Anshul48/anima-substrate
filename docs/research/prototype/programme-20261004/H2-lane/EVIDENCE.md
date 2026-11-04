# EVIDENCE.md — H2-lane build (AUTH-1, L2-DESIGN §5 delta H2)

Experimental host-delta build: successor-003 copy + ONLY delta H2
(H2.1 task-JSON lane path, H2.2 derived routing inputs, H2.3
lane-override hook) + builder tests. NOT successor-004, NOT a
release. $0, offline; stdlib-only except the carried SST leg
(vendored snapshot, pinned `pydantic==2.13.5` via `SST_VENV_PY`).

No frozen guarantee was weakened to make anything pass. All
§5 non-goals (solver, grants, capabilities, representations,
settle/fuse/fission/quarantine, SST leg, cross-host) behave
byte-identically to successor-003 (proven by the carried suites +
the structural accept comparison below).

## What changed (file list)

New: `test_lane_tasks.py` (18 builder tests), `runs/demo-*/`
(this build's accept-demo evidence), `EVIDENCE.md` (this file).
Modified behavior (the delta): `routing.py` (+227/-17:
`validate_lane_task`, `derive_routing_inputs`, `is_lane_task`,
`route(..., lane_override)` with derived path + override recording,
legacy path for non-lane descriptors; `CODE_REF`/lineage rebrand),
`api.py` (+82/-15: `run_tasks(..., task_json, lane_override)` +
`_resolve_lane_overrides`; `RELEASE` rebrand), `release.py` (+46/-6:
repeatable `--task-json` + `--lane-override`; rebrand).
Rebrand only: `calibrate.py`, `fusion.py`,
`make_snapshot_manifest.py`, `pipeline.py`, `recover.py`,
`resume.py`, `sched_checker.py`, `sched_domain.py`,
`sched_inputs.py`, `sst_leg.py`, `successor_demo.py`,
`test_atomicity.py`, `test_conformance.py`, `test_fission.py`,
`test_successor.py`, `verify_snapshot.py` (docstring/print/path
header lines; see PROVENANCE.md).
Docs: `PROVENANCE.md` (rewritten, copy-time hashes),
`LIMITS.md` (item 12 ADDED), `CONSUMER.md` + `ORG-OPS.md` (§8
ADDED) + `REPRODUCE.md` (H2 delta), `OBLIGATIONS.md` /
`VENDORING.md` / `CONTRACT-GAPS.md` / `SEPARATION-PATHS.md` /
`INTERRUPTION-BOUNDARIES.md` (carry notes),
`IDENTITY.sha256` + `FROZEN-BASELINE.sha256` (regenerated).
Untouched bytes: `minihost.py` (still pinned `a2b7ed59...05d3`),
`SUCCESSOR-REPORT.md`, `REPORT.md`, `accept/` (all 8 frozen
files), `vendor/` (all 57 files).
Full before-record: `PROVENANCE.md`.

## Commands + test output (repo root, `PYTHONDONTWRITEBYTECODE=1`)

`SST_VENV_PY=$PWD/prototype/w1/.venv/bin/python` is exported for
the SST leg in every command below (required: this tree sits one
level deeper than `successor-003/`, so the default venv path does
not resolve here — see CONSUMER.md; the SST leg code itself is
byte-identical to successor-003).

    python3 prototype/programme-20261004/H2-lane/test_lane_tasks.py
    # Ran 18 tests in 23.284s — OK (no SST):
    # test_refusals, test_no_partials_on_refusal,
    # test_unknown_names_still_raise,
    # test_duplicate_ids_refused_before_work,
    # test_pinned_derivation,
    # test_declared_fields_ignored_but_recorded,
    # test_s1_s2_validate_and_route_as_before,
    # test_legacy_s3_s4_s6_routing_unchanged,
    # test_s1_by_json_equals_by_name, test_s2_by_json_equals_by_name,
    # test_calibration_2_61x, test_override_against_rule_executes,
    # test_override_matching_rule_recorded,
    # test_override_map_none_entry_is_rule,
    # test_bad_overrides_refused_before_work,
    # test_unset_hook_byte_identical,
    # test_novel_both_lanes_conserve_and_settle,
    # test_kill_resume_converges_on_novel_lane_task

    python3 prototype/programme-20261004/H2-lane/test_conformance.py
    # Ran 9 tests in 12.673s — OK (no SST)

    python3 prototype/programme-20261004/H2-lane/test_fission.py
    # Ran 7 tests in 11.945s — OK (no SST)

    python3 prototype/programme-20261004/H2-lane/test_successor.py
    # Ran 17 tests in 60.131s — OK (incl. kill + SST legs:
    # snapshot MATCH, cost $0.0, termination champion_found)

    python3 prototype/programme-20261004/H2-lane/test_atomicity.py
    # Ran 27 tests in 343.767s — OK (no SST; refusal proofs,
    # kill-at-every-boundary CLI matrices, pre-spec kills, repeated
    # kills incl. kill-during-recovery, real SIGKILLs, forensics)

    python3 prototype/programme-20261004/H2-lane/calibrate.py
    # S2-central: central=810 direct=0
    # S2-local:   central=310 direct=500
    # ratio central/local = 2.61x (canonical-JSON bytes, task envelope only)

    python3 prototype/programme-20261004/H2-lane/verify_snapshot.py
    # snapshot MATCH: files=54 hash=5f1f37893b0f5ab9ff7dcf0ce2c60b287b51647e2f18f627eabf5510537cad96
    # (run AFTER all suites: the vendored snapshot was never written)

    python3 prototype/programme-20261004/H2-lane/sched_checker.py --self-check
    # known_good valid=True quality=4/4, known_bad valid=False (2 violations) — OK

    python3 prototype/programme-20261004/H2-lane/successor_demo.py
    # H2-lane integrated demo: OK (exit 0)
    # run_dir: H2-lane/runs/demo-20261004T154537Z
    # S1: lane=central valid=True quality=4/4 central=655 direct=0
    # S2: lane=local valid=True quality=4/4 central=310 direct=500
    # S3: lane=local valid=True quality=4/4 central=685 direct=500
    # S3 resume: skipped=3 re_executed=0 child_rc=-9 artifacts_identical=True
    # fusion/fission records as pinned; SST snapshot=MATCH cost=$0.0
    # pydantic=2.13.5; settle markers=5 stranded=0; routing decisions: 6

Accept comparison (`/tmp/accept_check_h2.py`, kept out of the tree):
H2 `EVIDENCE.json` vs `accept/EXPECTED.json` exact fields + byte
refs, and vs the successor-003 demo `EVIDENCE.json` structurally:

    # EXACT: 50 x PASS, 0 x FAIL (every exact field: S1–S6, SST,
    # fusion, fission, routing_decisions=6, settle markers=5/
    # terminals/stranded_zero, byte refs 655/0, 310/500, 685/500)
    # STRUCT-vs-003 (excl. routing payloads): IDENTICAL
    # ROUTING lanes vs 003: SAME; H2 S1/S2 delta fields: PRESENT;
    # S3 legacy rule: KEPT
    # RESULT: ALL EXACT FIELDS MATCH

## §5 acceptance bar, item by item

1. Existing suites green: conformance 9/9, fission 7/7, successor
   17/17 (incl. SST $0/MATCH), atomicity 27/27 — all OK above.
   Accept field comparison vs successor-003: 50/50 exact fields +
   byte refs match; demo evidence structurally identical except
   the specified H2 routing deltas; S1/S2 lanes + 655/0 + 310/500
   + 2.61x calibration reproduced. PASS.
2. Novel-lane conformance (`test_lane_tasks.py`, 18/18 OK):
   schema validation refuses 17 malformed shapes + non-objects
   loudly with zero ledger entries / zero artifacts / empty
   `tasks_run`, and the root runs valid tasks afterwards; unknown
   NAMES still raise; duplicate ids refused pre-work; derived
   routing matches hand-computed values on the 4-task pinned set
   (H2T-CENTRAL (2,False)->central, H2T-LOCAL4 (4,True)->local,
   H2T-SPLIT2 (2,True)->local, H2T-SPLIT3 (3,True)->local);
   lying declared fields ignored-but-recorded;
   S1/S2-by-JSON == S1/S2-by-name (identical lanes/bytes,
   byte-identical solutions + routing payloads); override
   true/false recorded and executed (against-rule and
   matching-rule); unset hook byte-identical (default vs
   explicit None: identical outputs, solutions, payloads);
   legacy S3/S4/S6 routing unchanged. PASS.
3. Conservation + recovery on novel lane tasks: ledger conserves
   on every novel run (`verify_conservation` ok mid-run and
   post-settle); kill-resume converges on novel lane task
   H2T-LOCAL4 (real `Popen.kill()` mid-dialogue; resume skips
   formulate + clarify@r1, `re_executed_invokes` 0, VALID 4/4,
   then settles 0-stranded); `inspect` reports clean
   (conservation ok, worlds active, 3 routing decisions). PASS.
4. successor-003 frozen intact: `IDENTITY.sha256` 45/45 OK
   immediately BEFORE the copy AND after all H2 work (see §Frozen
   verification); this tree carries its own `IDENTITY.sha256`
   (46 files, all OK) + `FROZEN-BASELINE.sha256` convention. PASS.
5. Verdict: builder-side bar 4/4 PASS; independent verification
   lane verdict PENDING (not this build's call).

## Frozen verification (frozen trees + neighbors untouched)

No git repo exists at this root, so immutability is proven by
content hashes instead:

- Pre-work: `cd prototype/successor-003 && sha256sum -c
  IDENTITY.sha256` → 45/45 OK; plus a full pre-work snapshot of
  603 files (`/tmp/h2-frozen-pre.sha256`: successor-002/,
  successor-003/, release-20261004/, programme-20261004/
  excl. runs/ and .test-tmp/).
- Copy check: per-file sha256 source-vs-copy over all 100 copied
  files → IDENTICAL (excluded: `runs/`, empty `.test-tmp/`).
- Post-work: `cd prototype/successor-003 && sha256sum -c
  IDENTITY.sha256` → 45/45 OK (before AND after: the frozen
  source is intact).
- Pre-work snapshot re-hash (`sha256sum -c
  /tmp/h2-frozen-pre.sha256` from the repo root) → 602/603 OK.
  The single mismatch is `programme-20261004/
  CONTINUING-PROGRAMME.md` (pre `4c5b257d...`, post
  `63bb882b...`, mtime 2026-10-04T15:28:16Z): an EXTERNAL
  concurrent coordinator append (P1-ACCEPTED / M1-ABORTED log
  entries; PREREG-LOG.md likewise written at 15:23Z) landing
  seconds after the pre-work snapshot while this build was
  copying bytes H2-lane-ward. This build never opened that file
  for writing (every build write is under
  `programme-20261004/H2-lane/`); all five frozen inputs
  (successor-002/, successor-003/, release-20261004/,
  L1-transfer/, L2-design/) re-hash IDENTICAL.
- This tree's `FROZEN-BASELINE.sha256` (run from `prototype/`)
  pins the post-build state of the whole `prototype/` universe
  EXCEPT: `programme-20261004/H2-lane/` (own tree, covered by
  `IDENTITY.sha256`), `*/runs/` + `*/.test-tmp/` (live evidence
  / scratch convention), `*/__pycache__/` + `*.pyc` (bytecode),
  `w1/.venv/` (executed, not a frozen source claim), and the
  programme-root live coordinator logs (`CONTINUING-
  PROGRAMME.md`, `PREREG-LOG.md`, `R1-VERIFICATION.md` —
  append-only coordinator-owned state, not frozen inputs).
  Check → all 1196 OK.
- Frozen `runs/` evidence (excluded from the live snapshots by
  convention): successor-003 `runs/` (2 demo dirs) and
  L1-transfer `runs/`+`logs/` file mtimes all predate this build
  (Oct 4 ≤14:xxZ vs build start 15:28Z) and were never opened
  for writing.
- Own tree: `cd prototype/programme-20261004/H2-lane &&
  sha256sum -c IDENTITY.sha256` → 46/46 OK.
