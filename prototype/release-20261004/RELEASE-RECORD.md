# Linux release record — substrate MiniHost hybrid r1 (2026-10-04, FROZEN)

Release candidate: `prototype/successor-002/` (41 files, identity below).
Status: FROZEN after independent acceptance round 2
(ACCEPT-WITH-NOTES, all notes fixed + coordinator-confirmed).
No further writes to this directory.

## 1. Requirement-by-requirement completion (R1–R12 + Q3/Q5)

| ID | Disposition | Evidence |
|---|---|---|
| R1 local responsibility | SATISFIED in envelope | Obligations O1–O5 + E1–E3 enforced structurally (H-guard refusal, void-by-ruling-only, giver-actor transfers); worlds self-solve/verify. Policy invention → deferred E4-adjacent |
| R2 heterogeneity | SATISFIED in envelope | LIST/SLOT representations + declared-loss adapters + SST-search op family + independent checker. Learned mappings/evaluators → deferred (scoped plans) |
| R3 revisability | SATISFIED in envelope | Versioned adapters, revision/revocation with rulings, durable across reopen. Learned revision → deferred E3-adjacent |
| R4 repertoire | SATISFIED single-host | Fusion (lineage + 3 transfers + channel removal 8→7) + reuse 5/5; fission (partition + back-transfer + lineage + channel restore) + reuse 4/4; quarantine separation path. Cross-host → deferred (multi-host design) |
| R5 actual change | SATISFIED single-host | Transfers, lifecycle moves, mechanism removal/restore, durable revocation/revision, commitment transfer |
| R6 reuse + lineage | SATISFIED (reuse + lineage) | S4 via fused composite + S6 via split pair, derived_from + fusion/fission entries, lineage_ok. Recipe inheritance → deferred E3-adjacent |
| R7 adaptation | SATISFIED (authorized mechanisms) | v1→v2 revision + revocation → escalation → ruling → void → re-propose → VALID. Autonomous discovery → B-frontier deferred |
| R8 reduced central load | SATISFIED (conditional, calibrated) | Hybrid routing (local iff ≥2 rounds AND split); measured 2.61x same-task central-bytes ratio (810 vs 310 canonical-JSON bytes, S2 envelope). No token/attention/cost equivalence claimed |
| R9 contracts | SATISFIED for this path | WORLD-CONTRACT-v1 C1–C7 + ORG-OPS OP-1–OP-6 + G1–G8 mapping, all conformance-tested (9/9) |
| R10 integrated Linux path | SATISFIED (toy scale, 2 envs) | One ledger, scheduling env + SST-search env (df78f42 snapshot, TEST, champion_found, $0) |
| R11 robustness | SATISFIED (declared paths) | Kill resume rc=-9, 0 re-invokes, byte-identical; revision/revocation/ruling; 5+ refusal shapes; quarantine. Kill-during-settle/fusion, disk loss, multi-writer → deferred per LIMITS |
| R12 independent verification | SATISFIED | Round 1 (REJECT: 1 FAIL + 7 notes, all fixed) + round 2 (ACCEPT-WITH-NOTES, 3 record notes fixed + confirmed), all through consumer paths on fresh state |
| Q3 reuse | RESOLVED | Unmodified resume engine on separate host + v1 coupling clauses |
| Q5 permanent host | OWNED FUTURE, non-blocking | Python lineage is the reversible working path; migration needs user-facing evidence + alternatives first |

## 2. Frozen identity

`successor-002/IDENTITY.sha256` (41 files) + `vendor/SNAPSHOT-MANIFEST.json`
(54 files, `snapshot_hash`
`5f1f37893b0f5ab9ff7dcf0ce2c60b287b51647e2f18f627eabf5510537cad96`).
Key pins: minihost.py d01049a9 (4th identical copy), fusion.py 07a76251,
resume.py 6fa71154 (OP-4 fix), sst_leg.py ff7de2b7, release.py 32f817a9,
api.py 0465f5c7, ORG-OPS.md 231439bc. Verify:
`cd successor-002 && sha256sum -c IDENTITY.sha256` (41/41 OK at freeze).

## 3. Reproduction

`REPRODUCE-ALL.md` §4 + `successor-002/REPRODUCE.md` + `CONSUMER.md`.
Tested env: WSL2 Ubuntu (`6.6.87.2-microsoft-standard-WSL2`), system
python3 3.12.3, w1/.venv python 3.12.3 + pydantic 2.13.5 (SST leg
only). $0, offline. Suites 33/33 (17+7+9), demo exit 0, calibrate
2.61x, snapshot MATCH or loud refusal.

## 4. Acceptance evidence (attribution-separated)

- Builder: 33/33 suites + demo + calibrate + CLI smoke (REPORT.md).
- Coordinator: OP-4 CLI retest (bogus→ValueError rc=1, valid→rc=0),
  worked-check verbatim (54 + hash = manifest), 9/9 conformance rerun,
  IDENTITY + baseline re-verification.
- Independent round 1: `acceptance/VERDICT.md` (REJECT, A1–A9 PASS,
  A10 FAIL OP-4 + 7 notes) + 37 logs + own tools.
- Independent round 2: `acceptance/round2/VERDICT2.md`
  (ACCEPT-WITH-NOTES: A10 8/8, A8 incl. rebase challenge PASS,
  A1/A6/A9 spots identical) + logs. N1–N3 record notes fixed by the
  coordinator after the verdict (docs + 2 docstrings, zero behavior
  change) and confirmed as above; no verifier rerun needed per the
  plan's ACCEPT-WITH-NOTES rule.
- Preserved failures: round-1 REJECT + OP-4 gap, withdrawn staging
  pin + drift, superseded cand-02 snapshot (hash retained in
  vendor/PROVENANCE.md history).

## 5. Known limits (see LIMITS.md, 11 items)

Toy scale, single machine/host, one kill boundary, bytes-only
calibration, TEST fixtures only, wall-clock timestamps excluded,
v1 non-goals carried, no learning of any kind, settle not atomic
on refusal.

## 6. Deferred obligations (owned)

| Obligation | Owner/status | Acceptance action when available |
|---|---|---|
| SST clean landing consumed | SST owner (df78f42 LANDED 2026-10-04; snapshot already re-based to it) | Deliberate pin advance: copy new bytes, regenerate manifest, re-qualify, accept |
| SST-owner release acceptance of snapshot vehicle | SST owner (evidence request stands) | Owner confirms; label updates |
| Live-model SST qual | SST owner (keys/budget) | Live caller qual on pinned bytes |
| Fission/cross-host, policy/recipe learning, scale, multi-writer, disk-loss, kill-during-settle | Substrate future (each needs its scoped plan; routine authorized work is NOT blocked — the phrase "newly scoped research" gates nothing already authorized) | Scoped plan → build → accept |
| Permanent host Q5 | User judgment + substrate evidence | Evidence + alternatives packet before any migration |
| STC-backend stretch, TRACE participation | Respective owners | Owner tracks |

Longer-horizon canvas (B-frontier discovery, D co-design) stays
visible in CANONICAL-RECORD.md; nothing in this release claims it.
