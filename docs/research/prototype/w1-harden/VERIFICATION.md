# Hardened Pilot Verification (independent, h2)

Verifier scratch: `/tmp/substrate-h2-001/` (fresh state dirs; nothing reused from
`/tmp/substrate-h1-001/`). `PYTHONDONTWRITEBYTECODE=1` everywhere. System python3 =
3.12.3, venv python = 3.12.3. No repo writes except this file. No git checkout/stash
anywhere. $0, offline, no keys.

## Verdict: ACCEPT-WITH-NOTES

All behavioral claims (H1-H3/S1-S3/A1-A3/I1-I3/X1-X3 + recovery) reproduced from the
candidate through its consumer path. Three record-keeping notes (low severity, none
affects behavior): N1 SST porcelain string omits one line, N2 DSH worktree gained an
untracked file, N3 venv-pins claim is wrong (venv HAS third-party packages).

| # | Area | Result | Observed |
|---|------|--------|----------|
| 1 | Suites 33 green x3 interpreters/CWDs | PASS | Ran 33 OK (pkg dir), Ran 33 OK (root+PYTHONPATH), Ran 33 OK (venv) |
| 2 | Demo stub fresh | PASS | exit 0, 40 entries, grant_settle x3 + settle grant_return, conservation OK, $0, METRICS |
| 3 | Demo SST-TEST (one, read-only) | PASS | exit 0, sst-controller-v0, champion_found, $0; sst 38->38, diff empty |
| 4 | Recovery R1 + refusals | PASS | exit 0, returncode -9, executed [score,verdict], 0 re-invokes, formulation ref asserted; R2/R3/R3b raise + deny |
| 5 | Settle zero + R4n reject | PASS | replay TERMINALS-ZERO True; live reopen verify ok; R4n test OK |
| 6 | Freeze honesty | PASS+N1,N2 | FREEZE.w1 7/7 OK; SST HEAD + 14/14 hashes match; porcelain 1-line diff (N1); DSH rev-parse matches, worktree +1 untracked (N2) |
| 7 | F3 mutation probe | PASS | pre-check removed -> test FAILS ('consume' != 'invoke'); control OK |
| 8 | Scope/boundary + H0 nums | PASS+N3 | exactly 17 files, no __pycache__; H0 15/2360/0.044/ad-hoc match run.log; venv has 55 pkgs (N3) |

## 1. Suites (system pkg-dir, system root, venv)

- `cd prototype/w1-harden && python3 -m unittest test_w1_harden test_failures test_recovery`
  -> `Ran 33 tests ... OK` (1.010s)
- `cd <root> && PYTHONPATH=prototype/w1-harden python3 -m unittest test_w1_harden test_failures test_recovery`
  -> `Ran 33 tests ... OK` (1.354s)
- `prototype/w1/.venv/bin/python -m unittest test_w1_harden test_failures test_recovery`
  (from w1-harden/) -> `Ran 33 tests ... OK` (1.366s)

## 2. Demo stub (fresh)

- `python3 prototype/w1-harden/demo_T.py --state-dir /tmp/substrate-h2-001/demo-stub
  --ledger /tmp/substrate-h2-001/demo-stub/ledger.jsonl` -> EXIT:0
- Tail: `ledger kinds: {... "grant_settle": 3, ... "grant_return": 1 ...}`,
  `conservation OK; METRICS {"artifact_bytes": {... "total": 4431}, "invokes_ok": 5,
  "ledger_entries": 40, "spend_usd": 0.0, "wall_s": 0.096}`
- `wc -l ledger.jsonl` -> 40; `grep -c grant_settle` -> 3; grant_return reason =
  `settle-on-terminal: assimilated into composite` (seq 32).

## 3. Demo SST-TEST (ONE run, read-only venv + PYTHONPATH)

- `PYTHONPATH=<sst>/src:prototype/w1-harden prototype/w1/.venv/bin/python
  prototype/w1-harden/demo_T.py --state-dir /tmp/substrate-h2-001/demo-sst ...`
  -> EXIT:0; `engine=sst-controller-v0 champion=cand_w1-5029fff4e1df_1_refine_0
  termination=champion_found`; composite `engine=sst-controller-v0`;
  `ledger_entries: 40, spend_usd: 0.0, wall_s: 6.287`. Cosmetic SST
  `Memory provider 'none' reported error` x2 observed (non-fatal, as reported).
- sst untouched by me: `git status --porcelain` 38 lines before AND after, `diff`
  empty (`PORCELAIN-UNCHANGED-BY-ME`); HEAD `079f4de6fd43881c2f1b529f0612f1df64a62f32`.

## 4. Recovery

- `python3 recovery_exercise.py --evidence-dir /tmp/substrate-h2-001/evidence`
  -> EXIT:0. R1: `child_returncode: -9, executed: [score, verdict],
  skipped: [formulate, propose], re_executed_invokes: 0, ledger_entries: 13,
  conservation: ok, spend: 0.0`, champion `stub-variant-08d7cd-0`.
