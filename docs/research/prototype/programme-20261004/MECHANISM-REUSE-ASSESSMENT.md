# MECHANISM-REUSE-ASSESSMENT — substrate gaps vs existing mechanisms

Date: 2026-10-07. Role: researcher (survey + recommend; no runs, no builds).
Authority: COMPLETION-MAP.md (R1–R12, Q4 ARC-negative, deferreds),
U-execute INDEPENDENT-ACCEPTANCE.md + U-OVERALL-FINAL.md (VOID change legs),
successor-004/005 trees, r1–r3 releases, X3, reuse-demo-001.
Standing constraints respected: D-005 signal semantics (five learning-signal
classes stay semantically distinct), Q4 ARC-negative (no learning in envelope;
transfer/invention negative, M1-redux instrument PASS), $0/offline/stdlib-only
except qualified SST snapshot.

Scope: four gaps — (1) local policy formation, (2) revisable cooperation
(learned revision), (3) adaptation (autonomous discovery), (4) inheritance
(developmental-recipe). For each: what exists today, concrete reuse candidates
with file pointers, tradeoffs/costs, recommendation
(reuse / adapt / build-new / defer).

Companion file: `ADAPT-EXPERIMENT-DESIGN.md` (discriminating adaptation
protocol, design only).

---

## Cross-cutting inventory (reused by several gaps)

Execution substrate (all ACCEPTED, frozen):

- `prototype/successor-005/minihost.py` — ledger/append/invoke/deny,
  grants+settle, conservation, suspend/reattach, reopen-by-replay.
- `prototype/successor-005/api.py` — consumer CLI/API (`init/run/
  explain-route/inspect/ops`, `open_run`, `run_procedure`,
  `create_proc_world`).
- `prototype/successor-005/routing.py` — `route()` hybrid rule
  (LOCAL iff expected_rounds ≥ 2 AND split_state, else CENTRAL),
  `record_routing`, `ROUTING-LOG.jsonl` mirror.
- `prototype/successor-005/pipeline.py` — `apply_revision`
  (pre-advertised v1↔v2 flip), formulate/propose/verify flow.
- `prototype/successor-005/resume.py` — `revoke_capability`,
  `reapply_revocations`, resume-by-skip, `scan_succeeded`.
- `prototype/successor-005/fusion.py` — `fuse_worlds`,
  `fission_worlds`, `reuse_composite`, `quarantine_world`,
  lineage (`derived_from`, `fusion`, `fission-of`), `lineage_ok` check.
- `prototype/successor-005/procedure.py` — OP-7 bounded procedure
  participant: advertise/run/recover, creation-fixed table, §1.4
  invocation envelope, L1–L5 interruption landings.
- `prototype/successor-005/recover.py`, `resume.py` — `ops recover`,
  `api.open_run` (restores creation lineage from ledger `create`
  payloads; raw `reopen` does not).
- `prototype/successor-005/calibrate.py` — 2.61× bytes-only calibration
  instrument (same task both lanes).
- `prototype/successor-005/vehicle/` — relcheck bundle + pins +
  readiness check (S5-A10 pattern).

Contracts (consumer-reliable):

- `prototype/successor-005/ORG-OPS.md` — OP-1..OP-7; §7 explicitly
  EXCLUDES all four gap items (policy invention, learned revision,
  recipe inheritance, autonomous discovery, new capabilities/versions
  post-creation). Any gap work that changes §7 needs a contract delta.
- `prototype/successor-005/LIMITS.md` — item 10 (no learning of any
  kind), item 6 (capability/version sets fixed at birth), item 2
  (process-crash only, no fsync).
- `prototype/successor-contract/WORLD-CONTRACT-v1.md` — C1–C7.

Evaluation instruments (reusable harnesses):

- `prototype/programme-20261004/L1-transfer/harness.py` (+ `PREREG.md`,
  `gen_tasks.py`) — extract → transfer → baseline → secondary → verdict
  pattern; frozen `recipe.json` (sha-pinned); P1/P2/P3 mechanical verdict.
  CURRENT VERDICT: clean NEGATIVE (P1 FAIL all-12 reuse, P3 FAIL
  1566v972, secondary tie 5/8).
