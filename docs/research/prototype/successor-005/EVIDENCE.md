# EVIDENCE.md — successor-005 (S5 bounded procedure participant; R3 carried)

## S5 result

S5 adds the bounded procedure participant (`procedure.py`: advertise /
run / recover for caller-supplied procedures through truthful, declared
capabilities) plus the `vehicle/relcheck` usefulness vehicle (bundle
program + pins + independent checker + direct baseline + readiness aid),
with all R3 behavior carried. Builder-side verification of S5-DESIGN §6:

| gate | claim | builder result |
|---|---|---|
| S5-A1 | carried suites green from this tree | 9/9 + 7/7 + 17/17 + 39/39 + demo + calib + snapshot (below) |
| S5-A2–A8 + A11-tests | procedure mechanism (advertise/run/recover/change/wording) | 57 tests: 56/56 full suite (6095.2 s) + cross-key P9 pin focused-green (lane re-runs all 57); loop landings L2=12 L3=28 |
| S5-A9 | frozen predecessors intact, both ends | 1161/1161 + 41/41 + 45/45 + 45/45 + 46/46, pre/post (§S5 frozen verification) |
| S5-A10 | vehicle readiness, no U-execute | READINESS-PASS (host + direct VALID, claims-diff 0, expense honest) |
| S5-A11 | wording audit, tree-wide | PASS: 3 mechanical tests green + manual sweep; N1/N2 defined below |
| S5-A12 | independent lane | PENDING (lane brief ready; spawns after this record freezes) |

U-execute was NEVER run (gated on S5-A12 + §7.8 filing). Q5 (permanent
host) stays open. No carried guarantee was weakened to make anything
pass; the four verification fixes are red-first repairs (§Verification
fixes), each with its preceding red preserved.

Test-class → gate map (`test_procedure.py` docstrings): Advertise
A2/A7/A8, Gates A3, Honesty A2, Permissions A4, Accountability A5,
Interruption A6, Recovery A7, Change A8, Construction A7, Wording A11.

Verification provenance: a host reboot mid-verification (2026-10-05
~08:40Z; uptime reset, /tmp wiped including partial logs) forced a
second verification pass. Every number below is a POST-REBOOT
re-observation with logs persisted under
`runs/verify-20261005T1005Z/` (in-tree evidence, unpinned by posture).
Pre-reboot observations matched (9/9, 7/7, 17/17, 39/39, READINESS-PASS
with identical pins `1fee2241…` / `2dbb0439…`, R-A EMPTY, 24/24 + 7/7
negatives) but their scratch logs are gone, so nothing below relies on
them; the pins themselves are current in-tree bytes. (/tmp proved
unreliable twice — once by reboot, once by a cleaner pass with no
reboot — so every material log and probe now lives under
`runs/verify-20261005T1005Z/`.)

## S5-A1 carried green (this tree, repo root, `PYTHONDONTWRITEBYTECODE=1`)

    python3 prototype/successor-005/test_conformance.py
    # Ran 9 tests in 9.269s — OK (log: runs/verify-20261005T1005Z/conformance.log)
    python3 prototype/successor-005/test_fission.py
    # Ran 7 tests in 8.387s — OK (log: runs/verify-20261005T1005Z/fission.log)
    python3 prototype/successor-005/test_successor.py
    # Ran 17 tests in 39.988s — OK, incl. kill + SST legs; S5 re-pin §1
    # (log: runs/verify-20261005T1005Z/successor.log)
    python3 prototype/successor-005/test_atomicity.py
    # Ran 39 tests in 528.986s — OK (log: runs/verify-20261005T1005Z/atomicity.log)
    python3 prototype/successor-005/test_procedure.py
    # Ran 56 tests in 6095.238s — OK (log: runs/verify-20261005T1005Z/procedure.log)
    # + test_p9_cross_key_scratch_still_guarded focused-green (19/19 with
    #   TestProcPermissions+TestProcWording in 39.4 s; added after the full
    #   run per the audit gap note — the lane re-runs all 57)
    # sigkill loop landings={'L2': 12, 'L3': 28} wall=131.50s
    # repeated-kill loop: 12 rounds, killed-live=12 l4-restored=0

