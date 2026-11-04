# r3 builder acceptance verdict — successor-004 release candidate

Date: 2026-10-04. Builder state: fresh dirs under `/tmp/r3build/*`
(never builder `runs/`); consumer interfaces only (`release.py` CLI +
`api.py`/host methods on frozen bytes with `/tmp` state); suites +
calibrate from byte-identical `/tmp` copies (diff -r clean × 4: a3,
a4, a6, + regen/manifest work) since they scratch `.test-tmp/`
in-tree. `PYTHONDONTWRITEBYTECODE=1` (one lapse, own residue removed —
see A9); system `python3` = 3.12.3; `prototype/w1/.venv` pydantic =
2.13.5. `successor-004/` + `successor-003/` + `successor-002/` content
never changed (IDENTITY 45/45 + 45/45 + 41/41 before AND after;
FROZEN-BASELINE 4140 + 1 expected live miss). No new findings; F1
re-verified as documented behavior, N1/N2 confirmed as disclosed.

## Verdict: BUILDER-ACCEPT (all A1–A10 PASS; no new findings)

All ten criteria PASS on observed evidence. Preserved attempts:
`A7-attempt1-note.md` (probe bug: read-only copy perms, fixed with
chmod on the COPY). Two builder-side file events inside the frozen
tree, both content-neutral and disclosed: (1) A1 `make_snapshot_
manifest.py` run without argv rewrote `vendor/SNAPSHOT-MANIFEST.json`
byte-identically (sha `e5d8bb0a` == IDENTITY pin, 45/45 re-verified);
(2) one `--help` call without the bytecode export created
`__pycache__/` (2 files), removed by the builder, 45/45 re-verified
after. The independent lane judges.

## Per-criterion results

- A1 PASS (identity/build). IDENTITY 45/45 OK; regen-to-/tmp manifest
  matches frozen (54 files, `5f1f3789…`, file list equal);
  `sched_checker --self-check` OK; pydantic 2.13.5; python 3.12.3.
  (`A1-identity.log`, incl. byte-identical-rewrite NOTE)
- A2 PASS (demo spine, fresh `/tmp` state). Exit 0; S1/S2/S3 VALID
  4/4 lanes+bytes r1-identical (655/0, 310/500, 685/500); S4 5/5 via
  SC-FUSED; S6 4/4 via SC-L2/SC-S2; resume 0 re-invokes, pre-kill
  bytes identical, child rc=-9; SST champion_found $0; settle 5
  markers 0 stranded; 6 routing decisions; EVIDENCE exact fields
  56/56 vs `accept/EXPECTED.json`. (`A2-demo.log`, `A2-expected.log`,
  `check_expected.py`)
- A3 PASS (carried suites). 9/9 conformance + 7/7 fission + 17/17
  successor (incl. SST $0/MATCH legs), all EXIT=0 from a verified
  byte-identical copy. (`A3-*.log`)
- A4 PASS (atomicity). 39/39 OK, EXIT=0: 27 carried + 4
  `TestAtomicConstruction` + 7 `TestWriteInterior` + 50-SIGKILL
  `TestSpecWindowKillLoop` (0 torn side files; landings 7
  no-trace-rerun + 43 completed-before-kill; 0 orphans).
  (`A4-atomicity.log`)
- A5 PASS (sampled kill matrices + mid-write crashes, consumer CLI,
  fresh `/tmp` state). 135/135: settle N=1,3,4,6,8clean; fuse
  N=1,5,7,12,15clean + pre-spec; fission N=1,3,8,12,15clean +
  pre-spec; real SIGKILL landing; kill-during-recovery — every
  ledger-prefix landing converged via `ops recover` (+ defined
  re-runs), conservation ok, 0 stranded, reuse serves after every
  fuse recovery; mid-ledger-append crash → torn tail (prefix
  parses, tail unparseable) → recover rc=1 disk-loss + inspect
  `release: error:` rc=1; mid-side-write worlds.json → old bytes +
  1 benign orphan (deleted per docs) → recover converges + reuse
  serves; mid-side-write fusion artifact → absent → recover
  converges with recovery note. (`A5-killmatrix.log`, `probe_a5.py`)
