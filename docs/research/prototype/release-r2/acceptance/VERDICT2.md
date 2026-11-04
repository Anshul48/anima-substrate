# r2 independent acceptance verdict (lane) — ACCEPT-WITH-NOTES

Date: 2026-10-04. Lane: independent (read + execute only; all run
state in /tmp/r2ind, since cleaned; frozen/programme/release/
neighbor trees never written). Builder verdict assessed, never
trusted: own N/params, own EVIDENCE↔EXPECTED mapping, own probes.

## Verdict: ACCEPT-WITH-NOTES (record-only; r2 freezes)

All A1–A10 PASS on lane-observed evidence. Two LOW record-only
findings (F1 concurred; F2 new) + minor notes. No criterion failed;
nothing requires a new tree.

## Per-criterion evidence (lane-observed)

- A1 PASS: IDENTITY 45/45 OK; manifest regen to /tmp diff-clean
  (REGEN-MATCH, 54 files, 5f1f3789…); self-check rc=0; pydantic
  2.13.5; python 3.12.3.
- A2 PASS: demo rc=0; 655/0, 310/500, 685/500; S4 5/5; S6 4/4;
  resume skipped=3 re_executed=0 rc=-9 artifacts identical; SST
  champion_found $0.0; settle 5/0; 6 routing decisions; own mapping
  54/54 EXPECTED leaves PASS.
- A3 PASS: 9/9 + 7/7 + 17/17 from diff-r-verified copy, incl. SST
  legs, zero skips.
- A4 PASS + F2: 27/27 OK on run 3; runs 1–2 scored 26/27 on
  test_sigkill_fission (delay=0.2) — real SIGKILL in the worlds.json
  truncate window → loud disk-loss-class refusal (see F2).
- A5 PASS: own 67-check CLI matrix green (settle/fuse/fission N of
  lane's choosing + pre-spec + real SIGKILL + kill-during-recovery);
  every landing converged, conservation ok, 0 stranded, reuse serves
  after every fuse recovery.
- A6 PASS: 810 vs 310 = 2.61x reproduced; wording audit clean (all
  ratio mentions bytes-scoped; every token/attention hit a
  disclaimer; no cost-generality sentence).
- A7 PASS: MATCH 54/5f1f3789; tamper-a-COPY rc=1 naming file + drift
  pre-import; zero ../sst refs in *.py (own grep); TEST-only,
  champion_found, $0.0, pydantic 2.13.5, snapshot_unchanged; MATCH
  re-verified post-run.
- A8 PASS (28/28 corrected): 14 CLI verbs + 5 api.py calls +
  negatives (run-after-revoke durable rc=1, bogus-owner ValueError
  with reopen-marker-only growth + worlds.json byte-identical, CLI
  error shape rc=1). Lane's first revoke probe passed vacuously;
  caught, fixed to fresh-root S1, re-ran green (builder setup correct).
- A9 PASS: s003 45/45 + s002 41/41 before AND after; baseline 3639 +
  exactly the 1 live miss (CONTINUING-PROGRAMME.md, coordinator log,
  zero new drift); .test-tmp empty; no tracked mtimes newer than
  session start; MATCH post-run. Substitution stated: no git/sst
  visible in lane environment → vendor MATCH + manifest pin +
  baseline 1364 w1 lines substituted. COORDINATOR CLOSED THE GAP:
  ../sst porcelain 0 lines at df78f42, observed directly.
- A10 PASS (30/30): wrong-partition→correct, torn-ledger disk-loss,
  bare-recover-settles-nothing (lifecycles identical), ghost-ledger
  exact error + zero partials, bad partitions marker-only,
  revoked-invoke denied+recorded, recover --worlds blocked + one-call
  complete+settle.

## F1 judgment (independent; reproduced at N=8 and N=5)

Sequence confirmed exactly. (a) No breach: settle is
custody-orthogonal by construction (code + own baseline); no clause
promises settle-refusal on partial fission; EVIDENCE.md:174 is
overbroad prose (pinned recover path verified blocked). (b) Loud at
every step (quoted rcs/messages). (c) Repair real and exact:
transfer_custody → custodians byte-equal to clean-fission reference
across all 5 worlds; children serve split-pair + settle 5/0;
residual lineage-only (fission kinds 0, loudly). (d) Builder's LOW
record-only disposition CORRECT. (e) r2 record accurate (one
negligible imprecision: "the next recover" = the partitioned one).

## F2 (new, lane's; LOW, record-only)

Real SIGKILL in the worlds.json truncate window (0-byte file) →
`ops recover` rc=1 RuntimeError, loud, contractually classified
(disk-loss class, LIMITS-2). Reproduced in isolation (1/10 at 0.2s;
ledger intact 66/66). Root cause: non-atomic `_write_specs`
write_text; 0.2s ≈ op-tail on this box. Every deterministic test
green in all runs. Two parts: (i) narrow loud window (behavior,
LOW); (ii) frozen doc overclaim — INTERRUPTION-BOUNDARIES.md:29 /
EVIDENCE.md:160 "all landings converge" is false for this landing.
Successor fix: atomic spec writes (temp+rename) + test. No tree edit
(frozen); correction carried in r2 records + owned deferred.

## Minor notes (recorded)

- Doubled "settle refused: settle refused:" message cosmetics.
- `inspect` appends the standard host_reopen marker (documented
  every-command reopen; lane probes tripped twice before measuring).
- Unattributed __pycache__ burst in s003 (14 files) — regenerable,
  integrity-neutral. COORDINATOR: removed (rm -rf __pycache__);
  IDENTITY 45/45 re-verified after. Matches residue-cleanup
  precedent; pinned bytes untouched.
- Builder-attributed counts (§4) not re-audited by design; behaviors
  re-verified with own probes instead.
- `empty sst porcelain @ df78f42` unverifiable in lane environment;
  coordinator closed it (above).

## Over-claim spot-checks (all pass)

RELEASE-RECORD: all 14 §2 pins exact; accept/(8)+vendor/(57)+REPORT+
SUCCESSOR-REPORT byte-identical to successor-002; 60/60 composition
matches A3+A4 greens (F2 disclosed); df78f42 usage consistent with
vendor/PROVENANCE.md. CONSUMER-DELTA: atomic-settle zero-partials ✓;
SST_VENV_PY default + live loud abort ✓; bare-recover ✓; SET-duplicate
marker observed ✓; rebrand sampled ✓.

## Acceptance mapping (RELEASE-PLAN.md A1–A10)

A1–A10 PASS: yes. F1 severity judged (LOW record-only): yes. F2
filed (LOW record-only + successor fix owned): yes. Records accurate:
yes. Frozen intact: yes. Independently verified: yes (this file +
lane report in coordinator session log).

**r2 status: ACCEPTED. successor-003/ + release-r2/ FROZEN.**
r2 = R1 gains (atomic settle, interruption boundaries, ops recover)
as a usable release; r1 (successor-002 + release-20261004) remains
frozen and reproducible; r1→r2 consumer staging per CONSUMER-DELTA.md.
Owned deferreds: F2 successor fix (atomic spec writes), F1/F2 doc
precision in successor docs, quarantine-transfer operator repair,
multi-writer, disk-loss recovery, cross-host, U-branch (producers),
Q5 (user).