Carried kill matrices (inside the 39/39): `test_settle_every_boundary`,
`test_fuse_every_boundary`, `test_fission_every_boundary`,
`test_sigkill_settle/fuse/fission` (9 staggered landings, all converged),
`test_full_flow_with_kills_at_every_op`, kill-during-recovery x3,
pre-spec x2, forensics negatives. Landing lines from the atomicity log:

    sigkill settle/fuse/fission x delays 0.05/0.2/0.5: all converged
      (8 killed-variants + 1 completed-before-kill — the 0.5 s settle
      kill missed its window on the faster box; still converged)
    spec-window kill loop: 50 SIGKILLs, 0 torn side files,
      landings={'killed+no-trace-rerun': 26, 'killed+classified-refusal': 20,
      'killed': 4}, benign tmp orphans=1 (never-read, safe to delete)

Demo / calibration / snapshot (repo root):

    python3 prototype/successor-005/successor_demo.py --run-dir=<tmp>  # OK exit 0
    #   SST: snapshot=MATCH hash=5f1f37893b0f ... pydantic=2.13.5
    #   settle: [...] markers=5 stranded=0; routing decisions: 6 recorded
    python3 prototype/successor-005/calibrate.py          # 2.61x
    python3 prototype/successor-005/verify_snapshot.py    # MATCH files=54

R-A byte-identity leg (r3 behavior preserved): r3 demo
(`successor-004`) vs r5 demo (`successor-005`), both exit 0 into fresh
/tmp run-dirs; demo sources differ by exactly one line (the
self-identity banner). Canonicalized outputs (run-dir paths + banner +
timings stripped, order kept):

    diff -u demo-r3.canon demo-r5.canon → EMPTY (15 lines each;
    logs: runs/verify-20261005T1005Z/demo-r3.log, demo-r5.log + .canon)

## S5-A10 vehicle readiness: READINESS-PASS

    SST_VENV_PY=$PWD/prototype/w1/.venv/bin/python \
    python3 prototype/successor-005/vehicle/s5-readiness-check.py --root <tmp>

    [PASS] frozen-pre: 969 files re-verified (clean)
    [PASS] hygiene-scan: 234 calls scanned (clean)
    [PASS] advertise: bundle sha matches pins (1fee2241d1fd2d48...)
    [PASS] host run: executed=6 skipped=0 re_executed=0 wall=175.8s
    [PASS] checker(host): RELCHECK-VALID
    [PASS] expense: host wall 175.8s (floor 60s, no padding)
    [PASS] direct run rc=0
    [PASS] checker(direct): RELCHECK-VALID
    [PASS] claims-diff: 0 differences (identical claims)
    [PASS] frozen-post: 969 files re-verified (clean)
    READINESS-PASS (exit 0; log: runs/verify-20261005T1005Z/readiness.log)

Pins (generated by `vehicle/make_vehicle_pins.py`, gates 1–3 pass):

    bundle_sha256=1fee2241d1fd2d482ab90ac2a3aa63b8d3f4e56dd44427a89c3aa6ce5161c91d
    pins_sha256=2dbb04399fab6c07abad4ceeb74b0128c61afe044141416013622d9891e455ee

Byte-identical regeneration: consecutive runs produce identical bytes
for all three files (`pins.json`, `MANIFEST.json`, `relcheck-pins.json`;
`sha256sum -c` 3/3 OK). The manifest records the absolute venv
interpreter per suite step (`env_extra.SST_VENV_PY`; §Verification
fixes). `pins.json` pins predecessor/release bytes only (zero
references to successor-005/vehicle), so s005-side fixes cannot
invalidate it (verified by content scan).

Preceding red (preserved): the first readiness run FAILED on the direct
conjunct — `direct suite-r1: FAILED rc=1` — because the direct runner
scrubbed `SST_VENV_PY` while children run from scratch copies lacking
the relative `w1/.venv` path (`SSTBoundary: venv interpreter missing`,
suite-r1 demo leg). The bundle runner already forwarded the override
with a comment naming this exact failure; the fix mirrors it into the
direct runner (§Verification fixes). The fail-closed SST boundary
itself is proven by this red. Re-run after the fix: READINESS-PASS.

Negative legs (all throwaway probes, s005 read-only; scripts kept out
of the tree, results quoted here):

