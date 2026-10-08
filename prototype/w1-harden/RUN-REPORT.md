# Harden Pilot Run Report (w1-harden, recovery focus)

Track: SUBSTRATE · Date: 2026-10-04 · Budget: $0 (no keys, no network, offline)
Plan: `/tmp/substrate-harden-001/HARDEN-PLAN.md` (proposal; deviations listed below)
Code: `substrate/prototype/w1-harden/` (new dir; `prototype/w1/` untouched, verified before AND after)
Scratch: `/tmp/substrate-h1-001/` (run state + evidence; key excerpts quoted here)

H0 baseline to beat (stub): wall=0.044s, invocations=15, context_bytes=2360,
human_interventions=1, spend=$0.0, champions stub-variant-48c83f-0 (F1) /
stub-variant-6cc00d-1 (T3), recovery = ad-hoc abort, no checkpoint, no resume.
W1 repro ledgers: 36 entries each (sst + stub runs).

## Verdicts

- Full suite: **33/33 green** on system python3 (package dir AND repo root) and on the
  read-only venv interpreter (19 adapted W1 + 5 failure-injection + 9 recovery).
- Demo: exit 0 stub AND real `sst-controller-v0` (TEST-only, $0), 40 ledger entries each.
- Recovery: scripted SIGKILL-mid-run resumes to verdict with **0 re-executed invokes**,
  formulation ref + prior artifacts reused byte-for-byte; all three refusal paths raise
  with recorded denials; settle-on-terminal leaves **0 stranded holdings** (live + replay).
- w1/ hashes: unchanged (7/7 `sha256sum -c` OK pre- and post-run). SST tree: unchanged
  (porcelain diff empty; 14/14 module hashes match FREEZE.json before and after).

## 1. Hosting claims (H1-H3)

All ledger probes below run against the stub demo ledger
`/tmp/substrate-h1-001/h-check/ledger.jsonl` (40 entries, exit 0; command in X2).

- [x] H1. Nested experiment runs under delegated grant; parent holding drops.
  Command: `python3 prototype/w1-harden/demo_T.py --state-dir /tmp/substrate-h1-001/h-check
  --ledger /tmp/substrate-h1-001/h-check/ledger.jsonl` (from repo root; asserts inline)
  + `grep -c '"kind": "grant"' /tmp/substrate-h1-001/h-check/ledger.jsonl`
  Observed: `nested E-explore-exp1: E-explore holding 2.0 -> 1.5`, grants = **4** (>= 3).

- [x] H2. Authority refusal recorded as denial (exp1 lacks execute.local).
  Command: `grep '"kind": "deny"' /tmp/substrate-h1-001/h-check/ledger.jsonl | grep -c execute.local`
  Observed: **1** (>= 1). Demo also asserts the ledger tail is `deny` right after the refusal.

