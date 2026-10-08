# COMPLETION-MAP.md — substrate requirement-to-evidence map

Integrated from direct user statements, the finalized ANIMA packet,
original excerpts, and actual current implementation (FINISH §3).
This map IS the programme canonical record (FINISH §7: one
concise record linking detailed evidence). No separate
programme-level CANONICAL-RECORD.md exists; the w1-harden
CANONICAL-RECORD.md is a frozen Oct-04 historical artifact, and
prototype/evidence-20261004/canonical-draft/ is a draft only.

## 1. Sources and authorship

- ANIMA packet: `../ANIMA/context/` (SIBLING of the substrate root —
  not under it). Entry: `README.md` → `OPERATIVE-BRIEF.md`.
- Key packet files: `IDEA-MAP.md` (vectors, priority, closeouts),
  `SOURCE-EXCERPTS.md` (verbatim cores), `DECISIONS-AND-CORRECTIONS.jsonl`
  (D-001–D-017), `OPEN-ISSUES.md` (O-01–O-12), `REQUIREMENTS-AND-EVIDENCE.md`,
  `SUBSTRATE.md`, `EXPERIMENTS.md`, `PERSONAL-MODEL.md`, `MEMORY-TIERS.md`,
  HARDWARE doc, `../SUBSTRATE-DIRECTION.md` (in substrate `docs/`).
- Status classes: REQ (accepted requirement), INSP (supplied
  inspiration, authorship-labeled, never evidence), HYPO (research
  hypothesis, resolves only in-envelope), DEFER (explicitly deferred
  with owning statement).
- Cautions: B1/B2 fuller review is PAUSED by user (do not begin);
  O-11: a reported 18-vector-chat addition was never observed in the
  transcript file — its contents must not be inferred.

## 2. Priority map A → C → B → D

A = computationally useful knowledge; C = learned schemas/operations;
B = cumulative capability discovery; D = computational/physical
co-design. Ordered A→C→B→D per user (IDEA-MAP:46, D-004): B/C swapped
because B nears RSI; D last but enabling HW work may start earlier;
many intermediate steps precede D; not a rigid stage gate.

## 3. A/B contexts (authorship-separated)

- A1 (INSP): bio complexity/evolution as existence proof, not
  blueprint; cumulative learning, culture, new hypothesis spaces.
- A2 (broad ambition user-reinforced; equations/five-band/implementation
  NOT ratified): computational holons (identity/state/resource/lifecycle),
  programmable+plastic boundaries, stateful relationships,
  coalitions→composites. A2/A3 extension (development, endosymbiosis,
  co-adaptation, selection, inheritance, HW/SW co-evolution) has an
  ambiguous boundary — do not relabel as doctrine.
- A3: user-authored question separating identity/ownership vs function
  vs information permeability (following long answer is pasted model text).
- A4 (INSP, lower priority): intelligence as inheritable lineage.
- B1 (direct user framing): delimit TL/TRACE, direction, bounded
  benchmark experiments, JEV placement; async deep research must not
  block delivery.
- B2: pointer to trace-architecture history (locator only).
- B3 (INSP): program-library learning, MDL, prospective abstractions,
  formulation search, equivalence, evaluator bias, value of computation.
- B4 (HYPO): limited scratchpad; lossy conceptual view + high-fidelity
  episodic/source retrieval; four hypotheses (abstract+domain
  schema+delta; compiled/mathematical form; TRACE-organized material;
  mixes). Analogy, not literal anatomy.

## 4. Eighteen-vector ambition (condensed; closeouts IDEA-MAP:23-42)

V1 breakthrough=both, organized-knowledge-first (D-002); V2 dated
project assessment (historical synthesis only); V3 TL/TRACE split now,
reorganization later; V4 exact-episodes vs conceptual-memory
interaction (four-store loop = proposal); V5 self-organization
evaluation candidates (not adopted); V6 STC construction + cumulative
capability (pilot preliminary; experience learning welcomed, D-005);
V7 async research must not block delivery (direct B1 instruction);
V8 SST-as-reusable-search (STC integration current, D-007; no TRACE
mandate); V9 formulation-changing search (no method adopted); V10
obstacle→capability loop (direction, not qualified generator); V11
noisy evaluation (no benchmark approved); V12 compiler/precise
representation (B4 hypothesis); V13 schemas+deltas (test it, keep
fidelity+diversity, D-009); V14 plastic boundaries/relationships
(D-006; A2 details stay inspiration); V15 adaptation/learning/
development/inheritance distinctions (no fixed five-layer mapping);
V16 variation/selection/inheritance (long-term ambition, D-004
conditions); V17 attention/metabolic allocation (policies proposed);
V18 HW/SW co-design roadmap (enabling work early; D later).

