# EVIDENCE.md — successor-003 (R1 atomic settle + interruption boundaries)

## R1 result

ACCEPTANCE (per `programme-20261004/CONTINUING-PROGRAMME.md` R1):

- `settle` all-or-nothing: refusal/failure leaves ZERO partial
  dissolves; ledger consistent + fail-closed (LIMITS-11 CLOSED).
  Proven by `TestAtomicRefusal` (7 tests): unknown world,
  unsettled-terminal probe, residual holdings, suspended-without-
  checkpoint (both batch orders), `check_settleable`
  side-effect-freedom, fuse/fission unsettleable-target rejection —
  every refusal asserts unchanged lifecycles + (`deny`-only or zero)
  ledger growth + conservation still holding.
- Kill-during-settle and kill-during-fusion/fission: defined
  behavior + recovery exercises, no silent partials
  (INTERRUPTION-BOUNDARIES.md). Proven by kill-at-EVERY-boundary
  matrices through the consumer CLI (settle 8/8, fuse 15/15,
  fission 15/15 incl. pre-spec side-file kills), repeated kills
  incl. kill-during-recovery (5 tests), real SIGKILLs at staggered
  delays (9 landings, all converged), and a full demo-spine flow
  with a kill inside every mutating op.
- Operator-repair paths explicit, tested, documented: fission input
  refusal (+ wrong-partition/names/presets), partial-quarantine
  detection with COMPLETE/ROLLBACK recipes, conservation-violation
  and torn-ledger refusals (`TestDetection`, 6 tests).
- r1 regression: 17/17 + 9/9 + 7/7 existing suites pass from this
  tree; demo EVIDENCE structurally identical to r1 (all exact
  accept fields match); calibrate still 2.61x; snapshot MATCH.
- r1 + neighbors untouched: `successor-002/IDENTITY.sha256` checks
  OK, pre/post sha256 snapshots identical, no writes outside
  `successor-003/` (see §Frozen verification).

No r1 guarantee was weakened to make anything pass (the one
behavior extension — settle refuses fail-closed-EARLIER with zero
partial `grant_return`s — is documented in LIMITS-11/CONSUMER/ORG-OPS
and covered by tests).

## What changed (file list)

New: `recover.py`, `test_atomicity.py`,
`INTERRUPTION-BOUNDARIES.md`, `EVIDENCE.md` (this file).
Modified: `minihost.py` (+`check_settleable`, settle pre-validation,
test-only crash hooks; re-pinned), `routing.py` (atomic
`finish_worlds`; rebrand), `fusion.py` (settleability pre-checks;
rebrand), `api.py` (+`recover_op`, pre-spec crash points; rebrand),
`release.py` (+`ops recover`; rebrand), `test_successor.py` (re-pin
+ rebrand), `test_conformance.py`/`test_fission.py`/
`pipeline.py`/`resume.py`/`sched_*.py`/`sst_leg.py`/
`verify_snapshot.py`/`calibrate.py`/`make_snapshot_manifest.py`/
`successor_demo.py` (rebrand only), `PROVENANCE.md` (rewritten),
`LIMITS.md` (item 11 closed, item 3 narrowed),
`ORG-OPS.md`/`CONSUMER.md`/`REPRODUCE.md` (R1 clauses),
`OBLIGATIONS.md`/`VENDORING.md`/`CONTRACT-GAPS.md`/
`SEPARATION-PATHS.md` (carry notes), `IDENTITY.sha256` +
`FROZEN-BASELINE.sha256` (regenerated).
Untouched bytes: `SUCCESSOR-REPORT.md`, `REPORT.md`, `accept/` (all
8 frozen files), `vendor/` (all 57 files).
Full before-record: `PROVENANCE.md`.

