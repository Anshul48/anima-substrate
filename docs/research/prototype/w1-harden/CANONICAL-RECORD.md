# SUBSTRATE / EXPERIMENTS — Canonical Record (PROMOTED 2026-10-04)

Home: `substrate/prototype/w1-harden/CANONICAL-RECORD.md` (frozen artifact).
Supersedes: `/tmp/substrate-canonical-001/CANONICAL-RECORD.md` (staging draft).
Scope: TEST/stub/toy, $0, offline. No live-model, learning, or generality claims.
Labels: USER-DIRECT / ACCEPTED (D-xxx) / PROPOSAL / OBSERVED / REPRODUCED.

## 1. Objective (USER-DIRECT + D-004/D-006/D-008)

Shape a computational substrate hosting worlds: nested cooperating
organizations, local responsibility, revisable boundaries, integration /
assimilation / fusion / fission, coalitions, composites, inheritance, and
actual changes to state, ownership, responsibility, lifecycle, machinery.
Priority map A → C → B → D (knowledge → schemas/ops → capability discovery
→ co-design), overlapping, not gated. A2/biology/model passages = hypotheses.

## 2. Candidate identities (frozen pins)

- W1 prototype `substrate/prototype/w1/` (sha256-short, verified repeatedly,
  last 2026-10-04; `substrate/` is NOT a git repo so this list is the anchor):
  HOST.py eb61a5d9cebc, contract.py 2d5bc5bb9db3, demo_T.py 933d2c9a58df,
  relationship.py b02d81a1282a, test_w1.py 4893929d3a8b,
  world_construct.py 91225a057b0c, world_explore.py 05c2b564bcfe.
  Full hashes: `w1-harden/FREEZE.w1`. Untouched by this track throughout.
- w1-harden (this artifact): 20 files under `substrate/prototype/w1-harden/`
  (`__init__`, contract, HOST, relationship, world_construct, world_explore,
  demo_T, recovery_lib, recovery_exercise, test_w1_harden, test_failures,
  test_recovery, FREEZE.w1, FREEZE.json, RUN-REPORT.md, RECOVERY-REUSE.md,
  LIMITS.md, VERIFICATION.md, REPRODUCE.md, CANONICAL-RECORD.md).
