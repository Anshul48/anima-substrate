# PREREG-ENTRY-DRAFT.md — U-execute §7.8 entry text + RULES-AMENDMENT-2 (DRAFT, NOT FILED)

Author: U-execute rebuild agent. Status: PREPARATION ONLY — the coordinator
issues the amendment and appends/countersigns the entry at U-prereg freeze.
Nothing here touches PREREG-LOG.md.

Ground truths this draft rests on:
- Built pins `prototype/successor-005/vehicle/relcheck-pins.json`
  (bundle `1fee2241…`, pins `2dbb0439…`, 6 steps, suites
  r1=9+demo / r2=9+27 / r3=9+39 with `expect_skipped: 0`, per-tag
  surface minima). Source file: 52136 bytes, sha256
  `de011effbed363499e29e2fd0ee8eb6e0012351d4c0f5edd3f4612d48d657988`.
- NOTE-1 closure: `prototype/successor-005/runs/note1-closure/`
  (READINESS-PASS, host wall 183.2 s, both arms ACCEPT; per-step walls
  host suite-r3 110.7 s / direct 111.483 s; launch load 0.98).
  NOTE-1 CLOSED by coordinator READINESS-PASS 183.2 s
  (COMPLETION-MAP.md:124-127); lane verdict ACCEPT-WITH-NOTES
  (S5-lane/VERDICT.md:3).
- NOTE on brief vs bytes: the brief's "14-key pins" and "CANONICAL-RECORD.md
  S5 paragraph" do not match the tree — the pins file holds 15 keys
  (see §4 key inventory; `pins_sha256` hashes the in-bundle 9-key
  pins.json, not the full file) and the NOTE-1 CLOSED record sits in
  COMPLETION-MAP.md, not CANONICAL-RECORD.md. This draft follows the bytes.

---

## 1. RULES-AMENDMENT-2 (DRAFT text for the coordinator to issue)

Style after RULES-AMENDMENT-1 (PREREG-LOG.md:64-75).

---

## RULES-AMENDMENT-2 <date> (coordinator; not an experiment entry)

Three built-bytes corrections to the S5-DESIGN §7 predicate/prose freeze are
admitted explicitly (all pre-freeze, all witnessed against built successor-005
bytes; the U-EXECUTE entry freezes the amended bytes):

(a) Compat-shape amendment. The §7.6 `p_ledger_report_agree` reads
`report["suites"][step]["rc"]`; the built packaged report nests the graded
COMPAT-REPORT under `report["compat"]` with per-tag suites `r1/r2/r3` carrying
`{ok, results[{file, rc, ran, skipped, ok}]}` (relcheck.py step_compat /
step_package). The amended predicate requires: every ledger suite-step exit 0
AND every per-tag ok flag True AND every per-program rc 0 with ok True over
non-empty results. Counts stay the checker's job (§2.3(b)). Logic preserved
(rc/ok agreement); input shape follows the built bytes.

(b) §7.6 + R-C + docstring-fix record. The frozen predicates are §7.6 verbatim
PLUS the coordinator-directed R-C delta (STEPS gains "package"; kill leg still
targets suite-r3) and the docstring fix (the §7.6 docstring overclaims counts;
the code checks rc/ok only — the fixed docstring says so). Both deltas predate
this amendment and are recorded here, not introduced by it.

(c) A-ENVELOPE wording correction. The §7.4 A-ENVELOPE parenthetical
"(outside SST leg — uninvolved)" and the §5.2(e)/§8.2 "no SST leg anywhere"
wording are FALSE against built bytes: SST executes inside the suite children
against the qualified vendored snapshot (relcheck.py run_child SST_VENV_PY
forwarding; manifest env_extra on suite steps; sst_leg.py pre/post snapshot
gates). The envelope stays $0/offline via the qualified snapshot, and
`p_no_sst_leg` is rescoped to `p_sst_snapshot_confined` (pinned venv
interpreter abspath; sst-leg outputs only under scratch copies; zero
network/key/cost evidence). A-ENVELOPE henceforth reads: any network/key/cost
evidence, or any non-stdlib execution outside the qualified SST snapshot
confinement, ⇒ ABORT. No U-execute run predates this correction.

This amendment changes rules + frozen prose only, not the entry chain.

---

## 2. U-EXECUTE §7.8 ENTRY TEXT (DRAFT for the coordinator to file)

Per PREREG-LOG.md format (`## <ID> <stamp>` + fields + `entry_hash`).

---

## U-EXECUTE <UTC-stamp>

