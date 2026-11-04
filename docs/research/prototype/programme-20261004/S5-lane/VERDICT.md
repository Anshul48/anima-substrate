# S5-lane/VERDICT.md — S5-A12 independent verification of successor-005

## Overall lane verdict: ACCEPT-WITH-NOTES (see NOTE-1..NOTE-4)

Lane: `prototype/programme-20261004/S5-lane/` (this dir + `logs/` +
`scratch/` are the lane's only writes). All commands from the
substrate repo root with `PYTHONDONTWRITEBYTECODE=1` unless noted.
U-execute was NEVER run. s005 + all frozen trees were never edited
(see §Frozen both-ends); the pins-regen leg rewrote 3 vehicle files
with byte-identical content per the brief, proven by pre/post hashes +
IDENTITY re-check. Interpreter: `prototype/w1/.venv/bin/python`
(Python 3.12.3) for all OWN runs; `SST_VENV_PY` exported to the same
path for readiness.

Provenance marks: OWN = run by the completing agent in this lane
(log `*.own.log`); PRIOR = run by the earlier lane agent (≈85% lane,
cancelled), whose logs + scratch persist and were VERIFIED by the
completing agent (line counts, ok Tallies, zero FAIL/ERROR, landings,
byte comparisons) but NOT re-executed.

## Per-gate table (S5-A1–S5-A11), all numbers quoted from lane evidence

| Gate | Verdict | Evidence (command → observed output) |
|---|---|---|
| S5-A1 carried suites + demo + calibrate + snapshot + R-A + accept | PASS | OWN: `test_conformance.py` → `Ran 9 tests … OK` (12.6 s, `02b-test_conformance.own.log`); `test_fission.py` → `Ran 7 … OK` (11.1 s); `test_successor.py` → `Ran 17 … OK` (52.1 s). PRIOR (log-verified): `Ran 9 … OK` (10.1 s), `Ran 7 … OK` (9.7 s), `Ran 17 … OK` (43.1 s), `Ran 39 … OK` (542.3 s, atomicity; 39 ok lines + landings incl. `50 SIGKILLs, 0 torn side files`). OWN: `successor_demo.py --run-dir=<lane-scratch>` → exit 0 `successor-005 integrated demo: OK` (`04-demo-r5.own.log`); s004 demo → exit 0 (`04-demo-r3.own.log`); R-A canon diff → EMPTY, 15 lines each (`04-demo-RA-diff.own.log`); `lane_accept_check.py` → `46/46 exact fields MATCH` + 6/6 byte refs MATCH (`04-accept.own.log`); `calibrate.py` → `2.61x` (`04-calibrate.own.log`); `verify_snapshot.py` → `MATCH files=54 hash=5f1f3789…` (`04-snapshot.own.log`). C2/C3 gating: negative legs inside the green successor/conformance suites. |
| S5-A2 declaration honesty | PASS (PRIOR evidence) | PRIOR `test_procedure.py` → `Ran 57 … OK` (5903.4 s): 57 ok lines incl. advertise/birth/table-mismatch/staged-tamper legs; 0 FAIL/ERROR (`02-test_procedure.log`, line-count verified). NOT re-run (100-min suite; handoff bound — see NOTE-2). |
| S5-A3 service honesty | PASS (PRIOR evidence) | Same 57/57 log: direct-invoke-without-envelope denied, forged-bundle gate, key-collision, nonzero-exit, hybrid-world legs all ok. NOT re-run (NOTE-2). |
| S5-A4 permissions + escape refusal | PASS (PRIOR evidence) | Same 57/57 log: P1–P9 legs (no-shell AST sweep, scratch/env/stdin/caps, timeout kill, interpreter pin, post-run tamper, outside-scratch) + P11–P13 non-claim legs ok. NOT re-run (NOTE-2). |
| S5-A5 accountability | PASS (PRIOR evidence) | Same 57/57 log: inputs-recorded, success-fields-recomputable, ledger-matches-bytes, staged-tamper legs ok. NOT re-run (NOTE-2). |
| S5-A6 interruption matrix | PASS (PRIOR evidence) | Same 57/57 log: L1–L5 legs ok + `sigkill loop landings={'L2': 13, 'L3': 27} wall=118.22s` + `repeated-kill loop: 12 rounds, killed-live=12`. PRIOR own-param legs (log-verified): opmatrix 15 fission boundaries + 4/4 settle SIGKILL `ALL CONVERGED wall=88.5s` (`03-lane-opmatrix.log`); L2/L3 10 rounds `landings={'L2': 3, 'L3': 6, 'complete': 1}` `ALL CONVERGED wall=1000.5s` (`03-lane-l2l3.log`). |
| S5-A7 conservation + recovery | PASS (PRIOR evidence) | Same 57/57 log: conservation-after-kills, grant-exactness, recover-classes, recover-never-spawns legs ok. NOT re-run (NOTE-2). |
| S5-A8 change flow | PASS (PRIOR evidence) | Same 57/57 log: `test_revised_bundle_new_world` ok. NOT re-run (NOTE-2). |
| S5-A9 frozen intact | PASS | PRIOR pre-hashes (verified: counts + zero non-OK): s002 41, s003 45, s004 45, H2-lane 46, s005 56, FROZEN-BASELINE 1161 OK / 0 non-OK (`00-pre-*.log`, `00-pre-baseline.log`). OWN post-hashes: IDENTICAL counts, all 0 non-OK (`08-post-hashes.own.log`). Copy manifests src/dst IDENTICAL. Readiness frozen-pre 969 clean in every attempt; frozen-post 969 clean in attempt 1. Vehicle MANIFEST `env_extra.SST_VENV_PY` pinned to the venv interpreter (3 steps). |
| S5-A10 vehicle readiness | LANE-RED (environmental; NOTE-1 gates) | RED-1 (PRIOR, verified from artifacts): READINESS-FAIL — host arm VALID (`executed=6 … wall=914.6s`, `checker(host): RELCHECK-VALID`), direct arm killed: suite-r3 atomicity rc=-9 at exactly 580.0 s with 34/39 ok + ZERO failures (`05-readiness.log` + `scratch/lane-readiness-direct/artifacts/suite-r3/`). RED-2 (OWN, quiet-lane, box load 6–7): READINESS-FAIL — host arm killed at suite-r3 (inner 580 s child timeout at 31/39 ok + ZERO failures, then 600 s step TimeoutError); suite-r1/r2 `ok: true` (`05-readiness2.own.log` + `scratch/lane-readiness2*/`). Supporting: builder READINESS-PASS host wall 175.8 s (EVIDENCE.md); PRIOR night retry host-green 165.0 s (incomplete, cancelled mid-direct-arm, `05-readiness-retry.log`). Same bytes pass in ~170 s on a fast box and are killed by the 580/600 s budgets on this box — environmental, not product (analysis in §Reds). Pins regen (PRIOR, byte-identity VERIFIED by own `cmp` + sha): bundle `1fee2241…`, pins `2dbb0439…` (`05-pins-regen.log`, `05-pins-preregen.sha256`, `scratch/pins-preregen/`). Tamper legs (OWN): T0 control `RELCHECK-VALID` + T1/T2/T3/T4a/T4b all `RELCHECK-INVALID` naming identity / suite-r2-skew / compat-argv-skew / verdict-rule / foreign-bundle axes (`07-tamper.own.log`; input root = attempt-1 host-VALID run). |
| S5-A11 wording | PASS (own verdict) | OWN re-audit of the PRIOR sweep (`06-wording-sweep.log`) + full-context reads: every C-family hit is negated (`no OS sandbox/containment`, `not a sandbox`, `CONTRACTUAL (not isolated)`, `(not OS isolation)`), a module path (`sst.sandbox.custody` import), or the SST-child `in-sandbox` descriptor with an explicit LEFT-non-atomic carve-out (IB:38, EVIDENCE:391 — NOTE-4); every IMPOSSIBLE hit is bounded (CONSUMER:96 cites mechanism + N1 carve-out + loud-refusal landing; rest are WITHDRAWN-claim prose or the defined `adopt-impossible` term); every durability sentence carries LIMITS-2 process-crash/power-loss + no-fsync separation; N1 defined EVIDENCE:206-208, N2 = LIMITS-2; required terms `accountable executor` + `scoped invocation` + `contractual` present in CONSUMER/EVIDENCE/procedure.py. Tree's 3 wording tests green inside PRIOR 57/57. |
| S5-A12 this lane | COMPLETE → ACCEPT-WITH-NOTES | Fresh-eyes re-run per S5-A12-BRIEF-DRAFT: byte-verify both ends, recount 9/7/17/39/57, suites (3 OWN + 2 PRIOR-verified), own-param kill legs (PRIOR-verified), own tamper legs (OWN), pins regen (PRIOR-verified), readiness ×2 to verdict (RED-1/RED-2), demo/R-A/accept/calibrate/snapshot (OWN), wording re-audit (OWN). All reds preserved below. |

## Reds (all preserved, none erased by retry)

- RED-1 — readiness attempt 1 (PRIOR agent, loaded box): `READINESS-FAIL`.
  Host arm fully VALID (`executed=6 skipped=0 re_executed=0
  wall=914.6s`, `checker(host): RELCHECK-VALID`, frozen-pre/post 969
  clean). Direct arm: `suite-r3: FAILED rc=1` — inner atomicity child
  SIGKILLed by the bundle's `CHILD_TIMEOUT_S=580.0` (`run_child`,
  `vehicle/relcheck/bin/relcheck.py:39`): rc=-9 at exactly 580.0 s,
  partial log 34/39 `... ok`, 0 FAIL/ERROR lines (verified by the
  completing agent: `grep -c` on
  `scratch/lane-readiness-direct/artifacts/suite-r3/SUITE-R3-atomicity.log`).
  No report ⇒ `checker(direct)` INVALID (missing file). Log:
  `logs/05-readiness.log`. Cause: box too slow for the 580 s budget —
  the suite was all-green when killed, zero test failures.
