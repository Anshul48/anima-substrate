# U-execute DRAFT-NOTES (pre-freeze, pre-build)

Author: U-execute draft researcher. Status: DRAFT ONLY — zero execution
beyond `python3 -m py_compile` (see §E attestation). All other trees
untouched; nothing here is frozen.

Sections: (A) spec ambiguities/underspecifications with chosen readings
+ alternatives; (B) reconciliation checklist against BUILT
successor-005; (C) honest §7.3 rubric blindability assessment;
(D) uncertainties; (E) execution attestation.

---

## A. Ambiguities found while drafting

### A1. `package` step I/O contract (R-C)

Spec says only: 6th step `package` (versioned artifact dir + single
hash; STEPS gains "package"). It does not fix: what the step consumes
(compat report + per-step artifacts? the whole artifacts tree?), what
"versioned" means (a version string from where — pinned? derived?),
what the "single hash" covers and where it is recorded, or which
declared outputs the checker/consumers rely on.
- CHOSEN (drafts): `package` is opaque content — predicates treat it as
  a begin-once/succeed-once step like the rest; the checker requires
  its ledger/stamp presence but asserts no package-specific semantics.
  Report schema (§2.2: identities/suites/surface/verdict) is unchanged
  by R-C — the compat report stays the graded artifact.
- ALTERNATIVES: (i) freeze a package-output contract (e.g.
  `PACKAGE/{version, manifest_sha256, files}` + checker verifies the
  single hash over the versioned dir); (ii) grade the packaged dir
  instead of COMPAT-REPORT.json in the rubric. (i) is cheap and I
  recommend adopting it at freeze IF the builder's bundle defines the
  layout; (ii) changes §7.3 and needs coordinator approval — not
  recommended.
- FREEZE ACTION: read the built bundle's package-step program; either
  adopt (i) with its exact relpaths or record "package opaque" here.

### A2. PARTIAL vs FAIL mapping (§2.3(d) "per frozen mapping")

"d recomputes the verdict rule: ACCEPT iff ...; PARTIAL/FAIL per frozen
mapping" — but no mapping text exists anywhere in the design. The
checker cannot recompute (d) without it.
- CHOSEN (PREREG P20 + checker `check_verdict_rule`): FAIL iff any
  identity MISMATCH or any suite rc≠0 (breakage evidence); PARTIAL iff
  identities all MATCH + all suite rc==0 + surface shortfall (evidence
  sound, compat gap). Rationale: PARTIAL must be reachable (else the
  mapping has a dead letter) and must not reward breakage.
- ALTERNATIVES: (i) FAIL iff any MISMATCH only; suite rc≠0 with MATCH
  identities ⇒ PARTIAL ("suites disagree, bytes intact"). Weaker —
  lets a red suite hide behind PARTIAL. (ii) Collapse PARTIAL (ACCEPT
  else FAIL). Loses the compat-gap nuance §2.3 clearly wants.
- FREEZE ACTION: coordinator adopts-or-replaces P20 text; checker
  cross-checks pins `verdict_mapping` against the coded rule.

### A3. Report run-identity fields (checker needs them; §2.3 silent)

`verdict_relcheck.py <report> <ledger> <artifacts> <pins>` takes no
key/world arguments, yet §2.3(b) requires binding ledger rows to the
run. The report MUST therefore carry run identity — but §2.2's schema
(identities/suites/surface/verdict) lists no such fields.
- CHOSEN (PREREG P18 + checker `check_schema`): report carries
  `world_id`, `idem_key`, `bundle_sha256`; the checker selects ledger
  rows by (`idem_key`, `bundle_sha256`) and rejects bundle mismatch.
- ALTERNATIVES: (i) pass key/world as extra CLI args (deviates from
  the §2.3 signature); (ii) infer the key as "the only key with full
  step coverage" (fragile with multi-run ledgers; kill+change legs
  share trees).