- experiment: U-execute (S5 §7; H = successor-005 procedure worlds,
  D = direct_run.py stdlib baseline; legs clean + change + kill, both arms)
- work_dir: prototype/programme-20261004/U-execute/
- prev_hash: <coordinator: sha256 of the full M1-REDUX entry text
  including its countersign line, per PREREG-LOG.md chain rule>
- gate_basis: S5-A1–S5-A12 all PASS (lane ACCEPT-WITH-NOTES;
  S5-A10 lane-RED environmental CLOSED by coordinator READINESS-PASS
  183.2 s, COMPLETION-MAP.md:124-127); G-RE re-gate applied pre-run
- rules_basis: RULES-AMENDMENT-2 (compat shape + §7.6/R-C/docstring
  record + A-ENVELOPE/SST correction), issued <date>, this log
- prereg: PREREG.md sha256 <RE-TAKE AT FREEZE; draft-basis 2026-10-06
  value recorded in §5>
- predicates: predicates.py sha256 <RE-TAKE AT FREEZE; amended-draft
  `71375005…`; amended functions quoted verbatim in PREREG.md §5>
- predicates_note: verdict imports this module verbatim, never
  reimplements; §7.6 + R-C + docstring fix + RULES-AMENDMENT-2(a)(c)
- checker: verdict_relcheck.py sha256 <RE-TAKE AT FREEZE — sibling
  reconcile in progress at draft time>
- baseline: direct_run.py sha256 <RE-TAKE AT FREEZE — sibling
  reconcile in progress at draft time> (stdlib form; Makefile.template
  discarded from freeze)
- pins: frozen-pins.json sha256 <RE-TAKE AT FREEZE after coordinator
  countersigns bytes; draft `f1c3b4d2…`, 55988 bytes>
- pins_note: 15 built keys verbatim from vehicle/relcheck-pins.json
  (source sha `de011eff…`, 52136 bytes) + u_execute chapter (graded
  file, redaction field list, kill-shape rule, envelope seal slot)
  + per-key provenance
- task_pins: P1 bundle `1fee2241…`; P2–P4 inline-JSON 6-tag identity
  (r1:76/s002:96, r2:27/s003:100, r3:24/s004:100); P5 frozen roots
  (pins `frozen`); P6 suites r1=9+demo/r2=9+27/r3=9+39, skipped 0;
  P7 per-tag surface minima r1 14/19, r2 15/21, r3 15/21;
  P8/P9 envelope slot {author: held-out-revision-agent,
  sha: SEALED-AT-FREEZE, reveal post-countersign, validation
  throwaway-disclosed}; P10 kill suite-r3 @0.5W (host 55.4 s /
  direct 55.7 s), ±0.25W, void-if-out-of-window; P11 cap 2; P12
  /usr/bin/python3 3.12.3 + venv abspath 3.12.3, /tmp ext4,
  quiet-load ≤2.0; P17 6 steps; P18 packaged {nonce,run_id,mode} +
  shas, world_id/idem_key ledger-side; P19 unittest grammar + demo
  marker + 2-log layout; P20 verdict_rule bools/per-tag
- envelope: revised bundle sha256 <SEALED-AT-FREEZE — held-out
  revision agent ref + sha filed here at freeze>
- blinding: graded file COMPAT-REPORT.json (§7.3, coordinator ruling,
  no amendment); frozen redaction field list in frozen-pins.json;
  empirical witness redact-guess.log (NOTE-1 compat bytes
  byte-identical 5065 B sha `099f4e33…`, redaction no-op, nothing
  arm-identifying)
- rule: HOST-VALUE-DEMONSTRATED iff H VALID + rubric bar on all legs
  AND guards hold AND ≥1 H-exclusive accountability cell present;
  else HOST-VALUE-NOT-DEMONSTRATED with failing cell named
  (PREREG.md §6; no cost/speed superiority claims by design)
- entry_hash_basis: sha256 of this entry body EXCLUDING this
  entry_hash line (all bytes above it, verbatim)
- entry_hash: <coordinator computes at append>
- countersigned: <coordinator verifies all file hashes + prev chain
  + envelope seal, quotes them, BEFORE first non-throwaway run>

---

## 3. DESIGN → BUILT CONCEPT MAP (§7.8 filing aid)