- [x] H3. Conservation replay passes incl. settle events.
  Command: demo exit 0 (asserts `verify_conservation()["ok"]` internally).
  Observed: `conservation OK`, ledger kinds
  `{"checkpoint": 1, "consume": 5, "create": 5, "deny": 1, "grant": 4, "grant_return": 1,
  "grant_settle": 3, "host_init": 1, "invoke": 5, "lifecycle": 10, "reattach": 1,
  "relationship": 2, "transfer": 1}` (40 = W1's 36 + 3 settle markers + 1 settle return).

## 2. Structural claims (S1-S3)

- [x] S1. Custody transfer moves custodian + ledger `transfer` entry.
  Command: `grep '"kind": "transfer"' /tmp/substrate-h1-001/h-check/ledger.jsonl`
  Observed: `search-state E-explore-exp1 -> C-solve` (1 entry).

- [x] S2. Terminal settle: dissolved/retired worlds leave zero stranded holdings.
  Command: demo step 8/10 assertions + replay probe (python scan of the ledger).
  Observed: terminals `{'E-explore-exp1': 'retired', 'coalition-T': 'dissolved', ...}`,
  settled `['E-explore-exp1', 'coalition-T']`; EXP_ID holdings all 0.0 live and in replay
  (`child_replay_balance` zeros in R4 too). Example marker:
  `"kind": "grant_settle", "payload": {"amounts_total": {"max_cost_usd": 0.5,
  "max_invocations": 18, "max_time_s": 55.0}, ...}` (EXP_ID remainder returned to E-explore).

- [x] S3. Composite reuse: `composite.solve` champions a follow-up task, 0 new code lines.
  Command: python scan for ok `composite.solve` invoke entries.
  Observed: 1 ok invoke; `solution_ref: .../C-solve/solutions/0005.json`,
  `champion: stub-variant-75bc18-0 engine: stub-deterministic-v1`.
  Reuse cost: 0 new code lines (same `composite_solve` closure as W1), matching H0 (0/3).

## 3. Adaptation claims (A1-A3)

- [x] A1. Mapping v1 re-derivation identical after v2 declared (pinning).
  Command: `python3 -m unittest test_w1_harden.TestRevisionPinning -v` (from w1-harden/)
  Observed: `test_v1_stable_after_v2_declared ... ok`.

- [x] A2. v2 carries assumptions; v1 lacks them (declared loss, not silent).
  Observed: same test asserts `assertIn("assumptions", v2)` ... ok.

- [x] A3. Failure feedback: all 5 injections produce typed errors + ledger entries.
  Command: `python3 -m unittest test_failures -v` (from w1-harden/)
  Observed: F1..F5 all ok (5 tests). Refusal shapes follow W1's convention, asserted per
  case: F1 timeout -> raised `TimeoutError` + `invoke` entry with error starting
  `TimeoutError:` + holdings unchanged (no consume on failure); F2 missing-file ->
  `build_verify` returns `passed=False, failures=["missing file nope.txt"]` + verdict file
  written, `artifact_read` raises `FileNotFoundError` + `invoke` entry names it; F3
  budget-exhausted -> 2nd invoke raises `ContractViolation("grant exceeded...")` + tail
  `deny` with `action: invoke`, reason contains `would exceed grant`; F4
  unknown-mapping-version -> raises `ContractViolation("unknown mapping version '9.9'...")`
  + `invoke` entry names it + v1 re-derivation byte-identical afterwards; F5
  double-custody-transfer -> 2nd raises `ContractViolation("...not custodian...")` + tail
  `deny` with `action: custody.transfer`. (Plan sketch said `deny` for F1/F2/F4; the
  implemented rule records execution failures as typed `invoke` error entries and
  pre-check refusals as `deny` — see Deviations.)

## 4. Inheritance claims (I1-I3)

- [x] I1. Composite `derived_from` records both parents.
  Command: python scan of `/tmp/substrate-h1-001/h-check/C-solve/solutions/*.json`.
  Observed: 1 solution file;
  `E-construct |inh: task-spec + acceptance |reacq: nothing` and
  `E-explore-exp1 |inh: search procedure + engine |reacquired: fresh search run (no state copied)`.

- [x] I2. Suspend/reattach preserves identity, versions, holdings.
  Command: `python3 -m unittest test_w1_harden.TestLifecycle -v` +
  `ls /tmp/substrate-h1-001/h-check/E-explore/checkpoint.json`.
  Observed: 3 lifecycle tests ok; checkpoint.json present (409 bytes).

- [x] I3. Fresh-search (no state copied) on composite reuse.
  Command: python assert on solution score refs.
  Observed: `score_refs: ['.../C-solve/scores/0004.json']` — under C-solve, no EXP-dir ref.

## 5. Cross-cutting (X1-X3)

- [x] X1. Full suite green both interpreters, both CWDs.
  Commands + observed:
  - `cd prototype/w1-harden && python3 -m unittest` -> `Ran 33 tests ... OK` (0.9s)
  - `PYTHONPATH=prototype/w1-harden python3 -m unittest test_w1_harden test_failures
    test_recovery` (from repo root) -> `Ran 33 tests ... OK` (1.3s)
  - `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=<sst>/src <w1/.venv>/bin/python -m unittest`
    (from w1-harden/) -> `Ran 33 tests ... OK` (1.4s)
  33 = 19 adapted W1 + 5 failure (F1-F5) + 9 recovery (R1-sim, R1-real, R2, R3, R3b,
  R4, R4m, R4n, R5).

- [x] X2. Metrics vs H0 (spend MUST be $0.0).
  Stub demo METRICS line (repo-root run):
  `{"artifact_bytes": {"candidates": 739, "formulations": 568, "scores": 515,
  "search-runs": 923, "solutions": 1272, "task-specs": 406, "total": 4423},
  "invokes_ok": 5, "ledger_entries": 40, "spend_usd": 0.0, "wall_s": 0.067}`
  SST-TEST demo METRICS line (venv run, TEST providers):
  `{"artifact_bytes": {... "total": 9457}, "invokes_ok": 5, "ledger_entries": 40,
  "spend_usd": 0.0, "wall_s": 5.122}`, engine `sst-controller-v0`,
  champions `cand_w1-5029fff4e1df_1_refine_0` (F1) / `cand_w1-75bc180a7125_1_refine_0` (T3).
  Comparison to H0 (15 invocations / 2360 bytes / 0.044s / ad-hoc recovery):
  - spend $0.0 in all runs (requirement met);
  - invocation counters differ by construction (H0 counted 15 ad-hoc adapter calls
    with branching=2; H1 counts 5 accountable ledger invokes with branching=1, same as W1);
    the honest comparison is W1->H1: identical 5 invokes, ledger 36 -> 40 entries
    (+3 grant_settle markers, +1 settle grant_return);
  - artifact bytes differ by construction (H0 summed 8 hand-picked files at branching=2;
    H1 sums all artifact classes at branching=1: 4423 stub / 9457 SST — the SST run is
    larger because real-controller candidates carry patch_diff content);
  - wall: 0.067s stub (same order as H0's 0.044s; delta is subprocess + ledger overhead
    on shared hardware, not a claim), 5.1s SST-TEST (real controller, TEST providers);
  - recovery: ad-hoc abort (H0) -> checkpoint + kill + resume-to-verdict with 0 rework (H1),
    see section 7.

- [x] X3. Freeze verified: w1/ untouched; SST dirty-with-hashes honestly frozen.
  Commands + observed:
  - `cd prototype/w1 && sha256sum -c ../w1-harden/FREEZE.w1` -> all 7 OK (pre-build AND
    post-run; short hashes eb61a5d9cebc, 2d5bc5bb9db3, 933d2c9a58df, b02d81a1282a,
    4893929d3a8b, 91225a057b0c, 05c2b564bcfe).
  - SST: HEAD `079f4de6fd43881c2f1b529f0612f1df64a62f32`, DIRTY (19 modified + 19 untracked,
    peer work in progress). Frozen as dirty-with-hashes in FREEZE.json per delegation
    (no clean-pin selection — SST owner's job). Porcelain diff before vs after the
    SST-TEST run: EMPTY (tree untouched; PYTHONDONTWRITEBYTECODE=1, PYTHONPATH-only,
    no checkout/stash/reset). 14/14 module hashes re-match FREEZE.json post-run.
    Drift vs W1-BUILD-NOTES appendix: 13/14 identical; only `search/controller.py`
    changed (3566e7bf... -> 99ed9aa3...).
  - DSH: `git rev-parse 639ed01` in /tmp/dsh-upstream ->
    `639ed015397290b3745d163aafe02ffee4aa3f84` (VERIFIED; worktree clean at freeze,
    1 untracked file at verification, clean at re-check — peer volatility, anchor
    unaffected; corrected per N2).
  - Venv: w1-harden code is stdlib-only (suites + stub demo pass on system python3);
    the w1/.venv used as SST-TEST interpreter holds 55 site-packages entries
    (corrected per N3 — was: claimed none); SST via PYTHONPATH, never installed.
    Interpreters: system python3 3.12.3, venv python 3.12.3.

## 6. SST-TEST check (one, read-only, TEST-only, $0)

Command (from repo root):
`PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=<sst>/src:<w1-harden> <w1/.venv>/bin/python
prototype/w1-harden/demo_T.py --state-dir /tmp/substrate-h1-001/h-check-sst
--ledger /tmp/substrate-h1-001/h-check-sst/ledger.jsonl`
Observed: exit 0; `engine=sst-controller-v0 ... termination=champion_found` (both the EXP
search and composite.solve); `cost_usd == 0.0` asserted inline; ledger kinds identical
shape to stub (40 entries incl. 3 grant_settle); conservation OK.
Labels: TEST-only providers (`test://local`), $0 spend, SST evidence is
DIRTY-WITH-HASHES (see X3), not a pinned release. Known cosmetic (carried from W1):
`Memory provider 'none' reported error` printed twice by SST; non-fatal, no memory
provider configured (deferred per plan section 4).

## 7. Recovery exercises (focus area)

Runner: `python3 recovery_exercise.py --evidence-dir /tmp/substrate-h1-001/evidence`
(exit 0; per-scenario ledgers under `evidence/run-state/`, excerpts + summaries beside them).
Same assertions also run hermetically in `test_recovery.py` (9 tests, green both interpreters).

- R1 kill-mid-run -> resume-to-verdict (real SIGKILL): child ran setup + formulate +
  propose + suspend(pending=[score, verdict]), printed READY, slept; parent SIGKILLed it
  (returncode **-9**), then `Host.reopen` (replayed 8 entries, `host_reopen` marker) ->
  `reattach` (`pending_effects_replayed: [score, verdict]`, `restored_ledger_position: 6`)
  -> `resume_to_verdict`. Result: `skipped: [formulate, propose]`, `executed: [score,
  verdict]`, **re_executed_invokes: 0**, verdict champion `stub-variant-08d7cd-0`,
  ledger 13 entries, conservation ok, spend $0. Formulation ref identical pre/post kill;
  candidate/formulation bytes sha256-identical (asserted in test R1-sim). No restart:
  exactly 1 host_init, 1 host_reopen, 1 create; only the score invoke billed post-kill.
- R2 missing checkpoint: reattach raises `ContractViolation(missing checkpoint)`; ledger
  tail is `deny` with that reason. R3 identity mismatch (world_id AND code_ref tamper
  variants in tests): raises `ContractViolation(checkpoint identity mismatch)` + deny.
- R3b reopen supply-record mismatch (code_ref tamper, unknown-world record): raises +
  `deny` with `action: reopen` (2 denies asserted).
- R4 settle-on-terminal: 2 `grant_settle` markers (one per terminal move); child holdings
  AND replay balance all 0.0; conservation ok. R4m multi-grantor: marker lists both
  grants, both grantors' holdings increase. R4n negative: hand-written ledger with a
  dissolved world and no marker is rejected by `verify_conservation` with
  `unsettled terminal`.
- R5 descriptor withholding: reopen without records restores names/versions with
  `required_authority=recovery.withheld`; non-host invoke denied naming it; host
  inspection invoke succeeds.

Edge rule implemented (R-REOPEN, see `Host.reopen` docstring + RECOVERY-REUSE.md):
reopen replays the ledger and resumes each world at its LAST ledger-recorded state with
NO lifecycle edge traversed — there is deliberately no active->active "resume" edge.
Suspended worlds continue through the ordinary contract edge suspended->active via
`reattach` (checkpoint identity still verified: world_id + code_ref + contract_version).
Active-at-kill worlds continue in place by reusing artifacts + ledger proof. This answers
the X1-Arm-A history (resume via checkpoint-identity + replay, never an illegal
reattach-across-reopen): reopen IS checkpoint-identity + replay; reattach keeps its
single contract meaning.

## 8. Deviations from HARDEN-PLAN.md (proposal)

1. SST frozen dirty-with-hashes, not clean-pinned (delegation order; peer WIP; the plan's
   clean-commit selection procedure explicitly NOT executed — SST owner's job). All
   SST-TEST evidence labeled accordingly.
2. `grant_settle` is emitted BEFORE the terminal `lifecycle` entry (settle-then-move; funds
   move while the world is still pre-terminal), while plan S2's sketch wording says
   "later grant_settle". The S2 check implemented is order-insensitive (marker exists +
   terminal balances zero). Rationale: a failed settle must refuse the transition, which
   is only possible if settle runs first.
3. F1/F2/F4 record typed `invoke` error entries (W1's existing execution-failure shape),
   not `deny` (the plan's table row). Pre-check refusals (F3/F5) record `deny`. The
   delegation allows "deny/error entry"; both shapes satisfy refusals-never-silent, and
   inventing a third shape (deny-on-exception) would have diverged from W1 semantics.
4. Relative imports are relative-WITH-FALLBACK (`try: from .x / except ImportError: from
   x`) plus a sys.path bootstrap, because `w1-harden/` (dash) cannot be a dotted package.
   Dual-CWD acceptance holds: `python3 -m unittest` from the package dir, and
   `PYTHONPATH=prototype/w1-harden python3 -m unittest <modules>` from the repo root.
5. Threading/concurrency probe NOT added as a test (plan: best-effort; delegation: F1-F5
   only). Strict Host locking stays deferred (see LIMITS.md).
6. H0 comparison numbers are reported with counter-definition caveats (X2) rather than
   forced into identical counters — the counters measure different things by construction.
7. Post-verification corrections (coordinator, 2026-10-04, per VERIFICATION.md N1-N3,
   all record-keeping, none behavioral): N1 added the freeze-omitted
   ` M src/sst/core/events.py` porcelain line to FREEZE.json (bytes hash-matched, no
   drift); N2 corrected the DSH worktree-clean claim to the observed
   clean->untracked->clean sequence; N3 corrected the venv no-third-party-packages
   claim (55 site-packages entries; code remains stdlib-only). This section + X3
   updated to match.

## 9. Files added (all under prototype/w1-harden/; nothing else written)

`__init__.py`, `contract.py`, `HOST.py`, `relationship.py`, `world_construct.py`,
`world_explore.py`, `demo_T.py`, `recovery_lib.py`, `recovery_exercise.py`,
`test_w1_harden.py` (19), `test_failures.py` (F1-F5), `test_recovery.py` (9),
`FREEZE.w1`, `FREEZE.json`, `RUN-REPORT.md` (this file), `RECOVERY-REUSE.md`, `LIMITS.md`.
Known limits: see LIMITS.md (no live models, no learned mapping, toy evaluator,
exists-family envelope, single-host, assistance-(ii) untested, ledger-as-overhead note).

