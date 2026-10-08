# L2 DESIGN — creating a task-conditional recipe surface (DESIGN ONLY)

- Written: 2026-10-04 (design research; no implementation, no runs)
- Author role: L2 design researcher (read-only on all existing trees)
- Work dir: `prototype/programme-20261004/L2-design/` (only location written)
- Status: PROPOSAL — L2-execute requires separate authorization (see §8)
- Consumes (read-only): `prototype/programme-20261004/L1-transfer/DESIGN.md`,
  `VERIFICATION.md`, `PREREG.md`, `EVIDENCE.md`, `programme-20261004/R1-VERIFICATION.md`,
  `programme-20261004/CONTINUING-PROGRAMME.md`,
  `prototype/successor-003/` (`ORG-OPS.md`, `LIMITS.md`,
  `INTERRUPTION-BOUNDARIES.md`, `CONSUMER.md`, `api.py`, `pipeline.py`,
  `fusion.py`, `routing.py`, `sched_domain.py`)

## 0. Starting point: what L1 + R1 established

L1 (ACCEPTED clean negative, `L1-transfer/VERIFICATION.md`): on the frozen
r1/successor-003 envelope, every reuse run costs 60 ledger entries / 13 invokes
and every split-pair run 81 / 15, at all sizes (4/5/6), all VALID. Both arms
share one deterministic solver (`sched_domain.solve`), so success/quality are
solver-determined and identical; the cost gap is a fixed pipeline constant
(21 entries, 2 invokes). The extracted recipe is therefore `always-reuse` —
no task-conditional content (P1 FAIL), success parity (P2 PASS), net loss
after acquisition (P3 FAIL: 1566 vs 972 entries).

R1 (ACCEPTED; `successor-003/` frozen 45/45): added atomic settle
(`check_settleable` pre-validation) and kill-during-settle/fusion/fission
recovery. It changed no pipeline cost structure: clean-path ledger bytes are
unchanged (R1-VERIFICATION: "phase-2 is byte-for-byte r1 logic"). The
no-recipe-surface finding carries over verbatim.

L1 lessons incorporated here (VERIFICATION Notes A/B): L2 prereg bytes must be
committed to an append-only, externally-anchored log (or git) before execution;
thresholds must be preregistered as exact coded predicates verbatim.

## 1. What "recipe surface" means (the requirement)

A recipe transfers task-conditional knowledge only if the host has a decision
point where the best choice varies with task content — i.e. at least two paths
whose cost (or success) functions CROSS OVER within the task family, so that
different tasks favor different paths and a content→path mapping beats every
fixed path. Formally, L2 needs a family F and paths X, Y such that for some
t1, t2 ∈ F: cost(X,t1) < cost(Y,t1) and cost(X,t2) > cost(Y,t2), with the
crossing predictable from observable task features. L1 proved no such crossing
exists on the reuse/split-pair dimension (constant gap at all sizes, uniform
success). §2 asks whether any crossing exists anywhere else on successor-003
as-is; §3 specifies minimal host deltas to create one.

## 2. Is there any surface on successor-003 as-is? (No — with one unsuitable exception)

Survey of candidate content-sensitive signals reachable through consumer
interfaces on the frozen host:

1. **Ledger entries / invokes on follow-up arms**: constant per arm (L1 §1:
   60/13 vs 81/15). No surface. Root cause: `reuse_composite` (1 invoke,
   `fusion.py`) and `run_split_pair_task` (3 invokes, `pipeline.py`) are
   straight-line pipelines whose ledger appends do not branch on content.
2. **VALID / quality / prefs_total**: solver-determined, identical on both
   arms. No surface (uniform success is itself the L1 finding).
3. **Canonical lane bytes on follow-ups**: unmeasurable by construction —
   follow-up paths run no clarification dialogue (`pipeline.py`:
   "no lane bytes are claimed here"). No surface.
