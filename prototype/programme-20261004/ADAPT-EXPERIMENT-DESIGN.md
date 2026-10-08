# ADAPT-EXPERIMENT-DESIGN — discriminating adaptation protocol (DESIGN ONLY)

Date: 2026-10-07. Status: DESIGN — no runs authorized by this file.
Execution requires a separate authorized objective + filed prereg entry.
Rev 2 (2026-10-07, user correction): identical H/D outputs are a scored
TIE when per-arm sensitivity holds (not an instrument failure); void
only on sensitivity failure (VOID-stimulus); §8 scope bar makes the
no-discovery-claim limit a protocol violation, not just a non-goal.
Parent: `MECHANISM-REUSE-ASSESSMENT.md` Gap 3 (recommendation: adapt
measurement now, defer discovery machinery until the protocol discriminates).

## §0. Goal and non-goals

GOAL: a protocol that measures ADAPTATION TO A HELD-OUT CHANGE and can
DISCRIMINATE between approaches (at minimum: H procedure-world adaptation
vs D direct-baseline adaptation; extensible to future triggers). The
protocol must be capable of producing three honest outcomes: H wins a
cell, D wins a cell, or tie-with-cause. A tie is a VALID scored
outcome when both arms demonstrably adapted (per-arm sensitivity
TRUE, §4.2): both approaches can correctly adapt and produce
identical results. The instrument-failure case is narrower: when the
revision cannot move an arm's artifact (sensitivity FALSE), the
comparison is VOID (stimulus failure), not a tie.

NON-GOALS (explicit, Q4-respecting):

- NOT a learning/discovery claim: this protocol tests EXECUTION of
  adaptation to a supplied held-out revision (authorized-mechanism class),
  not autonomous discovery of responses. Discovery needs a further protocol
  (stimulus without supplied response) and is B-frontier DEFERRED.
- NOT a re-run of U-change on the same stimulus: U's revision was VOID
  (degenerate); this design replaces the change-construction leg while
  reusing U's measurement/blinding/void machinery.
- NOT a cost/speed superiority claim: wall-clock stays guard-only
  (U precedent, PREREG §7); cost-to-adapt counts are REPORTED per arm,
  superiority unclaimed unless a future prereg declares it.

D-005 stimulus declaration: this protocol tests response to ONE signal
class — EXPLICIT REQUIREMENT CORRECTION (a revised bundle + revised pins
supplied post-freeze). Results generalize to no other class (prediction
discrepancy, independent-check failure, evaluator defect, comparative
advantage each need their own protocol).

## §1. Failure analysis: why U-change could not discriminate (normative lessons)

U-execute change legs stand VOID (U-OVERALL-FINAL.md; CHANGE-VOID-NOTEs;
INDEPENDENT-ACCEPTANCE §What-was-checked-3). Four independent defects,
each fatal; the repair must close ALL four (L1 lesson: failures compose).

F1 — DEGENERATE REVISION (content defect). The author's "added" suite
target was a DUPLICATE entry (same file/log/expectations as the proven
sibling; manifest: "same log file, so suite-r1 emits no new file").
Filed P9 counts distinct (tag,file) pairs: added = 0 ≠ 1 ⇒ VOID ×2
(identical re-run per C1). Root cause: the author brief OPTIMIZED FOR
THE DEGENERACY — "minimal and behavior-preserving," "passes by
construction," exit-0-always assay (REVISION-MANIFEST.json rationale).
Repair: §3 non-degeneracy bar + author brief that REQUIRES graded-bit
sensitivity and a failing control.