- FREEZE ACTION: reconcile field names against the built bundle's
  compat-step program; rename in checker + P18 if the builder chose
  differently.

### A4. Counts grammar (checker §2.3(b) "count claims")

"Cross-checks every suite rc/count claim against the LEDGER-recorded
invoke entries (exit codes) + log artifact hashes (recomputed)."
Ledger entries carry exit codes, not counts — so count verification
must mean: hash-verify the log bytes, then parse counts from them. No
log/count grammar is specified anywhere.
- CHOSEN (PREREG P19 + checker `_parse_counts`): suite steps emit
  `RELCHECK-COUNTS test=<name> passed=<n> failed=<n> total=<n>` (last
  line wins) into exactly one `.log` artifact per suite step; the
  checker parses it from hash-verified bytes and compares
  total/failed to pins + report claims.
- ALTERNATIVES: (i) parse unittest/pytest summary lines (couples the
  checker to runner output formats; brittle across r1/r2/r3 runners);
  (ii) a separate `COUNTS.json` artifact (cleaner parse, but one more
  contract for the bundle to honor — recommend only if the builder
  already emits it).
- FREEZE ACTION: read the built suite-step programs; adopt (i)/(ii) or
  require the P19 line. The checker MUST be re-frozen to match —
  this is the highest-risk reconcile item (see B1).

### A5. `--no-ledger` CLI shape (§7.7 names the mode, not the syntax)

§2.3 fixes `<report> <ledger> <artifacts> <pins>`; §7.7 requires a
`--no-ledger` mode for D but gives no argument shape.
- CHOSEN: `verdict_relcheck.py <report> --no-ledger --stamps DIR
  <artifacts> <pins>` (ledger positional omitted; stamps dir named
  explicitly — never overload the ledger slot, which would invite
  passing a ledger as stamps or vice versa).
- ALTERNATIVES: positional stamps in the ledger slot (rejected:
  silent mode confusion); `--stamps` with ledger still required
  (pointless).
- FREEZE ACTION: none (checker-authored surface; just freeze it).

### A6. Stamp content contract (§5.1 "containing output hashes")

"Stamp files `.stamps/<step>.ok` (containing output hashes)" — format
unspecified; the §7.7 stamps-vs-report audit needs a parseable stamp.
- CHOSEN: JSON stamps `{schema, step, rc, argv_sha256, artifacts:
  [{relpath, sha256, bytes}], run_id, at}` (STAMP_SCHEMA=1), committed
  atomically (temp+os.replace — no torn-stamp skips). Both baseline
  forms (direct_run.py, Makefile.template) share this contract.
- ALTERNATIVES: (i) bare hash list (loses argv binding — a stamp could
  skip different bytes; the host arm's key-collision refusal (§1.5)
  has no D analogue then); (ii) stamp = copy of RESULT.json (fine but
  RESULT.json is a host-arm shape — leaks H concepts into D).
- FREEZE ACTION: freeze exactly one baseline form (P15); the stamp
  contract above freezes with it.

### A7. kill fractional point + tolerance (§4/§5.2(c) "same fractional point")