- Verdict/parser/surface matrix (24/24 PASS):
  `verdict_rule` 8/8 input combinations agree across both
  implementations + 5 value checks (ACCEPT/PARTIAL/FAIL cells);
  `parse_unittest_log` 5 log shapes (OK/skipped/FAILED/missing-Ran/
  OK-plus-FAILED-marker) agree + 5 value checks (failed-marker wins,
  missing-Ran yields ran=None); `surface_of` agrees on a synthetic
  tree (both find api functions; cli_verbs [] on both — extractor
  recall on real trees is proven by generation: 14/15 verbs).
- Checker mutations (7/7 PASS): clean control RELCHECK-VALID;
  foreign bundle sha → `report binds a foreign bundle sha`; deleted
  `nonce` → `report schema: missing 'nonce'`; flipped verdict →
  `verdict rule recomputes ACCEPT; report claims FAIL`; truncated
  ledger line 3 → `ledger line 3 corrupt`; skewed proc_begin argv →
  `ledger: identity argv skews vs manifest`; flipped suite-log byte →
  `artifact suite-r1/... skews vs the manifest claim`. Every refusal
  names its axis; exit 1 throughout.
- Tampered-copy run leg: s002 copied to /tmp, 1 byte flipped in
  `api.py`, params re-pointed, `relcheck.py --step identity` →
  exit 1, `identity: MISMATCH` on stderr, `IDENTITY-RESULT.json`
  `ok: false`. (Real frozen trees never touched.)

Padding attestation (manual, honest-expense gate): zero `sleep` /
`time.sleep` calls in bundle + exec paths (two mentions are the
docstring `No sleeps` + a `nothing here sleeps` comment); `import
time` used for wall measurement only; zero `while True` loops in
`relcheck.py` / `procedure.py` / `direct_relcheck.py` /
`make_vehicle_pins.py`. The host wall (175.8 s) is 6 real
steps including full SST venv suite children. No padding exists to
remove.

## S5-A11 wording audit: PASS

Mechanical enforcement lives in `test_procedure.py` (`TestProcWording`,
three methods, green inside the full suite). This section describes
the predicates WITHOUT quoting their trigger vocabularies, because
the tests scan this file too (quoting a trigger here re-trips the
test — observed red, fixed by this wording; see the preserved reds).
Exact trigger lists live in the test source.

- The negation test: every C-family term hit outside import
  statements must share its line with a negation from NEGATIONS.
- The bounder test: every I-word hit must share its line with one of
  the seven bounders.
- The terms test: CONSUMER.md contains `accountable executor`,
  `scoped invocation`, `contractual`, `CONTRACTUAL`, `ENFORCED`,
  `P11`, `P15`; `procedure.py` contains `accountable executor`;
  N1/N2 predicates (below) hold.

Manual sweep (42 files: `*.py` + `*.md` excluding `vendor/`,
`__pycache__`, `runs/`; `muse.search` returned false-empty on this
tree, so the sweep used scoped `bash grep` — recorded here so the
lane does not inherit the tool gap):

- C-family sweep: all prose hits carry negations. Reviewed, not
  claims: two SST-child environment descriptives (carried R3 § +
  INTERRUPTION-BOUNDARIES §1 — they name the SST harness's own
  module context, not a procedure guarantee), a checker-independence
  test class name, the vendored SST module import (test-carved).
- I-word sweep: the kill-tear claim (CONSUMER torn-side row) is
  proven (F2 matrix + interior tests) with the N1 carve-out
  explicit; `cannot prevent / cannot be prevented` are limitation
  admissions (P11); the cannot-fund / cannot-act / adoption-refusal
  wordings are tested refusal behaviors and defined mechanism terms;
  the withdrawn ledger-no-tear sentence is a meta withdrawal.
- Crash-scope sweep: every persistence sentence carries the
  process-crash / power-loss + no-fsync separation, via in-sentence
  wording (`api.py`, CONSUMER, EVIDENCE, INTERRUPTION-BOUNDARIES §1,
  LIMITS item 2 + item 4, `minihost.py`, `procedure.py`, `resume.py`)
  or an explicit LIMITS-2 scope tag (LIMITS-2 = item 2: single
  machine, local disk, no multi-writer, no disk loss, no fsync;
  ledger tear specified as loud disk-loss refusal). The N2 test
  enforces the spelling family mechanically (LIMITS-2 tag rule).