F2 — INCOMPLETE VALIDATION (assurance defect). Throwaway validation
reached 6/7 steps; `package` never reached ("operator params key
'run_id' held out"); RELCHECK-REPORT.json emission unconfirmed
(REVISION-MANIFEST.json validation). The envelope was sealed on a
revision never shown to complete. Repair: §3.4 — package-reached is a
mechanical seal criterion; no seal without a packaged report.

F3 — UNPROVEN SENSITIVITY (interpretation defect). All four live
COMPAT-REPORTs + blind X/Y = sha 099f4e33, 5065 B, mutually identical —
INCLUDING ACROSS LEGS (clean X == kill X). The graded bytes are a
deterministic function of frozen inputs (INDEPENDENT-ACCEPTANCE §§5,10;
U-OVERALL-FINAL Reading-1). U honestly reported TIE — and a tie on
identical bytes is a legitimate outcome — but U could not show the
revision moved anything (F1: revision degenerate; sensitivity never
established), so the tie was UNINTERPRETABLE: consistent both with
"both arms adapted" and with "nothing was tested." Repair: §4.2
per-arm sensitivity gate — a tie is scored only with sensitivity
TRUE on both arms; otherwise the comparison is VOID-as-stimulus-
failure (named, not scored).

F4 — UNTESTED ADAPTATION PREDICATES (coverage defect). `p_change_leg_shape`
(new world + disjoint bundle pin), revised-universe `p_steps_complete`,
and revised-shape `p_ledger_report_agree` never executed against a real
revision (legs never started; zero commands). The predicates are FROZEN
but UNEXERCISED. Repair: §5 — predicates re-verified against the
throwaway validation trace BEFORE seal (frozen logic, exercised bytes).

## §2. Design constraints (inherited, non-negotiable)

- $0, offline, stdlib-only except qualified SST snapshot confinement
  (U PREREG §2(e) + RULES-AMENDMENT-2; `p_sst_snapshot_confined` 3 slots).
- Frozen artifacts read-only (r1/r2/r3/H2/successor-005-accepted banked
  line + release trees); experiment in its own work dir.
- Prereg-before-execution: PREREG-LOG hash-chained entry + countersign
  before first non-throwaway run (RULES-AMENDMENT-1 procedure); predicate
  edits after filing ⇒ new entry + re-freeze.
- Held-out authorship + sealed envelope + throwaway validation (own state
  dir, disclosed keys) for all change content.
- Independent verification lane before acceptance (auditor re-runs
  eval/derive/blinding from filed bytes, /tmp-only writes).
- Q4 negative preserved: no runs without a new hypothesis (COMPLETION-MAP
  §5). THE NEW HYPOTHESIS ENACTED HERE: a NON-DEGENERATE held-out change
  (per §3) produces discriminable adaptation behavior between arms. The
  prior (degenerate-change) hypothesis is retired, not re-tested.

## §3. Valid held-out change construction (the repair for F1+F2)

### §3.1 Shape (retained from U P9, tightened)

Base: U PREREG P9 as amended by RULES-AMENDMENT-2(f) — exactly one added
step carrying exactly one added declared output (base steps' declared
sets byte-equal) + exactly one added suite target in existing tags +
program delta present (relcheck.py bytes changed XOR one added bin/
program argv-referenced by the new step); no removals; bundle files =
base set + ≤1 added bin/ file. RETAIN — the shape rule is sound; U's
failure was content inside the shape, not the shape.

### §3.2 Non-degeneracy bar (NEW — closes F1)

The revised bundle MUST satisfy all five, mechanically checked by
`derive-revised-pins` (extended) BEFORE seal acceptance:

- ND1 — NEW EXECUTABLE CONTENT: added bin/ program exists, is
  argv-referenced by the added step, and differs from every base file
  (sha-distinct). (U met this: assay_surface.py 6017 B — necessary,
  not sufficient.)
- ND2 — DISTINCT SUITE TARGET: the added suites entry is a distinct
  (tag, file) pair whose execution EMITS A NEW FILE (new log path in
  the step's declared outputs; file-set of step outputs strictly grows
  base→revised). DUPLICATE-entry (same file as a sibling) ⇒ VOID.
  Direct repair of U's added=0 failure.
- ND3 — GRADED-BIT SENSITIVITY: the revision changes ≥1 graded output
  bit. Operationally: the packaged revised COMPAT-REPORT differs from
  the packaged base COMPAT-REPORT on ≥1 rated field (verdict input,
  per-tag ok, results roster, or surface record) when both are produced
  from the same release trees. A revision whose graded report is
  byte-identical to base is VOID (it cannot discriminate by construction
  — F3 at the bundle level).
- ND4 — FAILING CONTROL (author-demonstrated): the author supplies, in
  the sealed envelope, a MUTANT trace: the added check run against a
  deliberately broken target (e.g. corrupted pins roster, truncated log)
  MUST fail loudly (nonzero exit or ok:false with named defect). An
  exit-0-always / pass-by-construction check is VOID. The mutant trace
  is sealed-envelope evidence, re-runnable by the auditor.
- ND5 — WELL-FORMEDNESS PRESERVED: the revised bundle passes advertise-
  time validation on BOTH arms' staging (H `create-proc-world` ACCEPTS;
  D staging accepts) AND the base release trees still grade VALID under
  it (the revision adds signal, it does not break the base verdict —
  else the experiment measures breakage, not adaptation).

Author-brief constraints (normative for the held-out author):