- `prototype/programme-20261004/L2-transfer/step0/` — step-0 probe
  pattern: `STEP0-PROBES.md` pre-commit + frozen crossover criterion +
  abort. CURRENT VERDICT: ABORT (0/8 cheaper-central; byte-mass
  conservation `central_B(central) = central_B(local) + direct_B(local)`
  exact every probe; cheaper-central ungeneratable).
- `prototype/programme-20261004/M1-redux/harness.py` (+ `predicates.py`,
  `gen_main.py`, `run_main.py`) — fit→evaluate on held-out descriptors;
  verdict imports frozen predicates. CURRENT VERDICT: PASS as
  INSTRUMENT (MAE 0.00 vs const 233.25 vs rule 38.07; binding
  non-discovery — rides host (pattern,size,lane)-determinism).
- `prototype/programme-20261004/H2-lane/routing.py` — `route()` with
  `lane_override` + `derive_routing_inputs` (derived from executed
  `fragment_rounds`); legacy declared-field path preserved.
  ACCEPTED 46/46; provides a lane HOOK but per L2 no lane TRADE-OFF.
- `prototype/programme-20261004/U-execute/` — `predicates.py`
  (d12adfa2), `verdict_relcheck.py` checker (3ea4868d, 29-case battery),
  `frozen-pins.json` (15-key pins), `u-harness.py` (derive-revised-pins,
  blind-present, eval-u/eval-leg), `direct_run.py` repaired D baseline,
  `sealed/` envelope + throwaway-validation pattern, C1/C6/C11
  void/defect procedure. CURRENT VERDICT: HOST-VALUE-NOT-DEMONSTRATED;
  change legs VOID (degenerate revision, added=0 distinct (tag,file)
  pairs); H-vs-D TIED every rated leg (arm-invariant graded bytes
  099f4e33, 5065 B).
- `prototype/x3-20261004/` — `arm_c.py`/`arm_h.py`, `checker.py`
  (independent constraint checker), `xcommon.py` (central/direct byte
  metering), `frozen_inputs.py`. H3a 3-0 (ratios 0.16/0.29/0.45,
  VALID ties, recovery parity).
- `prototype/reuse-demo-001/` — `w1h_bridge.py` (explicit path importer),
  `minihost.py` (838-line second host), `test_reuse.py` (10/10),
  `REUSE-REPORT.md` (§Interface gaps = the 8-item resume-coupling list
  owed to R9).

D-005 signal semantics (binding on ANY future learning work; ANIMA
`DECISIONS-AND-CORRECTIONS.jsonl` D-005): prediction discrepancy,
explicit requirement/preference correction, independent-check failure,
evaluator defect, and comparative workflow advantage stay semantically
distinct. No future mechanism may conflate them into one "feedback" scalar.

---

## Gap 1 — Local policy formation (R1 missing piece; E4-adjacent, deferred)

### What exists today

- A HAND-WRITTEN routing policy: `routing.route()` in
  `prototype/successor-005/routing.py` (LOCAL iff rounds ≥ 2 AND split).
  Deterministic, declared-input, zero learned content.
- A content-sensitive hook: `prototype/programme-20261004/H2-lane/
  routing.py` `derive_routing_inputs()` (derived from executed
  fragment_rounds) + `lane_override` ({central, local, None},
  inert-when-unset). Accepted mechanism; dead-code question resolved
  immaterial (H2-VERIFICATION.md).
- A calibrated cost oracle: M1-redux mapping predicts per-lane
  `central_bytes` on held-out descriptors with MAE 0.00
  (`M1-redux/EVIDENCE.md` §2–§3). It is a validated INSTRUMENT, not a
  policy: it predicts cost, it does not choose lanes.