N1/N2 narrowings (defined here; ORG-OPS.md points here):

- N1 (resume-skip carve-out): `scan_succeeded` skips unreadable args
  fail-safe instead of refusing. Documented in CONSUMER.md (torn-side
  row); enforced by the test asserting `scan_succeeded` is named there.
- N2 (crash-scope disclaimer, LIMITS-2): every persistence-family
  wording carries a same-line no-fsync / LIMITS-2 / power tag.
  Enforced tree-wide by test (`bad == []`).

Preserved reds: (a) the first full `test_procedure` run failed the
bounder test on a `procedure.py` doc line using the -ion spelling
where the bounder list carries the shorter stem spelling (not a
substring of the longer). One-word doc fix to the listed spelling
(§Verification fixes); the re-run passes. (b) This section's first
draft quoted trigger vocabularies and tripped all three wording
tests (3 + 34 + 3 hits, all this file); rewritten in the present
trigger-free form. No test expectation was changed in either case.

## Verification fixes (builder bytes → verified bytes)

Five files, each red-first; no carried test changed any expectation
(the one scan-set change is justified below):

| file | red | fix | proof |
|---|---|---|---|
| `test_successor.py:58-64` | test_14 pin mismatch (s005 minihost differs) | S5 re-pin comment + `PINNED_MINIHOST_SHA=4cb3c1dd...095a4` (R1/R3 precedent; assertion untouched) | 17/17 OK; `sha256sum minihost.py` matches pin |
| `procedure.py:1214` | bounder-test FAIL (above) | -ion spelling → listed stem spelling | wording tests green in re-run |
| `procedure.py:768-779,876` | loop-test ERROR at K09: orphaned detached step child wrote `done.txt` into dead attempt1 during attempt2's P9 window → `ValueError: outside-scratch writes (P9)` | P9 excludes the key's whole proc-scratch subtree (all attempts); other keys, ballast, ledger, artifacts still guarded | focused regression red/green + 56/56 full suite (6095.2 s, L2=12/L3=28); independent read-only audit 5/5 PASS (see S5-VERIFICATION.md) |
| `vehicle/make_vehicle_pins.py:280-299` | pins lacked the venv interpreter record; suite children need the absolute override | resolve `SST_VENV_PY` (or default), fail loud if missing, record per-step `env_extra` in MANIFEST | MANIFEST carries absolute path; regen byte-identical; readiness green |
| `vehicle/direct_relcheck.py:43-53` | readiness direct conjunct FAIL (`SSTBoundary`, above) | forward non-empty `SST_VENV_PY` into step env, mirroring the bundle runner's own block + comment | READINESS-PASS; direct VALID |
| `test_procedure.py` (+17/+19/+16 lines) | (a) no focused cover for the P9 orphan race; (b) negation-test red on 30 `sandbox` path-hits inside generated pins (zero prose hits); (c) cross-key P9 tightness unpinned (audit gap note) | (a) +`test_p9_same_key_prior_attempt_tolerated` (deterministic: child writes into a same-key dead attempt dir); (b) `_scoped_files` carves the three generated manifests (`pins.json`, `MANIFEST.json`, `relcheck-pins.json`) — data, not prose, same principle as the import carve-out; hand-written vehicle files stay scanned; (c) +`test_p9_cross_key_scratch_still_guarded` (child writes into another key's scratch → must trip) | (a) red on old exclusion (`ValueError (P9)`, exact K09 shape) → green on fix, 3/3 with existing P9 tests; (b) wording 3/3 green; (c) first draft used a wrong relative depth (child exited 1 — the test caught its own bug) → fixed → 19/19 with Permissions+Wording |

Count history (record-only): builder docs said 56 procedure tests;
the loader-verified builder count was 55 (`countTestCases`); the two
P9 pin tests above make 57 (55 + 2). All in-tree counts now say 57.
(An unverifiable `2.0.5/3.0.5 (56 scenarios)` shorthand from working
notes is DROPPED from this record — no source found; matrices are
evidenced by suite test names + loop logs instead.)

## S5 commands + observed outputs (substrate repo root)

All with `PYTHONDONTWRITEBYTECODE=1`; `SST_VENV_PY` exported only where
noted (value = the default `prototype/w1/.venv/bin/python`):

    python3 prototype/successor-005/test_conformance.py   # 9/9 OK 9.3s
    python3 prototype/successor-005/test_fission.py       # 7/7 OK 8.4s
    python3 prototype/successor-005/test_successor.py     # 17/17 OK 40.0s
    python3 prototype/successor-005/test_atomicity.py     # 39/39 OK 529.0s
    python3 prototype/successor-005/test_procedure.py     # 56/56 OK 6095.2s + cross-key pin focused
    python3 prototype/successor-005/successor_demo.py     # OK exit 0 (R-A leg)
    python3 prototype/successor-004/successor_demo.py     # OK exit 0 (R-A leg)
    python3 prototype/successor-005/calibrate.py          # 2.61x
    python3 prototype/successor-005/verify_snapshot.py    # MATCH files=54
    python3 prototype/successor-005/vehicle/make_vehicle_pins.py  # gates pass; +regen identical
    python3 prototype/successor-005/vehicle/s5-readiness-check.py # READINESS-PASS
    neglegs probe                                       # 24/24 PASS (throwaway)
    checkneg probe                                      # 7/7 PASS (throwaway)
    relcheck.py --step identity (tampered copy)           # rc=1 MISMATCH ok:false
    cd prototype/successor-002 && sha256sum -c IDENTITY.sha256   # 41/41
    cd prototype/successor-003 && sha256sum -c IDENTITY.sha256   # 45/45
    cd prototype/successor-004 && sha256sum -c IDENTITY.sha256   # 45/45
    cd prototype/programme-20261004/H2-lane && sha256sum -c IDENTITY.sha256  # 46/46
    cd prototype && sha256sum -c successor-005/FROZEN-BASELINE.sha256  # 1161/1161

## Carried R3 record (preserved; the s004 evidence this tree inherits)

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
  contract). The "ledger-append tearing is impossible" claim was never
  proven and is WITHDRAWN: a kill inside an append MAY tear the tail;
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
the guarantee is atomicity across a PROCESS crash (no fsync), not durability
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

