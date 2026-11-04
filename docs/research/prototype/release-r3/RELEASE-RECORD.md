# r3 release record — substrate MiniHost hybrid r3 (2026-10-04, BUILDER-ACCEPT)

Release candidate: `prototype/successor-004/` (45 files, identity
below). Status: BUILDER-ACCEPT (all A1–A10 PASS, no new findings);
independent acceptance lane follows — this tree freezes only on the
lane's verdict. No content changes to the candidate by this builder
(read + execute only; suites ran from verified byte-identical `/tmp`
copies; two content-neutral file events disclosed in §4/A9).

## 1. Requirement-by-requirement completion (r2 R1–R12 carried + R3 delta)

R1–R12 dispositions are CARRIED from the r2 record
(`prototype/release-r2/RELEASE-RECORD.md` §1, lane-ACCEPTED) and
re-verified on r3 evidence (this record §4); the R3 delta column names
what R3 changed. No r2 requirement regressed.

| ID | Disposition | r3 evidence | R3 delta |
|---|---|---|---|
| R1 local responsibility | SATISFIED in envelope | O1–O5 + E1–E3 enforced (A2/A3/A8/A10: denials, void-by-ruling, giver-actor) | Unchanged |
| R2 heterogeneity | SATISFIED in envelope | LIST/SLOT + declared-loss + SST-search + independent checker (A2/A3/A7) | Unchanged |
| R3 revisability | SATISFIED in envelope | v1→v2 revision + revocation durable, re-propose VALID (A2/A8) | Unchanged |
| R4 repertoire | SATISFIED single-host | Fusion (3 transfers, 8→7) + reuse 5/5; fission + reuse 4/4; quarantine (A2/A3/A8) | Kill landings now old-or-new on side files (A4/A5) |
| R5 actual change | SATISFIED single-host | Transfers, lifecycle, mechanism removal/restore, durable revoke/revise (A2/A8) | Unchanged |
| R6 reuse + lineage | SATISFIED (reuse + lineage) | S4 via composite + S6 via split pair, lineage_ok (A2); reuse after fuse recovery (A5, incl. mid-side-write) | Recovered composites serve reuse after interior crashes |
| R7 adaptation | SATISFIED (authorized mechanisms) | S3 drill: revise→revoke→deny→ruling→void→re-propose→VALID (A2/A8 kill-resume) | Unchanged |
| R8 reduced central load | SATISFIED (conditional, calibrated) | 2.61x same-task central-bytes (810 vs 310), bytes-only wording audited (A6) | Unchanged (identical numbers) |
| R9 contracts | SATISFIED for this path | v1 C1–C7 + ORG-OPS OP-1–OP-6 + G1–G8, 9/9 conformance (A3) + R1/R3 clauses (A4/A8/A10) | ORG-OPS/CONSUMER extended (atomic side writes, checkpoint classification) |
| R10 integrated Linux path | SATISFIED (toy scale, 2 envs) | One ledger, scheduling + SST-search (df78f42 snapshot, TEST, champion_found, $0) (A2/A7) | Unchanged |
| R11 robustness | SATISFIED (declared paths, EXTENDED) | Kill resume rc=-9 0 re-invokes byte-identical; refusals; quarantine (A2/A3/A8) | F2 window CLOSED (atomic side writes); ledger no-tear claim withdrawn with tested loud landing; process/power separated (A4/A5/A6/A10); LIMITS-2 narrowed (side-file half) |
| R12 independent verification | BUILDER DONE, lane pending | Builder A1–A10 all PASS (this record §4); R3's own independent ACCEPT-WITH-NOTES stands beneath | Independent r3 lane follows (not this builder) |
| Q3 reuse | RESOLVED (carried) | Unmodified resume engine + v1 coupling clauses (A3/A5) | Unchanged |
| Q5 permanent host | OWNED FUTURE, non-blocking (carried) | Reversible Python lineage; no migration claimed | Unchanged |

R3 closes r2 finding F2 (atomic spec/side writes — A4 construction +
50-kill loop + A5 mid-side-write legs), withdraws the ledger no-tear
claim with a tested loud landing (A5 mid-append + A10 torn legs),
separates process-crash atomicity from power-loss durability in every
guarantee sentence (A6 audit; N1/N2 narrowings owned), and keeps F1
documented (INTERRUPTION-BOUNDARIES.md §5 F1 WARNING; A10 F1 legs).

## 2. Frozen identity

