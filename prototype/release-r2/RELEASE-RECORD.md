# r2 release record — substrate MiniHost hybrid r2 (2026-10-04, BUILDER-ACCEPT)

Release candidate: `prototype/successor-003/` (45 files, identity
below). Status: BUILDER-ACCEPT (all A1–A10 PASS + 1 low-severity
finding F1 recorded); independent acceptance lane follows — this
tree freezes only on the lane's verdict. No writes to the candidate
by this builder (read + execute only; suites ran from verified
byte-identical `/tmp` copies).

## 1. Requirement-by-requirement completion (r1 R1–R12 carried + R1 delta)

R1–R12 dispositions are CARRIED from the r1 record
(`prototype/release-20261004/RELEASE-RECORD.md` §1) and re-verified
on r2 evidence (this record §4); the R1 delta column names what R1
changed. No r1 requirement regressed.

| ID | Disposition | r2 evidence | R1 delta |
|---|---|---|---|
| R1 local responsibility | SATISFIED in envelope | O1–O5 + E1–E3 enforced (A2/A3/A8/A10: denials, void-by-ruling, giver-actor) | Unchanged |
| R2 heterogeneity | SATISFIED in envelope | LIST/SLOT + declared-loss + SST-search + independent checker (A2/A3/A7) | Unchanged |
| R3 revisability | SATISFIED in envelope | v1→v2 revision + revocation durable, re-propose VALID (A2/A8) | Unchanged |
| R4 repertoire | SATISFIED single-host | Fusion (3 transfers, 8→7) + reuse 5/5; fission + reuse 4/4; quarantine (A2/A3/A8) | Kill-during-fusion/fission covered (A4/A5) |
| R5 actual change | SATISFIED single-host | Transfers, lifecycle, mechanism removal/restore, durable revoke/revise (A2/A8) | Unchanged |
| R6 reuse + lineage | SATISFIED (reuse + lineage) | S4 via composite + S6 via split pair, lineage_ok (A2); reuse after fuse recovery (A5) | Recovered composites serve reuse |
| R7 adaptation | SATISFIED (authorized mechanisms) | S3 drill: revise→revoke→deny→ruling→void→re-propose→VALID (A2/A8 kill-resume) | Unchanged |
| R8 reduced central load | SATISFIED (conditional, calibrated) | 2.61x same-task central-bytes (810 vs 310), bytes-only wording audited (A6) | Unchanged (identical numbers) |
| R9 contracts | SATISFIED for this path | v1 C1–C7 + ORG-OPS OP-1–OP-6 + G1–G8, 9/9 conformance (A3) + R1 clauses (A4/A8/A10) | ORG-OPS/CONSUMER extended (atomicity, recover) |
| R10 integrated Linux path | SATISFIED (toy scale, 2 envs) | One ledger, scheduling + SST-search (df78f42 snapshot, TEST, champion_found, $0) (A2/A7) | Unchanged |
| R11 robustness | SATISFIED (declared paths, EXTENDED) | Kill resume rc=-9 0 re-invokes byte-identical; refusals; quarantine (A2/A3/A8) | Atomic settle + kill-during-settle/fusion/fission + ops recover (A4/A5/A10); LIMITS-11 CLOSED, LIMITS-3 narrowed to quarantine-transfer |
| R12 independent verification | BUILDER DONE, lane pending | Builder A1–A10 all PASS (this record §4); R1's own independent ACCEPT-WITH-NOTES stands beneath | Independent r2 lane follows (not this builder) |
| Q3 reuse | RESOLVED (carried) | Unmodified resume engine + v1 coupling clauses (A3/A5) | Unchanged |
| Q5 permanent host | OWNED FUTURE, non-blocking (carried) | Reversible Python lineage; no migration claimed | Unchanged |

R1 closes r1 LIMITS-11 (settle atomic on refusal — A4 refusal proofs
+ A8/A10 deny-only growth) and narrows r1 LIMITS-3 (one S3 kill →
kill-during-settle/fusion/fission covered; quarantine-transfer stays
operator repair — A4/A5/A10).

## 2. Frozen identity