4. **Lane bytes on lane tasks (`run`)**: content-sensitive AND crossed —
   S1 central 655/0, S2 local 310/500; X3 evidence says central wins small,
   local wins dialogue-heavy (the H3a cut encoded in `routing.route`).
   BUT: `run_tasks` (`api.py`) refuses every task except frozen S1/S2
   (`ValueError` on unknown names), and the routing inputs
   (`expected_rounds`, `split_state`) are *declared descriptor fields*, not
   content derivations. Two executable observations cannot support
   extraction (L1-secondary showed 2 observations underdetermine even the
   AND rule). Surface exists mechanistically but is unreachable: gated by
   the S1/S2 allowlist. Unlocking it is Option A (§3).
5. **Routing prediction (`explain-route --task-json`)**: accepts novel
   descriptors, but prediction-only (no execution, no cost). Supports a
   secondary-style prediction test only, not performance transfer.
6. **Wall-clock solver time**: the ONLY as-is content-sensitive performance
   signal on novel tasks (backtracking scales with constrainedness/size).
   REJECTED as a primary metric: machine-dependent, noisy, non-replayable,
   and excluded from byte-identity comparisons by precedent (LIMITS-8
   excludes wall-clock `at` fields for the same reason). A recipe fitted on
   wall-clock would not be honestly verifiable by an independent lane on
   another machine. Usable at most as a recorded, non-binding covariate.

Conclusion: successor-003 as-is has no adequate recipe surface. L2-execute
must run against successor-003 plus the smallest specified host delta (§5),
built and accepted under separate authorization (§8). The delta must live in
a new successor dir; successor-003 stays frozen.

## 3. Candidate minimal host changes (4 options)

### Option A — Content-derived routing + open lane execution (RECOMMENDED core)

Mechanism sketch (3 small, additive changes to a successor-003 copy):
1. `run_tasks` (or a new `run_lane_task` op through the same pipeline)
   accepts novel lane-task JSON (grid + holdings + adapter) validated by
   schema, replacing the S1/S2-name allowlist. Pipeline
   (`run_sched_task`: formulate → clarify×rounds → propose → verify),
   solver, ledger shapes, and settle/recovery paths are untouched.
2. Routing inputs are DERIVED from task content instead of read from
   declared fields: `derived_rounds := len(fragment_rounds(task))`
   computed from the holdings partition (`pipeline.fragment_rounds`
   already computes exactly this from holdings), and `derived_split :=
   holdings span both worlds` (both sides non-empty). The rule form is
   unchanged (`local iff rounds>=2 AND split else central`); only the
   inputs change from declared to derived. Declared `expected_rounds` /
   `split_state`, if present, are ignored and both derived values plus
   the provenance (`inputs_derived_from: holdings`) are recorded in the
   routing ledger entry. S1/S2 must route identically to today (their
   declared fields agree with derivation — asserted by test).
3. Policy hook: an optional per-task lane override supplied by the caller
   (`lane_override: central|local|null`), recorded in the routing entry
   (`override: true/false`, `rule_lane`, `final_lane`). Unset/null =
   rule decides (inert default, R1-hooks precedent). This is the handle
   the recipe grips: recipe application = feature lookup → override flag.

Why it creates recipe surface: lane assignment becomes a function of task
content (grid + holdings partition); lane costs (central vs direct bytes)
are content-sensitive in magnitude AND cross over (X3 H3a cut: central wins
small/low-dialogue, local wins dialogue-heavy — already evidenced, not
hoped for). A recipe mapping observable features
{n_tasks, derived_rounds, derived_split, pref_mass, ...} → lane can beat
fixed-lane paths on a family spanning the crossover. The differential
machinery already exists and is calibrated (2.61x, EXPECTED pins); the
delta only removes the consumer-interface gate blocking it.

Preserves: solver + assignments (untouched); ledger append-only semantics;
all ORG-OPS clauses (no op signatures change except additive optional
args); S1/S2 byte-exactness (guard test); settle atomicity + interruption
boundaries (no new append sequences on clean paths — one routing entry as
today, with extra payload fields); frozen-tree compat (delta lives in a new
dir; successor-003 untouched).