## Commands + test output (repo root, `PYTHONDONTWRITEBYTECODE=1`)

    python3 prototype/successor-003/test_atomicity.py
    # Ran 27 tests in 286.753s — OK (27 x "... ok", 0 failures)

    python3 prototype/successor-003/test_successor.py
    # Ran 17 tests in 44.374s — OK (incl. kill + SST legs)

    python3 prototype/successor-003/test_conformance.py
    # Ran 9 tests in 9.017s — OK

    python3 prototype/successor-003/test_fission.py
    # Ran 7 tests in 9.370s — OK

    python3 prototype/successor-003/successor_demo.py
    # successor-003 integrated demo: OK
    #   S1: lane=central valid=True quality=4/4 central=655 direct=0
    #   S2: lane=local valid=True quality=4/4 central=310 direct=500
    #   S3: lane=local valid=True quality=4/4 central=685 direct=500
    #   S4: lane=SC-FUSED valid=True quality=5/5 central=- direct=-
    #   S6: lane=fission-reuse valid=True quality=4/4 central=- direct=-
    #   S3 resume: skipped=3 re_executed=0 child_rc=-9 artifacts_identical=True
    #   S3 ruling: void v1 proposal; SC-S re-proposes under v2; revoked=SC-L:sched.propose@1.0->SC-S
    #   fusion: SC-FUSED from ['SC-L', 'SC-S']; removed=direct-channel:SC-L<->SC-S
    #   fission: SC-FUSED -> ['SC-L2', 'SC-S2']; restored=direct-channel:SC-L2<->SC-S2
    #   S5 quarantine: SC-Q -> SC-B; probe_denied_seq=14
    #   SST: snapshot=MATCH hash=5f1f37893b0f termination=champion_found champion=cand_tree_successor_sst_0_0 cost=$0.0 pydantic=2.13.5
    #   settle: ['SC-FUSED', 'SC-L', 'SC-L2', 'SC-S', 'SC-S2'] markers=5 stranded=0
    #   routing decisions: 6 recorded
    # (run twice: demo-20261004T143829Z, demo-20261004T144817Z; both OK)

    python3 prototype/successor-003/calibrate.py
    # S2-central: central=810 direct=0
    # S2-local:   central=310 direct=500
    # ratio central/local = 2.61x (canonical-JSON bytes, task envelope only)

    python3 prototype/successor-003/verify_snapshot.py
    # snapshot MATCH: files=54 hash=5f1f37893b0f5ab9ff7dcf0ce2c60b287b51647e2f18f627eabf5510537cad96

    python3 prototype/successor-003/sched_checker.py --self-check
    # known_good valid=True quality=4/4, known_bad valid=False (2 violations) — OK

Accept comparison (`/tmp/accept_check_003.py`, kept out of the tree):
new `EVIDENCE.json` vs `accept/EXPECTED.json` exact fields + vs r1
`runs/demo-20261004T100134Z/EVIDENCE.json` structurally:

    # 42 x PASS (every exact field: S1–S6, SST, fusion, fission,
    # routing_decisions=6, settle markers=5/terminals/stranded_zero,
    # byte refs 655/0, 310/500, 685/500)
    # PASS old-vs-new EVIDENCE structurally identical (modulo paths/run_dir)
    # RESULT: ALL EXACT FIELDS MATCH

Note: r1's frozen EVIDENCE carries `snapshot_hash 61f523a5...`
while the current manifest + this tree's runs record `5f1f3789...`.
Cause (pre-existing r1 quirk, out of R1 scope): the snapshot was
re-vendored AFTER the r1 demo runs (snapshot files 10:35–10:36Z vs
run 10:01Z; HASH-CONSTRUCTION "v1 scope history": 50→54 files).
EXPECTED.json pins only `snapshot_check MATCH` (not the hash), and
this tree's runs match the CURRENT manifest pre/post SST leg.

## Kill-exercise logs (via `release.py` CLI + `ops recover`)

Settle matrix (7 appends: reopen + 2x(return+marker+life); N=8 clean):

    settle N=1..7: rc=42 -> recovered (both dissolved, 0 stranded, conservation ok)
    settle N=3, N=6: markers=3 (benign duplicate marker: crash landed
      marker-without-lifecycle; set-semantic, asserted); else markers=2
    settle N=8: rc=0 -> recovered markers=2

Fuse matrix (14 appends; N=15 clean; every N also proves `reuse` serves):

    fuse N=1: crash_rc=42, no trace -> op re-run -> recovered + reuse OK
    fuse N=2..14: crash_rc=42 -> recovered (composite active, custody
      union, exactly 1 fusion entry, specs repaired, artifact-or-note
      present) + reuse OK
    fuse N=15: crash_rc=0 -> recovered + reuse OK