- A closed no-surface finding: L2 step-0 proved the current host family
  has NO task-conditional policy surface — local wins within-task by
  construction (strict per-task inequality), entries/invokes
  lane-invariant, byte mass conserved. Any fitted "policy" degenerates
  to always-local exactly as L1's recipe degenerated to always-reuse.

### Reuse candidates

| # | Candidate | File pointer | Reuse as |
|---|---|---|---|
| 1a | Hybrid rule + override hook | `H2-lane/routing.py` `route()`, `derive_routing_inputs()`; `successor-005/routing.py` `route()` | Policy EXECUTION point: a future learned policy plugs into `lane_override` without touching the rule default (additive, inert-when-unset precedent) |
| 1b | Cost-mapping instrument | `M1-redux/harness.py`, `M1-redux/predicates.py`, `M1-redux/gen_main.py` | Policy EVALUATION oracle: exact held-out cost predictions + frozen-predicate verdict pattern; feature partition (pattern,size,lane) |
| 1c | Calibration + metering | `successor-005/calibrate.py`; `x3-20261004/xcommon.py` | Ground-truth byte measurement both lanes, same task |
| 1d | Step-0 gate pattern | `L2-transfer/step0/` (pre-commit + frozen crossover criterion) | Cheap abort gate: any future policy experiment must first re-prove a crossover exists on its host, or abort at probe cost |

### Tradeoffs / costs

- Fitting a policy on the CURRENT host is provably pointless (L2): cost
  is lane-determined with a strict inequality, so the argmax is constant.
  Any policy-learning budget spent here buys a constant function.
- A genuine policy surface needs a HOST change first: the local lane must
  sometimes lose. Candidate trade-off sources (design sketches, not
  builds): per-lane error/retry risk, capacity/grant cost on the direct
  channel, quality differential between lanes (today quality cannot differ
  — one shared deterministic solver, LIMITS-1), or a second environment
  where central wins within-task (O-04; X3's "central wins small" was
  cross-task and does not transfer).
- D-005 cost: a policy learner must declare WHICH signal class trains it
  (prediction discrepancy on cost? comparative advantage across lanes?).
  Conflating "lane A cheaper this time" (comparative advantage) with
  "model mispredicted cost" (prediction discrepancy) is a D-005 violation.
  The M1-redux instrument already separates these cleanly (model vs rule
  vs const MAEs) — reuse that separation.
- Contract cost: ORG-OPS §7 excludes policy invention; a learned override
  needs a contract delta (who vouches for override decisions? what
  happens when the policy disagrees with the rule on a settled run?).

### Recommendation: DEFER the learner; ADAPT the instruments

- DEFER local policy formation (no trade-off surface exists; L2 proof
  stands; re-test only after a host change re-opens the surface, gated
  by the step-0 crossover pattern 1d).
- ADAPT 1b as the standing cost oracle for any future host design: before
  building a new host, specify the policy surface it would provide and
  verify M1-redux-style mapping CANNOT already arbitrate it trivially.
- BUILD-NEW (when authorized) is the trade-off surface itself — a minimal
  host delta that makes lane choice genuinely task-conditional — NOT the
  learner. The learner is a small argmax-over-oracle once the surface
  exists; building it now is building on air.

---

## Gap 2 — Revisable cooperation (R3 missing piece: learned revision)

### What exists today

- REVISE execution substrate: `pipeline.apply_revision` + ORG-OPS OP-3
  (ledger `revision` entry, ACTIVE-version switch between PRE-ADVERTISED
  versions, world records never mutated) + O3/E1–E3 flow (void-by-ruling-
  only, kept-artifact void-notice, re-proposal cites revision).
- Full drill: S3 (v1→v2 revision + SC-L→SC-S revocation + denied retry +
  escalation → ruling → void → v2 re-propose → cross-verify, VALID 4/4;
  kill between revision and re-propose covered by resume-by-skip).
- Revocation companion: `resume.revoke_capability` + mandatory
  `reapply_revocations` after reopen (OP-4; lapse demonstrated in
  conformance — the re-application obligation is load-bearing).