"Same fractional point ± stated tolerance" — neither the fraction, the
denominator (fraction of what: suite-r3 step wall? whole run? suite-r3
test count?), nor the tolerance is specified.
- CHOSEN (PREREG P10): holes for fraction + delay-scaling rule +
  tolerance; RECOMMEND fraction-of-measured-`suite-r3`-wall on the
  pinned machine (r3-lane lesson: scale delays, confirm in-window
  landings), tolerance ±25% of step wall, in-window landing CONFIRMED
  post-hoc (kill-leg shape predicate is the confirmation on H;
  stamps+log on D) — an out-of-window kill (completed-before-kill, cf.
  r3 builder's 43/50 weak leg) VOIDS the leg, it does not count.
- ALTERNATIVES: fraction-of-test-count (breaks if tests have uneven
  durations); no tolerance stated (unverifiable "same").
- FREEZE ACTION: fill P10 from S5-A10 measured walls; pre-register the
  void-if-out-of-window rule explicitly.

### A8. "0 completed steps" on D — what counts as a completed step

R2: D's re-work "counted exactly (stamp-miss audit)". Edge: a stamp
present-but-invalid (outputs since modified) forces re-run — is that a
"re-executed completed step" (breaks the expected tie) or honest
re-work (counted, tie intact)?
- CHOSEN: stamp VALID (present + hashes match) = completed; re-run of
  a valid-stamped step = re-executed-completed (tie-breaker, must be
  0 on both arms by construction); re-run after invalid/absent stamp
  = honest current-step-equivalent re-work, counted in RUN-LOG with
  the reason. The draft runner logs all three cases distinctly.
- ALTERNATIVES: any re-run of a previously-succeeded step counts
  against the tie (punishes D for H-meaningless filesystem churn).
- FREEZE ACTION: freeze this reading in PREREG §2 (already drafted
  there in prose; coordinator confirms).

### A9. Blinding procedure (§7.3 fixes the rubric, not the redaction)

"The lane sees report bytes only (no arm labels, no ledger)" — but raw
report bytes WILL carry arm-identifying traces (see §C). No redaction
procedure is specified.
- CHOSEN (PREREG §3 [DRAFT-PROPOSAL]): coordinator strips run-identity
  fields + arm-identifying paths, presents redacted X/Y in random
  order, seals the mapping until scores file.
- ALTERNATIVES: (i) score unredacted (blinding theater — see C2);
  (ii) third-party redactor (better, if staffing allows).
- FREEZE ACTION: coordinator adopts a procedure; the redaction RULES
  (field list) must themselves be frozen pre-scores.

### A10. `compat` step inputs vs `package` ordering

With R-C, does `compat` still emit the final COMPAT-REPORT.json (and
`package` wraps it), or does `package` emit the report? §2.2 step 5
says `compat` emits it; R-C adds packaging after.
- CHOSEN: `compat` emits COMPAT-REPORT.json (graded artifact,
  unchanged); `package` wraps {report + artifacts} into the versioned
  dir + single hash. No spec change needed.
- ALTERNATIVES: none sane (moving the report into `package` would
  rewrite §2.2/§7.3/§7.7).
- FREEZE ACTION: confirm against the built bundle's step programs.

### A11. Touch counting on D for multi-invocation flows

§5.2(d): "`make resume` = 1, leaving 1 spare". But a kill leg on D may
need: resume (re-run) + possibly a second invocation if the operator
must inspect-then-resume. And `--step`/`--force` invocations?
- CHOSEN: every baseline CLI invocation that executes work = 1 touch
  (runner prints `touches_used`; Makefile invocations counted by hand
  in the leg record); pure `--audit` inspection = 0 touches (it reads
  stamps/logs only — construction + the audit code path never spawns).
  Cap 2 covers resume + one spare exactly as §5.2(d) budgets.
- ALTERNATIVES: audit counts as a touch (overly strict; the H arm's
  `recover` REPORT reads are part of its 2-touch budget — parity
  argues inspection parity, but H's recover is load-bearing work while
  `--audit` is optional).
- FREEZE ACTION: freeze the 0-touch audit claim with the baseline.

### A12. Surface minimum sets — per-release or global? (§2.2/§2.3)

§2.2: surface = "{per-release CLI verbs + api.py function lists +
ledger kinds observed}"; §2.3: "surface lists superset the pinned
minimum verb/function sets". Per-release minima × 3 releases, or one
global minimum? And are ledger kinds part of the ACCEPT rule? (§2.3(d)
names only verbs/functions.)
- CHOSEN: ONE global minimum verb set + ONE global function set in
  pins (P7); report surface lists are per-release; the ACCEPT rule
  requires EACH release's lists to superset the minima (compat means
  no release regressed the surface). Ledger kinds observed-but-
  unruled (reported, not gated — matches §2.3(d) naming only
  verbs/functions). [DRAFT-PROPOSAL refinement — the "each release"
  quantifier is mine.]