Fission matrix (14 appends; N=15 clean; bare recover refuses iff partial):

    fission N=1: bare_rc=0 (no trace) -> op re-run -> converged
    fission N=2..13: bare_rc=1 ("need operator input") -> recover with
      partition -> converged (children exact custody, exactly 1 fission
      entry, conservation ok)
    fission N=14 (entry complete, specs missing): bare_rc=0 -> converged
    fission N=15: bare_rc=0 -> converged
    wrong-partition recover: refused ("contradicts"), correct one completes

Pre-spec kills (`SUBSTRATE_CRASH_AT=api:{fuse,fission}:pre-spec`):
ledger-complete + stale specs -> composite reopens WITHHELD (invoke
denies, fail-closed) -> recover repairs specs -> reuse serves;
recovery note written.

Repeated kills (kill-during-recovery converges on re-run):
settle (4, then recover@3), fuse (6, then recover@5), fission (8,
then recover-with-partition@4), spec-repair
(`recover:pre-spec` mid-repair), full flow
fuse@6 -> recover -> reuse -> fission@9 -> recover+partition ->
split-pair -> settle@4 -> recover (5/5 settled terminals).

Real SIGKILLs (staggered delays; every landing converges):

    sigkill fission delay=0.05/0.2: killed+no-trace-rerun -> converged
    sigkill fission delay=0.5: killed -> converged
    sigkill fuse delay=0.05/0.2: killed+no-trace-rerun -> converged
    sigkill fuse delay=0.5: killed -> converged
    sigkill settle delay=0.05/0.2: killed -> converged
    sigkill settle delay=0.5: completed-before-kill -> converged

Forensics (in-process via `api`): partial quarantine detected with
`OPERATOR REPAIR` steps (involved world blocked, others settle);
conservation-violation ledger refuses recover; torn ledger refuses
("disk-loss"); fission args without partial refused; bare recover
settles NOTHING by default (safe default asserted); partial fission
blocks settle of its composite until completed (one call can then
complete fission AND settle children).

Bug found BY the matrices during this build (fixed, not waived): kill
between composite `create` and its initial `grant` left an unfunded
composite that completed fusion but failed reuse (`grant exceeded`).
Fix: `complete_fusion` restores a missing initial grant (validated
before mutating). Fuse N=2 now passes with reuse OK.

## Frozen verification (r1 + neighbors untouched)

No git repo exists at this root (`git status` → "not a git
repository"), so immutability is proven by content hashes instead:

- Pre-work snapshot (before ANY write): sha256 of all 445 files
  under `successor-002/` + `release-20261004/` → post-work
  re-hash compared IDENTICAL (command + result below).
- `cd prototype/successor-002 && sha256sum -c IDENTITY.sha256` →
  all 41 OK.
- `cd prototype && sha256sum -c
  successor-003/FROZEN-BASELINE.sha256` → all 3640 OK (1878
  carried lines re-verified + 1762 new: successor-002/ incl. runs/
  (369), release-20261004/ (76), closeout (7), evidence (1230),
  successor-contract (1), windows-check (77), w0-probes.sh (1),
  CONTINUING-PROGRAMME.md (1)). Live sibling workspace
  `programme-20261004/L1-transfer/` (1665 files, concurrent L1
  track) is EXCLUDED from the pin (it changes under its owner);
  my non-interference there is covered by the `-newer` check below.
- No writes of mine outside `successor-003/`: `find prototype
  -newer <pre-work marker> -not -path "./successor-003*"` returns
  ONLY `.` (dir mtime from my `mkdir successor-003`),
  `programme-20261004/L1-transfer/**` (the CONCURRENT L1 sibling
  track's live workspace — its owner agent wrote there during my
  session, not me), and `programme-20261004/
  CONTINUING-PROGRAMME.md` (touched by coordinator/sibling
  activity mid-session; I only read it). Everything else —
  successor-002/, release-20261004/, all other neighbors — has
  no path newer than my start marker.
  (`PYTHONDONTWRITEBYTECODE=1` throughout: no `.pyc`.)
- `../sst` never touched (SST leg consumes the vendored snapshot
  read-only; pre/post MATCH verified by tests); $0, offline,
  stdlib-only except the pinned SST venv interpreter.
