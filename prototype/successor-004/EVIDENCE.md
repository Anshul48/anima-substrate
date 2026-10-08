# EVIDENCE.md — successor-004 (R3 atomic side writes + F1/F2 doc precision)

## R3 result

R3 closes the lane's F2 window (SIGKILL in the `worlds.json`
truncate window → 0-byte specs → loud disk-loss refusal) and
corrects the two frozen-doc overclaims in this tree's successor
docs (F2 "all landings converge", F1 "partial fission blocks settle
of its composite"):

- Atomic side files: EVERY whole-file side write on every op path
  is same-dir temp + `os.replace` (old-or-new, never torn), via the
  one `minihost.atomic_write_text` helper. Ledger `append()` and
  the `ROUTING-LOG.jsonl` mirror keep byte-identical append-only
  semantics (the entry-granular prefix property the kill matrices
  depend on).
- The F2 window is closed, proven three ways: (a) construction
  proof — AST + runtime routing proofs that no direct whole-file
  write remains in shipped code (`TestAtomicConstruction`, 4
  tests); (b) statistical proof — 50 real SIGKILLs staggered
  across the fission op tail (the F2 op: two trailing spec writes
  + artifact write): ZERO torn side files, every landing converged
  via `ops recover` (`TestSpecWindowKillLoop`); (c) interior proof
  — deterministic crashes INSIDE side-file writes leave old bytes
  and converge, and crashes inside ledger appends refuse loudly as
  disk-loss (`TestWriteInterior`, 7 tests).
- F2 reproduced FIRST on a pristine successor-003 copy (below):
  0-byte `worlds.json` via real SIGKILL, both in a tight loop
  against `_write_specs` and in full fission ops — then the exact
  loud refusal the lane observed. No fix without a preceding red.
- Doc precision: "all landings converge" → ledger-prefix landings
  converge + side files old-or-new (torn-side-file landing closed;
  genuinely torn files still refuse loudly as disk-loss);
  "partial fission blocks settle of its composite" → scoped to
  `recover_op`'s targeted settle, with the recover path named and
  the F1 warning kept (direct settle stays custody-orthogonal per
  contract). The unproven "ledger-append tearing is impossible"
  claim is WITHDRAWN: a kill inside an append MAY tear the tail;
  the specified landing is a loud disk-loss refusal (tested).
- r2 regression: 17/17 + 9/9 + 7/7 carried suites pass from this
  tree; demo EVIDENCE structurally identical to r2 (all exact
  accept fields match); calibrate still 2.61x; snapshot MATCH.
- r2 + neighbors untouched: `successor-003/IDENTITY.sha256` checks
  OK (45/45), `successor-002/IDENTITY.sha256` OK (41/41), pre/post
  sha256 snapshots identical, no writes outside `successor-004/`
  (see §Frozen verification).

No carried guarantee was weakened to make anything pass (the one
behavior extension — an unreadable checkpoint now refuses
classified, `deny` + `ContractViolation`, instead of a raw decode
error — is fail-closed and covered by tests; no carried test
changed any expectation).

## F2 red (pristine successor-003 copy, before the fix)

Probes ran against `/tmp/s003red`, a byte-copy of the frozen
`successor-003/` (api.py/minihost.py hashes verified PRISTINE
before the runs). Scratch scripts `/tmp/f2red_loop.py`,
`/tmp/f2red_runroot.py`, `/tmp/f2red_sweep.py` (kept out of all
trees; the in-tree `TestWriteInterior`/`TestSpecWindowKillLoop`
are the regression tests).

Tight loop, real SIGKILL vs the real `_write_specs` (`f2red_loop.py`):

    clean sizes: A=201 B=201
    round 1: TORN size=0 head=b''
    RED AUTHENTICATED at round 1

Same tear inside a REAL run root + the F2 loud refusal
(`f2red_runroot.py`):

    run root ready; clean specs size=1007
    round 1: TORN size=0 head=b''
    recover rc=1
    recover stderr: release: error: RuntimeError: recovery refused:
    ledger or worlds.json unreadable (Expecting value: line 1 column 1
    (char 0)); torn files are the disk-loss class (LIMITS-2, out of
    scope): restore from backup, never hand-edit; see
    INTERRUPTION-BOUNDARIES.md
    inspect rc=1
    inspect stderr: release: error: JSONDecodeError: Expecting value:
    line 1 column 1 (char 0)

Full-op sweep, real SIGKILLs aimed at the profiled spec-write
offset (`f2red_sweep.py`; fission wall 0.179s on /tmp/ext4,
first spec write @0.166s; 60 kills across ±30ms):

    fission rc=0 wall=0.179s first-spec-write@0.166s
    delay=0.153: TORN size=0
    delay=0.156: TORN size=0
    delay=0.160: TORN size=0
    sweep done: 3 torn landings in 60 kills (window is microseconds;
    misses prove nothing)

Verbatim F2 reproduction: 0-byte specs + `ops recover` rc=1
RuntimeError disk-loss refusal, exactly as the lane filed it.

## Side-file write survey (every path + disposition)

Audited every `write_text` / `open(..., "w")` in shipped `*.py`
(AST-verified by `TestAtomicConstruction`, which fails on any
direct whole-file write outside the helper):

| path (writer) | disposition |
|---|---|
| `worlds.json` specs (`api._write_specs` — THE F2 window) | ATOMIC (temp+replace) |
| `worlds.json` spec repair (`recover.repair_specs`) | ATOMIC |
| `CONFIG.json` (init + run-tasks update) | ATOMIC (2 sites) |
| `artifacts/fusion-*.json`, `artifacts/fission-*.json` | ATOMIC (bytes unchanged: no trailing newline, as before) |
| `artifacts/recovery-*.json` (recovery notes) | ATOMIC |
| `checkpoint.json` (`MiniHost.suspend`) | ATOMIC |
| `args/*.json` (`MiniHost.store_args`) | ATOMIC |
| formulations/candidates/results/verdicts (`MiniWorld._write`, `SchedWorld._write`) | ATOMIC |
| `verdict-<tid>.json` copies (`pipeline` x2, `fusion` x1) | ATOMIC |
| `artifacts/solution-*.json` (`routing.write_json`) | ATOMIC |
| ledger-create empty file (`MiniHost.__init__`) | ATOMIC |
| `SNAPSHOT-CHECK.json`, `sst_child_test.py` (SST leg, parent side) | ATOMIC |
| `child.READY`, `EVIDENCE.json` (demo) | ATOMIC |
| `calibrate.py` report, `make_snapshot_manifest.py` manifest | ATOMIC |
| `ledger.jsonl` (`MiniHost.append`) | APPEND-ONLY, byte-identical (prefix property preserved) |
| `ROUTING-LOG.jsonl` (`routing.record_routing`) | APPEND-ONLY, byte-identical (ledger mirror) |
| SST child in-sandbox writes (`CHILD_SCRIPT` string: repo fixtures + `sst-result.json`) | LEFT non-atomic BY DESIGN: the child runs under the venv interpreter with only the snapshot on its path (no `minihost` importable), and no kill boundary spans those writes — a kill there re-runs the whole leg. Documented, not on any op path. |

Crash guarantee (in `atomic_write_text`'s docstring):
`os.replace` is atomic for a single file on POSIX and on NTFS, so
a kill at ANY point leaves old-or-new bytes, never a tear. A kill
between the temp write and the replace may orphan a
`<name>.tmp-<pid>` file (never read; safe to delete). No fsync:
the guarantee is atomicity across a PROCESS crash, not durability
across power loss (disk-loss class, LIMITS-2, out of scope).

## What changed (file list)

New tests (in `test_atomicity.py`, normal layout): 4
atomic-construction proofs + the 50-SIGKILL spec-window loop + 7
write-interior proofs (27 → 39).
Modified: `minihost.py` (+`atomic_write_text`, 4 writes routed,
2 write-interior hooks, classified unreadable-checkpoint
refusal; re-pinned), `api.py` (6 writes routed; `RELEASE`
rebrand), `recover.py` / `routing.py` / `resume.py` /
`pipeline.py` / `fusion.py` / `sst_leg.py` / `successor_demo.py` /
`calibrate.py` / `make_snapshot_manifest.py` (writes routed;
rebrand), `test_successor.py` (re-pin + rebrand),
`test_conformance.py` / `test_fission.py` / `release.py` /
`verify_snapshot.py` / `sched_*.py` (rebrand only),
`INTERRUPTION-BOUNDARIES.md` (F1/F2 precision, narrowed ledger
claim, R3 guarantees), `LIMITS.md` (item 2 narrowed),
`CONSUMER.md` / `ORG-OPS.md` / `REPRODUCE.md` (R3 clauses),
`OBLIGATIONS.md` / `VENDORING.md` / `CONTRACT-GAPS.md` /
`SEPARATION-PATHS.md` (carry notes), `PROVENANCE.md` (rewritten),
`EVIDENCE.md` (this file), `IDENTITY.sha256` +
`FROZEN-BASELINE.sha256` (regenerated).
Untouched bytes: `SUCCESSOR-REPORT.md`, `REPORT.md`, `accept/` (all
8 frozen files), `vendor/` (all 57 files).
Full before-record: `PROVENANCE.md`.

## Commands + test output (repo root, `PYTHONDONTWRITEBYTECODE=1`)

    python3 prototype/successor-004/test_atomicity.py
    # Ran 39 tests in 625.642s — OK (39 x "... ok", 0 failures)

    python3 prototype/successor-004/test_successor.py
    # Ran 17 tests in 53.652s — OK (incl. kill + SST legs)

    python3 prototype/successor-004/test_conformance.py
    # Ran 9 tests in 14.154s — OK

    python3 prototype/successor-004/test_fission.py
    # Ran 7 tests in 12.027s — OK

    python3 prototype/successor-004/successor_demo.py
    # successor-004 integrated demo: OK
    #   run_dir: .../prototype/successor-004/runs/demo-20261004T183136Z
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

    python3 prototype/successor-004/calibrate.py
    # S2-central: central=810 direct=0
    # S2-local:   central=310 direct=500
    # ratio central/local = 2.61x (canonical-JSON bytes, task envelope only)

    python3 prototype/successor-004/verify_snapshot.py
    # snapshot MATCH: files=54 hash=5f1f37893b0f5ab9ff7dcf0ce2c60b287b51647e2f18f627eabf5510537cad96

    python3 prototype/successor-004/sched_checker.py --self-check
    # known_good valid=True quality=4/4, known_bad valid=False (2 violations) — OK

Accept comparison (`/tmp/accept_check_004.py`, kept out of the tree;
same methodology as the r2 `/tmp/accept_check_003.py`): new
`EVIDENCE.json` vs `accept/EXPECTED.json` exact fields + vs the
frozen r2 `runs/demo-20261004T144817Z/EVIDENCE.json` structurally:

    # 43 x PASS (every exact field: S1–S6, SST + hash==manifest,
    # fusion, fission, routing_decisions=6, settle
    # markers=5/terminals/stranded_zero, byte refs 655/0, 310/500,
    # 685/500)
    # PASS old-vs-new EVIDENCE structurally identical (modulo paths/run_dir)
    # RESULT: ALL EXACT FIELDS MATCH

## Kill-loop numbers (F2 window, this tree)

`TestSpecWindowKillLoop`: 50 real SIGKILLs, delays 0.05..0.90s
across the fission op tail (fission wall ~0.85s on this box):

    spec-window kill loop: 50 SIGKILLs, 0 torn side files,
    landings={'killed+no-trace-rerun': 27, 'killed+classified-refusal': 19,
    'killed': 4}, benign tmp orphans=0

Every iteration asserted worlds.json + every `*.json` parses and
the ledger stays entry-granular BEFORE recovering; every landing
then converged via `ops recover` (bare, plus the partitioned
re-run exactly where the classified need-operator-input refusal
fired, plus an idempotent bare re-run that repairs specs for
recovery-born children — a pre-existing R1 semantic verified
byte-identical on successor-003). Zero torn side files; zero
unclassified refusals.

Carried R1 matrices still pass unchanged from this tree (settle
8/8, fuse 15/15, fission 15/15 incl. pre-spec kills, repeated
kills incl. kill-during-recovery, 9 staggered SIGKILL landings all
converged) — same logs as r2, see the suite output.

## Write-interior logs (deterministic, via CLI + `ops recover`)

    mid-append fission (N=8): rc=42 -> torn tail ("Unterminated
      string..."), prefix intact -> recover rc=1 "disk-loss"
      (CLI + API), inspect rc=1
    mid-side-write worlds.json (fission): rc=42 -> specs ==
      pre-op bytes + 1038-byte partial orphan vs 1598-byte target
      -> bare recover rc=0 -> converged (dissolved, 1 fission,
      conservation ok, all 5 specs)
    mid-side-write fusion artifact (fuse): rc=42 -> artifact
      absent -> recover rc=0 -> recovery note -> reuse serves
    mid-side-write CONFIG (run): rc=42 -> CONFIG == pre-run
      bytes -> follow-up fuse rc=0 (CONFIG staleness harmless:
      the API re-reads only worlds.json + ledger)
    mid-side-write checkpoint (quarantine): rc=42 -> no
      checkpoint, world active (no trace) -> clean re-quarantine
      rc=0 -> suspended
    torn worlds.json fixtures (0-byte + truncated): recover
      refuses RuntimeError "disk-loss" (CLI rc=1 + API)
    torn checkpoint fixture: reattach refuses ContractViolation
      "unreadable ... disk-loss" + `deny` entry, world stays
      suspended

Forensics (carried, unchanged): partial quarantine detected with
`OPERATOR REPAIR` steps (involved world blocked from
`recover_op`'s targeted settle, others proceed);
conservation-violation ledger refuses recover; torn ledger refuses
("disk-loss"); fission args without partial refused; bare recover
settles NOTHING by default (safe default asserted); a partial
fission withholds its composite (and created children) from
`recover_op`'s targeted settle until completed — one call can then
complete the fission AND settle the children. DIRECT settle of
such a composite does NOT refuse (custody-orthogonal by contract;
F1 warning kept — see INTERRUPTION-BOUNDARIES.md §5).

## Frozen verification (r2 + neighbors untouched)

No git repo exists at this root (`git status` → "not a git
repository"), so immutability is proven by content hashes instead:

- Pre-work snapshot (before ANY write): sha256 of all 754 files
  under `successor-002/` + `successor-003/` + `release-20261004/`
  + `release-r2/` → post-work re-hash compared IDENTICAL (command
  + result below).
- `cd prototype/successor-003 && sha256sum -c IDENTITY.sha256` →
  all 45 OK. `cd prototype/successor-002 && sha256sum -c
  IDENTITY.sha256` → all 41 OK.
- `cd prototype && sha256sum -c
  successor-004/FROZEN-BASELINE.sha256` → all 4141 OK (3639
  carried lines re-verified + 1 live re-pin +
  `successor-003/` incl. runs/ (282) + `release-r2/` (27) +
  `programme-20261004/H2-lane/` excl. `.test-tmp` (192)). The
  carried `successor-003/FROZEN-BASELINE.sha256` itself still
  verifies 3639/3640 (the 1 miss is the live
  `CONTINUING-PROGRAMME.md`, re-pinned at current bytes with a
  note — same posture as r2's "exactly the 1 live miss").
  Live sibling workspaces (`programme-20261004/L1-transfer/`,
  `L2-transfer/`, `M1-*`, `P1-*`, `R1-VERIFICATION.md`,
  `H2-VERIFICATION.md`, `PREREG-LOG.md`) are EXCLUDED from the
  pin (they change under their owners); non-interference there
  is covered by the `-newer` check below.
- No writes of mine outside `successor-004/`: `find prototype
  -newer <pre-work marker> -not -path "./successor-004*"` returns
  ONLY `.` (dir mtime from my `mkdir successor-004`),
  `programme-20261004/CONTINUING-PROGRAMME.md` (coordinator live
  log) and `programme-20261004/P1-adapters/{PRODUCER-ASK,SURVEY}.md`
  (concurrent sibling-track activity — not mine; every write I
  issued targeted `successor-004/` or `/tmp`). Everything else —
  successor-002/, successor-003/, release-20261004/, release-r2/,
  H2-lane/, all other neighbors — has no path newer than my
  start marker.
  (`PYTHONDONTWRITEBYTECODE=1` throughout: no `.pyc`; both
  `.test-tmp/` dirs exist but are empty.)
- `../sst` never touched (SST leg consumes the vendored snapshot
  read-only; pre/post MATCH verified by tests); $0, offline,
  stdlib-only except the pinned SST venv interpreter.
