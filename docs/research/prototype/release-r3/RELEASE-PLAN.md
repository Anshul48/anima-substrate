# r3 RELEASE PLAN — bank successor-004 as a usable frozen release

Release candidate: `prototype/successor-004/` (45 files, IDENTITY below).
Pattern: r2 (`prototype/release-r2/`: RELEASE-PLAN + builder VERDICT +
independent VERDICT2 + RELEASE-RECORD with coordinator appendix +
CONSUMER-DELTA).
Authority: R3 ACCEPT-WITH-NOTES
(`prototype/programme-20261004/R3-VERIFICATION.md`; notes N1–N3
record-only). Standing constraints: $0, offline, stdlib-only except
the carried SST leg (`SST_VENV_PY=$PWD/prototype/w1/.venv/bin/python`,
pydantic exactly 2.13.5); `PYTHONDONTWRITEBYTECODE=1` throughout.

## 1. What r3 is

r3 = successor-004 accepted as a usable frozen release, i.e. **r2
(successor-003) + R3 gains, nothing else**:

- **Atomic side writes** (closes r2 finding F2): EVERY whole-file side
  write (`worlds.json`, `CONFIG.json`, fusion/fission artifacts,
  recovery notes, `checkpoint.json`, args, verdicts, solutions) goes
  through `minihost.atomic_write_text` (same-dir temp + `os.replace`),
  so a kill at ANY point leaves old-or-new bytes, never a torn file.
  Process-crash atomicity only; no fsync; power loss stays disk-loss.
- **Write-interior coverage**: deterministic mid-append crashes (ledger
  tail tear → specified loud landing) and mid-side-write crashes
  (old bytes + benign orphan → convergence) on both media, tested.
- **Withdrawn ledger no-tear claim**: the unproven "ledger-append
  tearing is impossible" claim is WITHDRAWN; the specified landing for
  a torn tail is a loud disk-loss refusal (tested, CLI + API).
- **Process/power separation**: every R3 durability sentence carries
  the process-crash vs power-loss + no-fsync distinction (N2 carves
  the only four narrowings, tree-level-covered by LIMITS-2).
- **F1/F2 doc precision**: F1 WARNING kept verbatim in
  INTERRUPTION-BOUNDARIES.md §5 (targeted-recover refuses, direct
  settle stays custody-orthogonal); "all landings converge" narrowed
  to "all ledger-prefix landings converge; torn side-files refuse
  loudly as disk-loss" semantics; one fail-closed-earlier behavior
  extension (classified unreadable-checkpoint refusal on reattach).
- Everything else is the r2 behavior carried forward: hybrid routing,
  fusion/fission/quarantine, reuse+lineage, revision/revocation with
  rulings, atomic settle, kill-resume, ops recover, vendored
  hash-pinned SST snapshot (`5f1f3789…`, 54 files,
  SUBSTRATE-QUALIFIED posture unchanged), 2.61x bytes-only calibration.

Deliberate staging (no silent drift): `accept/` (8 files) and `vendor/`
(57 files) are byte-identical to r2; `REPORT.md` + `SUCCESSOR-REPORT.md`
carried byte-identical; all other `.py`/doc files differ by rebrand at
minimum; code diffs beyond rebrand are the R3 atomic-write routing +
crash hooks + checkpoint classification only (see §4 of the record).

## 2. Consumer surface (unchanged shape, one behavior extension)

- CLI: `release.py` (`init/run/explain-route/inspect/ops`, incl.
  `ops recover`). All state via explicit `--state-dir`; nothing written
  elsewhere.
- Programmatic API (`api.py`): `init_run`, `open_run`, `run_tasks`,
  `fuse_op`, `fission_op`, `quarantine_op`, `revise_op`, `revoke_op`,
  `reuse_op`, `split_pair_op`, `settle_op`, `kill_resume_op`,
  `recover_op`, `explain_route_op`, `inspect_state_op`.
