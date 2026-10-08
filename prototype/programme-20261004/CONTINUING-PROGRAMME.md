# CONTINUING PROGRAMME — substrate beyond r1

Authority: user CONTINUING AUTHORITY message 2026-10-04 (active programme,
minimal back-and-forth). Standing constraints unchanged: $0, offline,
stdlib-only except SST leg, producer ownership + deliberate pins, builder
scope = substrate project, frozen artifacts read-only (r1 = successor-002 +
release-20261004).

## Dependency DAG

```
r1 (frozen) ──┬──> L-branch (learning/reuse experiments; needs only r1)
              └──> R-branch (robustness/scale; needs only r1)
producer qualified releases (STC/SST, owner-minted)
              └──> U-branch (real-use acceptance; BLOCKED until producers land)
P-branch (survey + adapter prep; no producer action needed, no acceptance claimed)
```

Unavailable producer releases block only U-branch acceptance claims, never
L/R/P progress. All branches keep failures and distinguish
hypothesis / observed / accepted.

## Next bounded objectives (coordinator-set acceptance criteria)

### L1 — Held-out recipe transfer (priority: learning + reusable procedures)
Question: do procedures extracted from completed r1 runs improve HELD-OUT
task performance vs a competent cold baseline, net of acquisition cost?
- Design + pre-registration committed BEFORE execution (thresholds, tasks,
  baseline, metrics: in-envelope bytes, rounds, success; acquisition cost
  counted against the gain).
- Held-out tasks never used during recipe extraction; baseline = cold
  competent run through the same consumer interfaces.
- r1 frozen untouched; experiment lives in its own successor dir.
- ACCEPT: pre-reg followed, held-out gain OR honest negative with sound
  method, independently verified. A clean negative is a complete result.

### R1 — Atomic settle + interruption boundaries (priority: robustness)
Closes r1 LIMITS-11 and part of LIMITS-3 (kill-during-settle/fusion).
- `settle` all-or-nothing: refusal/failure leaves zero partial dissolves;
  ledger stays consistent and fail-closed (as now).
- Kill-during-settle and kill-during-fusion/fission: defined behavior +
  recovery exercises (no silent partials; operator-repair path explicit
  where automation is out of scope).
- Fault-injection tests through consumer interfaces; successor dir, r1 untouched.
- ACCEPT: tests pass, no partial states demonstrable, independently verified.

### P1 — Producer survey + adapter prep (enables future real use)
- Survey STC/SST release posture (read-only); record exact pins + what
  "qualified" would require from each owner.
- Adapter scaffolding against pinned snapshots (no producer runtime refs).
- Record the smallest concrete producer ask. NO acceptance claim until an
  owner-minted qualified release exists.

## Sequencing

L1-design+execute, R1-build, P1-survey run concurrently (independent).
Independent verification lanes follow each branch's completion (as in r1).
Milestone reports: what became usable, what evidence supports, what is next.

## Standing deferrals (unchanged from r1 §6)

