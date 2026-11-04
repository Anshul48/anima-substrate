# REALUSE-DESIGN.md — U-branch real-use experiment (DESIGN ONLY)

- Status: design complete; verdict §0.
- Workdir: `prototype/programme-20261004/RealUse-design/` (only location written).
- All other trees read-only for this design (successors, releases, H2-lane, P1-adapters, programme records).
- No implementation, no runs, no host modification performed.

## §0 Verdict (read first): NO honest useful task fits the qualified envelope

This design evaluated every consumer-interface path that could carry a
"useful software task" through the qualified frozen components
(successor-004/R3 host ops + SST TEST snapshot leg; H2-lane novel lane
tasks as the experimental alternative). **None of them can honestly
execute a task that is both (a) genuinely useful — a real artifact a
competent engineer would want, not a scheduling-grid re-skin — and
(b) executed through qualified frozen components via consumer
interfaces with a meaningful matched-resource comparison against a
competent direct baseline.**

This is a **complete step-0 negative result**, not a failure: it
re-scopes the U-branch (see §6) rather than failing it. The evidence
is in §1 (per-candidate rejection with file/line receipts) and the
honesty analysis is in §5. Sections §2–§4 are written as far as the
block allows: the changed-requirement and interrupted-run legs cannot
be instantiated without a task, so §4 freezes the executability gate
that fired (instead of theater predicates for a nonexistent task) plus
the template invariants a future task must satisfy to reopen U-execute.

Design rule applied throughout (from the brief): do not inflate
usefulness. Every candidate below is argued in good faith first
(useful? host-help? where-lose?) and rejected only on evidence.

## §1 Candidate tasks: proposed, argued, rejected on evidence

Qualified compute inventory (what consumer interfaces can honestly
execute — established by reading, not assumption):

1. **Scheduling payload.** successor-004 `run_tasks` accepts ONLY the
   fixed names S1/S2 (`api.py:70` `LANE_TASKS`, `api.py:170-174`
   unknown names raise). H2-lane additionally accepts novel lane
   tasks via task-JSON, but the schema is fixed to scheduling grids:
   required keys `task_id/slots/tasks/precedence/prefs/holdings/
   adapter`, holdings must partition exactly the grid
   (`H2-lane/ORG-OPS.md` §8.1). S4/S6 follow-ups run via reuse ops on
   the same scheduling family. One deterministic backtracking solver
   is shared by both lanes; 4–5 tasks/slots
   (`H2-lane/LIMITS.md` item 1).
2. **SST TEST leg.** `run_sst_test_search(rundir, timeout_s)` takes no
   task parameter (`successor-004/sst_leg.py:162`); the child script
   is a fixed constant (`CHILD_SCRIPT`, `sst_leg.py:53-159`) running
   one hardcoded fixture (fix `mul` in a scratch repo) against a
   hardcoded deterministic `TestGateway` that returns the canned
   string `"def mul(a, b): return a * b\n"`
   (`sst_leg.py:107-115`). Caller-supplied tasks are not expressible;
   changing the script is host modification (forbidden).
3. **Org ops.** fuse/fission/reuse/revise/revoke/quarantine/settle
   manipulate worlds, custody, ledger entries, and grants
   (`ORG-OPS.md` OP-1..OP-6). They perform no software-work compute
   of their own; `reuse_op` runs scheduling follow-ups through the
   composite (`ORG-OPS.md` OP-2.1).
4. **P1 adapters.** Read-only validators (snapshot bytes + envelope
   shape; `P1-adapters/sst_adapter.py:1-16`). No compute surface.