## 5. Requirement detail (intended behavior → evidence → remaining)

Conventions: S5-L/E/C = successor-005 LIMITS/EVIDENCE/CONSUMER.md;
S5-V = S5-lane/VERDICT.md. Envelopes bound
every SATISFIED: single-host, toy scale, TEST-only SST, process-crash
(not power-loss), no fsync.

- R1 nested orgs / owned responsibility — REQ PARTIAL. Worlds
  self-solve/verify, exports-only coordination, O1–O5+E1–E3
  structural. Missing: local POLICY invention. Next: policy learning
  (E4-adjacent, deferred).
- R2 heterogeneous participants — REQ PARTIAL. Construct/explore
  worlds, hand-written v1/v2 declared-loss mapping, toy evaluator.
  Missing: learned mapping. Next: deferred.
- R3 revisable cooperation — REQ PARTIAL. Versioned relationships,
  v1 pin after v2, S3 void-v1/re-propose-v2. Missing: learned
  revision. Next: deferred probe.
- R4 fusion/fission/coalitions — REQ SATISFIED single-host. r1:
  fusion lineage + 3 transfers + 8→7 mechanisms + reuse 5/5; fission
  + reuse 4/4; quarantine path; round-2 accepted. Missing:
  cross-host (DEFERRED, needs multi-host design).
- R5 actual state/ownership/lifecycle change — REQ SATISFIED
  single-host. Mechanism inventory before/after; durable revocation/
  revision across reopen. Cross-host: DEFERRED (see deferred list).
- R6 composite reuse + lineage — REQ PARTIAL. Reuse + derived_from
  lineage VALID 5/5. Missing: developmental-recipe inheritance
  (descendant advantage on unfamiliar work) — DEFERRED, needs
  learning loop.
- R7 adaptation — REQ PARTIAL (authorized mechanisms). v1→v2 +
  revocation → escalation → ruling → VALID. Autonomous discovery =
  B-frontier DEFERRED.
- R8 local negotiation load cut — REQ CONDITIONAL. 2–6× dialogue-heavy
  (X3 H3a 3-0, 0.16/0.29/0.45); central wins small-scale. Calibrate
  2.61× bytes-only, task-envelope-only. Rule held; no runs without
  new hypothesis.
- R9 consumer contracts — REQ SATISFIED for this path. C1–C7 +
  OP-1–OP-6 + G1–G8; 9/9 conformance; OP-4 gap fixed in acceptance.
  Owed item CLOSED: CC1–CC9 coupling contract filed + tested in
  successor-006 (test_coupling 10/10, engine byte-identical to s005),
  independently ACCEPTED (S6-ACCEPTANCE.md). New paths need deltas.
- R10 integrated Linux path — REQ SATISFIED toy-scale. r1→r3→S5
  carried; S5: 129 tests + procedure participant + vehicle,
  ACCEPT-WITH-NOTES. Scale is future work, not a gap.
- R11 interruption/recovery/separation — REQ SATISFIED declared
  paths. Kill resume rc=-9/0 re-invokes/byte-identical; 5 refusal
  shapes; quarantine separation; S5 adds kill-during-settle/fusion
  matrices. Quarantine-transfer repair DONE in successor-006
  (quarantine-complete/rollback ops, 13/13 incl. kill at every
  boundary × both directions), independently ACCEPTED. Remaining:
  disk-loss + multi-writer DEFERRED.
- R12 independent verification — REQ SATISFIED all candidates.
  r1 two lanes; S5-A12 ACCEPT-WITH-NOTES (57/57 + own legs + tamper
  5/5 + post-hashes); S5-A10 lane-RED environmental with NOTE-1
  gating, CLOSED by coordinator READINESS-PASS 183.2 s.
- Q1/E1, Q2/E2 — resolved in envelope (conditional rule; H2b).
  No further runs without new hypotheses.
- Q3 recovery reuse — DEMONSTRATED-WITH-COUPLING-LIST (10/10
  unmodified resume on separate MiniHost); contract now COMPLETE
  (CC1–CC9 in successor-006, S6-ACCEPTANCE.md ACCEPT).