`successor-004/IDENTITY.sha256` (45 files) + `vendor/
SNAPSHOT-MANIFEST.json` (54 files, `snapshot_hash`
`5f1f37893b0f5ab9ff7dcf0ce2c60b287b51647e2f18f627eabf5510537cad96`,
label SUBSTRATE-QUALIFIED, no SST-owner acceptance).
Key pins (sha256 short): minihost.py 8551ed92, fusion.py a2211a5d,
resume.py f07111cd, routing.py db4074e1, recover.py 5cce4e44,
release.py 6a42c4b3, api.py 66ccfc4d, sst_leg.py 24d03c27,
test_atomicity.py aad3d037, ORG-OPS.md 78367329,
CONSUMER.md cc24fe61, LIMITS.md 4f7f5712,
INTERRUPTION-BOUNDARIES.md 533434f7, EVIDENCE.md 84ca80ae.
Verify: `cd successor-004 && sha256sum -c IDENTITY.sha256`
(45/45 OK before AND after the builder run).
Deliberate staging: `accept/` (8/8) + `vendor/` (57/57) +
`REPORT.md` + `SUCCESSOR-REPORT.md` byte-identical to r2 (verified
by `cmp`/`diff -r`); all other `.py`/docs differ by rebrand at
minimum (rebrand map: CONSUMER-DELTA.md; r2 pins for comparison:
minihost a2b7ed59, fusion 6e70fe47, resume 2cd99df7, routing
36dd4833, recover 9c013ee5, release e4d50ac1, api c52da8ff, sst_leg
913fd1c1, test_atomicity 770fa1ef, ORG-OPS 2f089831, CONSUMER
98ef59d6, LIMITS 5985a8d4, INTERRUPTION-BOUNDARIES 18500eaa,
EVIDENCE 991ea380).

## 3. Reproduction

`REPRODUCE-ALL.md` §r3 (coordinator-owned, when written) +
`successor-004/REPRODUCE.md` + `CONSUMER.md`. Tested env: WSL2
Ubuntu, system python3 3.12.3, w1/.venv python + pydantic 2.13.5
(SST leg only). $0, offline. Builder rhythm (frozen-safe): suites +
calibrate from byte-identical `/tmp` copies (`diff -r` clean); demo
with `--run-dir=/tmp/...`; CLI probes with `--state-dir /tmp/...`;
`PYTHONDONTWRITEBYTECODE=1` throughout. Expected: 72/72 tests
(17+7+9+39), demo exit 0, calibrate 2.61x, snapshot MATCH or loud
refusal, probes all PASS (counts in §4).

## 4. Acceptance evidence (attribution-separated)

- R3 beneath: builder 72/72 (39 atomicity incl. 11 new + 50-kill
  loop) + demo + calibrate (EVIDENCE.md) + independent R3
  ACCEPT-WITH-NOTES, notes N1–N3 record-only
  (`prototype/programme-20261004/R3-VERIFICATION.md`).
- r3 builder (this lane): A1 identity 45/45 + regen MATCH +
  self-check OK; A2 demo exit 0 + 56/56 exact fields; A3 9/9+7/7+
  17/17 EXIT=0; A4 39/39 EXIT=0 (50 SIGKILLs, 0 torn); A5 135/135
  sampled kill + mid-write landings; A6 2.61x + ratio/durability
  wording audits clean; A7 MATCH + tamper-COPY refusal rc=1 + zero
  `../sst` refs + TEST/champion/$0 leg; A8 31/31 consumer paths; A9
  45/45 + 45/45 + 41/41 + baseline 4140 + 1 expected live miss +
  clean residue + empty sst porcelain @ df78f42; A10 38/38
  edge/negative + F1 + N1/N2. Logs:
  `prototype/release-r3/acceptance/logs/`; verdict:
  `acceptance/VERDICT.md`. Preserved non-verdict attempts: 1 A7
  probe-bug run (read-only COPY perms; fixed with chmod on the copy).
- Builder file-event disclosures (content-neutral, no waivers): (1)
  `make_snapshot_manifest.py` run without argv rewrote in-tree
  `vendor/SNAPSHOT-MANIFEST.json` byte-identically (sha `e5d8bb0a`
  == IDENTITY pin; 45/45 re-verified; mtime-only effect visible in
  the A9 sweep); (2) one `--help` call without the bytecode export
  created `successor-004/__pycache__/` (2 files), removed by the
  builder, 45/45 re-verified after (matches r2 residue-cleanup
  precedent; pinned bytes untouched).
- F1 (r2 LOW record-only, re-verified on s004): direct `ops settle`
  on a partial-fission composite succeeds (custody-orthogonal per
  longstanding contract) and strands custody; partitioned recover
  refuses loudly ("still holds custody"). Off-procedure (CONSUMER §6
  mandates recover after a kill), loud throughout, now documented
  in-tree (INTERRUPTION-BOUNDARIES.md §5 F1 WARNING). Disposition
  stands: record-only.
- N1/N2 (R3 record-only, confirmed as disclosed): resume.py:70
  fail-safe skip vs CONSUMER.md:93 universal (N1); four "durable"
  wordings without inline no-fsync disclaimer (N2: api.py:271,
  resume.py:14/158, SUCCESSOR-REPORT.md:181), all ledger-replay-
  scoped and tree-level-covered by LIMITS-2. No widening observed.
  Owned for the next docs pass; no frozen-tree edit.
- r3 independent lane: pending (runs after this builder).

## 5. Known limits (carried from successor-004 LIMITS.md)