- Procedure-world revision path: new content ⇒ NEW world
  (`TestProcChange.test_revised_bundle_new_world` in
  `successor-005/test_procedure.py:1616+`; `revise_op` never used for
  procedure revision, LIMITS-14). Advertise-time validation refuses
  malformed revisions pre-work (S5-A8).
- Change-evaluation harness: U-execute P9 shape rule + `derive-revised-
  pins` + sealed envelope + throwaway validation (currently VOID on a
  degenerate revision — see companion design for the repair).

### Reuse candidates

| # | Candidate | File pointer | Reuse as |
|---|---|---|---|
| 2a | Revision execution flow | `successor-005/pipeline.py` `apply_revision`; S3 drill (`successor_demo.py`, `REPORT.md` §5); OP-3 | Unchanged SUBSTRATE: whatever a learned trigger decides, this flow executes it with ruling/void/lineage guarantees |
| 2b | New-world revision + advertise gate | `successor-005/procedure.py` + `test_procedure.py:1616+` (TestProcChange); S5-A8 legs | Content-bearing revision path (genuinely new bytes go here, never into `revise_op`); fail-closed malformed-revision refusal |
| 2c | Sealed-envelope + P9 conformance | `U-execute/u-harness.py` derive-revised-pins; `U-execute/PREREG.md` P9/C6; `sealed/REVISION-MANIFEST.json` | Evaluation harness for revision QUALITY: mechanical shape conformance (distinct (tag,file) counting) + authenticity + throwaway validation |
| 2d | Revocation + reapply obligation | `successor-005/resume.py`; OP-4; `test_conformance.py` lapse leg | Template for durable partner-switching: any learned re-routing of cooperation must survive reopen (reapply-pattern) or loudly lapse |

### Tradeoffs / costs

- Two separable sub-problems with very different costs: (i) revision
  TRIGGER (when to revise, given evidence) — a policy over D-005 signals,
  moderate cost, evaluable against 2c; (ii) revision CONTENT invention
  (what new version to propose beyond the pre-advertised set) — breaks
  LIMITS-6 unless routed via 2b new-world path; high cost, needs the
  repaired held-out-change protocol (companion file) before any claim.
- D-005 cost is highest here: a revision trigger fires on SOME signal —
  prediction discrepancy (v1 output diverged from expectation)?
  independent-check failure (cross-verify failed)? explicit correction
  (coordinator ruled)? evaluator defect (checker wrong)? These demand
  DIFFERENT responses (re-propose vs escalate vs fix-checker), and the
  S3 drill already distinguishes ruling-driven void from autonomous
  retry (denied retry leg). A learned trigger that fires one "revise!"
  output for all five classes destroys that structure. Each trigger
  input must be single-class-labeled.
- The U VOID is a direct warning for content invention: the held-out
  author, optimizing for "minimal and behavior-preserving," produced a
  degenerate no-op (duplicate suite entry, same log file, exit-0-always
  assay). Learned revision content needs a NON-DEGENERACY bar (new bytes
  that change at least one graded bit — see companion §3), or it will
  converge on the same no-op optimum.

### Recommendation: ADAPT substrate + harness; BUILD-NEW only the trigger; DEFER content invention

- REUSE 2a as-is (no changes to the ruling/void/re-propose flow).
- ADAPT 2c per the companion design (non-degeneracy predicates added;
  shape rule kept) as the standing revision evaluator.
- BUILD-NEW (small, when authorized): a single-signal revision TRIGGER —
  e.g. independent-check-failure → re-propose-under-v2 — with the signal
  class declared in its prereg and the S3 drill as its baseline. One
  signal class, one response, pre-registered.
- DEFER revision content invention beyond the pre-advertised set (except
  via the 2b new-world path, which already works structurally) until the
  repaired adaptation protocol (companion) demonstrates a discriminable
  revision-quality gap. Do not build a version inventor against an
  evaluation that cannot tell versions apart.

---

## Gap 3 — Adaptation (R7 missing piece: autonomous discovery)