- FORBIDDEN: behavior-preserving/pass-by-construction suite targets;
  duplicate (tag,file) entries; exit-0-always checks; shared log files
  for the added target; any instruction to "minimize acceptance signal."
- REQUIRED: ND1–ND5 self-attestation with file pointers + the ND4 mutant
  trace + full throwaway validation log reaching `package` (§3.4).
- The author optimizes for DISCRIMINATIVE POWER (a change that exercises
  the adaptation path end to end and could fail), not for smoothness.

### §3.3 Content guidance (advisory — the author decides, ND1–ND5 judge)

Plausible non-degenerate changes (examples, not prescriptions): a new
pre-flight step that schema-checks the suite roster AND fails closed on
a corruption class (with the added suite target exercising that class);
an added surface-minimum entry (new CLI verb/api function) that the
checker enforces (base trees must genuinely provide it — else ND5 fails
honestly); a strict log-grammar extension (new required marker) with a
new emitter. The author may propose anything meeting ND1–ND5.

### §3.4 Seal criteria (NEW — closes F2)

The envelope may be sealed IFF, in disclosed throwaway validation:

1. Full run reaches `package` (7/7 steps adopted or executed);
2. RELCHECK-REPORT.json + packaged COMPAT-REPORT.json emitted;
3. ND1–ND5 mechanically verified against the throwaway trace;
4. F4 predicates (§5) executed green against the throwaway trace;
5. All validation under disclosed keys in the author's own state dir
   (never in frozen trees, never in the experiment work dir).

Missing any item ⇒ author revises (new envelope version, old preserved);
the coordinator never seals an incomplete validation.

## §4. Measurements capable of distinguishing approaches (repair for F3)

### §4.1 Primary cells (per arm, per leg)

Retain U CELL structure (PREREG §6), revised bundle as stimulus:

- CELL-VALIDITY: H = `p_report_valid` ∧ `p_ledger_report_agree` (revised
  universe) ∧ `p_hashes_recompute`; D = `p_report_valid` on --no-ledger
  checker verdict. FAIL ⇒ arm-leg INVALID.
- CELL-ADAPT (the discriminating cell): H = VALID ∧ `p_change_leg_shape`
  (new world + disjoint bundle pin — C9 rationale: without it H could
  pass without versioning); D = VALID. Cost-to-adapt REPORTED per §4.3.
  PLUS the new accountability sub-cell: H-only predicates
  (`p_ledger_report_agree`, `p_hashes_recompute`, `p_conservation_ok`)
  hold under the REVISED universe — stated as accountability evidence,
  not as a recovery/adapt win (U §6 precedent).
- CELL-USEFUL: `p_rubric_bar` per arm on the REVISED reports, blind (§6).
  The rubric text is retained (R1/R2/R3 + bar total ≥4 AND R2 ≥1); the
  purpose statement stays fixed boilerplate.

### §4.2 Discriminating-delta predicates (NEW)

- `p_reports_bundle_sensitive`: packaged revised COMPAT-REPORT ≠ packaged
  base COMPAT-REPORT on ≥1 rated field (ND3 at grading time, both arms).
  If FALSE on an arm, that arm's CELL-ADAPT is VOID-stimulus (the
  change did not affect that approach's graded artifact — a finding
  about staging/sensitivity, reported, not scored).
- TIE RULE (F3 repair): if the two arms' revised graded bytes are
  IDENTICAL and per-arm sensitivity is TRUE on both arms, the
  comparison is a scored TIE — both approaches correctly adapted and
  produced identical results. A tie is a complete result, not a
  failure. The comparison then proceeds on the behavior/cost cells
  (CELL-ADAPT accountability sub-cell, §4.3 cost-to-adapt counts),
  which can still discriminate the approaches on how they adapted.
  DIVERGENCE is not required to favor H — D-favoring divergence is
  an equally complete result.
- VOID rule: sensitivity FALSE on either arm ⇒ that arm-leg is
  VOID-stimulus (the change did not affect the approach's graded
  artifact — a finding about staging/sensitivity, reported, not
  scored). No tie is scored without sensitivity TRUE on both arms.

### §4.3 Cost-to-adapt (reported, both arms, same grammar)

- H: invokes-to-first-VALID-revised-report (ledger count under the new
  key) + touches used (C2 grammar: run-procedure + ops-recover) +
  completed-step re-runs (asserted 0 by `p_no_completed_rerun`) +
  current-step re-runs (begins beyond first per step).
- D: steps-to-first-VALID-revised-report (direct-ledger count) + touches
  (direct_run run/resume) + completed/current-step re-runs (stamps+log
  grammar, C3).