- S6 owed-repairs + J1 — REQ SATISFIED in envelope, independently
  ACCEPTED (no notes). 48/48 tests (10 coupling + 13 quarantine-
  repair + 6 J1 + 9 conformance + 7 fission + 3 proc-smoke) +
  10/10 demo: persistent project world, nested experiment world
  w/ real delegation, real-SIGKILL resume byte-identical,
  fuse w/ ownership change, composite reused unmodified ×2,
  settle stranded=0. Envelope: single-host, toy scale,
  process-crash-only, no SST leg (loud refusal). BANKED 2026-10-07
  (IDENTITY.sha256, 35/35 OK, manifest 48462368…; routine, no
  freeze hold existed); frozen predecessors untouched.
- REL-0.1.0 public release — COMPLETE 2026-10-08. Maintained
  package `anima-substrate` 0.1.0 (M1–M4, src/ 31 py + 8 JSON):
  207 passed, 11 skipped (SST-conditional), 147 subtests; ruff
  clean; PKG-ACCEPTANCE.md ACCEPT-WITH-NOTES (notes closed).
  Apache-2.0 (Copyright 2026 Anshul48; agent bytes assigned).
  Repo https://github.com/Anshul48/anima-substrate (commit
  9d07c11, tag v0.1.0, main 56d6693 CI green); release assets
  (wheel/sdist/SHA256SUMS) verified + fresh-clone repro OK.
  Patch 0.1.1 (tag v0.1.1, commit 9a1c795; v0.1.0 preserved):
  requires-python >=3.11 (datetime.UTC), CI matrix 3.11+3.12
  green, ROADMAP M1–M4 recorded accepted/published; release
  assets verified + clean install OK.
  Remaining obligations: STC execution integration (Ask 2B),
  policy learning/inheritance, cross-host/multi-writer/disk-loss,
  Q5 host, adaptation runs (designs only) — all explicit in
  docs/ROADMAP.md.
- Q4/E3/E4 learning — ARC CLOSED negative (L1/L2/M1/M1-redux);
  no learning in s005. Bounded probe only on live uncertainty.
  Nuance: M1-redux itself PASSED as an instrument (MAE 0.00);
  the negative covers transfer/invention, not the instrument.
  Standing: D-005 signal semantics (prediction discrepancy /
  explicit correction / independent-check failure / evaluator
  defect / comparative advantage stay semantically distinct)
  binds ANY future learning work.
- Q5 permanent host — UNDECIDED, standing user obligation.
  Reversible trials + successors advance meanwhile.
- S5-proc bounded procedure participant — REQ SATISFIED in
  envelope. 57/57 incl. wording + tamper; P1–P9/P14 enforced;
  P11–P13 contractual; L1–L5 process-crash-only; no
  checkpoint-resume; power/media = disk-loss class.
- U-exec real use — COMPLETE FINAL, INDEPENDENTLY ACCEPTED
  (INDEPENDENT-ACCEPTANCE.md 2026-10-07, auditor re-ran eval-u/eval-leg/
  derive-revised-pins, blinding + C11 legitimacy verified). Step-0
  negative preserved (frozen-interface envelope). §7.8 FILED
  2026-10-06T13:35:45Z (entry ba821dd0…, RULES-AMENDMENT-2(a)-(f),
  G-RE re-gate green); acceptance experiment COMPLETE FINAL
  (mechanical overall HOST-VALUE-NOT-DEMONSTRATED, 6 failing
  cells named):
  H-clean/D-clean-R2 VALID + bar-met; H-kill recovery TRUE,
  D-kill-R2 VALID, both miss kill bar equally (identical
  bytes, rater variance); H-vs-D TIED every rated leg
  (deterministic arm-invariant reports); change legs VOID
  (adaptation untested); r5 NOT banked. C11 ×4 (incl.
  baseline package-layout fix + C1 D re-runs). See runs/
  U-OVERALL-FINAL.md (U-OVERALL-NOTE.md = interim).
- P1-prod producer qualification — byte identity SATISFIED
  (SST df78f42/54-file recompute exact; STC pin landed+persists;
  TRACE presence-only; TL absent); contracts/evidence genuinely
  missing (owners). Consume qualified exports only.
- Deferred ambitions (preserved, owned statements): V16 evolution
  machinery (D-004 conditions); V18 HW co-design (roadmap only);
  V17 attention policy (proposal); personal-model + memory-tiers
  (hypotheses/proposals); A2 five-layer equations (INSP, never
  results); cross-host, multi-writer, disk-loss, all learning
  forms, recipe inheritance, autonomous discovery; D-008
  use-case training + primitive mutation/evolution; multi-party
  collective participation (beyond single-host pair); second
  meaningfully-different environment (O-04); V10 obstacle→
  capability loop + E3/E4 discriminating-protocol obligations.

## 6. Producer state (refreshed read-only)