### What exists today

- AUTHORIZED-mechanism adaptation (R7 PARTIAL): the S3 drill
  (revision + revocation mid-task → escalation → ruling → void-notice →
  re-propose by new owner → VALID). Adaptation runs through
  revise/revoke/rule — every step pre-authorized, content pre-advertised.
- Procedure adaptation shape: new-world revision + cost-to-adapt counters
  (TestProcChange), advertise-time malformed-revision refusal (S5-A8).
- U CELL-ADAPT design (PREREG §6 + C9): both arms must reach VALID under
  the revised bundle; H CELL-ADAPT = VALID ∧ `p_change_leg_shape` (new
  world + disjoint bundle pin); D CELL-ADAPT = VALID; cost-to-adapt
  counts REPORTED. Preregistered expectation was honest parity on a
  well-formed revision (no rigged defect). CURRENT STATE: UNTESTED (VOID).
- Q4 ARC-negative bounds the ambition: no learning in s005 (LIMITS-10);
  transfer has no surface (L1 + L2-closed); mapping is a validated
  instrument (M1-redux), not discovery; invention gated (no trade-off
  surface). Autonomous discovery = B-frontier DEFERRED (COMPLETION-MAP R7).

### Reuse candidates

| # | Candidate | File pointer | Reuse as |
|---|---|---|---|
| 3a | S3 authorized-adaptation drill | `successor-005/successor_demo.py` S3 leg; `REPORT.md` §5; X3-T2 (`x3-20261004/RESULT.md` T2: resume0, esc=1 H) | BASELINE behavior: any discovery claim must beat this drill's outcome (VALID + cost) on the same stimulus class |
| 3b | U CELL-ADAPT + change predicates | `U-execute/predicates.py` (`p_change_leg_shape`, `p_steps_complete` w/ steps universe, `p_ledger_report_agree`, `p_sst_snapshot_confined`); `PREREG.md` §6/C9 | Adaptation MEASUREMENT: validity-under-revision + new-world discipline + accountability (H-only predicates have no D analogue — the accountability cell) |
| 3c | Advertise-time refusal gate | `successor-005/procedure.py` advertise validation; S5-A8 legs | Fail-closed FRONTIER for discovery: candidate adaptations validate pre-work; malformed ⇒ refuse with zero ledger effect |
| 3d | Companion protocol | `ADAPT-EXPERIMENT-DESIGN.md` (this programme dir) | THE next step: repaired held-out-change construction + discriminating measurements + blinding + budget |

### Tradeoffs / costs

- Execution vs discovery are different claims sharing one word. Executing
  a supplied revision (3a/3b) is demonstrated machinery; DISCOVERING a
  response to a novel stimulus is unbuilt and currently unmeasurable
  (U change legs VOID; no valid held-out change has ever been graded).
  Building discovery machinery before the measurement exists repeats the
  U failure mode (machinery without a discriminating stimulus).
- D-005 cost: "adaptation" as a single capability conflates responses to
  all five signal classes. The companion design restricts the next
  protocol to ONE declared class (explicit requirement correction =
  revised bundle) and forbids generalizing the result to other classes.
  A discovery mechanism must likewise declare its stimulus class; a
  mechanism that "adapts" without naming what it adapts TO is untestable.
- Cost evidence from U: H-vs-D TIED everywhere with arm-invariant graded
  bytes. There is currently ZERO evidence that any autonomous mechanism
  would outperform a competent direct baseline on adaptation tasks in
  this envelope. The burden of proof is on the protocol first.

### Recommendation: ADAPT measurement now; DEFER discovery machinery until the protocol discriminates

- ADAPT 3b + 3c per the companion design and RUN the repaired protocol
  (design-only in this delegation; execution is a future authorized
  objective). This is the only adaptation work currently justified.
- REUSE 3a as the baseline every future adaptation claim must beat.
- DEFER autonomous discovery machinery (inventors, searchers, mutators —
  incl. D-008 primitive mutation/evolution) until the repaired protocol
  shows a discriminable gap between authorized-mechanism adaptation and
  something better. If the repaired protocol still ties H-vs-D, the
  honest finding is that authorized mechanisms suffice in-envelope, and
  discovery stays B-frontier.