- Wall-clock: guard-only (A-EXPENSE floor retained; no superiority claim).
- Acquisition cost: author + validation cost is SUNK (both arms share the
  sealed bytes) — counted in the budget (§7), not charged to either arm.
  (Contrast L1-P3, where acquisition was arm-specific.)

### §4.4 Load-bearing controls (NEW — prove the stimulus matters)

- FROZEN-H CONTROL: base-bundle H run (no revision) graded against the
  REVISED pins MUST be INVALID (checker refuses: bundle-sha mismatch).
  Proves the revision is load-bearing (adaptation was necessary, not
  optional). If the control PASSES, the revision is non-binding ⇒ VOID.
- MALFORMED-REFUSAL PROBE (preregistered, throwaway-adjacent): a
  deliberately malformed revision variant (bad bundle sha pin) MUST be
  refused pre-work by H advertise validation (S5-A8 precedent) with zero
  ledger effect. Demonstrates the fail-closed frontier 3c. (Well-formed
  main revision still measures parity honestly — U CELL-ADAPT precedent.)

## §5. Predicates (frozen bytes, exercised before seal — repair for F4)

RETAIN from `U-execute/predicates.py` (d12adfa2) verbatim unless noted:
`p_report_valid`, `p_steps_complete` (steps-universe parameter),
`p_no_completed_rerun`, `p_kill_leg_shape` (kill legs run BASE bundle, C5),
`p_ledger_report_agree` (extended: revised suites universe incl. ND2 new
target — results non-empty per tag incl. the added program), `p_hashes_
recompute`, `p_change_leg_shape`, `p_conservation_ok`, `p_rubric_bar`,
`p_touch_cap`, `p_sst_snapshot_confined` (3 slots; change legs pass revised
manifest steps). STEPS fixed per P17 for base; revised manifest steps for
change legs (RULES-AMENDMENT-2(e)).

NEW (frozen with the prereg, same file):

- `p_revision_nondegenerate` — ND1–ND5 mechanical check (file-set growth,
  distinct (tag,file), graded-bit sensitivity base-vs-revised, mutant-
  trace fail-loud marker, base-validity-preserved). Consumed by
  derive-revised-pins at seal AND by eval-leg at grading.
- `p_reports_bundle_sensitive` (§4.2), `p_arms_diverge_or_explained` (§4.2).
- `p_full_package_reached` — packaged report exists + `package` success
  invoke under the leg key (§3.4 item 1–2).

F4 repair procedure: after throwaway validation completes (§3.4) and
BEFORE seal, the coordinator runs every §5 predicate against the
throwaway trace; all must execute (no import/shape errors) and return
the expected value. Predicate LOGIC stays frozen (no edits to pass);
bytes-mismatch failures ⇒ author-revision or coordinator RULES-
AMENDMENT entry (never silent repair). The exercised-trace transcript
is seal evidence.

## §6. Baselines and blinding

### §6.1 Baselines

- H arm: successor-005 procedure worlds (`create-proc-world` +
  `run-procedure` + `recover`) on the REVISED bundle under a NEW world
  (C9). Pins: banked-line identities + derived revised pins (C6
  derivation retained: envelope pins when schema-valid else mechanical
  graft + recomputed shas; transcript + derived sha are leg evidence).
- D arm: repaired `direct_run.py` form (U C11-004 fix carried: atomic
  mirror of stamp bytes for `artifacts/<step>/RESULT.json`; H-parity
  shape) on the identical revised bytes. Same kill class/plan-phase if a
  kill leg is included (scope decision, §8).
- FROZEN-H control (§4.4) + MALFORMED-REFUSAL PROBE (§4.4) as above.

### §6.2 Blinding (retained from U §3/C4, plus tie rule)

- Coordinator applies the frozen redaction field list to both arms'
  packaged COMPAT-REPORT.json, presents X/Y in random order per leg,
  records mappings sealed until that leg's scores are filed.
- Held-out rater(s) see report bytes + rubric only (no arm labels, no
  ledger, no logs). Purpose statement fixed boilerplate.
- Identical bytes across arms are rated NORMALLY (no void-on-identical):
  with sensitivity TRUE on both arms, identical scores are a scored
  TIE (both adapted correctly); byte-identity is recorded as a
  finding. Rating is skipped only where sensitivity already VOIDED
  the leg (VOID-stimulus, §4.2) — there is nothing to score.
