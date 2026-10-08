# PREREG-LOG — append-only pre-registration anchor

Purpose: L1 lesson A fix — prereg bytes committed to an append-only,
externally-anchored log BEFORE execution. No git repo exists in this
workspace (deliberately not created); anchoring is by hash chain +
coordinator countersignature (entry hashes quoted in milestone reports,
which live outside the experiment dirs).

Rules:
- Coordinator-maintained. Experiment agents PREPARE entry text; the
  coordinator appends (or verifies + countersigns an agent-drafted
  entry) before the experiment's first non-throwaway run.
- Each entry carries: UTC stamp, experiment id, content sha256 of the
  frozen prereg file(s), the exact coded predicates (verbatim or by
  hash), task/generator pins, and prev_hash chaining to the prior entry.
- Format per entry: `## <ID> <stamp>` + fields + `entry_hash: <sha256
  of the entry body>`. Chain verified by recomputation (independent
  lanes welcome).
- Amendments are new entries referencing the old (never edits).

## GENESIS 2026-10-04T00:00:00Z

- prev_hash: 0000000000000000000000000000000000000000000000000000000000000000
- note: log created at L2 authorization; L1 predates it (L1 ordering
  evidence: DESIGN.md anchor + pins, see L1-transfer/VERIFICATION.md).
- (genesis carries no entry_hash; the first real entry's prev_hash is
  the sha256 of the genesis section bytes above, recomputable by anyone)

## M1-REDUX 2026-10-04T16:42:17Z

- experiment: M1-redux (grid+holdings → per-lane central_bytes on held-out
  lane descriptors; ACCEPTED H2 host; step-0 PROCEED with 26 observations)
- work_dir: prototype/programme-20261004/M1-redux/
- prev_hash: af809304fc61ba4698292232f1d8ff7a54c3a066df2815b67013dbf82cf88f0e
- prev_basis: sha256 of the PREREG-LOG.md genesis section bytes
  (## GENESIS line through end-of-file, 394 bytes as read 2026-10-04;
  coordinator to verify/recompute at append)
- prereg: PREREG.md sha256 cfe4f633840337abe96aca6743c69d691ef59c10762fa2edfdcb9a621a58d33c
- design: DESIGN.md sha256 89c0f0d95aebbdc88c8dcef564dbbaed1a21643f2de60ef77a86be20352f5556
- predicates: predicates.py sha256 a1089fb58c4952f8f566c689ebbc3d71fbd6e93e98b891bb5379039656935235
- predicates_note: exact coded predicates; verdict imports this module
  (never reimplements); quoted verbatim in PREREG.md section 3
- tasks: main/task-pins.sha256 sha256 96aa3a91c8134e532b3d92c954877d3405c2df70aa5786dd23a6e7f9e99b7c6e
- tasks_note: 36 pins (18 train M1R-TR-01..18 + 18 test M1R-TE-01..18,
  all 9-char IDs, disjoint from each other and from M1R-T0-* probes)
- generator: gen_main.py sha256 34fb6e618fc890605870abd00f9bd7b7f06dcfa1d04bfa66e6aea234d65effb0
- generator_note: deterministic; regeneration verified byte-identical
  (sha256sum -c 36/36) before freezing
- harness: harness.py sha256 28ff96906c8e1d058420a93638d73ecf522ff6f3a191e7db64017f484edaed7d
- runner: run_main.py sha256 7aebd2e46d629f23d7adf1faef8b8a11ce492e496e43942ff4a30e2bf722b76f
- rule: N_TEST_ITEMS=36; P1=(mae_model < 0.5*mae_const);
  P2=(mae_model < 0.5*mae_rule); valid=(36 test items present AND VALID,
  fallback_uses==0, both phase guards reproduce S1 655/0 + S2 310/500,
  TR/TE/T0 IDs pairwise disjoint); OVERALL=PASS iff valid AND P1 AND P2,
  VOID iff not valid, else NEGATIVE