| Design language | Built concept (frozen here) | Amendment? |
|---|---|---|
| §7.1 IDENTITY.sha256 full bytes (P2–P4) | Inline-JSON 6-tag identity maps in pins (`identity.{r1,r2,r3,s002,s003,s004}`); no separate files exist | No — pin fill, concept change recorded in P2–P4 |
| §7.1 suite file lists + counts (P6) | `suites.{r1,r2,r3}.programs` verbatim (9+demo / 9+27 / 9+39, skipped 0) | No — fill |
| §7.1 surface minima (P7) | PER-RELEASE minima `surface_min.{r1,r2,r3}`; ACCEPT = per-release superset | No — fill (supersedes A12 global draft-proposal) |
| §2.2 report schema identities/suites/surface/verdict | Compat report keys exactly `{pins_sha256, identities, suites, surface, verdict}` | No — match |
| §2.3(d) PARTIAL/FAIL mapping (P20) | `verdict_rule`: ACCEPT iff all-ok; PARTIAL iff ident+suites ok w/ surface shortfall; else FAIL; bool/per-tag inputs | No — fill, logic = draft text |
| §7.6 `report["suites"][step]["rc"]` | `report["compat"]["suites"][tag]{ok, results[…]}` | YES — amendment (a) |
| §7.6 STEPS 5 + docstring "rc/count" | STEPS 6 (+package); docstring rc/ok-only | Recorded — amendment (b) |
| §5.2(e)/§7.4/§8.2 "no SST leg / uninvolved" | SST executes in suite children; qualified-snapshot confinement + $0/offline envelope | YES — amendment (c) |
| §7.3 graded COMPAT-REPORT.json | Unchanged — coordinator ruling, follows §7.3 text | No amendment |
| P18 run-identity-in-report proposal | Packaged `{nonce,run_id,mode}`+shas; world_id/idem_key ledger-side only | No — draft-proposal superseded by bytes |
| P19 RELCHECK-COUNTS line | unittest grammar + demo marker + 2-log layout; COUNTS line deleted | No — draft-proposal superseded by bytes |
| A14 worlds/key binding | Procedural binding kept; world_id IS on proc_begin rows (no predicate change) | None needed |

---

## 4. FROZEN-PINS KEY INVENTORY (byte provenance per key)

Source: `prototype/successor-005/vehicle/relcheck-pins.json` (52136 bytes,
sha256 `de011effbed363499e29e2fd0ee8eb6e0012351d4c0f5edd3f4612d48d657988`).
All 15 keys copied VERBATIM into `frozen-pins.json` (asserted by rebuild
script post-check); per-key sha256 over canonical JSON
(sort_keys/separators/ascii) is recorded in `frozen-pins.json` `provenance.keys`:

| Key | Content (built) | U-hole |
|---|---|---|
| `argv` | per-step argv pins (6 steps) | P17 support |
| `artifacts` | declared outputs per step (identity 1; suites 3/3/3; compat 1; package 1) | P19 2-log layout + P6 |
| `bin_relcheck_sha256` | `24e9425f…` (verified: matches `sha256sum vehicle/relcheck/bin/relcheck.py`) | P1 support |
| `bundle_sha256` | `1fee2241…` (= P1; canonical-manifest rule in make_vehicle_pins.py) | P1 |
| `demo_marker` | `integrated demo: OK` | P19 |
| `frozen` | 6 abspath roots (r1/r2/r3/s002/s003/s004) | P5 |
| `identity` | 6 inline maps (76/27/24/96/100/100 files; sizes match closure compat `files` counts exactly) | P2–P4 |
| `ignore_top` | `[runs, .test-tmp, __pycache__, .hypothesis, .pytest_cache]` | identity/copy contract |
| `pins_format` | `1` | format |
| `pins_sha256` | `2dbb0439…` — hashes the IN-BUNDLE 9-key pins.json bytes, NOT this file (make_vehicle_pins.py) | P16 anchor |
| `steps` | 6 steps incl. package | P17 |
| `suites` | r1 9+demo / r2 9+27 / r3 9+39, all skipped 0 | P6 |
| `surface_min` | per-tag minima r1 14/19, r2 15/21, r3 15/21 | P7 |
| `surface_trees` | `{r1: s002, r2: s003, r3: s004}` | P7 |
| `trees` | tag→dirname map (6) | P5 |

Plus `u_execute` chapter (graded file, redaction field list, kill-shape
rule ref, envelope seal slot) and `provenance` (source id + per-key shas).
frozen-pins.json: 55988 bytes, draft sha `f1c3b4d2…` (re-taken after
coordinator countersigns bytes).

## 5. A14 VERIFICATION (do built proc entries record world_id?)