Cost/risk: LOW-MEDIUM. ~50-150 lines (schema validation, derivation fn,
override plumbing, tests). Main risk is design-side, not code-side: the
holdings partition for novel tasks must come from somewhere — if the task
generator assigns holdings, the recipe partly learns generator structure
(see open question Q1, §7; mitigated by pre-registering varied partition
schemes and requiring the crossover to persist across schemes).

How it could still fail: (a) the central/local byte crossover may not
materialize within the generatable family (e.g. if byte gaps are monotonic
in the generatable range) — then the recipe is again degenerate and L2
reproduces a negative at higher cost; mitigate with throwaway calibration
probes BEFORE prereg (§6 step 0) with an abort criterion. (b) Ledger
entries/invokes are likely lane-INVARIANT (same plan steps both lanes), so
entries cannot be the primary unit — L2 must promote central_bytes to
primary (principled: it is the host's own canonical cost model, LIMITS-4).
(c) If derived_rounds rarely varies under natural holdings splits, the
family must force it via partition schemes — pushing content-dependence
toward the generator (Q1 again).

### Option B — Metered solver + differentially-scaling arms

Mechanism sketch: (1) instrument `domain.solve` to count search effort
(backtrack nodes / partial-assignment visits) and record it in the invoke
payload + solution artifact (result identical, cost now content-sensitive);
(2) give the two arms DIFFERENT scaling: keep reuse as whole-task solve,
change split-pair to partitioned solve (each child solves a holdings-half,
merge step reconciles) so search cost scales differently per arm
(superadditive whole-solve vs partitioned-solve + fixed merge overhead →
crossover: split wins hard/large, reuse wins easy/small).

Why it creates recipe surface: ledger-visible cost becomes a function of
task constrainedness with a genuine crossover driven by algorithmic
scaling, not pipeline constants. Recipe maps hardness features (window
tightness, precedence density, size) → arm.

Preserves: final assignments/VALID (same solver, same optimum — merge must
be proven optimum-preserving); ledger append-only shape; lineage/lifecycle
clauses.

Cost/risk: MEDIUM-HIGH. Partitioned-correct-solve + optimum-preserving
merge is new algorithmic semantics (not plumbing): needs its own proof +
conformance tests; merge bugs could silently change quality (violates the
loud-failure norm). The crossover is unproven until built (partition
overhead may dominate everywhere, or nowhere). Bigger review + verification
burden than A.

How it could still fail: (a) no crossover in practice (most likely failure:
merge overhead dominates at toy scale 4-6, reproducing always-reuse);
(b) metering without differential scaling is vacuous — both arms shift
together and no decision surface appears (metering alone is NOT sufficient;
the risky partitioned-solve half is load-bearing); (c) toy-scale search
costs may be too small/noisy to fit stable recipes (all tasks solve in
dozens of nodes).

### Option C — Policy hook with recorded decisions (learnable lane; enabler, not standalone)

Mechanism sketch: add a host-supported decision point at an existing branch
(lane selection, clarify granularity — one-fragment-per-round vs batched —
or reuse-vs-split choice) where an external policy object supplies the
decision, the host executes it and records {decision, policy_ref, context
features, outcome} in the ledger. Default-unset = current behavior
(inert-when-unset, R1-hooks precedent).

Why it creates recipe surface: it does NOT, by itself — it creates the
*recording and application plumbing* for a learnable lane. It turns an
existing-or-new content-sensitive cost difference into a fittable,
transferable policy object with ledger provenance. It is the necessary
complement to A or B (A already includes the minimal hook: per-task lane
override), not an alternative to them.

Preserves: everything when unset (purely additive); contract changes are
additive payload fields.

Cost/risk: LOW for one hook (lane override); MEDIUM for a general policy
object with feature-context recording. Risk: over-generalizing into a
policy framework (sprawl) — must stay one hook, one decision.

How it could still fail: without A/B-style content-sensitive costs, the
hook records decisions that do not matter (all paths cost the same) — a
learnable lane over a flat landscape learns nothing. C never runs alone.

### Option D — No host change: differential-solvability family on successor-003 as-is

Mechanism sketch: construct task families where the arms differ in SUCCESS
rather than cost (tasks failing on one arm, succeeding on the other), or
fit recipes on wall-clock solver time (§2.6), or extend L1-secondary-style
routing prediction to a larger descriptor set.

Why it (nominally) creates surface: none of these creates performance
transfer surface. Success is solver-determined and shared by both arms, so
joint success/failure moves together (a task failing `solve` fails both
arms — loud `ValueError`, as L1 PROBE-4 showed); grants are non-binding
(costs 0.0 USD / 1.0s vs fixed limits), so no arm can fail on budget;
adapters v1/v2 both drop prefs identically for solve purposes. Wall-clock
is rejected (§2.6). Routing prediction without execution is advisory only
(L1-secondary precedent).

Preserves: everything (no change) — and proves nothing new. This option is
included to record its rejection: running "L2" on the frozen host would
re-spend acquisition to re-derive the L1 negative (or launder a wall-clock
positive that no independent lane could reproduce).

Cost/risk: LOW cost, HIGH information risk (false positive on noise, or a
second negative that teaches nothing L1 did not).

## 4. Recommendation

**Recommended: Option A (content-derived routing + open lane execution),
with the Option C lane-override hook as its built-in application handle —
as the smallest host delta (§5) enabling L2-execute (§6).**

Why A over B: A unlocks a differential mechanism that already exists,
is already calibrated (S1/S2 EXPECTED pins, 2.61x, X3 H3a crossover
evidence), and is already the host's canonical cost model (lane bytes,
LIMITS-4). B invents new algorithmic semantics (partitioned solve +
optimum-preserving merge) whose crossover is unproven and whose failure
mode (silent quality change) cuts against the host's loud-failure norm.
A is ~plumbing; B is ~research. If A's calibration probes (§6 step 0) show
no crossover in the generatable range, that itself is a cheap, decisive
result (kill L2-execute, pivot to mapping work — see §9), whereas B's
failure would arrive only after building new solver semantics.