- SST: HEAD 079f4de6fd43881c2f1b529f0612f1df64a62f32, DIRTY (38 porcelain
  lines at freeze: 19 modified + 19 untracked, peer WIP). Frozen
  dirty-with-hashes: full HEAD + porcelain + 14 module sha256 in FREEZE.json.
  No clean ANIMA pin selected (SST owner's job). Historical M1 pin
  INT-2026-09-13.2 only.
- DSH: 639ed015397290b3745d163aafe02ffee4aa3f84 (label 639ed01, v0.2.0-rc.2),
  rev-parse VERIFIED in /tmp/dsh-upstream; worktree peer-volatile (clean →
  1 untracked → clean across freeze/verify/re-check); anchor-only.
- STC bundle: @stc/dsh-plugin-stc 0.1.0, `stc-bundle`, lib/ built Sep 29.
  STC HEAD 851e4a4b9072f203d18ed4fb33987cdd21d6a084, DIRTY. No STC-backend
  stretch in this track.
- H0 baseline: /tmp/substrate-h0-001/h0_run.py (8b0e9f6b6b54e) — /tmp-only,
  not promoted (numbers quoted in RUN-REPORT X2, verified vs run.log).
- Engines: stub-deterministic-v1 (primary) / sst-controller-v0 (TEST-only,
  `test://local`, $0). Interpreters: system python3 3.12.3, w1/.venv 3.12.3
  (read-only use; venv holds 55 site-packages entries — corrected per N3).

## 3. Evidence (REPRODUCED; builder + independent verifier + coordinator)

- S1 W1 repro: 19/19; demo_T exit 0 stub + SST-controller ($0, 150 scripted
  tokens); 36-entry ledgers; conservation + 1 denial + v1 pin + custody
  transfer/retire + composite.solve. (/tmp/substrate-w1-repro-001/)
- S2 H0: exit 0, deterministic; 2360 context bytes, 15 invocations, mapping
  edit 1/6, T3 reuse 0/3, ad-hoc recovery. (/tmp/substrate-h0-001/)
- X1 (negotiation vs central): H1b SUPPORTED. Correctness ties 3/3 probes;
  central wins bytes (573<1105, 589<1184, 3457<5414) + effort (117<168).
  Host wins recovery only. (/tmp/substrate-x12-001/X1-PREREG.md,
  /tmp/substrate-x1-001/RESULT.md)
- X2 (composites vs fixed+tooling): H2b SUPPORTED. Ties on fresh task,
  exception correctness, threshold change (old verdicts byte-identical);
  fixed wins effort (210<354) + bytes (6.8K<11.5K); composite wins recovery
  (3/3 resume vs fail-with-note) + E1 rework (2 vs 7). One SST-TEST check
  PASS. (/tmp/substrate-x12-001/X2-PREREG.md, /tmp/substrate-x2-001/RESULT.md)
- X1G (generality probe, frozen X1 arms): gap REAL. Novel conflicts A 2/2
  vs B 0/2 loud CRASH; novel versions both 2/2 deny. No deviations.
  (/tmp/substrate-x1g-001/)
- X1H (central-generalization spike): GAP-CLOSED-CHEAPLY. +11 lines →
  Bgen 6/6 PASS at effort 128<168, ~half A's bytes on every probe.
  (/tmp/substrate-x1h-001/)
- H1 hardened pilot (this artifact): 33/33 green (19 adapted + F1–F5 + 9
  recovery) on system python3 (package dir + repo root) and venv python;
  demo exit 0 stub + SST-TEST ($0, champion_found both), 40-entry ledgers
  (36 + 3 grant_settle + 1 settle return); real-SIGKILL resume with 0
  re-executed invokes; settle leaves 0 stranded holdings (live + replay);
  all refusal paths raise with recorded deny/error entries. Full per-item
  evidence: RUN-REPORT.md H1–H3/S1–S3/A1–A3/I1–I3/X1–X3 + §7.
- H2 independent verification: ACCEPT-WITH-NOTES — every behavioral claim
  re-run fresh from the candidate (suites x3, stub demo, SST-TEST, SIGKILL
  recovery, settle replay, F3 mutation probe PASS, freeze re-check, boundary
  + H0 numbers). 3 low-severity record notes (N1–N3), all corrected by the
  coordinator (RUN-REPORT §8 item 7). VERIFICATION.md.

## 4. Decisions / investment read (ACCEPTED within stated envelopes)

- Working path: central orchestration + evidence/tooling/docs (H1b/H2b/X1H).
- Retain narrowly: checkpoint schema + identity rule, `grant_settle` marker +
  `unsettled terminal` replay check, `host_reopen` marker, resume-by-skip
  rule, descriptor re-supply + fail-closed withholding. Independently reusable
  through the interface in RECOVERY-REUSE.md §2; rewrite-per-host: replay
  adapter + settle distribution. Do NOT retain: path-shaped refs, in-memory
  relationship evidence (lost across reopen).
- Defer: host negotiation promotion; permanent host (extend-DSH / Cordis-seam
  / distinct) UNDECIDED — evidence does not warrant migration.
- Every result above closes ONLY its toy TEST/stub envelope. Negative results
  do not satisfy unimplemented product requirements. This pilot does not
  establish the developmental-substrate ambition.

## 5. Failures / gaps (preserved)

- W1 repro gaps (carried unless fixed in H1): dirty SST; TEST-only; hand-written
  mapping; toy evaluator; grant-stranding FIXED in H1 via settle-then-move;
  w1 un-pinned (sha256 anchor only).
- H1 honest limits (LIMITS.md, 10 items): no live models; no learned mapping;
  toy evaluator; exists-family envelope; single-host, no concurrent writers;
  assistance-(ii) untested; ledger pure overhead except recovery/audit;
  SST dirty-with-hashes; single kill boundary (kill-during-settle needs
  operator repair; partial-invoke side effects must be re-runnable; disk loss
  uncovered); Windows-safe coded but executed on Linux only.
- X1 harness bugs (voided, artifacts kept): 6 crashed runs (KeyError),
  stdout truncation (re-collected), 1 dirty-dir rerun. X2: 1 PILOT crash
  (fixed pre-run-1). X1G/X1H/H1/H2: none.
- History preserved: live-model SST search previously 0 proposals; STC 13/13
  journey scripted-provider, 0 model calls; DSH pilot tied 1–1; X1 Arm A
  resume used checkpoint-identity + replay (H1 answers with `Host.reopen`).

## 6. Exclusions (explicit, owner + dependency)

- TRACE participation: EXCLUDED. Owner: TRACE track. Needs TR1/M1.
- STC-backend stretch: NOT attempted. Owner: construct-world/STC.
- Live-model SST: NOT run ($0 envelope). Owner: SST. Needs budget + keys + SST2.
- Clean SST pin: NOT selected (dirty-with-hashes frozen). Owner: SST.
- Mapping learning / training: separately scoped. Owner: substrate semantics.
- Real domain evaluator, distributed ledger, Host locking, Windows execution,
  non-exists predicates, multi-kill/disk-loss recovery: deferred (LIMITS.md).

## 7. Reproduction

REPRODUCE.md (same dir): exact ordered commands for suites (x3), stub demo,
SST-TEST demo, recovery exercise, freeze checks. All $0, offline. Expected
outputs quoted with tolerances (wall time, path-embedded bytes).

## 8. Provenance

Context: ANIMA/context (OPERATIVE-BRIEF, SESSION-STEER-2026-10-03, tracks,
IDEA-MAP, SOURCE-EXCERPTS, DECISIONS D-001..D-017, REQUIREMENTS, OPEN-ISSUES).
Prior W0–W3/E1–E4 assignments used as optional historical inputs only.
Authorizations: user released spawn (specialists), then write+builder hold for
`substrate/prototype/w1-harden/` + canonical promotion + qualification
evidence, $0 experiments. Spend: $0 throughout. Repo writes: confined to
`substrate/prototype/w1-harden/` (20 files); `prototype/w1/` sha256-verified
unchanged; `sst/` read-only (porcelain diff empty across every lane's runs).