- RED-2 — readiness attempt 2 (OWN run, quiet lane, box load 6–7, no
  other lane jobs; `ps` quiet-check + `uptime` at launch in the
  session record): `READINESS-FAIL` on the HOST arm this time:
  suite-r1/r2 `ok: true` (identity → r1 → r2 done 10:03→10:10, r2
  step ≈ 367 s), then suite-r3 killed — inner 580 s child timeout at
  31/39 ok + 0 FAIL/ERROR (died mid-`test_sigkill_spec_window_50`),
  then host step `TimeoutError: step 'suite-r3' exceeded
  timeout_s=600.0`. Partial log:
  `scratch/lane-readiness2/state/proc-scratch/s5a10readiness/suite-r3-attempt1/SUITE-R3-atomicity.log`
  (31 ok / 0 FAIL). Log: `logs/05-readiness2.own.log`. Cause: SAME
  environmental signature as RED-1 — identical bytes run the full
  host arm in 165–176 s on a fast box (builder EVIDENCE 175.8 s;
  PRIOR night retry 165.0 s) but exceed the 580/600 s budgets on this
  daytime box (this lane's own direct atomicity reference: 542.3 s,
  already within 7% of the 580 s budget before host overhead). No
  third attempt was made: load stayed 5–7 and rising through the
  window, so a retry had no reasonable prospect of passing and would
  only add churn; NOTE-1 gates the downstream step instead.