`successor-003/IDENTITY.sha256` (45 files) + `vendor/
SNAPSHOT-MANIFEST.json` (54 files, `snapshot_hash`
`5f1f37893b0f5ab9ff7dcf0ce2c60b287b51647e2f18f627eabf5510537cad96`,
label SUBSTRATE-QUALIFIED, no SST-owner acceptance).
Key pins (sha256 short): minihost.py a2b7ed59, fusion.py 6e70fe47,
resume.py 2cd99df7, routing.py 36dd4833, recover.py 9c013ee5 (NEW),
release.py e4d50ac1, api.py c52da8ff, sst_leg.py 913fd1c1,
test_atomicity.py 770fa1ef (NEW), ORG-OPS.md 2f089831,
CONSUMER.md 98ef59d6, LIMITS.md 5985a8d4,
INTERRUPTION-BOUNDARIES.md 18500eaa (NEW), EVIDENCE.md 991ea380.
Verify: `cd successor-003 && sha256sum -c IDENTITY.sha256`
(45/45 OK before AND after the builder run).
Deliberate staging: `accept/` (8/8) + `vendor/` (57/57) +
`REPORT.md` + `SUCCESSOR-REPORT.md` byte-identical to r1 (verified
by `cmp`/`diff -r`); all other `.py`/docs differ by rebrand at
minimum (rebrand map: CONSUMER-DELTA.md; r1 pins for comparison:
minihost d01049a9, fusion 07a76251, resume 6fa71154, routing
f158ddac, release 32f817a9, api 0465f5c7, sst_leg ff7de2b7,
ORG-OPS 231439bc).

## 3. Reproduction

`REPRODUCE-ALL.md` §r2 (coordinator-owned) + `successor-003/
REPRODUCE.md` + `CONSUMER.md`. Tested env: WSL2 Ubuntu, system
python3 3.12.3, w1/.venv python + pydantic 2.13.5 (SST leg only).
$0, offline. Builder rhythm (frozen-safe): suites + calibrate from
byte-identical `/tmp` copies (`diff -r` clean); demo with
`--run-dir=/tmp/...`; CLI probes with `--state-dir /tmp/...`;
`PYTHONDONTWRITEBYTECODE=1` throughout. Expected: 60/60 tests
(17+7+9+27), demo exit 0, calibrate 2.61x, snapshot MATCH or loud
refusal, probes all PASS (counts in §4).

## 4. Acceptance evidence (attribution-separated)

- R1 beneath: builder 60/60 + demo + calibrate (EVIDENCE.md) +
  independent R1 ACCEPT-WITH-NOTES, notes A–E record-only
  (`programme-20261004/R1-VERIFICATION.md`).
- r2 builder (this lane): A1 identity 45/45 + regen MATCH +
  self-check OK; A2 demo exit 0 + 56/56 exact fields; A3 9/9+7/7+
  17/17 EXIT=0; A4 27/27 EXIT=0; A5 119/119 sampled kill landings;
  A6 2.61x + 10-mention wording audit clean; A7 MATCH + tamper-COPY
  refusal rc=1 + zero `../sst` refs + TEST/champion/$0 leg; A8
  31/31 consumer paths; A9 45/45 + 41/41 + baseline 3639 + 1
  expected live miss + clean `.test-tmp` + empty sst porcelain @
  df78f42; A10 26/26 edge/negative. Logs:
  `prototype/release-r2/acceptance/logs/`; verdict:
  `acceptance/VERDICT.md`. Preserved non-verdict attempts: 2 A8
  probe-bug runs + 1 A10 over-strict run (led to F1).
- Finding F1 (LOW, not blocking, lane judges): direct `ops settle`
  on a partial-fission composite succeeds (custody-orthogonal per
  longstanding contract, verified on baseline) and strands custody;
  next recover refuses loudly; custody operator-transferable to
  exactness but the `fission` entry stays unappendable (loud).
  Off-procedure (CONSUMER §6 mandates recover after a kill), loud
  throughout, no contract clause promises otherwise. Suggested
  disposition: record-only doc clarification (see
  `acceptance/logs/A10-F1-sharp-edge.md`); no frozen-tree edit.
- r2 independent lane: pending (runs after this builder).

## 5. Known limits (carried from successor-003 LIMITS.md)

Toy scale + shared deterministic solver; single machine/disk, no
multi-writer, no disk loss; kill-during-settle/fusion/fission
covered, quarantine-transfer operator repair; bytes-only 2.61x (no
token/cost generality); single-host fusion/fission/quarantine;
revocation = stamp flip + replayed entry, capabilities fixed at
creation; SST TEST-only, SUBSTRATE-QUALIFIED (no SST-owner
acceptance); wall-clock `at` excluded from byte-identity; no
siloed balances/content-refs/relationship persistence, `retired`
unexercised, channels in-memory-only; no learning of any kind.
Delta vs r1: LIMITS-11 CLOSED, LIMITS-3 narrowed (see §1).