- Behavior extension: `reattach` on an unreadable checkpoint now
  refuses with a classified `ContractViolation` ("unreadable …
  disk-loss", deny recorded, stays suspended) instead of an
  unclassified error.
- Setup/config/inputs/outputs/failure table/state layout/recovery
  procedure: `successor-004/CONSUMER.md` (authoritative for r3).

## 3. Acceptance criteria A1–A10 (builder run; independent lane follows)

Executed by the builder on fresh `/tmp` state through consumer interfaces.
Suites + calibrate run from byte-identical `/tmp` copies (they scratch
`.test-tmp/` in-tree); demo + CLI probes + snapshot checks execute the
FROZEN bytes directly with `/tmp` state (read-only use). Any FAIL stops
the release (report with evidence; do not patch the frozen tree, do not
weaken the criterion).

- **A1 identity/build**: `successor-004/IDENTITY.sha256` 45/45 OK;
  regenerated vendor snapshot manifest (to `/tmp`) matches the frozen
  manifest; `sched_checker --self-check` OK; `SST_VENV_PY` pydantic ==
  2.13.5; system python3 version recorded.
- **A2 demo spine on fresh state**: `successor_demo.py --run-dir=/tmp/...`
  exit 0; S1/S2/S3 VALID 4/4 with r1-identical lanes+bytes
  (655/0, 310/500, 685/500); S4 5/5 via fused reuse; S6 4/4 via
  fission reuse; S3 resume 0 re-invokes + byte-identical pre-kill
  artifacts; SST leg champion_found $0; settle 5 markers 0 stranded;
  6 routing decisions; EVIDENCE.json exact-fields match
  `accept/EXPECTED.json`.
- **A3 carried suites 9/9+7/7+17/17**: `test_conformance.py` 9/9 OK,
  `test_fission.py` 7/7 OK, `test_successor.py` 17/17 OK (incl. SST
  $0/MATCH legs) from a byte-identical copy (diff -r clean).
- **A4 atomicity incl. the 11 new construction/interior tests +
  sampled kill-loop**: `test_atomicity.py` 39/39 OK from a
  byte-identical copy (27 carried + 4 `TestAtomicConstruction` + 7
  `TestWriteInterior` + 50-SIGKILL `TestSpecWindowKillLoop` with 0
  torn side files).
- **A5 sampled kill matrices + ≥1 mid-write crash per medium through
  consumer CLI on fresh /tmp state**: settle/fuse/fission boundary
  samples (builder's own N, distinct from suite + r2 samples),
  pre-spec kills, ≥1 real SIGKILL landing, ≥1 kill-during-recovery
  convergence — every ledger-prefix landing converges via consumer
  `ops recover` (+ fresh `ops settle`/op re-run where defined),
  conservation holds, 0 stranded, reuse serves after fuse recovery;
  PLUS mid-ledger-append crash → torn tail → loud disk-loss refusal
  (recover + inspect), and mid-side-write crashes (worlds.json +
  artifact) → old-or-new bytes → recover converges.
- **A6 calibrate 2.61x bytes-only + wording audit incl. no unproven
  durability language**: `calibrate.py` from a byte-identical copy →
  S2-central 810 vs S2-local 310 = 2.61x; every ratio mention stays
  bytes-scoped with an explicit no-token/attention/cost disclaimer;
  no sentence claims power-loss durability, fsync-grade durability,
  or multi-writer safety (N1/N2 narrowings disclosed, LIMITS-2 cover
  verified, zero fsync calls).
- **A7 SST MATCH + refusal legs $0**: `verify_snapshot.py` MATCH
  (54 files, `5f1f3789…`); tamper-a-COPY refusal (loud identity error,
  exit 1, before any SST import); no `../sst` runtime references (grep);
  SST leg in A2 shows TEST-only gateway, champion_found, cost $0.0,
  pydantic 2.13.5; snapshot untouched by the run (pre/post MATCH).
- **A8 consumer coverage**: every CLI verb exercised on fresh /tmp state
  (`init/run/explain-route/inspect`, `ops fuse/fission/quarantine/
  revise/revoke/reuse/split-pair/kill-resume/settle/recover`) +
  `api.py` op coverage (incl. `recover_op`) + negative paths (refused
  invoke → ContractViolation + deny; bad preconditions →
  ValueError/RuntimeError/ContractViolation BEFORE mutation; CLI error
  → `release: error: …` exit 1).
- **A9 all frozen predecessors intact incl. r2**: `successor-002/
  IDENTITY.sha256` 41/41 OK; `successor-003/IDENTITY.sha256` 45/45 OK;
  `successor-004/IDENTITY.sha256` 45/45 OK (before AND after);
  FROZEN-BASELINE over frozen paths OK (1 live-file line excepted per
  R1 note E); no writes outside `prototype/release-r3/` + `/tmp`
  (newer-than-marker check, exceptions disclosed with byte-identity
  proof); `../sst` porcelain untouched-by-me at df78f42.
- **A10 edge/negative incl. torn-tail loud refusal + F1 sequence +
  N1/N2 disclosure check**: wrong-partition recover refused
  (contradiction, never silent divergence); torn-ledger recover refused
  (disk-loss class) + inspect loud; torn-checkpoint reattach refused
  classified (new extension); bare `ops recover` settles NOTHING by
  default; unsettled-terminal ledger rejected with the exact error; bad
  partition shapes refused with zero partial effects; revoked invoke
  denied with recorded deny; fission-args-without-partial refused;
  partial fission blocks composite settle until completed (pinned
  recover path); F1 sequence re-verified (direct settle strands,
  partitioned recover refuses "still holds custody"); N1/N2 pins
  present exactly as disclosed.

## 4. In-envelope bounds (carried from successor-004 LIMITS.md)

Toy scale (4–5 tasks/slots, one shared deterministic solver); single
machine + local disk; PROCESS-CRASH ONLY (no fsync issued; power/media
loss is the disk-loss class); no multi-writer; single-host; one
injected kill per S3 run + kill-during-settle/fusion/fission covered
(quarantine transfer stays operator repair); side-file kill-tear
exposure zero on op paths (temp+`os.replace`, old-or-new); ledger
append interior explicitly NOT covered (torn tail → loud disk-loss
refusal); bytes-only 2.61x (no token/cost generality); revocation =
authority-stamp flip + replayed ledger entry, capabilities fixed at
creation; SST TEST fixtures only, SUBSTRATE-QUALIFIED (no SST-owner
acceptance claimed); wall-clock `at` excluded from byte-identity;
no siloed balances/content-refs/relationship persistence, `retired`
unexercised, channels in-memory-only; no learning of any kind.
LIMITS-11 CLOSED (atomic settle); LIMITS-3 narrowed (kill-during-
settle/fusion/fission covered); LIMITS-2 narrowed (side-file half;
ledger half explicitly withdrawn from the no-tear claim).

## 5. Out of scope (unchanged posture)

No U-branch / real-producer consumption claims (still blocked;
SUBSTRATE-QUALIFIED posture unchanged). No L/R/P experiment
re-verdicts. `CANONICAL-RECORD.md` + `REPRODUCE-ALL.md` are
coordinator-owned (not touched). Verdict levels per r1 plan:
ACCEPT (all PASS) / ACCEPT-WITH-NOTES (all PASS + record-only notes)
/ REJECT (any FAIL → report, builder fixes in a NEW tree, rerun).