- Incomplete, NOT a red: PRIOR night retry (host green 165.0 s through
  the expense gate, cancelled mid-direct-arm; root did not persist —
  presumably /tmp). No verdict attachable; cited only as supporting
  speed evidence. Log: `logs/05-readiness-retry.log`.
- RED-3 — lane operator error (OWN, fixed in-lane, product never
  implicated): demo with relative `--run-dir` → S3 child crashed,
  `RuntimeError: child never signaled READY`; no stray files left;
  absolute-path re-run exit 0. Preserved in
  `logs/04-demo-r5-red3.note`.
- RED-4 — lane script bug (OWN, fixed in-lane, product never
  implicated): `lane_tamper.py` T2 copy named `artifacts-t2` tripped
  the checker's `proc-<key>` naming rule before reaching the skew
  leg; fixed to keep the `proc-s5a10readiness` basename → 5/5 legs
  green. Preserved in `logs/07-tamper-red4.note`.

## Notes

- NOTE-1 (BEHAVIOR-GATING): S5-A10 is lane-RED (RED-1 + RED-2, both
  timeout kills of all-green suites on a slow box, zero test failures
  in either partial log). U-execute prereg (§7.8) MUST NOT be filed on
  this lane's readiness evidence alone: re-run
  `vehicle/s5-readiness-check.py` to an observed READINESS-PASS on a
  fast/quiet box (reference: full host arm ≈ 165–176 s) and attach
  that log to the filing. This lane's reds stay preserved regardless.