5. **`resume.execute_plan`.** Steps carry an `fn` callable that
   `MiniHost.invoke` DOES call (`minihost.py:796-797`
   `result_ref = fn()`). BUT every invoke is ledger-recorded under a
   `capability` name the world must advertise
   (`minihost.py:772-778`), the advertised sets are fixed at world
   creation (`ORG-OPS.md` §7: "no genuinely NEW capabilities ...
   after world creation"), `execute_plan` enforces the C2 args shape
   (`formulation_ref` + `candidate_refs`, `resume.py:102-106`) and
   the C3 result shape for propose (`resume.py:109-115`). There is no
   advertised capability that honestly names arbitrary software work.

### Candidate A — Real-content allocation on H2 novel lane tasks (BEST rejected bet; see also §7)

- Proposal: encode a REAL small allocation (e.g. the programme's own
  pending verification-run assignments, or real reviewer→PR
  allocation with expertise prefs + dependency precedence) as an H2
  task-JSON; host arm produces `solution-*.json` + verdicts + ledger
  audit trail; direct arm is a competent backtracking script or
  hand-derived assignment; independent lane judges via
  `sched_checker.py` + usefulness rubric.
- Why useful (steelman): real content, real consumer, machine-checkable
  validity; the artifact would be consumed, not graded and discarded.
- Why the host could help (steelman): ledger audit trail of the
  routing + revision history; kill-recovery mid-run; reuse for
  follow-up allocations.
- Where it loses / why REJECTED:
  1. It is a scheduling-grid re-skin by construction: same schema,
     same solver, same 4–5 scale, same dynamics — only labels change.
     The brief explicitly excludes this class.
  2. Usefulness fails at toy scale: a 4–5-item assignment is solvable
     by hand in minutes; no competent engineer wants this artifact
     *from this pipeline* over direct reasoning or a 30-line script.
     The "real consumer" claim does not survive contact with the
     scale limit (`LIMITS.md` item 1: toy scale, deterministic stubs).
  3. The comparison is degenerate: host arm = direct-equivalent solve
     plus ledger overhead. The only host-exclusive value (audit
     trail) is not part of any defensible *useful-output* criterion
     an independent lane would accept as usefulness, and kill-recovery
     on a sub-second deterministic computation has ~zero value vs
     free re-run (see §2).
  4. Changed-requirement cannot run through `revise_op`: revision
     switches the ACTIVE representation between PRE-ADVERTISED
     versions and never mutates requirements (`ORG-OPS.md` OP-3.1);
     a genuine new constraint/p Dropout is expressible only as a new
     task-JSON + re-run — identical in both arms, so the host adds
     nothing to that leg either.

### Candidate B — Durable multi-step software procedure via `execute_plan` (rejected: ledger-dishonest)

- Proposal: run a real procedure (draft module → run checks → repair →
  package) as plan steps with resume-by-skip; kill mid-procedure;
  host arm resumes, direct arm re-runs from scratch.
- Why REJECTED: the only way to put real work in a step is an `fn`
  whose behavior contradicts its ledger-recorded capability name
  (e.g. ledger says `sched.propose`, `fn` runs pytest). The ledger —
  the host's sole audit artifact — would then contain false
  statements, and no advertised capability honestly names the work
  (§1 inventory item 5; `ORG-OPS.md` §7 excludes new capabilities).
  A competent direct baseline with checkpoint files (make-style)
  provides the same resume value honestly. This candidate mistakes
  "the host can be made to execute bytes" for "the host can honestly
  execute this task through consumer interfaces." It cannot.

### Candidate C — Novel search task through the SST TEST leg (rejected: fixed content + stub gateway)

- Proposal: produce a real patch/solution via `run_search` TEST.
- Why REJECTED: (1) the leg accepts no caller task (§1 inventory
  item 2); any novel content requires editing `CHILD_SCRIPT` = host
  modification, forbidden. (2) Even if it did, the TEST gateway
  returns deterministic canned strings — outputs are stub outputs,
  and every real-use claim on them is forbidden (see §5). The only
  valid SST-leg claim (envelope/byte conformance) is already covered
  by qualification, not by a "useful software task."

### Candidate D — Deliverable organized via fuse/fission/reuse across worlds (rejected: theater)

- Proposal: hold modules in worlds, fuse for integration, fission for
  parallel revision, ship the ledger as provenance.
- Why REJECTED: worlds hold custody of sched state classes, not code
  artifacts; no consumer op reads, writes, transforms, or checks code
  (`api.py`, `fusion.py` surface: custody/ledger/grants only). All
  real authoring would happen in experimenter code outside the host,
  making the host load-bearing for nothing and the comparison empty
  (host arm ≡ direct arm + ceremony). The ledger would record
  scheduling-custody events mislabeled as software-engineering
  history — same dishonesty as Candidate B, at higher page count.

### Candidate E — SST-envelope conformance / adapter validation as "the task" (rejected: not useful output)

- Proposal: treat snapshot verification + envelope validation as the
  useful artifact (supply-chain evidence).
- Why REJECTED: that evidence already exists as qualification output
  (`verify_snapshot.py`, P1 selftest); re-running it is not a useful
  software task with a direct baseline, changed requirement, or
  interrupted run — it has no competent-direct competitor that the
  host could beat or lose to on usefulness, and no independent
  usefulness criterion beyond "MATCH," which is circular.

## §2 Changed requirement + interrupted run (designed to the block)

Both legs were designed far enough to locate the exact breakage. No
task exists to instantiate them on (§0), so this section records the
design and the breakage symmetrically for host arm (H) and direct
arm (D).

### Changed requirement (pre-registered shape, held-out content)

- Intended shape: at freeze, pre-register the CHANGE SHAPE (e.g.
  "one new precedence edge + one capability withdrawal"), hold out
  the CONTENT (which edge, which capability) in a sealed envelope
  (hash-committed at freeze, revealed mid-run); apply at a fixed
  mid-stream point to both arms; measure cost-to-adapt + final
  artifact validity.
- Breakage on H: `revise_op` cannot express a requirement change —
  it flips between pre-advertised representation versions only
  (`H2-lane/ORG-OPS.md` OP-3.1; world records never mutated). A real
  new constraint is expressible only as a brand-new task input +
  full re-run, which is byte-identical work in both arms. There is
  therefore NO comparison in which the host's revision machinery is
  load-bearing for a genuine requirement change; the "revision" leg
  would compare two identical re-runs. Symmetric application is
  possible but meaningless (both arms do the same thing; the metric
  cannot differ by arm except in overhead).
- Breakage on D: none (direct arm re-runs trivially) — which is
  itself the finding: where the change is expressible, the host has
  no mechanism the direct arm lacks.
- Verdict: changed-requirement leg NOT INSTANTIABLE with host
  load-bearing. Any future task reopening U-execute must name a
  consumer op whose honest semantics cover the change shape (§4
  invariant I3).

### Interrupted run (real kill + recovery through consumer ops)

- Intended shape: real `Popen.kill()` (process-crash class only, per
  envelope) at a pre-registered mid-task point in both arms; H
  recovers via `api.open_run` + `resume.execute_plan` skip-match
  (`re_executed_invokes == 0` asserted) or `ops recover` for
  structural ops; D recovers by documented re-run procedure
  (re-run-from-scratch or checkpoint resume, whichever the competent
  baseline would honestly use); measure recovery cost + final
  artifact equivalence.
- What is genuine here: the host's kill-recovery machinery is real
  and proven (R1/R3: kill-at-every-boundary matrices, recover
  idempotence, `INTERRUPTION-BOUNDARIES.md`). This leg COULD be
  instantiated symmetrically and honestly.
- Why it still does not save the U-branch: on every honestly
  expressible host payload (sub-second deterministic scheduler runs;
  fixed SST fixture), re-run-from-scratch costs ~nothing, so recovery
  value is ~zero and the comparison measures overhead, not
  usefulness. Recovery is load-bearing only for long/expensive
  computations, and the qualified envelope contains none (toy scale,
  deterministic stubs). A recovery-only comparison would be a
  robustness experiment (R-branch territory, already covered by
  R1/R3), not a real-use experiment.
- Symmetry note: kill-during-quarantine-transfer stays operator
  repair on H (`LIMITS.md` item 3) with no D analogue — correctly out
  of scope for both arms (pre-register the exclusion, do not route
  the kill there).

## §3 Artifact acceptance, resource matching, metrics (template + block)

Since no task exists, this section freezes the ACCEPTANCE TEMPLATE any
future U task must satisfy, and records why no current candidate
satisfies it.

### Independently checkable useful-output criteria (template)

- U1. The artifact is consumed by a named real consumer for a named
  real purpose (not graded-and-discarded); the consumer and purpose
  are pinned at freeze.
- U2. Validity is checkable by an independent lane WITHOUT trusting
  either arm: a frozen checker (program + pins) decides VALID/INVALID
  from artifact bytes alone. (Note: `sched_checker.py` satisfies the
  mechanism but only for scheduling grids — which §1 Candidate A
  excludes as re-skins.)
- U3. Usefulness rubric scored blind to arm: the lane scores "would a
  competent engineer want this artifact for this purpose" from the
  artifact + purpose statement; rubric frozen at prereg.
- Block: no candidate passes U1+U3 simultaneously — the only
  checker-backed artifacts (scheduling solutions) fail U1 at toy
  scale / fail the re-skin exclusion, and every non-scheduling
  artifact fails U2 (no honest host path produces it).

### Resource matching (template; precise)

- Held equal across arms: (a) task input bytes (identical); (b) change
  content + reveal point (identical sealed envelope); (c) kill point
  class (process-crash, same plan-phase); (d) human touches counted
  and capped (pre-register the cap; every operator input — e.g.
  `--partition` on fission recovery — is a counted touch on H, and D
  gets the same touch budget for its recovery procedure);
  (e) compute envelope ($0/offline/stdlib-only-except-SST-leg,
  inherited standing constraints).
- NOT held equal (measured as outcomes): ledger/artifact byte counts,
  invoke/step counts, re-executed work (must be 0 on H resume),
  operator wall-clock touches beyond the cap (guard).
- No wall-clock primaries: all timing is guard-only unless replayable
  conditions are specified (pinned machine, fixed repetition count,
  interleaved A/B order, reported as distributions, never as a
  single-race winner). Primary metrics must be count/byte/validity
  predicates (see §4 invariants).

### Metrics (template)

- Primary (had a task existed): blind usefulness score (U3) +
  validity (U2) jointly — artifact must be VALID and meet the
  usefulness bar; arm comparison on cost-to-adapt (invoke/step
  counts) and recovery cost (re-executed work = 0 on H; D re-work
  counted honestly).
- Guards: conservation holds on H; `re_executed_invokes == 0`;
  frozen hosts byte-intact (IDENTITY re-check); SST snapshot MATCH
  (if leg used); no wall-clock primaries; no TEST-stub content
  scored as engineering value (§5).

## §4 Pre-registration (honest form: the gate that fired + reopen invariants)

There is deliberately NO full prereg draft with coded
validity/usefulness predicates for a task: exact predicates for a
nonexistent task would be theater, and L1 lesson B (exact coded
predicates, verbatim) forbids inventing precision that does not
exist. What follows is what CAN be frozen honestly: (a) the
step-0 executability gate that this design applied, with its verdict;
(b) the invariants a future task must satisfy before U-execute may be
preregistered; (c) the PREREG-LOG entry plan.

### (a) Step-0 executability gate (applied 2026-10-04; FIRED = no task)

Gate rule (design-time, applied by reading, receipts in §1):

```
GATE U-STEP0 (all must hold for at least one candidate task T):
  G1. T names a real artifact + real consumer (U1/U3 achievable).
  G2. T is NOT a scheduling-grid re-skin (brief exclusion).
  G3. Every artifact-producing step of T executes through a consumer
      interface whose HONEST semantics cover that step (no capability
      mislabeling, no host modification, frozen trees read-only).
  G4. A competent direct baseline exists that does T without the host
      (so the comparison is meaningful, not host-vs-nothing).
  G5. Changed-requirement and interrupted-run legs are expressible
      with the host load-bearing in at least one of them.
Verdict rule: PROCEED iff some T passes G1..G5; else STEP0-ABORT
  (complete negative; re-scope, do not execute).
Observed verdict: STEP0-ABORT. Best T (Candidate A) fails G2 (+G1 at
  scale); B/D fail G3; C fails G3 (+§5 stub bar); E fails G1/G4.
```

This gate text is the frozen decision record for this design. It is
NOT a PREREG-LOG experiment entry (no experiment exists to anchor).

### (b) Reopen invariants (a future T must satisfy ALL before prereg)

- I1. T's payload executes through named consumer interfaces with
  honest semantics (cite op + doc section per step, as §1 does).
- I2. T clears G1+G2 simultaneously (real consumer; not a grid re-skin).
- I3. The change shape is expressible through a named consumer op
  whose honest semantics cover it (revise_op covers representation
  flips only — a T needing requirement edits must name a different,
  actually-qualifying mechanism).
- I4. The payload is long/expensive enough that recovery value is
  measurable (else the kill leg is R-branch, not U-branch).
- I5. TEST-stub content is never scored as engineering value (§5);
  STC uninvolved unless Q-STC-0..2 close (§5).
- I6. Full prereg follows the M1-redux pattern: frozen PREREG.md +
  verbatim `predicates.py` (verdict imports it, never reimplements),
  task pins, PREREG-LOG entry before first non-throwaway run (L1
  lessons A+B; `PREREG-LOG.md` rules + RULES-AMENDMENT-1).

### (c) PREREG-LOG entry plan

- No experiment entry is filed (nothing to anchor; filing one would
  imply an executable task exists).
- If the coordinator accepts this design as the U-branch step-0
  record, the acceptance note belongs in `CONTINUING-PROGRAMME.md`
  log prose (as with the M1/L2 step-0 aborts), not in PREREG-LOG.
- On a future T satisfying I1–I6, the U-execute agent prepares a
  standard entry (UTC stamp, prereg/design/predicates/task/generator/
  harness shas, prev_hash chain, rule line) per `PREREG-LOG.md`
  format; coordinator appends/countersigns before first
  non-throwaway run.

## §5 Honesty section

### TEST fixtures are deterministic stubs

- What they are: hardcoded canned returns (`sst_leg.py:107-115`
  fixed strings; fixed `CHILD_SCRIPT` task) executed through real
  controller/plumbing code. The plumbing is real; the CONTENT is
  stub content.
- FORBIDDEN claims on TEST: any claim that a TEST-leg output
  demonstrates search quality, engineering value, patch usefulness,
  model behavior, generalization, or any property of live SST. Also
  forbidden: scoring stub outputs under a usefulness rubric,
  comparing stub outputs across arms as if they were work products,
  or citing TEST success as producer qualification.
- What claim REMAINS valid: byte/shape conformance only — the
  8-key envelope is produced, keys/shapes match the pin, provider is
  TEST, cost is $0, snapshot pre/post MATCH. That claim is already
  established by qualification (`verify_snapshot.py`, SST-leg
  asserts); it needs no U-branch and supports no usefulness
  conclusion.

### SST posture stays SUBSTRATE-QUALIFIED (owner evidence missing)

- Citable today: byte identity only — commit
  `df78f42` + verified manifest `5f1f3789…` (Q-SST-0 SATISFIED;
  `P1-adapters/SURVEY.md` §3).
- Genuinely missing: owner contract (Q-SST-1) + owner acceptance
  evidence (Q-SST-2); `run_search` is owner-"proposed," not promised
  (`P1-adapters/SURVEY.md` §2). Label stays SUBSTRATE-QUALIFIED
  SNAPSHOT with NO SST-OWNER RELEASE ACCEPTANCE, exactly as
  `sst_leg.py:18` + `LIMITS.md` item 7 state.
- How this design stays honest: it claims no real-SST consumption
  beyond byte identity; it uses the SST leg's fixed/stub character
  as a REJECTION reason (Candidate C), never as a usefulness input;
  and reopen invariant I5 bars stub content from any future
  usefulness scoring even if Q-SST-1/2 later close (closing them
  qualifies the envelope promise, not stub content as engineering).

### STC excluded

- STC is EXCLUDED from this design and from any U-execute until
  Q-STC-0 (clean commit byte identity) + Q-STC-1 (owner names a
  substrate-consumable artifact — today none exists) + Q-STC-2
  (contract + evidence) close (`P1-adapters/SURVEY.md` §3,
  `P1-adapters/PRODUCER-ASK.md` Ask 2). No argument for inclusion
  exists: there is no artifact to consume and no immutable bytes to
  pin. The STC adapter remains a doc-reader + UNQUALIFIED gate —
  its honest terminal state.

### Envelope limits carried (non-negotiable for any reopen)

- Single-host, local disk; process-crash class only (power-loss
  durability never claimed; no fsync anywhere — R3 record).
- Toy-adjacent scale; deterministic stubs; no learning; no cross-host;
  no new capabilities/representations after world creation; `retired`
  unexercised (`LIMITS.md`, `ORG-OPS.md` §7).
- Kill-during-quarantine-transfer = operator repair, excluded from
  kill legs by pre-registration, never routed into.
- Frozen trees read-only (r1/successor-002, successor-003/release-r2,
  successor-004, H2-lane as-verified); any future U-execute runs in
  its own experiment dir.

## §6 Open questions + exact authorization needed

### Open questions (for coordinator / user, not for this design to answer alone)

1. Is the U-branch premise ("useful software task on qualified frozen
   components") retained as stated — in which case it stays BLOCKED
   until a qualifying general-compute surface exists (see options
   below) — or is it rescoped (option B)?
2. Does the SST owner intend any caller-parameterized TEST surface to
   become a stable consumer offering (needed even to REACH the stub
   bar honestly for novel content — and live-model qualification is a
   standing deferral, so the stub bar is terminal for usefulness)?
3. Is a new host payload leg (a successor feature honestly executing
   caller-supplied deterministic procedures as first-class,
   ledger-honest capabilities) in scope as future builder work, or
   does that exceed the substrate project's builder scope?

### Exact authorization needed

- **For execution: NONE requested. There is no executable task; no
  runs, dirs, hosts, or lane effort should be authorized on this
  design.** (Had Candidate A proceeded despite §1, it would have
  needed: H2-lane frozen host + own experiment dir, ~dozens of runs
  for arms × change × kill cells, and an independent lane to blindly
  score usefulness — but authorizing that would authorize a known
  re-skin with a degenerate comparison. This design recommends
  against it explicitly.)
- **Requested instead: a re-scope decision.** Options:
  - **Option 1 (recommended): accept this design as the U-branch
    step-0 negative** (log it in `CONTINUING-PROGRAMME.md` beside
    the M1/L2 step-0 aborts; no PREREG-LOG entry per §4c); keep
    U-execute BLOCKED behind reopen invariants I1–I6; pursue
    producer asks (Q-SST-1/2; STC clean commit + artifact decision)
    without implying they unblock usefulness by themselves (they
    don't — see Q2 above).
  - **Option 2: rescope U to "durable coordination audit"** —
    drop the useful-software-task premise and test what the host
    actually is (crash-safe coordination with an audit ledger).
    Honest, but it is R-branch-adjacent work under a new name; say
    so if chosen.
  - **Option 3: authorize builder work on a qualifying payload leg**
    (Q3) — a real feature with its own acceptance, after which THIS
    design's §1–§4 get re-run against the new surface. Largest cost,
    only path to a genuine U-execute on the current premise.

## §7 Best-bet assessment: is there a stronger alternative?

- The best real-use bet within the qualified envelope is Candidate A
  (real-content allocation on H2 novel lane tasks, §1) — it is the
  ONLY candidate that executes honest host compute end-to-end with a
  real checker and a symmetric direct baseline. It was rejected
  because the brief's own bars (genuinely useful; NOT a
  scheduling-grid re-skin) exclude it: same schema/solver/scale with
  relabeled nodes is a re-skin, and 4–5-item allocations are not
  artifacts a competent engineer wants from a pipeline. Proceeding
  with A would produce a comparison that can only measure host
  overhead, dressed as a usefulness finding. Rejecting the best bet
  is the load-bearing judgment of this design; the evidence is §1.A
  items 1–4.
- The stronger alternative OUTSIDE the envelope — a caller-supplied
  deterministic procedure leg with ledger-honest capability labeling
  (what Candidate B wants to abuse `execute_plan`/`fn` for) — does
  not exist as a qualified component and cannot be built by an
  experiment lane (it is builder work + its own acceptance; §6
  option 3). Naming it here so the re-scope decision sees the full
  board: U-execute on the current premise needs either that leg or a
  producer-qualified general surface, and the latter still dead-ends
  at the stub bar for usefulness (§5) while live-model work stays
  deferred.
- No other alternative was found: the §1 inventory exhausts the
  consumer interfaces (payload, SST leg, org ops, adapters,
  execute_plan), and each was carried to its breakage point with
  receipts. If the coordinator believes an interface was missed, the
  cheapest next step is a named-pointer challenge ("use interface X
  for step Y") answered by reading, not running.