Toy scale + shared deterministic solver; single machine/disk, no
multi-writer, no disk loss; PROCESS-CRASH ONLY — no fsync issued,
power/media loss is the disk-loss class; kill-during-settle/fusion/
fission covered, quarantine-transfer operator repair; side files
old-or-new on op paths (temp+`os.replace`); LEDGER append interior
explicitly NOT covered (torn tail → loud disk-loss refusal, tested);
bytes-only 2.61x (no token/cost generality); single-host
fusion/fission/quarantine; revocation = stamp flip + replayed entry,
capabilities fixed at creation; SST TEST-only, SUBSTRATE-QUALIFIED
(no SST-owner acceptance); wall-clock `at` excluded from
byte-identity; no siloed balances/content-refs/relationship
persistence, `retired` unexercised, channels in-memory-only; no
learning of any kind. Delta vs r2: LIMITS-2 narrowed (side-file
kill-tear closed; ledger half withdrawn from the claim).

## 6. Deferred obligations (owned, carried + steady)

| Obligation | Owner/status |
|---|---|
| SST clean landing consumed | SST owner (df78f42 LANDED; snapshot already re-based to it) — deliberate pin advance when asked |
| SST-owner release acceptance of snapshot vehicle | SST owner (evidence request stands); label stays SUBSTRATE-QUALIFIED |
| Live-model SST qual | SST owner (keys/budget) |
| N1/N2 wording narrowings | Next successor/docs pass (frozen tree untouched; disclosures in this record §4 + A6/A10 logs) |
| Quarantine-transfer automation, multi-writer, disk-loss, cross-host, policy/recipe learning, scale | Substrate future (each needs its scoped plan; authorized work NOT blocked) |
| Permanent host Q5 | User judgment + substrate evidence (packet before any migration) |
| STC-backend stretch, TRACE participation, U-branch real use | Respective owners; U-branch stays BLOCKED (no producer qualified release; P1 asks filed; blocked behind I1–I6) |
| F1 doc precision | DONE in-tree (INTERRUPTION-BOUNDARIES.md §5 F1 WARNING); record-only standing |

## 7. r2→r3 upgrade note for consumers

- What changed (behavior): every whole-file side write is crash-
  atomic (temp+`os.replace`): a kill leaves `worlds.json`/artifacts/
  checkpoints old-or-new, never torn (F2 closed); genuinely torn
  files (media loss/hand-edit) and torn ledger tails refuse loudly
  as disk-loss (tested); one fail-closed-earlier extension —
  `reattach` on an unreadable checkpoint refuses classified
  (`ContractViolation` "unreadable … disk-loss", deny recorded,
  stays suspended); `<name>.tmp-<pid>` orphans may appear after a
  kill (never read; safe to delete).
- What stayed byte-identical: `accept/` inputs + EXPECTED, all of
  `vendor/` (snapshot bytes + manifest + hash `5f1f3789…`),
  `REPORT.md`, `SUCCESSOR-REPORT.md`; demo metrics + 2.61x numbers
  identical; SST posture unchanged (SUBSTRATE-QUALIFIED, $0, TEST,
  pydantic 2.13.5, `SST_VENV_PY` default `prototype/w1/.venv`).
- Rebrand map: every other file carries the successor-003→
  successor-004 path/docstring rebrand (behavior-neutral except the
  R3 items above: `atomic_write_text` in minihost + routing of all
  side writes through it in api/fusion/resume/routing/recover/
  release/make_snapshot_manifest + `SUBSTRATE_CRASH_MID_APPEND` /
  `SUBSTRATE_CRASH_MID_SIDE_WRITE` hooks + checkpoint
  classification in `reattach`/`check_settleable`).
- Consumer action: none required for clean paths (same CLI/API
  shapes, no new verbs); after any kill, run `ops recover` per
  CONSUMER.md §6 (unchanged); a `<name>.tmp-<pid>` file next to a
  side file is a benign replace orphan — ignore or delete it, never
  hand-edit the ledger or specs; keep `PYTHONDONTWRITEBYTECODE=1`
  and explicit `--state-dir`s.

## Independent acceptance (lane) — ACCEPT-WITH-NOTES, r3 FROZEN

Date: 2026-10-04. Full record: `acceptance/VERDICT2.md` (this section
is the coordinator's append; builder bytes above untouched).

- Lane verdict: A1–A10 all PASS on lane-observed fresh-state evidence
  (own N/params/mappings/probes incl. 61/61 own accept mapping, full
  39/39 loop, 45 own aimed in-window kills with 0 torn). r3 ACCEPTED;
  successor-004/ + release-r3/ FROZEN as-verified.
- Coordinator's weak-leg note on the builder's 43/50 completed loop:
  CLOSED by the lane (8 in-window suite landings + 45 aimed kills,
  0 torn, all classes covered).
- Two record-only notes: accept/README stale successor-002/8-8 refs
  (pre-existing, frozen by policy); lane's own export-less probe
  with verified zero effect. No new product findings.
- ../sst porcelain 0 @df78f42 checked by the lane directly (visible
  in its environment); no substitution needed.