- NOTE-2 (record-only): `test_atomicity` 39/39, `test_procedure` 57/57,
  and the own-param opmatrix/L2-L3 kill legs rest on PRIOR-agent runs
  whose logs + landings the completing agent verified
  (line/ok-counts, zero FAIL/ERROR, landings lines) but did not
  re-execute; the 100-min procedure suite was deliberately not re-run
  per handoff bounds. Gates S5-A2–S5-A8 verdicts inherit this
  provenance. (Prior `00-byte-verify-pre.log` is a 30-line partial
  summary ending mid-baseline; the complete pre-evidence is the
  `00-pre-*.log` set, verified clean.)
- NOTE-3 (record-only): lane tamper legs ran against the attempt-1
  host-VALID root (`scratch/lane-readiness`, report ACCEPT/ACCEPT);
  the legs themselves (control + 5 mutations + axis assertions) are
  OWN runs with OWN params/sites.
- NOTE-4 (record-only, advisory): the SST-child `in-sandbox` descriptor
  (INTERRUPTION-BOUNDARIES.md:38, EVIDENCE.md:391) is not an isolation
  claim for procedures (explicit LEFT-non-atomic carve-out, not on any
  op path) — S5-A11 PASS stands — but a future docs pass may put
  `in-sandbox` in scare-quotes or name the SST custody module to deny
  misreading.

## Frozen both-ends

Pre (PRIOR logs, verified): s002 41/41, s003 45/45, s004 45/45,
H2-lane 46/46, s005 56/56, FROZEN-BASELINE 1161/1161, every file 0
non-OK. Post (OWN `08-post-hashes.own.log`, after ALL lane runs):
IDENTICAL counts, all 0 non-OK. No frozen byte changed in either
direction. s005 was never edited; all lane writes are inside `S5-lane/`
(logs + scripts + scratch). $0/offline/stdlib-only held (venv
interpreter only); `PYTHONDONTWRITEBYTECODE=1` throughout; U-execute
never run.

## Bottom line

Successor-005 is ACCEPTED-WITH-NOTES as builder acceptance (EVIDENCE +
this lane verdict, no PREREG-LOG entry): gates S5-A1–S5-A9 + S5-A11
PASS on lane evidence; S5-A10 is lane-RED on two environmental
timeout kills with zero test failures, counter-evidenced by the
builder's READINESS-PASS and a night host-green — NOTE-1 (gating)
requires one observed READINESS-PASS on a capable box before any
U-execute prereg filing.