- model: per-group-mean over (n_tasks,nL_req,nS_req,nL_pref,nS_pref,lane);
  baselines CONSTANT (train global mean) + HOST-RULE (train mean per
  (rule_lane, exec_lane)); metric MAE on central_bytes
- entry_hash_basis: sha256 of this entry body EXCLUDING this entry_hash
  line (all bytes above it, verbatim)
- entry_hash: e077d5e49797cdac01d2e59b912f6010d4c27e3d8eeb0fc2d13018b912b93de5
- countersigned: 2026-10-04T16:50Z coordinator verified all 7 file hashes + prev af809304... + entry e077d5e4...; next prev_hash = sha256 of this full entry text including this line

## RULES-AMENDMENT-1 2026-10-04 (coordinator; not an experiment entry)

The no-round-trip exception procedure used by M1-redux is admitted
explicitly: an agent MAY proceed to non-throwaway runs after writing
PREREG bytes + entry text with hashes in its report, WITHOUT waiting
for the coordinator append, PROVIDED (a) the entry text predates the
first non-throwaway run, (b) all prereg bytes are immutable afterward
(any fix = new file + report note), (c) the coordinator later verifies
hashes + chain and countersigns by quoting them. M1-redux met all
three (ENTRY 14s before first run; 0 byte changes; chain verified).
The default (append-before-run) remains preferred where no round trip
is at stake. This amendment changes rules only, not the entry chain.

## RULES-AMENDMENT-2 2026-10-06 (coordinator; not an experiment entry)

Six built-bytes corrections to the S5-DESIGN section 7
predicate/prose freeze are admitted explicitly (all pre-freeze, all
witnessed against built successor-005 bytes; the U-EXECUTE entry
freezes the amended bytes):

(a) Compat-shape amendment. The section 7.6 `p_ledger_report_agree`
reads `report["suites"][step]["rc"]`; the built packaged report nests
the graded COMPAT-REPORT under `report["compat"]` with per-tag suites
`r1/r2/r3` carrying `{ok, results[{file, rc, ran, skipped, ok}]}`. The
amended predicate requires: every ledger suite-step exit 0 AND every
per-tag ok flag True AND every per-program rc 0 with ok True over
non-empty results. Counts stay the checker's job (section 2.3(b)).
Logic preserved (rc/ok agreement); input shape follows the bytes.

(b) Section 7.6 + R-C + docstring-fix record. The frozen predicates
are section 7.6 verbatim PLUS the coordinator-directed R-C delta
(STEPS gains "package"; kill leg still targets suite-r3) and the
docstring fix (the section 7.6 docstring overclaims counts; the code
checks rc/ok only -- the fixed docstring says so). Both deltas
predate this amendment and are recorded here, not introduced by it.

(c) A-ENVELOPE wording correction. The section 7.4 A-ENVELOPE
parenthetical "(outside SST leg -- uninvolved)" and the section
5.2(e)/8.2 "no SST leg anywhere" wording are FALSE against built
bytes: SST executes inside the suite children against the qualified
vendored snapshot (relcheck.py run_child SST_VENV_PY forwarding;
manifest env_extra on suite steps; sst_leg.py pre/post snapshot
gates). The envelope stays $0/offline via the qualified snapshot,
and `p_no_sst_leg` is rescoped to `p_sst_snapshot_confined` (pinned
venv interpreter abspath; sst-leg outputs only under scratch
copies; zero network/key/cost evidence). A-ENVELOPE henceforth
reads: any network/key/cost evidence, or any non-stdlib execution
outside the qualified SST snapshot confinement, implies ABORT. No
U-execute run predates this correction.

(d) Kill-leg adopt-shape acceptance. `p_kill_leg_shape` accepts two
suite-r3 shapes: rerun (began twice, succeeded once) and adopt
(began once, success invoke carries recovered:true -- the kill
landed between DONE and the invoke row, so resume adopted without
re-running; built L3 adopt-if-complete). Kill legs run the BASE
bundle (P17 6 steps); the predicate's steps parameter stays
default (PREREG.md C5).