- SST `../sst`: HEAD df78f42894a65c48f524337a498032617689a013
  (2026-10-04), porcelain 0, no tags, main only. 54-file snapshot
  recomputed exact (5f1f3789…). Ask 1 (owner contract + gate
  record) genuinely missing; byte identity satisfied.
- STC `../stc`: HEAD 548615a (freeze, Oct 7; record-only over
  code 1d1c535; +5 since 62cf5e6); EXTERNAL_PINS sst = df78f42
  unchanged; porcelain = 12 untracked only (zero tracked
  modifications). Ask 2A landed/stale; 2B (artifact decision +
  contract/evidence) genuinely missing. Recovery contract
  code-verified: fail-closed recover + explicit stc_restart =
  FULL replay, skipped:[], effect-repeat (see
  STC-548615a-ASSESSMENT.md). stc_adapter correctly stays
  UNQUALIFIED doc-reader; no re-pin.
- TRACE `../trace`: a24a937 (Sep 9), presence-only, no asks. TL:
  absent. `../trace-lite` (0df044b, Sep 12) unreferenced, out of scope.
- PINS.json STC section deliberately pins 8fa8ac3-era docs
  (no HEAD-following); re-pin only when pursuing STC consumption.

## 7. U-execute rectification state

Drafts (U-execute/, 2026-10-04/05) are coherent pre-build design
contradicted by built bytes on every load-bearing interface: report
schema (flat vs envelope+compat), counts (invented RELCHECK-COUNTS
vs unittest grammar + demo marker), identity (byte-blobs vs inline
JSON + extras scan), surface (global vs per-tag AST), ledger
binding (subset vs argv/input_hashes/invoke_id/deny/create gating),
baseline CLI/staging/env (broken vs built), pins sketch (7 keys vs
15), "no SST leg" wording (false — SST executes in suite children).
Frozen checker + p_ledger_report_agree as drafted return
INVALID/False on every real run: reconciliation is a rewrite, not
a fill-in. Coordinator rulings (recorded in worker briefs):
checker rewritten data-first with deliberate kill-shape acceptance
(rev4 3ea4868d…, battery 29/29); predicates amended via
RULES-AMENDMENT-2 (a) compat shape + (b) §7.6/R-C/docstring record
+ (c) A-ENVELOPE correction + (d) kill adopt shape + (e) steps
universe + (f) P9 budget/subset rule (d12adfa2…); direct_run.py
schema-3 (44ced7dd…) is THE baseline form; frozen pins rebuilt
from built 15-key pins (1e3a3a6a…, seal 5c3d1bbd…);
p_no_sst_leg rescoped to snapshot confinement; graded file =
COMPAT-REPORT.json (§7.3 text, no amendment); P10 from closure
walls (suite-r3 110.7/111.483 s → 55.4/55.7 s, ±0.25W); P12 =
3.12.3/3.12.3 + ext4 /tmp + quiet-load ≤2.0; revision by held-out
author with sealed envelope + throwaway validation. Workers (write
ownership + information barriers): urec-checker, urec-baseline,
urec-pins-predicates, urec-revision-author. §7.8 countersigned
2026-10-06T13:35:45Z (PREREG-LOG entry ba821dd0…); G-RE re-gate
green at filing (freeze 6/6, IDENTITY 56/56, baseline 1161/1161,
zero pre-countersign runs); legs executing per RUNBOOK.

## 8. Change log (this refresh)

- R10/R11/R12/Q4 rows corrected to S5-era evidence; S5-proc/U-exec/
  P1-prod rows added; ANIMA authorship + cautions (B1/B2 paused,
  O-11 unobserved) recorded; producer states refreshed with exact
  identities; U-execute moved BLOCKED→IN PROGRESS per FINISH
  directive with step-0 negative preserved in envelope.
- Stale wordings fixed: r1-era SST posture marked superseded; r1
  "current useful result" → historical; §4 stale X3 clause replaced;
  §5 SST line + deferred-ambitions list updated; §6 r3 standing
  updated (re-scope answered).
- Reconciliation pass (2026-10-06, read-only agent + coordinator
  integration): all rows checked vs ANIMA packet + bytes, no
  material overclaim; STC HEAD refreshed (62cf5e6, +10);
  dangling CANONICAL-RECORD §2 companion pointer repaired (this
  map IS the canonical record); §7 "vs 14" → "vs 15"; R4
  channels→mechanisms; R5 cross-host unified to DEFERRED; Q4
  M1-redux-instrument nuance + D-005 standing signal-semantics
  row; deferred list extended (D-008 training/mutation,
  multi-party collective, O-04 second environment, V10/E3-E4
  loop); §7.8 filing recorded in U-exec row.