Why A+C over C or D alone: C without content-sensitive costs is a
recorder over a flat landscape; D re-spends budget to re-learn L1.

What A+C deliberately does NOT do: no solver change, no new capabilities
or representations (ORG-OPS §7 exclusions stand), no grant/budget semantics
change, no cross-host anything, no general policy framework (one hook, one
decision). The learned content (a lane rule) will partly re-discover the
built-in rule — that is accepted and reframed honestly: L2 is a positive
control for the recipe methodology (can extraction→transfer→net-gain
re-discover a KNOWN crossover?), not a hunt for unknown knowledge (see §9
for where unknown-knowledge bets live).

## 5. Specified host delta (the smallest change enabling L2-execute)

Target: a NEW successor dir (working name `successor-004-lane`, to be fixed
at build authorization), copied from frozen successor-003 + ONLY the delta
below. successor-003 itself is never modified.

Delta H2 (three additive items; nothing else):
- H2.1 Open lane execution: `run_tasks` accepts a task-JSON path for novel
  lane tasks (grid + holdings + adapter, schema-validated: required keys
  `task_id, slots, tasks, precedence, prefs, holdings, adapter`; holdings
  must reference exactly the grid's tasks/prefs, both worlds present).
  Unknown task NAMES still raise (S3/S4/S6 routing unchanged); only
  explicit task-JSON files take the new path. Execution flows through the
  unmodified `run_sched_task` pipeline.
- H2.2 Derived routing inputs: `route()` gains a derivation step —
  `derived_rounds = len(fragment_rounds(task))`,
  `derived_split = both holdings sides non-empty` — computed from the
  validated task; the rule `local iff rounds>=2 AND split else central`
  applies to the DERIVED values. Routing ledger entries record
  `{rule, inputs: {derived_rounds, derived_split}, inputs_derived_from:
  "holdings", declared_ignored: {...if present...}}`. Declared
  `expected_rounds`/`split_state` are ignored (never trusted, never
  error). S1/S2 route exactly as today (guard test).
- H2.3 Lane-override hook: optional caller arg `lane_override ∈
  {central, local, None}` per task (CLI flag + api param), threaded to
  the `LaneCtx` selection; routing entries record `{rule_lane,
  override: bool, final_lane}`. `None` (default) = rule decides; hooks
  are inert-when-unset.

Acceptance bar for the delta itself (must pass BEFORE any L2-execute run;
independent verification lane as in R1):
1. Existing suites green on the new tree: conformance 9/9, atomicity 27/27
   (or current counts), accept field comparison vs successor-003 (S1/S2
   byte-exact: lanes + 655/0 + 310/500 + 2.61x calibration reproduced).
2. Novel-lane conformance (new tests, builder-written, verifier re-run):
   schema validation refuses malformed tasks loudly (no partial runs);
   derived routing matches hand-computed derivation on a pinned set;
   S1/S2-by-JSON route identically to S1/S2-by-name; override=true/false
   recorded correctly; unset hook = rule path byte-identical to no-hook.
3. Conservation + recovery on novel lane tasks: ledger conserves on every
   test run; kill-resume (`ops kill-resume` shape) converges on at least
   one novel lane task; `inspect` reports clean.
4. successor-003 frozen intact (IDENTITY 45/45 before AND after); new tree
   carries its own IDENTITY + FROZEN-BASELINE convention.
5. Verdict: ACCEPT (possibly WITH-NOTES as in L1/R1) by an independent
   lane. L2-execute is BLOCKED until this bar passes.

Explicit non-goals for H2: solver, grants, capabilities, representations,
settle/fuse/fission/quarantine semantics, SST leg, cross-host — all
byte-identical behavior to successor-003.

## 6. L2-execute pre-registration DRAFT (full; to be frozen at authorization)

This draft is complete enough to execute from after pins + step-0 probes.
It is NOT yet frozen (no task bytes exist; step-0 calibration has not run).

### Step 0 — Throwaway calibration probes (pre-prereg, L1 §DESIGN-2 precedent)

On the ACCEPTED H2 tree only, with throwaway `L2P-*` IDs never reused as
train/test: run both lanes (override central/local) on ~6-10 probe grids
spanning sizes 4/5/6 × holdings splits (1..4 derived rounds × split True
(mandatory for lane tasks) — plus tiny unsplit holdings for the central
corner). Record per-task×lane: VALID, central_bytes, direct_bytes, ledger
entries, invokes. ABORT CRITERION (frozen here): if no probe pair shows a
lane crossover (some probe cheaper-central AND some probe cheaper-local in
central_bytes, both VALID), L2-execute DOES NOT PROCEED — report the
no-crossover finding and pivot to §9 mapping work. Otherwise the probe
results size the family (round-counts and sizes that straddle the observed
crossover) and are then discarded from the experiment.

### Task family (frozen by a new `gen_tasks_l2.py`)

Lane tasks (grid + holdings + adapter), built ONLY by solvability-preserving
transforms (L1 `gen_tasks.py` label-permutation + machine-swap, same bases
T4/T5/T6) PLUS pre-registered holdings-partition schemes (e.g. even split,
2-vs-rest, prefs-together/reqs-split) chosen to span derived_rounds ∈
{1,2,3,4} per step-0. Sizes 4/5/6.
- TRAIN (extraction only): 8 tasks (sizes and schemes fixed post-step-0,
  e.g. 3×size-4, 3×size-5, 2×size-6 across ≥3 partition schemes).
- TEST (held-out): 16 tasks, disjoint seeds from train, same size/scheme
  coverage (≥2 per scheme). Never executed/routed before the transfer test.
- Generator pin + all task sha256 pins committed to the anchored prereg log
  (L1 lesson A). Any host-reported failure preserved; tasks never replaced.

### Recipe representation + extraction (mechanical, `harness_l2.py extract`)

Recipe R-lane: JSON decision list mapping task features
`{n_tasks, derived_rounds, derived_split, n_prefs}` (all computable from
the task file WITHOUT execution) to a lane ∈ {central, local}, plus
`default`. Fit: for each TRAIN task run BOTH lanes on FRESH state dirs
(`init` → `run lane-task --lane-override <lane>` → `settle`; H2.3 hook),
record VALID + central_bytes + entries + invokes; per feature-group the
cheaper-in-central_bytes VALID lane wins (majority over members); ties →
globally cheaper lane; groups with any failure → successful lane or
`default` (reported, never hidden). Emit `recipe.json` (mode 444) +
`extraction-log.json`. Acquisition = central_bytes + entries + invokes
summed over ALL training runs (both lanes, setup included).

### Held-out split + baselines

- Held-out: the 16 TEST tasks (pins in frozen prereg). Transfer test
  (`harness_l2.py transfer`): recipe-prescribed lane per task via H2.3
  override, fresh dirs, same setup + settle.
- PRIMARY baseline (`harness_l2.py baseline`): the HOST RULE lane per task
  (no override — cold, competent, zero training knowledge; the built-in
  X3-cut rule). Fixed BEFORE extraction results exist.
- Reference lines (reported, non-binding): always-central and always-local
  on the same 16 tasks (context for P1/P3 interpretation, exactly as L1's
  always-reuse line).

### Metrics + acquisition accounting

Per task×lane (from OUR run dirs only): VALID (solution artifacts),
central_bytes PRIMARY (host-canonical coordinator cost, recomputed from
durable state per `lane_bytes`), direct_bytes (recorded), ledger entries +
invokes (pipeline-overhead guards), wall time (recorded, non-binding).
Calibration guard: every setup-equivalent run must reproduce S1/S2
EXPECTED lanes+bytes on demand (guard batch: 2 S1/S2-by-name runs per
phase; any deviation voids the phase — method failure, not a result).
Acquisition charged IN FULL against held-out gains (L1 discipline, no
amortization): recipe_total = acquisition + transfer-arms; baseline_total
= host-rule arms on the same 16 tasks.

### Thresholds — EXACT CODED PREDICATES (verbatim; L1 lesson B)

The frozen prereg will contain this exact code block, and the verdict
script will import these predicates (not reimplement them):

```python
N_TEST = 16
# P1: task-conditional content — recipe differs from BOTH fixed lanes
diff_central = sum(1 for t in TEST if recipe_lane[t] != "central")
diff_local = sum(1 for t in TEST if recipe_lane[t] != "local")
P1 = (diff_central >= 2) and (diff_local >= 2)
# P2: success parity — all VALID in both arms (strict; see note)
P2 = (n_valid_transfer == N_TEST) and (n_valid_baseline == N_TEST)
# P3: net gain in central_bytes (acquisition charged) + no entry regression
P3 = ((acq_central_bytes + transfer_central_bytes < baseline_central_bytes)
      and (transfer_entries <= baseline_entries)
      and (transfer_invokes <= baseline_invokes))
OVERALL = "PASS" if (P1 and P2 and P3) else "NEGATIVE"
```

Notes (part of the prereg, frozen): P2 deliberately requires all-VALID
both arms (L1's coded behavior, stated upfront this time — NOT "equal
rates" prose). P3's primary unit is central_bytes because lanes share plan
steps (entries/invokes are expected lane-invariant, hence guards with
`<=` on test arms only, NOT charged with acquisition — entries measure
pipeline overhead which the recipe must not regress; bytes measure lane
cost which must improve net). Secondary (advisory): recipe test bytes vs
each fixed-lane line; recipe-vs-rule agreement rate (re-discovery
measure); per-scheme breakdown.

### Predicted outcome (design-time expectation, NOT a result)

If step-0 finds the X3-style crossover: recipe re-discovers approximately
the host rule (high agreement), P1 PASS (differs from fixed lanes wherever
the family straddles the cut), P2 PASS (all VALID), P3 depends on
crossover magnitude × 16 vs 16-run acquisition — PASS iff mean per-task
byte saving vs the rule exceeds mean acquisition cost per test task. NOTE:
vs the host RULE (already near-optimal), P3 is the hard, honest bar; a
P1∧P2 PASS with P3 FAIL is still informative (methodology positive,
net-gain negative — bounds the value of re-discovery). If step-0 finds no
crossover: L2-execute aborts per the frozen criterion (a second clean
negative arrived at for the price of probes, not a full experiment).

### Analysis rules (frozen, carried from L1 PREREG §4 + lessons)

No task replacement/re-rolls/single-shot transfer+baseline; recipe frozen
(mode 444 + sha in anchored log) after extraction, consumed read-only;
all commands/raw logs/ledgers preserved under `runs/` + `logs/`; prereg
bytes (this §6 completed with pins) committed to the append-only anchored
log BEFORE step-1 extraction (step-0 probes explicitly pre-prereg with
throwaway IDs); verdict script imports the §6 predicate block verbatim.
Harness fixes allowed ONLY before the transfer test starts, logged (L1
EVIDENCE §5 precedent).

## 7. Open questions (must be settled at L2-execute authorization)

- Q1 Who partitions holdings? The generator assigning holdings means the
  recipe's key feature (derived_rounds) is generator-structured. Options:
  (a) accept, with ≥3 pre-registered partition schemes + per-scheme
  breakdown (recipe must win within schemes, not just across them);
  (b) host derives a canonical partition from grid content (e.g.
  deterministic task-halving) — moves structure into the host, bigger
  delta. Draft recommends (a); (b) is the fallback if step-0 shows
  scheme-confounded crossovers.
- Q2 Exact train/test sizes: 8/16 is a starting bid. Step-0 effect sizes
  should set N_TEST (larger if per-task savings are small — fixed in
  prereg, NOT tuned after seeing transfer data).
- Q3 Guard semantics if entries turn out lane-VARIANT: if step-0 shows
  entries differ by lane (unexpected — same plan steps), the prereg may
  promote entries to co-primary with strict inequality; decide at freeze
  time, record the choice.
- Q4 Override shape: per-task flag (draft) vs feature→lane policy file.
  Per-task is simplest and keeps the recipe (feature→lane JSON) separate
  from the mechanism; a policy-file hook would merge them (C-sprawl risk).
- Q5 Should the recipe ALSO be tested against a shuffled-holdings
  ablation (same grids, permuted partitions) to separate grid-content
  from partition-content? Recommended as a secondary analysis if budget
  allows — it directly answers "what did the recipe learn."
- Q6 Anchored prereg log: git repo vs append-only log file with
  coordinator countersignature — coordinator to provide before freeze
  (L1 lesson A is otherwise unfixable).

## 8. Exact authorization needed for L2-execute

Two separable authorizations (either may be declined independently):

AUTH-1 (host delta build): permission to copy frozen successor-003 to a
new dir + implement ONLY delta H2 (§5, three items) + builder tests, then
submit to an independent verification lane against the §5 acceptance bar
(5 checks). Estimated small (one build agent + one verifier, same pattern
as R1). Blocking precondition for everything below.

AUTH-2 (L2-execute experiment): on the ACCEPTED H2 tree only — permission
to run step-0 throwaway probes, then (if the abort criterion passes) freeze
the §6 prereg with pins to the anchored log (Q6) and run
extract→transfer→baseline→verdict in a new `L2-transfer/` work dir,
followed by independent verification (L1 pattern). Explicitly includes:
24+ task generations, ~48 training+test lane runs + guard batches, all
state inside the L2 work dir, frozen trees read-only.

If AUTH-1 is declined: L2-execute cannot run (no as-is surface, §2) — the
honest next step is §9 mapping work against the frozen host, not a
re-scoped transfer claim.

## 9. Frank section: is recipe transfer the right next learning bet?

Context for "vectors 13/15": taken here as (13) learned-mapping
experiments — fitting predictive models (feature→cost/lane/quality
mappings, adapters, evaluators) from run observations — and (15)
policy-invention experiments — the host inventing genuinely new local
policies (routing rules, revision triggers, adaptation moves) beyond
built-in ones. (If the coordinator's numbering differs, this section's
argument survives under the plain-language readings.)

The uncomfortable fact: L2 as designed (§6) is a POSITIVE CONTROL, not a
discovery experiment. The H2 delta builds a surface whose crossover (X3
H3a cut) the builders already know, then tests whether the recipe pipeline
re-discovers it. A PASS validates the recipe methodology
(extraction→freeze→transfer→net-gain accounting — the L1 harness was
built for exactly this and deserves its positive control); it does NOT
produce knowledge the programme didn't have. Price that honestly against
the alternatives:

- Vector 13 (mapping) DOMINATES on novelty-per-cost right now. A cost
  model (grid+holdings features → central_bytes per lane) can be fitted
  against the FROZEN host — prediction needs execution, not a new decision
  surface: S1/S2 give 2 points, and every L1 run dir + cheap new frozen-S1/S2
  re-runs are free observations; larger observation budgets need only
  machine time, no host change. L1-secondary's lesson (2 observations
  underdetermine the AND rule) cuts both ways: it shows few-shot mapping
  is hard — which is exactly why a mapping vector with a REAL observation
  budget (dozens of runs, varied descriptors via explain-route +
  executed S1/S2 confirmations) is the experiment that could learn
  something new (a calibrated cost model usable for planning) instead of
  re-learning the lane rule. Mapping work is also concurrent-safe with
  AUTH-1/2 (frozen host, separate dir).
- Vector 15 (policy invention) is the highest-value and highest-risk bet,
  and it is PREMATURE today: invention needs (a) a decision surface to
  invent over, (b) a policy representation with safety rails, (c) an
  evaluation loop. (a) is what H2 builds — so 15 is downstream of AUTH-1
  regardless. Attempting 15 before H2 lands means inventing policies for
  branch points that don't exist (flat landscape, §3-C failure mode).
  Sequence: H2 → L2 (validates the surface + methodology) → 15 (invents
  on the validated surface).
- Recipe transfer (L2) DOMINATES on boundedness and falsifiability. It is
  the only vector with a pre-registered, mechanically-verdictable design
  executable in days on the L1 pattern, with a frozen abort criterion
  (step-0) that caps downside at probe cost. If the programme needs a
  near-term learning-side result to pair with R1's robustness result, L2
  is the right bet. If the programme optimizes for novel learned content
  per unit effort, vector 13 first, L2 as the methodology control, 15
  gated on H2.

Bottom line: recommend L2-execute (bounded, falsifiable, reuses the L1
harness investment) AND concurrent vector-13 mapping work on the frozen
host (cheap, the only near-term source of genuinely new learned content),
with vector 15 explicitly sequenced after H2 acceptance. Do not sell an
L2 PASS as discovery — sell it as the validated instrument that later
discovery vectors (15, richer recipes) will need.

## 10. What evidence would change this recommendation

- Step-0 no-crossover (or crossover confined to degenerate corners, e.g.
  only unsplit holdings): kill L2-execute (§6 abort), pivot the learning
  budget to vector 13. Would also weaken the case for H2-dependent 15.
- A demonstrated as-is surface I missed (e.g. a content-sensitive ledger
  signal on the frozen host beyond wall-clock): re-scope L2-execute to
  the frozen tree, skip AUTH-1. Bar: the signal must be ledger- or
  artifact-recorded (independently re-derivable), content-sensitive, and
  crossed within a generatable family — wall-clock does not qualify (§2.6).
- Step-0 crossover MUCH larger than X3 suggests (order-of-magnitude byte
  gaps): consider promoting P3-vs-rule expectations and enlarging N_TEST
  at freeze; consider whether the recipe could BEAT the rule somewhere
  (rule suboptimality — the discovery-flavored L2 outcome).
- Evidence that holdings-partitioning (Q1a) fully explains the crossover with
  zero grid-content contribution: downgrade L2 to "generator-structure
  re-discovery" (still a valid control, weaker story) and prefer Q1b or
  vector 13.
- Coordinator renumbering/scope of vectors 13/15 that contradicts §9's
  reading: §9's sequencing argument (mapping-concurrent, invention-gated-
  on-surface) should be re-checked against the true definitions, but the
  surface-dependence logic stands regardless of labels.

---
*End of L2-DESIGN.md (design only; no code, no runs, no modifications
outside this dir). Authoritative inputs: files listed in the header; all
line/file claims above refer to the frozen trees as read on 2026-10-04.*