---

## Gap 4 — Inheritance (R6 missing piece: developmental-recipe inheritance)

### What exists today

- STRUCTURAL inheritance (works, accepted): `derived_from` lineage +
  `fusion`/`fission-of` entries + `lineage_ok` gate (≥2 `derived_from`
  resolving to ledger `create` entries + ledger `fusion` entry, else
  loud `AssertionError`, no work done — OP-2). Composite reuse VALID
  5/5 (S4), fission reuse VALID 4/4 (S6). Mechanism inventory before/
  after (8→7 fusion, channel restore fission).
- CROSS-HOST reuse (works, accepted): reuse-demo-001 drove UNMODIFIED
  `resume_to_verdict` (~171/235 lines) through a kill boundary on a
  separate 838-line host: 10/10 tests, SIGKILL rc=-9, 0 re-invokes
  (Q3 DEMONSTRATED-WITH-COUPLING-LIST). The 8 interface gaps found are
  the owed coupling list (REUSE-REPORT.md §Interface gaps → R9).
- RECIPE inheritance (negative, closed in-envelope): L1 extracted a
  recipe from 6 train tasks and tested held-out transfer — the recipe
  had NO task-conditional content (all 12 choices = reuse), P3 net-gain
  FAIL (1566v972 entries), secondary tie. "No surface in the r1 envelope
  for org-path transfer to grip" (L1 EVIDENCE.md §1). L2 confirmed for
  the H2 lane family (always-local degeneracy).
- Developmental framing stays INSP: A2/A4/V16 (endosymbiosis,
  co-adaptation, selection, inheritable lineage, HW/SW co-evolution)
  are inspiration/ambition with D-004 conditions — never cited as
  results, never relabeled as doctrine (COMPLETION-MAP §§3–4).

### Reuse candidates

| # | Candidate | File pointer | Reuse as |
|---|---|---|---|
| 4a | Lineage carrier format | `successor-005/fusion.py` (lineage entries); OP-1/OP-6 §5 lineage clauses; `artifacts/fusion-record.json`, `fission-record.json` | CARRIER: a future recipe artifact attaches to `derived_from`/`fusion-of` exactly like existing lineage; the `lineage_ok` gate pattern extends to recipe-presence checks |
| 4b | Cross-host transport | `reuse-demo-001/w1h_bridge.py` (explicit path importer, no copy); `REUSE-REPORT.md` (171-line reuse account + 8-item coupling list) | TRANSPORT: the demonstrated pattern for one host consuming another's capability bytes unmodified; coupling list is the porting contract |
| 4c | Transfer-evaluation template | `L1-transfer/harness.py` (extract/transfer/baseline/ secondary/verdict), `L1-transfer/PREREG.md` (P1 conditional-content / P2 parity / P3 net-gain incl. acquisition cost) | EVALUATOR: the exact three-predicate shape (conditionality + parity + NET gain with acquisition counted) any inheritance claim must pass; P1 (differs from BOTH fixed paths) is the anti-degeneracy predicate L1 already validated |
| 4d | Unfamiliar-work differential | (none exists — O-04 second environment deferred; V10 loop direction-only) | The MISSING ingredient: a task family where descendants plausibly outperform cold baselines. Nothing to reuse; must be built or deferred |

### Tradeoffs / costs

- Carrier (4a) and transport (4b) are SOLVED and cheap — inheriting
  POINTERS (lineage) and BYTES (bridge import) works. The gap is purely
  CONTENT: a recipe whose inheritance produces descendant advantage on
  UNFAMILIAR work. L1 proved content has no surface in the current
  envelope (fixed pipelines, constant costs, shared solver).