(e) Steps-universe parameter. The step-universe predicates
(`p_steps_complete`, `p_change_leg_shape`, `p_kill_leg_shape`) take
an optional steps list defaulting to STEPS; change legs pass the
revised manifest's step list. No other logic change.

(f) Change-leg conformance budget + checker subset rule. The revised
bundle must meet the P9 section 3 (1+1+1) budget: exactly one added
step carrying exactly one added declared output (base steps'
declared sets byte-equal) + exactly one added suite target in the
existing tags + a program delta present (relcheck.py bytes changed
XOR one added bin/ program argv-referenced by the new step); no
removals anywhere. u-harness.py derive-revised-pins enforces this
mechanically (P9-conformance; violation implies VOID). On change
legs the checker applies the non-base input subset rule: non-base
step inputs must carry params/pins presence (extras advertise-bound
via bundle files[] re-hash); base steps keep exact input-set
equality.

This amendment changes rules + frozen prose only, not the entry chain.

## U-EXECUTE 2026-10-06T13:35:45Z

- experiment: U-execute (S5 section 7; H = successor-005 procedure
  worlds, D = direct_run.py stdlib baseline; legs clean + change +
  kill, both arms)
- work_dir: prototype/programme-20261004/U-execute/
- prev_hash: 4e865fea70365dc601b4ad178dee853fe275d1e46e9b701198698f499804af0a
- prev_basis: sha256 of the PREREG-LOG.md M1-REDUX entry bytes (file
  bytes 1398..3825): the `## M1-REDUX` line through the countersigned
  line including its newline, per that entry's "next prev_hash"
  declaration; recomputable (M1 entry_hash also recomputed OK)
- gate_basis: S5-A1 through S5-A12 all PASS (lane
  ACCEPT-WITH-NOTES; S5-A10 lane-RED environmental CLOSED by
  coordinator READINESS-PASS 183.2 s, COMPLETION-MAP.md:124-127);
  G-RE re-gate at filing: freeze-check 6/6 OK, IDENTITY 56/56 OK,
  FROZEN-BASELINE 1161/1161 OK, zero U-execute runs pre-countersign
- rules_basis: RULES-AMENDMENT-2 (a) compat shape + (b) section
  7.6/R-C/docstring record + (c) A-ENVELOPE/SST correction +
  (d) kill adopt shape + (e) steps universe + (f) P9 budget/subset
  rule, issued 2026-10-06, this log
- prereg: PREREG.md sha256 56f3b30997dc069f666dba75d01ee6f90b08e6b0600e4dc1824f582c5a8c88c4 (29770 bytes, FILED)
- predicates: predicates.py sha256 d12adfa2229c326de6567e0f00cdba50c7ce6be8f51498913aebe548676e3d47
- predicates_note: verdict imports this module verbatim, never
  reimplements; section 7.6 + R-C + docstring fix + amendment
  (a)(c)(d)(e); amended functions quoted verbatim in PREREG.md
  section 5 (5 functions + constants block verified byte-exact)
- checker: verdict_relcheck.py sha256 3ea4868d485d04ffa5b4d152217a7c54baa3bfabbead0ceb91fc1351fbe38de5 (rev4)
- baseline: direct_run.py sha256 44ced7ddffb9a45ddd2384eaad48267d52db89165e17e674582f26bcb559333e (stdlib STAMP_SCHEMA 3;
  Makefile.template discarded from freeze)
- pins: frozen-pins.json sha256 1e3a3a6a587e6eee5d2de57bce9738417c24eb4114d4ba24ceaea2937fe04884 (56036 bytes; seal slot filled)
- pins_note: 15 built keys verbatim from
  vehicle/relcheck-pins.json (source sha de011effbed363499e29e2f
  d0ee8eb6e0012351d4c0f5edd3f4612d48d657988, 52136 bytes) +
  u_execute chapter (graded file, redaction field list, kill-shape
  rule, envelope seal slot) + per-key provenance