- ALTERNATIVES: (i) union-across-releases superset (lets one release
  drop a verb silently); (ii) gate ledger kinds too (needs a frozen
  kind list; §2.3(d) deliberately omits it — don't add).
- FREEZE ACTION: coordinator confirms the "each release" quantifier;
  checker currently implements GLOBAL-list superset — MUST be updated
  at freeze if the report shape is per-release (see B2).

### A13. Envelope contents vs §1.1 advertise-time validation

§3: envelope holds revised-bundle sha + reveal point; "CONTENT (which
step, which bytes, which target) is held out". But SOMEONE must build
the revised bundle pre-freeze (its sha is pinned) — who, and how is it
kept from the arms' authors? Also: is the revised bundle validated
(well-formed per §1.1) before sealing? CELL-ADAPT says "the revision
is well-formed" — who proves that, and when?
- CHOSEN: coordinator (or a held-out author) builds + validates the
  revision pre-freeze (throwaway validation run, disclosed like
  S5-A10); envelope seals {revised bundle bytes ref + sha + reveal
  point}; at reveal BOTH arms receive identical bytes. Pre-freeze
  validation is what makes "well-formed" a fact rather than a hope.
- ALTERNATIVES: builder authors the revision (leaks content to the H
  arm's author — the H arm IS the builder's tree; actually the arms
  don't author step content at reveal, they execute it — leak risk is
  low either way, but held-out authorship is cleaner).
- FREEZE ACTION: name the envelope author + validation disclosure in
  PREREG §1/P8-P9.

### A14. `p_change_leg_shape` worlds tuple + key binding

The predicate takes `worlds=(old,new)` and `key_new` but never checks
that `key_new` was used UNDER `new_w` (ledger rows don't carry
world_id in the §7.6 field set — proc entries carry idem_key/step/
bundle, not world). A same-key-different-world mix-up would pass.
- CHOSEN: keep the predicate verbatim (bundle-pin disjointness +
  steps-complete is the specified check); the WORLD binding is
  enforced procedurally (H change leg uses a fresh key K2 on W2;
  key-collision-across-bundles refusal (§1.5) prevents K2-on-W1
  confusion mechanically). Checker additionally asserts every row's
  bundle == report bundle == pinned revised pin (change leg).
- ALTERNATIVES: extend the predicate with a world field (needs the
  built ledger to record world on proc entries — reconcile; if
  present, ADOPTING it at freeze is a predicate change requiring the
  amendment procedure — expensive. Prefer procedural binding.)
- FREEZE ACTION: check whether built proc entries record world_id; if
  yes, NOTE it (do not change the predicate post-freeze).

---

## B. Reconciliation checklist (against BUILT successor-005 + bundle)

To be worked at freeze/reconcile time, in this order (highest risk first):

- B1. Suite-step log emission (A4): read the built `suite-r1/r2/r3`
  programs. Adopt P19 grammar or re-freeze the checker's count parser
  to the actual emission. BLOCKER if unresolvable (no counts ⇒ §2.3(b)
  unverifiable).
- B2. Report surface shape (A12): per-release vs global lists in the
  built compat program. Update `check_verdict_rule` + P7/P20 to match.
- B3. Report run-identity fields (A3): exact field names the built
  compat program emits. Rename in checker + P18.
- B4. Ledger field spellings: `proc_begin`/`invoke`/`create` kinds;
  `capability`/`proc`/`result_ref`/`error`/`idem_key`/`step`/
  `bundle_sha256`/`exit_code`/`artifacts[]`/`procedures[]` spellings;
  artifact layout `artifacts/proc-<key>/<step>/<relpath>`; RESULT.json
  shape. Every one is load-bearing for predicates.py + checker.
- B5. `package` step program (A1/A10): inputs/outputs/declared-output
  names; adopt-or-record package-output contract.