- Filing order enforced by mtime audit (mappings → scores → leg finals →
  overall), auditor re-verified (INDEPENDENT-ACCEPTANCE §9 precedent;
  rater "at" fields must be true timestamps, not placeholders — U's
  12:00:00Z wart must not recur: harness stamps filing time).

## §7. Cost budget (upper bounds; abort if exceeded)

Basis: observed U/S5 walls on capable hardware (native ext4, quiet load).

| Item | Basis | Budget |
|---|---|---|
| Author throwaway validation (≤3 runs + mutant trace) | U sealed-val 1–191 s/run; readiness 175.8–183.2 s | ≤ 4 h wall (generous; includes author iteration) |
| H change leg (1 run + ≤1 C1 re-run) | suite-r3 ~110 s closure; full bundle ~3–6 min | ≤ 30 min |
| D change leg (1 run + ≤1 C1 re-run) | same class | ≤ 30 min |
| Frozen-H control + malformed probe | single advertise + single graded refusal | ≤ 30 min |
| Predicate-exercise + derive-revised-pins + eval | seconds–minutes (stdlib) | ≤ 1 h (incl. auditor re-runs) |
| Blind rating (1 rater × 1 leg-pair + spares) | U precedent (2 legs rated) | ≤ 2 h rater time |
| Independent audit | U INDEPENDENT-ACCEPTANCE scope | ≤ 4 h auditor time |
| TOTAL | | ≤ 12 h wall + ≤ 6 h human-equivalent rater/auditor |

ABORT rules: A-FROZEN (any IDENTITY mismatch pre/post any leg ⇒ ABORT +
investigate); A-ENVELOPE (network/key/cost evidence or non-stdlib outside
SST confinement ⇒ ABORT); A-TOUCH (over-cap ⇒ leg VOID, C1 once-re-run);
A-EXPENSE (honest clean wall <60 s ⇒ ABORT, padding forbidden); P10/P12
kill rules IF a kill leg is in scope (recommendation §8: exclude kill —
adaptation stimulus is the revision, not the crash; kill recovery already
has unilateral TRUE evidence from U H-kill).

## §8. Open scope decisions (coordinator-set at prereg, not author-set)

1. Legs: change-only (RECOMMENDED — the revision is the stimulus; clean
   legs add no adaptation information and kill legs re-test settled
   recovery) vs full clean/change/kill replication of U. Change-only
   halves cost and keeps the verdict sentence on adaptation.
2. Rater count: 1 held-out rater (U precedent per leg) vs 2 (variance
   estimate; U's clean-PASS/kill-FAIL split on identical bytes shows
   rater variance is real — 2 raters recommended IF budget allows).
3. Overall verdict rule: HOST-ADAPTATION-DEMONSTRATED iff H CELL-ADAPT +
   bar met + guards hold + ≥1 H-exclusive accountability cell present
   (U §6/C10 shape, change-legged); else HOST-ADAPTATION-
   NOT-DEMONSTRATED with the failing cell named. A clean negative is
   complete. No cost/speed superiority verbiage. SCOPE BAR: the
   verdict sentence may claim at most correct EXECUTION of the
   supplied revision — never autonomous discovery (NON-GOALS).
   Discovery needs a stimulus-without-supplied-response protocol and
   is B-frontier DEFERRED; any discovery verbiage in the verdict
   text is a protocol violation.
4. Predicate provenance: import U `predicates.py` d12adfa2 bytes verbatim
   + append NEW predicates (RECOMMENDED — continuity, diff-auditable) vs
   fresh-file freeze (cleaner slate, higher review cost).

## §9. Pre-registration checklist (filing gate)

- [ ] Pins P1–P20 refreshed vs built bytes (bundle/shas/interpreters/
  machine re-observed, not copied from U).
- [ ] §5 predicate file frozen (sha filed) + F4 exercised-trace green.
- [ ] §3 envelope SEALED (§3.4 all five) + seal sha filed (P8 slot).
- [ ] Redaction field list frozen; rater brief filed; sensitivity + tie rule coded.
- [ ] Verdict text contains no discovery verbiage (§8 scope bar).
- [ ] §8 scope decisions recorded; verdict rule coded in eval (imports
  frozen predicates verbatim).
- [ ] G-RE executability re-gate green (G1–G5 re-applied to built s005).
- [ ] PREREG-LOG entry countersigned BEFORE first non-throwaway run.
- [ ] Zero pre-countersign runs (auditor verifies by mtime + ledger scan).

*End of design. No runs authorized. Next action (future objective):
held-out author produces the §3 envelope; coordinator seals per §3.4;
prereg files per §9; legs execute; auditor accepts.*