Cross-host, multi-writer (beyond R1 scope if it grows — split, don't sprawl),
disk-loss, live-model SST, STC-backend stretch, TRACE participation,
permanent host Q5 (needs user judgment + evidence packet first),
physical co-design (in view; enabling research only where justified).

## Log

- 2026-10-04: programme opened. r1 ACCEPT (VERDICT2). L1/R1/P1 launched.
  Producer survey: SST df78f42 clean, no tags; STC 8fa8ac3 (live readiness
  packet — inspect before any use claim), tree dirty, tags pending; TRACE
  present (state pending); TL absent (no ../tl dir). No owner-minted
  qualified release located yet — U-branch remains blocked, L/R/P proceed.
- 2026-10-04: L1 executed → clean NEGATIVE (P1 FAIL all-12 reuse, P2 PASS
  12/12, P3 FAIL 1566v972, secondary tie 5/8, calib 36/36). Coordinator
  reconciled: all 19 pins match, isolation holds (0 cross-refs), verdict
  code == prereg rule, r1 41/41 intact. Independent verification lane
  launched; L1 acceptance pending its verdict. R1 build still running.
- 2026-10-04: L1 **ACCEPTED** (ACCEPT-WITH-NOTES; notes A+B recorded in
  L1-transfer/VERIFICATION.md, both immaterial to the verdict). Negative
  stands: no task-conditional recipe surface in r1 envelope. L2 needs a
  content-sensitive host before re-test. Builder files unmodified by
  verification. R1 build running.
- 2026-10-04: R1 build complete → successor-003/ (recover.py, atomic
  settle via check_settleable pre-validation, ops recover, 27
  atomicity tests, INTERRUPTION-BOUNDARIES.md). Coordinator spot-checks
  pass: r1 IDENTITY 0 fails, s003 IDENTITY 0 fails, 9/9 + 7/7
  regression observed, settle code is pre-validate+deny-only, hooks
  inert-when-unset, rebrand diffs trivial, EXPECTED pins MATCH-only
  (61f523a5 quirk confirmed record-only). Independent verification
  lane launched; R1 acceptance pending its verdict.
- 2026-10-04: R1 **ACCEPTED** (ACCEPT-WITH-NOTES; notes A–E in
  programme-20261004/R1-VERIFICATION.md, all record-only).
  successor-003/ FROZEN as-verified (45/45). LIMITS-11 closed,
  LIMITS-3 narrowed to quarantine-transfer. Next: L2 design-only
  research (what host change creates recipe surface) + P1 adapter
  prep (survey + scaffold + producer ask), launched concurrently.
- 2026-10-04: L2-DESIGN.md accepted as proposal (578 lines; load-bearing
  code claims verified: run_tasks allowlist, fragment_rounds from
  holdings, declared-input rule form). CORRECTION: "vectors 13/15" as
  used in the L2 brief/design does NOT match IDEA-MAP numbering
  (V13 = domain schemas + deltas; V15 = adaptation/learning
  timescales) — proceed on plain-language meanings; sequencing logic
  unaffected. AUTH-1 GRANTED (H2 delta build in programme-20261004/
  H2-lane/, experimental tree, NOT successor-004); AUTH-2 GRANTED
  CONDITIONALLY (H2 accepted + step-0 crossover + prereg frozen to
  PREREG-LOG, else abort/pivot per design §10). Q1a/Q2/Q3/Q4/Q5 draft
  answers accepted. Q6 decided: hash-chained PREREG-LOG.md (created,
  genesis, no git init). M1 cost-mapping launched (frozen host,
  step-0 observation-budget abort). P1 still running.
- 2026-10-04: P1 **ACCEPTED** (survey + scaffold + asks; no behavior
  claim, coordinator-verified, no independent lane needed). Survey
  claims verified verbatim (SST "proposed" run_search, STC packet
  079f4de6/AWAITS-blessing, HEAD-vs-worktree pin split); selftest
  all-PASS observed; SST clean, s003 45/45 intact; STC delta (one
  untracked dir) by an external concurrent actor, not P1. Standing:
  SST 0/4 (nearest — clean commit, stable-in-practice), STC 0/4
  (needs freeze + design answer; no substrate-facing surface exists).
  U-branch remains blocked; asks filed in P1-adapters/PRODUCER-ASK.md.
  Running: H2 build, M1 mapping.
- 2026-10-04: M1 **ABORTED at step 0** (complete, publishable negative):
  frozen host yields 2 same-class (feature→central_bytes) observations
  (+1 different-class S3) vs ~20 needed. No DESIGN/PREREG, correctly.
  Abort corroborated (novel-task ValueError re-observed verbatim;
  s003 45/45 intact). PROGRAMME IMPLICATION: L2-DESIGN §9's "mapping
  concurrent-safe on the frozen host" is FALSIFIED — cost mapping needs
  novel lane execution too. H2 is now the single gate for ALL learning
  vectors (transfer, mapping, invention). Mapping re-queued behind H2
  acceptance. Running: H2 build only.
- 2026-10-04: H2 build complete in programme-20261004/H2-lane/
  (delta confined to routing/api/release; 1-line rebrands elsewhere;
  minihost untouched). Coordinator spot-checks pass: H2 IDENTITY 0
  fails, 18/18 lane suite observed, routing delta == spec (derived
  via executed fragment_rounds, legacy path preserved), functional
  CLI probe (novel tasks execute VALID with content-sensitive bytes
  894/715; override forces rule-local→central). s003 45/45 intact.
  Independent verification vs §5 bar launched; L2-execute BLOCKED on
  its verdict. Note for verifier: route() override-on-legacy is
  plausibly dead code (assess reachability).
- 2026-10-04: H2 **ACCEPTED** (ACCEPT-WITH-NOTES; 4 record-only notes
  in H2-VERIFICATION.md; verifier ran FULL 27/27 atomicity + own
  5-task grid + own kill-resume; dead-code question resolved
  immaterial; SST-porcelain gap closed by coordinator direct check).
  H2-lane/ FROZEN as-verified (46/46). AUTH-2 chain unblocked.
  Launched concurrently: L2-execute (step-0 → prereg → execute) +
  M1-redux (mapping rescoped to H2). Lessons: verifiers preserve
  /tmp proofs; producer-porcelain checks are coordinator-side.
- 2026-10-04: L2-execute **ABORTED at step 0** (complete negative,
  frozen criterion fired mechanically: 0/8 cheaper-central, 8/8
  cheaper-local, 16/16 VALID, guard MATCH). Coordinator-verified:
  pre-commit (seeds/partitions) predates runs, hashes match,
  conservation re-derived 8/8 exact, entries invariant 8/8, H2 46/46
  intact. CLOSED FINDING: lane choice only re-routes a fixed byte
  mass (central_B(central) = central_B(local) + direct_B(local) to
  the byte) — no recipe surface in ANY unit (central: local always
  wins; total: conserved; entries/invokes: invariant). X3 "central
  wins small" was cross-task; within-task local wins by
  construction. CORRECTION to abort-file prose: pivot target is
  M1-redux on H2 (running), not frozen-host mapping (M1 falsified).
  Recipe transfer CLOSED on this host family; policy invention stays
  gated (no trade-off surface exists yet). H2 acceptance stands
  (mechanism met its bar; finding is about cost structure).
- 2026-10-04: M1-redux executed → builder-claim PASS (model MAE 0.00
  vs const 233.25 vs rule 38.07, 36/36 VALID, 0 fallback, guards
  exact). Coordinator reconciled: all 7 file hashes + 36 task pins
  match, verdict imports frozen predicates, rows show 36/36 exact,
  H2 46/46 intact; PREREG-LOG countersigned (genesis af809304...
  → entry e077d5e4..., chain verified). Independent verification
  launched (skeptical brief: MAE 0.00 re-derivation, isolation,
  lookup-table materiality); M1-redux acceptance pending its verdict.
- 2026-10-04: M1-redux **ACCEPTED** (ACCEPT-WITH-NOTES; PASS stands:
  MAEs re-derived exactly 0.0000/233.2500/38.0694 from raw ledgers,
  72 fresh executions, isolation holds; 4 record-only notes in
  M1-redux/VERIFICATION.md incl. 24-item genuinely-novel re-verdict
  still PASS). PREREG-LOG RULES-AMENDMENT-1 filed (exception
  procedure admitted explicitly). LEARNING ARC CLOSED: transfer has
  no surface (L1 + L2-closed), mapping validated as instrument
  (M1-redux), invention gated (no trade-off surface). Next bounded
  objective: r2 release (bank successor-003 as a usable frozen
  release, r1-pattern acceptance) — builder launched.
- 2026-10-04: r2 builder-run complete → BUILDER-ACCEPT (10/10 PASS
  on fresh /tmp state; finding F1 LOW/record-only: direct settle on
  partial fission strands custody loudly, off-procedure, custody
  repairable, fission entry then unappendable; carried in
  RELEASE-RECORD with lane-judges disposition). Coordinator:
  s003 45/45 + s002 41/41 intact; F1 read and assessed plausibly
  LOW (custody-orthogonal settle is longstanding; no clause
  promises refusal) — independent lane reproduces + judges.
  Independent r2 acceptance launched (A1–A10 fresh + F1 severity);
  r2 freezes or stops on its verdict.
- 2026-10-04: r2 **ACCEPTED** (ACCEPT-WITH-NOTES; lane A1–A10 PASS on
  own evidence incl. full 27/27 + own 67-check matrix + 54/54 own
  mapping; F1 concurred LOW with byte-exact repair proof; F2 new LOW:
  torn-specs SIGKILL window, loud disk-loss refusal, non-atomic
  _write_specs root-caused). Coordinator: VERDICT2 filed, record
  appended (F2 + both doc corrections carried), SST gap closed
  (porcelain 0 @df78f42), pycache residue removed (45/45 after),
  CANONICAL-RECORD updated. successor-003/ + release-r2/ FROZEN.
  Next: R3 (atomic spec writes, lane-specified F2 fix) — launched.
- 2026-10-04: USER CORRECTIONS (2) received + applied. (1) Recovery:
  R3 brief amended mid-flight — "ledger cannot tear" WITHDRAWN as
  unproven (Linux write(2) permits partial writes); R3 must test
  interruptions INSIDE actual writes (ledger + side-files), evidence
  or narrow every no-tear claim, separate process-crash (in scope,
  tested) from power-loss durability (out of scope, never claimed),
  reproduce F2 red on the pristine copy first, keep focused
  regression in the tree's normal test layout. (2) Producer gates:
  P1 reconciled — commit hash + verified manifest = sufficient byte
  identity (SST Q-SST-0 SATISFIED, no tag needed); genuine gaps are
  owner contract + owner acceptance evidence only (SST 2 gaps; STC
  needs clean commit + artifact decision + contract/evidence);
  SURVEY.md + PRODUCER-ASK.md rewritten, ceremony removed.
  QUEUED after R3 acceptance: real-use branch (useful software task
  on qualified frozen components vs competent direct baseline, with
  changed requirement + interrupted-run recovery); learning
  experiments regrounded in application trade-offs (prior negatives
  preserved in-envelope).
- 2026-10-04: R3 build complete → successor-004/ (atomic_write_text
  temp+replace on all op-path side writes; 12 new tests in normal
  layout 27→39; no-tear WITHDRAWN for ledger with tested loud
  landing; process/power separated; F1/F2 docs corrected).
  Coordinator spot-checks pass: s004 IDENTITY 0 fails, 9/9
  conformance observed, helper + hooks + LIMITS-2 narrowing read
  and honest, ZERO stale impossibility wordings tree-wide, s003
  45/45 + s002 41/41 intact. Corrections visibly honored (F2 red
  first, interior proofs, red-first discipline). Independent
  verification launched (strengthened: authentic-red reproduction,
  interior arbitrariness, wording audit, left-non-atomic probes);
  R3 freezes or stops on its verdict.
- 2026-10-04: R3 **ACCEPTED** (ACCEPT-WITH-NOTES; all 8 checks PASS:
  authentic red reproduced round-1, 11/11 new tests + own 18-kill
  loop 0-torn, interior arbitrariness with own params, AST sweep +
  wording audit clean, SST/CONFIG probes green, full 9+7+17
  regression, frozen 41/41+45/45+45/45; 3 record-only notes N1–N3
  in R3-VERIFICATION.md). SST gap closed (porcelain 0 @df78f42).
  successor-004/ FROZEN as-verified (45/45). User-correction
  compliance verified live. Next: real-use DESIGN (design-only) —
  launched (task + baseline + changed-requirement + recovery +
  artifact acceptance + prereg draft).
- 2026-10-04: U-branch design returned STEP-0 NEGATIVE (no honest
  useful task fits the qualified envelope; 5 candidates argued +
  rejected with receipts; REALUSE-DESIGN.md). Coordinator verified
  all 5 load-bearing claims from frozen bytes (capability-gated
  invoke + fixed sets §7; C2/C3 shapes; fixed SST fixture + canned
  returns + no task param; H2 grid-fixed schema; revise =
  pre-advertised flip only) and probed for a missed 6th interface
  (none; escrow-shaped tasks fail U1 same as Candidate A).
  NEGATIVE ACCEPTED as correct. U-execute BLOCKED behind reopen
  invariants I1–I6 (no PREREG entry per §4c). Re-scope decision
  ESCALATED to user (recommendation: bank negative + approve
  design-only scoping of a ledger-honest procedure leg).
  Independent work continuing: r3 release cut — launched.
- 2026-10-04: r3 builder-run complete → BUILDER-ACCEPT (10/10 PASS,
  no new findings; F1 re-verified, N1/N2 confirmed as disclosed; 2
  content-neutral in-tree file events disclosed: byte-identical
  manifest rewrite + pycache created/removed). Coordinator: s004
  45/45 + s003 45/45 + s002 41/41 intact. NOTE: builder's 50-kill
  loop landed 43/50 completed-before-kill (weak statistical leg) —
  lane briefed to scale delays to measured wall + confirm in-window
  landings. Independent r3 acceptance launched; r3 freezes or stops
  on its verdict. U re-scope escalation still awaiting user.
- 2026-10-04: r3 **ACCEPTED** (ACCEPT-WITH-NOTES; lane A1–A10 PASS on
  own evidence incl. 61/61 own mapping, full 39/39 loop + 45 aimed
  in-window kills 0-torn, 81/81 own matrix, durability audit, SST
  checked directly; 2 record-only notes in VERDICT2). VERDICT2
  filed, record appended, SST 0 @df78f42 (both lane + coordinator).
  successor-004/ + release-r3/ FROZEN. PROGRAMME STATE: r1/r2/r3
  frozen+accepted; H2 accepted; learning arc closed (transfer: no
  surface; mapping: validated instrument; invention: gated);
  U-branch step-0 negative (re-scope with user); producers filed;
  Q5 with user. ALL REMAINING PATHS NEED USER/OWNER INPUT — see
  escalation. Coordinator stopping per completion rule.
- 2026-10-04: USER AUTHORIZED procedure-successor line (design +
  build + acceptance together; Q5 stays open; U negative banked
  in-envelope). r3 bank-confirmed (41/41+45/45+45/45). Producer
  refresh: STC @5c65427 (SST pin df78f42 COMMITTED — old blocker
  stale; worktree dirty again, owner active; no tags); SST @df78f42
  clean. P1 record updated append-only (SURVEY §7 + ASK-2 step A
  partly landed; genuine gaps unchanged: SST contract+evidence,
  STC artifact decision + contract/evidence). S5 DESIGN launched
  (design-only: procedure participant + default identity/compat
  utility vehicle + acceptance bar + U prereg draft); build follows
  coordinator review without further user rounds.
- 2026-10-04: S5-DESIGN (1034 lines) REVIEWED + APPROVED with 5
  binding refinements. Accepted: §2 strengthening (bare checker
  UNFIT, relcheck-as-specified is the vehicle), Q2 CONTRACTUAL
  split (executor-not-sandbox, stated trust model; isolation stays
  future scope), N1/N2 ride-along. Refinements: R-A sched-path
  byte-identity (additive-absent-when-empty emission; identical
  runs byte-identical modulo paths/timestamps; any carried-test
  edit = BLOCKER); R-B suite steps from hash-verified scratch
  copies (ZERO frozen writes); R-C add `package` step (versioned
  artifact dir + single hash; STEPS gains "package"); R-D checker/
  baseline/predicates authored by the U-execute agent at prereg
  (builder's S5-A10 checker is disclosed throwaway); R-E pin P9
  compare order + grant sizing + no exact wall-clock assertions.
  Noted for U-prereg: §7.6 docstring overclaims counts (checker
  covers). S5 BUILD launched (successor-005, §1 delta + §6 bar).
- 2026-10-04: user: subagents-for-speed (S5 builder untouched) +
  compact-soon. Parallel shape: S5 BUILD (38) + U-execute DRAFT (39,
  draft-only: predicates/checker/baseline-scaffolding/prereg
  skeleton, py_compile-only, reconciled post-build). No wider
  fan-out: verification + U-execute are serially gated on the build
  by the acceptance discipline; manufacturing more lanes would idle
  them. agents-skill machinery (agents.py/tmux/PRs) assessed and
  declined: no repos/PRs/clones in this programme; in-session lanes
  + file verification stand. Compaction: operator-triggered, not
  coordinator-triggered; all state durable in this log + records.
- 2026-10-05: U-execute DRAFT accepted (6 files: predicates + checker
  + baseline scaffolding + Makefile template + PREREG skeleton +
  DRAFT-NOTES; py_compile-clean; zero executions; s004 45/45
  intact). Drafts reconcile against built successor-005 at U-prereg
  time. Awaiting S5 BUILD (running).
- 2026-10-04: USER ADDENDUM (received truncated; coordinator reading:
  agreed software must be carried to FULL completion, while
  wider-vision completion claims require explicit criteria first —
  assumption flagged, correction welcome). Applied as: every
  authorized objective runs through independent acceptance with
  nothing left half-delivered; no "programme complete" claim against
  the 18-vector vision without user-set criteria. Standing
  interpretation of "done" per objective is unchanged (accepted +
  frozen + recorded).