- Independent: `R1-summary.json` contains `child_returncode: -9` (OS wait status,
  real SIGKILL); R1 ledger has exactly 2 invoke entries (`search.propose`
  inv-000005 pre-kill, `search.score` inv-000012 post-resume) -> no re-executed
  propose; `pending_effects [score, verdict]` replayed; 1 host_init + 1 host_reopen.
- Formulation ref identical pre/post: asserted in `test_recovery.py:124,171`
  (`assertEqual(report["formulation_ref"], form_ref)`, byte-reuse per module
  docstring); R1 tests green (see below).
- Refusals: `test_R2... + test_R3... + test_R3b... + test_R4n...` -> `Ran 4 ... OK`.
  Fresh ledgers: R2 tail `deny action=reattach reason="missing checkpoint"`;
  R3 tail `deny action=reattach reason="checkpoint identity mismatch"`.
  Full `test_recovery -v`: `Ran 9 ... OK`.

## 5. Settle

- Independent replay of MY stub ledger: terminals
  `{coalition-T: dissolved (no holdings ever), E-explore-exp1: retired
  {0.0, 0.0, 0.0}}` -> TERMINALS-ZERO: True.
- Live consumer path: `Host.reopen(scratch-copy)` + `verify_conservation()` ->
  `ok: True, settled: [E-explore-exp1, coalition-T]`; E-explore-exp1 balances all 0.
  (Methodology note: fresh `Host()` over an existing ledger appends a 2nd host_init
  and fails global conservation by design per `reopen` docstring; reopen is the
  correct path and passes.)
- R4n: `test_R4n_unsettled_terminal_ledger_rejected ... ok` (hand-made
  unsettled-terminal ledger rejected with `unsettled terminal`).

## 6. Freeze honesty

- `cd prototype/w1 && sha256sum -c ../w1-harden/FREEZE.w1` -> all 7 OK, EXIT:0.
- SST HEAD `079f4de6...62f32` matches; all 14 module sha256 match FREEZE.json
  (capsule b6e11f83..., contracts 34ce5767..., events 65a6924f..., models 4f83df4a...,
  backends 3909dc51..., gw-contracts 26a62c2a..., gateway d8a60fc1..., dialectic
  c4b4c165e..., evaluator 9bde42e5..., custody b2588803..., controller 99ed9aa3...,
  policy 53d59071..., projection 756ab900..., store 850342c5...).
- N1 (low): live porcelain has 38 lines vs 37 frozen; extra line
  ` M src/sst/core/events.py` (real 8-line diff vs HEAD) is missing from
  FREEZE.json's string, yet events.py bytes hash-match the freeze -> omission at
  freeze time, NOT subsequent drift. No content changed.
- DSH: `git rev-parse 639ed01` -> `639ed015397290b3745d163aafe02ffee4aa3f84`
  MATCHES. N2 (low): worktree not clean (1 untracked
  `packages/shell/tool-bash/tests/demo-manual-task.e2e.spec.ts`) vs claimed clean.
  Anchor-only; pinned commit unaffected.

## 7. Mutation probe (F3 budget-exhausted)

- Scratch copy `/tmp/substrate-h2-001/mut/`; deleted the 5-line invoke budget
  pre-check in `HOST.py` (`would exceed grant` + `raise ContractViolation`).
- Mutated: `test_F3_budget_exhausted_second_invoke_denied` -> FAIL
  (`AssertionError: 'consume' != 'invoke'`, line 121; downstream consume guard fires
  instead). Control (unmutated): same test -> OK. Test is genuine.

## 8. Scope/boundary + H0 numbers

- `find prototype/w1-harden/ -mindepth 1`: exactly the 17 reported files, no
  subdirs, no `__pycache__`/artifacts (this VERIFICATION.md is the 18th and only
  addition). `w1/` untouched (FREEZE.w1 7/7 OK); `sst/` untouched by me (38->38).
- H0 quotes verified against `/tmp/substrate-h0-001/run.log`:
  `wall=0.044s invocations=15 context_bytes=2360 ... spend=$0`,
  `SUMMARY: {..."invocations": 15, ..."total": 2360, ..."wall_time_s": 0.044 ...}`,
  champions `stub-variant-48c83f-0`/`stub-variant-6cc00d-1`, recovery `ad-hoc abort,
  no checkpoint, no resume`. All match RUN-REPORT.md.
- N3 (low): FREEZE.json `venv_pins` claims "no third-party packages"; observed
  `prototype/w1/.venv/.../site-packages/` has 55 entries (aiohttp, httpx, anyio,
  ...). Doesn't affect claims: suites + stub demo pass on system python3, SST-TEST
  used venv as interpreter only via PYTHONPATH, no network touched.
