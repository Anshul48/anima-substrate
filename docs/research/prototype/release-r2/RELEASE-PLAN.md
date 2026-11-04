# r2 RELEASE PLAN — bank successor-003 as a usable frozen release

Release candidate: `prototype/successor-003/` (45 files, IDENTITY below).
Pattern: r1 (`prototype/release-20261004/`: FINISH-LINE + ACCEPTANCE-PLAN +
RELEASE-RECORD, independent lane after the builder run).
Authority: programme log 2026-10-04 ("Next bounded objective: r2 release
— builder launched"). Standing constraints: $0, offline, stdlib-only
except the carried SST leg (`SST_VENV_PY=$PWD/prototype/w1/.venv/bin/python`,
pydantic exactly 2.13.5); `PYTHONDONTWRITEBYTECODE=1` throughout.

## 1. What r2 is

r2 = successor-003 accepted as a usable frozen release, i.e. **r1
(successor-002) + R1 gains, nothing else**:

- **Atomic settle**: refusal leaves ZERO partial dissolves / grant_returns
  (rehearse-before-dissolve; closes r1 LIMITS-11).
- **Interruption boundaries**: kill-during-settle/fusion/fission is defined
  behavior with recovery exercises, no silent partials (narrows r1 LIMITS-3
  to quarantine-transfer only).
- **Ops recover**: `release.py ops recover` / `api.recover_op` completes
  interrupted settle/fuse/fission idempotently (incl. kill-during-recovery
  convergence) or refuses loudly with exact operator steps (fission input,
  partial quarantine, conservation violation, torn ledger).
- Everything else is the r1 behavior carried forward: hybrid routing
  (local iff >=2 rounds AND split), fusion/fission/quarantine,
  reuse+lineage, revision/revocation with rulings, kill-resume,
  vendored hash-pinned SST snapshot (`5f1f3789…`, 54 files,
  SUBSTRATE-QUALIFIED posture unchanged), 2.61x bytes-only calibration.

Deliberate staging (no silent drift): `accept/` (8 files) and `vendor/`
(57 files) are byte-identical to r1; `REPORT.md` + `SUCCESSOR-REPORT.md`
carried byte-identical; all other `.py`/doc files differ by rebrand at
minimum (see CONSUMER-DELTA.md rebrand map + §4 of the record).

## 2. Consumer surface (unchanged shape, one added op)

- CLI: `release.py` (`init/run/explain-route/inspect/ops`, ops incl. NEW
  `ops recover`). All state via explicit `--state-dir`; nothing written
  elsewhere.
- Programmatic API (`api.py`): `init_run`, `open_run`, `run_tasks`,
  `fuse_op`, `fission_op`, `quarantine_op`, `revise_op`, `revoke_op`,
  `reuse_op`, `split_pair_op`, `settle_op`, `kill_resume_op`,
  NEW `recover_op`, `explain_route_op`, `inspect_state_op`.
- Setup/config/inputs/outputs/failure table/state layout/recovery
  procedure: `successor-003/CONSUMER.md` (authoritative for r2).

## 3. Acceptance criteria A1–A10 (builder run; independent lane follows)

Executed by the builder on fresh `/tmp` state through consumer interfaces.
Suites + calibrate run from byte-identical `/tmp` copies (they scratch
`.test-tmp/` in-tree); demo + CLI probes + snapshot checks execute the
FROZEN bytes directly with `/tmp` state (read-only use). Any FAIL stops
the release (report with evidence; do not patch the frozen tree, do not
weaken the criterion).

- **A1 identity/build**: `successor-003/IDENTITY.sha256` 45/45 OK;
  regenerated vendor snapshot manifest matches the frozen manifest;
  `sched_checker --self-check` OK; `SST_VENV_PY` pydantic == 2.13.5;
  system python3 version recorded.
- **A2 demo spine on fresh state**: `successor_demo.py --run-dir=/tmp/...`
  exit 0; S1/S2/S3 VALID 4/4 with r1-identical lanes+bytes
  (655/0, 310/500, 685/500); S4 5/5 via fused reuse; S6 4/4 via
  fission reuse; S3 resume 0 re-invokes + byte-identical pre-kill
  artifacts; SST leg champion_found $0; settle 5 markers 0 stranded;
  6 routing decisions; new EVIDENCE.json exact-fields match
  `accept/EXPECTED.json`.
- **A3 carried suites**: `test_conformance.py` 9/9 OK,
  `test_fission.py` 7/7 OK, `test_successor.py` 17/17 OK (incl. SST
  $0/MATCH legs) from a byte-identical copy (diff -r clean).
- **A4 atomicity**: `test_atomicity.py` 27/27 OK from a byte-identical
  copy (refusal proofs, kill-at-every-boundary matrices,
  kill-during-recovery, real SIGKILLs).
- **A5 sampled kill matrices through consumer CLI on fresh /tmp state**:
  settle kills (pre-first-append N=1, mid-batch, marker-without-lifecycle
  N=3/N=6 class), fuse kills (no-trace N=1, mid-transfer, post-entry
  pre-spec), fission kills (no-trace, mid-transfer with bare-recover
  refusal → partitioned recover, post-entry), ≥1 real SIGKILL landing,
  ≥1 kill-during-recovery convergence — every landing converges via
  consumer `ops recover` (+ fresh `ops settle`/op re-run where defined),
  conservation holds, 0 stranded, no silent partials, reuse serves
  after fuse recovery.
- **A6 calibrate 2.61x bytes-only**: `calibrate.py` from a byte-identical
  copy → S2-central 810 vs S2-local 310 = 2.61x; wording audit: every
  ratio mention stays bytes-scoped with an explicit
  no-token/attention/cost disclaimer.
- **A7 SST MATCH + refusal legs $0**: `verify_snapshot.py` MATCH
  (54 files, `5f1f3789…`); tamper-a-COPY refusal (loud identity error,
  exit 1, before any SST import); no `../sst` runtime references (grep);
  SST leg in A2 shows TEST-only gateway, champion_found, cost $0.0,
  pydantic 2.13.5; snapshot untouched by the run (pre/post MATCH).
- **A8 consumer coverage incl. ops recover + negative paths**: every CLI
  verb exercised on fresh /tmp state (`init/run/explain-route/inspect`,
  `ops fuse/fission/quarantine/revise/revoke/reuse/split-pair/
  kill-resume/settle/recover`) + `api.py` op coverage (incl.
  `recover_op`) + negative paths (refused invoke → ContractViolation +
  deny; bad preconditions → ValueError/RuntimeError/ContractViolation
  BEFORE mutation; CLI error → `release: error: …` exit 1).
- **A9 all frozen predecessors intact**: `successor-002/IDENTITY.sha256`
  41/41 OK; `successor-003/IDENTITY.sha256` 45/45 OK (before AND after);
  FROZEN-BASELINE over frozen paths OK (1 live-file line excepted per
  R1 note E); no writes outside `prototype/release-r2/` + `/tmp`
  (newer-than-marker check); `../sst` porcelain untouched-by-me.
- **A10 edge/negative behaviors**: wrong-partition recover refused
  (contradiction, never silent divergence); torn-ledger recover refused
  (disk-loss class); bare `ops recover` settles NOTHING by default;
  unsettled-terminal ledger rejected with the exact error; bad
  partition shapes (incomplete/unknown/outsider/one-sided) refused with
  zero partial effects; revoked/quarantined invoke denied with recorded
  deny; fission-args-without-partial refused; partial fission blocks
  composite settle until completed.

## 4. In-envelope bounds (carried from successor-003 LIMITS.md)

Toy scale (4–5 tasks/slots, one shared deterministic solver); single
machine + local disk, no multi-writer, no disk loss; one injected kill
per S3 run + kill-during-settle/fusion/fission covered (quarantine
transfer stays operator repair); bytes-only 2.61x (no token/cost
generality); single-host fusion/fission/quarantine; revocation =
authority-stamp flip + replayed ledger entry, capabilities fixed at
creation; SST TEST fixtures only, SUBSTRATE-QUALIFIED (no SST-owner
acceptance claimed); wall-clock `at` excluded from byte-identity;
no siloed balances/content-refs/relationship persistence, `retired`
unexercised, channels in-memory-only; no learning of any kind.
LIMITS-11 CLOSED (atomic settle); LIMITS-3 narrowed (kill-during-
settle/fusion/fission covered).

## 5. Out of scope (unchanged posture)

No U-branch / real-producer consumption claims (still blocked;
SUBSTRATE-QUALIFIED posture unchanged). No L/R/P experiment
re-verdicts. `CANONICAL-RECORD.md` + `REPRODUCE-ALL.md` are
coordinator-owned (not touched). Verdict levels per r1 plan:
ACCEPT (all PASS) / ACCEPT-WITH-NOTES (all PASS + record-only notes)
/ REJECT (any FAIL → report, builder fixes in a NEW tree, rerun).