- The L1 P1 predicate (recipe differs from BOTH fixed paths on ≥2
  held-out tasks) is the key anti-degeneracy asset: it caught always-
  reuse mechanically. Any future inheritance protocol MUST keep an
  equivalent P1 — without it, "inheritance" degenerates to "descendant
  does the one thing the envelope allows" (cf. U's degenerate revision,
  same failure shape one level up).
- Acquisition-cost accounting (L1 P3: extraction + recipe < baseline) is
  the second load-bearing asset: inheritance that costs more to transmit
  than it saves is not an advantage. D-005 adds: the inherited content's
  signal class must be declared (a recipe learned from comparative
  advantage is not evidence about prediction-discrepancy learning).
- 4d is the expensive item: unfamiliar-work families need a solvability
  story (L1 DESIGN §2: the generator must preserve solvability — the
  hand-edited PROBE-4 `ValueError: no valid schedule` is the warning),
  held-out discipline (never executed during extraction), and a competent
  cold baseline through the same consumer interfaces. O-04 (second
  meaningfully-different environment) is the natural home; it is deferred
  with good reason (cost) and should not be smuggled in as a side quest.

### Recommendation: REUSE carrier + transport + evaluator; DEFER advantage claims; BUILD-NEW only 4d and only if O-04 opens

- REUSE 4a/4b/4c without modification: lineage carries, bridge transports,
  L1 three-predicate shape judges. No new inheritance machinery is needed
  at the mechanism level.
- DEFER developmental-recipe advantage claims (L1 negative stands;
  no surface; nothing has changed since).
- BUILD-NEW 4d ONLY as part of an authorized O-04 second-environment
  objective — never as an unscoped "richer generator" side task. The
  build contract: solvability-preserving generator + held-out discipline
  + cold baseline + L1-P1-equivalent anti-degeneracy predicate,
  pre-registered before extraction. Without all four, do not start.

---

## Summary recommendation table

| Gap | Exists (reuse as-is) | Adapt (modify) | Build new (small, gated) | Defer |
|---|---|---|---|---|
| 1. Local policy formation | — | M1-redux oracle (standing cost instrument); step-0 gate pattern | Trade-off surface host delta (only when authorized) | The learner itself (no surface; L2 proof) |
| 2. Learned revision | S3/OP-3 execution flow; revocation pattern | U P9+envelope harness (add non-degeneracy per companion) | Single-signal trigger (one D-005 class, preregistered) | Content invention beyond pre-advertised set (except new-world path) |
| 3. Adaptation / discovery | S3 drill as baseline | U CELL-ADAPT measurement per companion; run repaired protocol | Valid held-out change (per companion — the ONLY adaptation build now) | Discovery machinery (inventors/search/mutation, D-008) until protocol discriminates |
| 4. Recipe inheritance | Lineage carrier; bridge transport; L1 3-predicate evaluator | — | Unfamiliar-work family (only inside authorized O-04) | Advantage claims (L1 negative stands) |

## Standing rules for any gap work (non-negotiable)

1. D-005: every learning/adaptation/trigger artefact declares its single
   signal class; cross-class generalization is never claimed without a
   dedicated protocol per class.
2. Q4 negative preserved in-envelope: no result re-runs L1/L2/M1/U-change
   on the same host family expecting a different verdict without a new
   hypothesis + new surface (COMPLETION-MAP: "no runs without new
   hypothesis").
3. Anti-degeneracy predicates are mandatory: L1-P1-equivalent
   (differs-from-fixed-paths) for any policy/recipe claim;
   file-set-growth + graded-bit-sensitivity for any revision claim
   (companion §3).
4. Acquisition/transmission cost counted against every gain claim
   (L1-P3 precedent).
5. ORG-OPS §7 / LIMITS-10 contract deltas filed before any excluded item
   is implemented (policy invention, learned revision, recipe
   inheritance, autonomous discovery, post-creation capabilities).
6. Frozen artifacts read-only; new work in its own successor/work dir;
   prereg-before-execution with hash-chained PREREG-LOG entry; held-out
   authorship + sealed envelope + throwaway validation for any change
   content; independent verification lane before acceptance.