YES. Closure `artifacts/host/ledger.jsonl` `proc_begin` payloads carry
`world_id` (value `RELCHECK`) at file lines 7 (identity), 10 (suite-r1),
13 (suite-r2), 16 (suite-r3), 19 (compat), 22 (package); the same payloads
also record `interpreter` (`/usr/bin/python3`), `interpreter_version`
(`3.12.3 … GCC 13.3.0`), `scratch`, `env_keys`, `argv_sha256`. Invoke
`proc` payloads do NOT repeat world_id (they carry `idem_key` =
`s5a10readiness`, `step`, `bundle_sha256`, `exit_code`, …) — binding a
proc row to its world still goes through the `create` row + procedural
fresh-key discipline, so per DRAFT-NOTES.md A14 no predicate change is
made; the finding is recorded only.

## 6. HOLE-BY-HOLE FILL / REDEFINE / OMIT

- P1 FILL: bundle sha from pins `bundle_sha256` (= manifest canonical rule).
- P2–P4 REDEFINE (concept change, not fill): separate IDENTITY.sha256 bytes
  do not exist in the built vehicle; redefined as inline-JSON lane-pair maps
  P2={r1,s002}, P3={r2,s003}, P4={r3,s004}, verbatim in frozen-pins.json.
- P5 FILL: frozen abspaths from pins `frozen` (r1/r2/r3 + s00x).
- P6 FILL: suite programs + expects from pins `suites` verbatim.
- P7 FILL: per-tag minima from pins `surface_min` verbatim (built shape
  supersedes the A12 global-minimum draft-proposal).
- P8/P9 SEAL SLOT (omit values by design): author held-out-revision-agent,
  sha SEALED-AT-FREEZE, reveal + validation terms fixed; content held out.
  This agent did not look in the sibling `sealed/` dir.
- P10 FILL (proposal): fraction 0.5 of arm's own closure suite-r3 wall
  (host 110.7 s → 55.4 s; direct 111.483 s → 55.7 s), tolerance ±0.25W,
  void-if-out-of-window, per-arm scaling — derived per DRAFT-NOTES A7 +
  §5.2(c) "mid-suite-r3"; coordinator adopts-or-replaces.
- P11/P17 FIXED: carried, verified against built manifest/steps.
- P12 FILL (+1 proposal): interpreters `/usr/bin/python3` 3.12.3 (proc_begin
  rows) + venv abspath `…/prototype/w1/.venv/bin/python` 3.12.3 (manifest
  env_extra; `--version` observed); `/tmp` ext4 (`df -T`); quiet-load
  ≤2.0 1-min at launch is a PROPOSAL (0.98 passed, 6–7 failed).
- P13 OMIT-SHA (coordinator re-take): checker reconcile owned by a sibling
  (observed `abfc56b0…`, 801 lines, moving); built reference `776924c5…`.
- P14 FILL (draft sha): amended predicates.py `71375005…`; re-taken at freeze.
- P15 FILL-FORM + OMIT-SHA: form = direct_run.py (stdlib; Makefile.template
  discarded); observed `9ee19b44…`, 587 lines, MOVING (sibling) — re-take.
- P16 FILL (draft sha): frozen-pins.json `f1c3b4d2…`, 55988 bytes; re-taken
  after coordinator countersigns bytes.
- P18 REDEFINE: packaged `{nonce,run_id,mode}`+shas; world_id/idem_key
  ledger-side only (built compat carries no run identity — redact-guess.log).
- P19 REDEFINE: unittest grammar + demo marker + 2-log layout; RELCHECK-COUNTS
  deleted (never in built bytes).
- P20 FILL (logic kept, inputs rebuilt): `verdict_rule` with bools/per-tag.

## 7. RESIDUAL FILING GAPS (coordinator acts)

1. Issue RULES-AMENDMENT-2 (§1 draft) to PREREG-LOG.md.
2. Adopt-or-replace the two [Proposal] values (P10 numbers, P12 load rule).
3. Build + throwaway-validate the revised bundle; file the P8/P9 seal
   (held-out revision agent; identical bytes to both arms at reveal).
4. Re-take ALL file shas (PREREG.md draft-basis `b25f6683…` — recompute:
  this draft's §2 `<RE-TAKE>` slots) after all sibling agents stand down;
  P13/P15 were observed moving during this rebuild.
5. Reconcile-or-adopt the U-execute checker (P13) against built bytes
  (sibling-owned; built reference `776924c5…`, 506 lines).
6. Countersign + append the §2 entry BEFORE the first non-throwaway run.