- harness: u-harness.py sha256 ded5fd36a73461423562850684830ee8057e3f387fc75944880e801dbb519ed2 (kill-watch/eval/blind/
  derive/freeze-check/selftest)
- battery: checker-battery.py sha256 f95e8a3693c9732b1ff4e105181198ecd2d20f9c8ba3a1ba8c24accdece7fee3; battery-bytes tree
  6922cd65d259cd95ed6c7260ef6752e37982b077714c097ab5457f86bb6b12b7 (60 files, SNAPSHOT-EXACT)
- evidence: checker-negatives.log sha256 796b54e50271ef1192fcc0a55f1c1312f1f80a985bf72646fa408cb2a90474ba (29/29: 8 pos +
  21 neg); u-harness-selftest.log sha256 4d06907777c99e3c0bda54f4ddb68a52d0fa19159a549622ec4fcbdfa0e9b8cc (54/54)
- runbook: RUNBOOK.md sha256 319c0b628b945124d99376be9f8690064e0bb33b1c3fbff6eecf37d9810c27d2 (execution order)
- task_pins: P1 bundle 1fee2241d1fd2d48; P2-P4 inline-JSON 6-tag
  identity (r1:76/s002:96, r2:27/s003:100, r3:24/s004:100); P5
  frozen roots (pins `frozen`); P6 suites r1=9conf+demo/
  r2=9conf+27atom/r3=9conf+39atom, skipped 0; P7 per-tag surface
  minima r1 14/19, r2 15/21, r3 15/21; P8/P9 envelope slot
  {author: held-out-revision-agent, sha: 5c3d1bbdd9a74dc00436983a72f743072af79ea5bd647e1184d4a1cd9790ce60, reveal
  post-countersign, validation throwaway-disclosed}; P10 kill
  suite-r3 at 0.5W (host 55.4 s / direct 55.7 s), +-0.25W,
  void-if-out-of-window; P11 cap 2; P12 /usr/bin/python3 3.12.3 +
  venv abspath 3.12.3, /tmp ext4, quiet-load <=2.0; P17 6 steps;
  P18 packaged {nonce,run_id,mode} + shas, world_id/idem_key
  ledger-side; P19 unittest grammar + demo marker + 2-log layout;
  P20 verdict_rule bools/per-tag
- envelope: revised bundle sha256 5c3d1bbdd9a74dc00436983a72f743072af79ea5bd647e1184d4a1cd9790ce60 (held-out-revision-agent;
  REVISION-MANIFEST.json sha256 d2e6dcd48c2dc947173225c5c66d0037213424de1c8a46bc220137b4fe94008b verified values-only;
  revision-bundle/ never opened pre-countersign)
- blinding: graded file COMPAT-REPORT.json (section 7.3,
  coordinator ruling, no amendment); frozen redaction field list
  in frozen-pins.json; empirical witness redact-guess.log (NOTE-1
  compat bytes byte-identical 5065 B sha 099f4e3388a6b8dc7ed1df1bf4e9411c921dd7696932d9be983d2fbb6bf31167, redaction no-op,
  nothing arm-identifying)
- rule: HOST-VALUE-DEMONSTRATED iff H VALID + bar met on all legs
  AND guards hold AND at least 1 preregistered H-exclusive
  accountability cell present; else HOST-VALUE-NOT-DEMONSTRATED
  with failing cell named (PREREG.md section 6; no cost/speed
  superiority claims by design)
- entry_hash_basis: sha256 of this entry body EXCLUDING this
  entry_hash line (all bytes above it, verbatim)
- entry_hash: ba821dd039077c29820da9a6b3fb0cca44eeb7f89db4e46078786e58c2f45eea
- countersigned: 2026-10-06T13:35:45Z coordinator verified all 10 file hashes + battery tree + prev 4e865fea70365dc6... + entry ba821dd039077c29... + envelope seal 5c3d1bbdd9a74dc0... (values-only) + G-RE re-gate (freeze 6/6, IDENTITY 56/56, baseline 1161/1161, zero pre-countersign runs); next prev_hash = sha256 of this full entry text including this line