- B6. Manifest shape: `MANIFEST.json` keys (`files`/`steps`/`step`/
  `argv`/`declared_outputs`/`timeout_s`/`env_extra`), bundle-sha rule
  (canonical-JSON over WHAT bytes exactly — manifest file as stored,
  or re-serialized canonical form?), `env_extra` value passing (my
  draft assumes `env_extra_values` — likely wrong; reconcile).
- B7. `inspect` output shape: `release.py inspect --json` (or
  successor-005 equivalent) must expose `conservation.ok` for
  `p_conservation_ok` (s004 `inspect_state_op` does — confirm carried).
- B8. CLI/API names: `ops create-proc-world`, `ops run-procedure`,
  `ops recover`, `api.create_proc_world`, `api.run_procedure`
  (§1.8) — confirm exact flags/params for the leg procedures.
- B9. Attempt numbering + scratch layout: `<step>-<attemptN>` naming,
  `attempt`/`child_executions` recording — needed for the kill-leg
  leg-record (not the predicates, which count `proc_begin` rows).
- B10. Pinned machine facts: `make` present? `python3` path/version?
  measured suite walls (P10) + honest clean-run total (A-EXPENSE).
- B11. Change-envelope authorship + pre-freeze validation disclosure
  (A13); revised-bundle manifest diff vs original (one step's bytes +
  one declared output + one suite target — verify the SHAPE, not just
  the sha).
- B12. `.log` artifact naming: checker assumes exactly one `*.log`
  per suite step (ledger + no-ledger modes). Confirm or re-freeze.

---

## C. Honest blindability assessment (§7.3)

### C1. Do H and D reports share one schema?

YES by construction — both arms run byte-identical step programs
(§5.2(a)): the SAME compat program emits COMPAT-REPORT.json on both
arms. Schema-level blinding is therefore free: field names, verdict
strings, counts shapes are identical. This is the strongest point for
blindability, and it is real, not theater. What the rubric scores
(R1–R3: actionability/trustworthiness/completeness of the report as a
cut-record filing) is genuinely arm-independent CONTENT — in fact the
two reports SHOULD be near-identical on the clean leg (same inputs,
same programs), differing only in run-identity metadata and paths.

That near-identity cuts both ways (C3).

### C2. What could leak arm identity (leak inventory)

Ordered by leak severity (pre-redaction):

1. Run-identity fields (world_id/idem_key/bundle paths) — DIRECT
   label if world naming differs by arm (e.g. `relcheck-H` vs
   hand-run ids). CERTAIN leak without redaction.
2. Filesystem paths in surface/evidence traces (state-dir paths
   `.../successor-005/...` vs `/tmp/direct-...`, artifact relpaths
   `proc-<key>/...` vs `artifacts/...`). CERTAIN leak — paths name
   the arm's work layout.
3. Timing/elapsed fields (H ledger round-ups to 0.1 s per §1.4 P14
   vs D's raw floats; systematic formatting differences). PROBABLE
   leak to an attentive scorer.
4. Interpreter/env fingerprints (P7 pins recorded by H; D's env may
   record differently or not at all). POSSIBLE leak.
5. Ordering/whitespace in generated JSON (same program ⇒ same
   formatting — NO leak expected; verify at freeze).
6. Counts/evidence depth (same programs ⇒ same depth — NO leak
   expected; a leak here would mean the arms diverged in CONTENT,
   which is a validity finding, not a blinding failure).

Redaction (PREREG §3 proposal) kills leaks 1–2 fully, 3–4 partially
(normalize or strip timing/env detail — BUT R2 "every claim
recomputable from attached evidence" needs SOME trace detail; strip
too much and both arms score R2=0 on redacted evidence — see C3).

### C3. The hard problem: blinding vs R2, and the near-identity problem

Two honest difficulties, stated plainly:

(a) R2-vs-redaction tension. R2 rewards claims "independently
recomputable from attached evidence" — evidence traces (paths,
hashes, log refs) are exactly what leaks arm identity. Full redaction
may cap R2 for both arms; no redaction voids blinding. The workable
middle: redact IDENTITY (fields + path prefixes) but keep STRUCTURE
(relative layout, hashes, counts). Whether the residual structure
still leaks (H's `proc-<key>` nesting vs D's flat steps) is an
EMPIRICAL question at freeze — test it: redact two S5-A10 readiness
reports and ask a blind reader to guess arms. If guessable, the
blinding procedure (not the rubric) needs another round.