- A6 PASS (calibrate 2.61x bytes-only + durability wording). 810 vs
  310 = 2.61x reproduced; all 2.61x mentions bytes-scoped with
  explicit no-token/attention/cost disclaimers; no sentence claims
  power-loss/fsync-grade/multi-writer durability (all 5 `power`
  hits are disclaimers; 0 fsync calls; every guarantee
  process-crash-scoped; N1/N2 narrowings confirmed present and
  LIMITS-2-covered). (`A6-calibrate.log`, `A6-wording.log`)
- A7 PASS (SST MATCH + refusal $0). MATCH 54/`5f1f3789…`; tamper-a-
  COPY refused rc=1 naming the file + hash drift, before any SST
  import; zero `../sst` / staging refs in `*.py` (real grep rc=1);
  A2 leg: TEST-only (`"kind": "TEST"` ×2, `"provider_kind":
  "TEST"`, test-prof/fake-model fixtures), champion_found, $0.0,
  pydantic 2.13.5, snapshot_unchanged, sst_file inside snapshot;
  pre/post MATCH. (`A7-sst.log`, `A7-attempt1-note.md`)
- A8 PASS (consumer coverage). 31/31: every CLI verb on fresh state
  (init/run/explain-route±json/inspect/fuse/reuse/fission/
  split-pair/settle/revise/revoke/quarantine/kill-resume/recover)
  + api.py direct (open_run/explain/inspect/recover/settle
  refusal with deny-only growth + zero partials) + negatives
  (run-after-revoke rc=1 ×3 durable, bogus-owner ValueError with
  ≤1-line growth, CLI `release: error:` shape rc=1).
  (`A8-consumer.log`, `probe_a8.py`)
- A9 PASS (frozen intact incl. r2). s004 45/45 + s003 45/45 + s002
  41/41 after; baseline 4140 + exactly the R1-note-E live miss
  (CONTINUING-PROGRAMME.md, coordinator log); r2's 27 files inside
  the baseline all OK; complete newer-than-marker list = 2 dir
  mtimes + the disclosed byte-identical manifest rewrite; own
  `__pycache__` removed; `.test-tmp/` dirs empty + pre-existing;
  `../sst` porcelain 0 lines @ df78f42. (`A9-frozen.log`)
- A10 PASS (edge/negative + F1 + N1/N2). 38/38: wrong-partition
  contradicts (then correct completes); torn-ledger recover refuses
  disk-loss + inspect loud; torn-checkpoint reattach refuses
  classified ("unreadable … disk-loss", deny recorded, stays
  suspended); bare recover settles nothing (lifecycles unchanged);
  unsettled-terminal inspect-readonly + settle exact error + zero
  partials; bad partitions ×4 + non-composite refused with ≤1-line
  growth; fission-args-without-partial refused; recover `--worlds
  COMPOSITE` blocked on partial with one-call complete+settle-
  children; revoked invoke denied + recorded; F1 sequence
  re-verified (direct settle rc=0 strands custody, partitioned
  recover rc=1 "still holds custody"); N1/N2 pins present exactly
  as disclosed (resume.py:70 skip, CONSUMER.md:93, api.py:271,
  resume.py:14/158, SUCCESSOR-REPORT.md:181, LIMITS-2 cover).
  (`A10-edge.log`, `probe_a10.py`)

## No new findings

F1 (r2, LOW record-only) re-verified on s004 bytes: same sequence,
same loud landings, still off-procedure + contract-consistent (F1
WARNING now kept in INTERRUPTION-BOUNDARIES.md §5). N1/N2 (R3,
record-only) confirmed present exactly as disclosed; no widening
observed (wording audit in A6). No other sharp edges encountered.