## Frozen verification, carried R3 record (r2 + neighbors untouched)

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

## S5 frozen verification (both-ends; r3-style posture)

- Pre-work snapshot (before ANY S5 write): sha256 of all 1161 files
  under `successor-002/` + `successor-003/` + `successor-004/` +
  `release-20261004/` + `release-r2/` + `release-r3/` +
  `programme-20261004/H2-lane/` + neighbors → frozen snapshot
  (2026-10-05T01:38Z).
- Installed byte-exact as this tree's `FROZEN-BASELINE.sha256` (`cmp`
  clean, 1161 lines); post-everything re-hash (after the host reboot
  and all re-verification): 1161/1161 OK.
- Individual re-checks after all suites: s002 41/41, s003 45/45, s004
  45/45, H2-lane 46/46 (above); readiness's own frozen pre/post
  (969 files) clean in every readiness run.
- No writes of mine outside `successor-005/`: the pre-reboot
  `find prototype -newer <marker> -not -path "./successor-005*"`
  returned ONLY `.` (dir mtime from the `mkdir`),
  `programme-20261004/` dir mtimes, `CONTINUING-PROGRAMME.md`
  (coordinator live log) and `programme-20261004/U-execute/*`
  (concurrent sibling-track activity incl. their `__pycache__` —
  not mine; every write I issued targeted `successor-005/` or
  scratch). Live sibling files are EXCLUDED from the pin (0 baseline
  hits — same posture as R3). Content hashes (1161/1161) are the
  primary proof; they were re-observed post-reboot.
- `PYTHONDONTWRITEBYTECODE=1` throughout: no `.pyc` of mine anywhere.
  `.test-tmp/` dirs exist but are empty at handoff.

## S5 deferred and open

- S5-A12 lane verdict (spawns after this record freezes).
- U-execute prereg + filing (§7.8) — gated on S5-A12.
- Q5 permanent host — open, non-blocking.
- R3-carried defers (unchanged): quarantine-transfer operator-repair,
  multi-writer, disk-loss recovery, cross-host, live-model SST,
  STC-backend, TRACE, scale, policy invention (gated), co-design.
- In-tree `runs/` outputs are evidence scratch, not pins (IDENTITY
  covers source + records only).