(b) Near-identity makes the USEFULNESS comparison weak, not the
blinding. On the clean leg both arms SHOULD produce
content-identical reports (same bytes in, same programs). The rubric
then measures the VEHICLE's usefulness (is relcheck output worth
filing?), not an H-vs-D difference. That is FINE per §7.7 (CELL-USEFUL
is per-arm VALID+bar; no H-superiority claim) — but it means the blind
comparison cannot discriminate arms on content, only certify both.
The discriminating H evidence lives in the accountability cell
(ledger cross-checks with no D analogue), which is CHECKER-graded,
not rubric-graded, and NOT blind (nor should it be — it IS the arm
difference). State this plainly at freeze so nobody over-reads "both
arms met the bar" as "arms tied on usefulness" — the rubric was never
the discriminator; the checker is.

### C4. Verdict on blindability

BLINDABLE with the PREREG §3 redaction procedure, for the claim it is
asked to support (per-arm bar certification). NOT blindable raw (leaks
1–2 are certain). The residual risk is (a)-style structural leakage —
mitigate by the empirical redact-and-guess test at freeze, and by
freezing the redaction field list BEFORE scores are seen. Do NOT use
rubric scores comparatively across arms beyond the bar rule — the
design already forbids this (§7.5/§7.7), and (b) is why.

---

## D. Uncertainties (things I could not resolve from the spec alone)

- D1. Whether the builder's MANIFEST adds keys beyond §1.3's sketch
  (`inputs`, `env_extra` value mechanism) — B6 covers.
- D2. Whether `compat` on the DIRECT arm can emit identical surface
  lists (D has no ledger — "ledger kinds observed" for D means what?
  The compat program shells out to frozen trees' CLIs; ledger kinds
  must come from somewhere both arms can read — likely the frozen
  trees' own docs/ledgers, not the run ledger. Confirm at freeze; if
  compat reads the RUN ledger for kinds, the D arm needs a defined
  equivalent or the field differs by arm — a C2 leak AND a content
  divergence).
- D3. Kill-harness mechanics (who fires the wall-clock kill, process-
  group kill implementation on the pinned machine) — leg-procedure
  detail, not a draft blocker.
- D4. Whether S5-A12's lane verdict imposes additional freeze-time
  conditions beyond §6 (unknown until the lane reports).
- D5. Exact PARTIAL/FAIL text (A2) and redaction field list (A9) need
  coordinator adoption — flagged as [DRAFT-PROPOSAL], not assumed.

---

## E. Execution attestation

ZERO executions beyond `python3 -m py_compile` (stdlib compile check;
imports nothing, contacts nothing, runs no module code). Specifically:

- ALLOWED AND DONE: `python3 -m py_compile` on the drafted `.py`
  files (result recorded in the completion report).
- NEVER DONE in this task: no harness runs, no host contact (no
  `ops`/API calls against any successor tree), no baseline trial
  runs, no suite executions, no bundle builds, no frozen-tree reads
  beyond read-only spec grounding (design doc, CONTINUING-PROGRAMME
  log, s004 ledger-shape lines, M1-redux precedent, PREREG-LOG
  format), no writes outside
  `prototype/programme-20261004/U-execute/`.
- No pins filled (nothing is frozen); no PREREG-LOG entry prepared.

Pre-freeze execution would void the future prereg; none occurred.