## 6. Deferred obligations (owned, carried + steady)

| Obligation | Owner/status |
|---|---|
| SST clean landing consumed | SST owner (df78f42 LANDED; snapshot already re-based to it) — deliberate pin advance when asked |
| SST-owner release acceptance of snapshot vehicle | SST owner (evidence request stands); label stays SUBSTRATE-QUALIFIED |
| Live-model SST qual | SST owner (keys/budget) |
| Quarantine-transfer automation, multi-writer, disk-loss, cross-host, policy/recipe learning, scale | Substrate future (each needs its scoped plan; authorized work NOT blocked) |
| Permanent host Q5 | User judgment + substrate evidence (packet before any migration) |
| STC-backend stretch, TRACE participation, U-branch real use | Respective owners; U-branch stays BLOCKED (no producer qualified release; P1 asks filed) |
| F1 doc clarification | Coordinator/lane disposition (record-only; no behavior change) |

## 7. r1→r2 upgrade note for consumers

- What changed (behavior): settle refuses atomically (zero partial
  dissolves/returns, deny-only growth); kill-during-settle/fusion/
  fission is defined with `ops recover` completion (idempotent,
  kill-during-recovery converges); new `ops recover` /
  `api.recover_op` (+ documented operator-repair refusals); one
  fail-closed-earlier extension (single-world settle pre-validates).
- What stayed byte-identical: `accept/` inputs + EXPECTED, all of
  `vendor/` (snapshot bytes + manifest + hash `5f1f3789…`),
  `REPORT.md`, `SUCCESSOR-REPORT.md`; demo metrics + 2.61x numbers
  identical; SST posture unchanged (SUBSTRATE-QUALIFIED, $0, TEST,
  pydantic 2.13.5, `SST_VENV_PY` default `prototype/w1/.venv`).
- Rebrand map: every other file carries the successor-002→
  successor-003 path/docstring rebrand (behavior-neutral except the
  R1 items above + `check_settleable`/pre-validation/crash hooks in
  minihost + atomic `finish_worlds` in routing + settleability
  pre-checks in fusion + `recover_op`/pre-spec points in api +
  `ops recover` in release.py).
- Consumer action: none required for clean paths (same CLI/API
  shapes + one added op); after any kill during settle/fusion/
  fission, run `ops recover` per CONSUMER.md §6 (never `ops settle`
  a composite with a partial fission — see F1); keep
  `PYTHONDONTWRITEBYTECODE=1` and explicit `--state-dir`s.

## Independent acceptance (lane) — ACCEPT-WITH-NOTES, r2 FROZEN

Date: 2026-10-04. Full record: `acceptance/VERDICT2.md` (this section
is the coordinator's append; builder bytes above untouched).

- Lane verdict: A1–A10 all PASS on lane-observed fresh-state evidence
  (own N/params/mappings/probes). r2 ACCEPTED; successor-003/ +
  release-r2/ FROZEN as-verified.
- F1: lane reproduced at N=8 and N=5, concurs LOW record-only (no
  clause breach; loud; repair byte-exact across all 5 worlds;
  residual lineage-only; record accurate). Disposition stands.
- F2 (new, lane's; LOW record-only): SIGKILL in the worlds.json
  truncate window → 0-byte specs → loud disk-loss-class refusal
  (contractually classified, LIMITS-2). Root cause: non-atomic
  `_write_specs`. Two corrections carried here (frozen docs cannot
  be edited): (i) "all landings converge" (successor-003
  INTERRUPTION-BOUNDARIES.md:29 / EVIDENCE.md:160) is FALSE for a
  torn-specs landing — the honest statement is "all ledger-prefix
  landings converge; torn side-files refuse loudly as disk-loss";
  (ii) EVIDENCE.md:174 "partial fission blocks settle of its
  composite" names the wrong path — the pinned behavior is
  `recover --worlds COMPOSITE` refuses (direct `ops settle` remains
  custody-orthogonal by contract; see F1). Successor fix owned: atomic
  spec writes (temp+rename) + regression test + doc precision (R3).
- A9 substitution closed by coordinator: ../sst porcelain 0 lines at
  df78f42, observed directly (lane environment lacked git/sst).
- Residue: unattributed __pycache__ in successor-003/ removed by
  coordinator (regenerable, integrity-neutral); IDENTITY 45/45
  re-verified after.
