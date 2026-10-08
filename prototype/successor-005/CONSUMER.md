# CONSUMER.md — successor-005 consumer guide

Freezable Linux release candidate: hybrid central/local coordination,
two scheduling lanes, structural fusion + fission + quarantine, reuse
with lineage, revision/revocation with rulings, kill-resume, atomic
settle + kill recovery (`ops recover`), crash-atomic side files (R3:
a kill leaves every `worlds.json`/artifact/checkpoint old-or-new,
never torn), and an SST-TEST search leg
over a vendored, hash-pinned snapshot. $0, offline. Core is
stdlib-only; the SST leg needs a venv interpreter with pinned
`pydantic==2.13.5`.

## 1. Setup (Ubuntu)

Core (everything except the SST leg) — system Python only:

```
sudo apt update && sudo apt install -y python3
cd <substrate-repo>
export PYTHONDONTWRITEBYTECODE=1
python3 prototype/successor-005/test_conformance.py   # 9/9 OK, no SST
python3 prototype/successor-005/test_atomicity.py     # 39/39 OK, no SST
python3 prototype/successor-005/test_procedure.py     # 57/57 OK, no SST
```

SST leg — one venv with the pinned dependency:

```
sudo apt install -y python3-venv
python3 -m venv /path/to/sst-venv
/path/to/sst-venv/bin/pip install 'pydantic==2.13.5'
export SST_VENV_PY=/path/to/sst-venv/bin/python
python3 prototype/successor-005/verify_snapshot.py    # snapshot MATCH
```

Notes: `SST_VENV_PY` defaults to the in-repo
`prototype/w1/.venv/bin/python` (pydantic 2.13.5, used for
qualification). Any interpreter with EXACTLY pydantic 2.13.5 works;
any other version aborts the SST leg loudly (re-qualification
required — see REPORT.md §SST). No network, no keys, no cost.

## 2. Config

- CLI: `release.py` (`init/run/explain-route/inspect/ops`, incl.
  `ops recover`, `ops create-proc-world`, `ops run-procedure`).
  All state via explicit `--state-dir` (see §5).
- Env vars: `SST_VENV_PY` (SST interpreter override);
  `PYTHONDONTWRITEBYTECODE=1` (REQUIRED — keeps bytecode out of the
  snapshot and run dirs).
- `CONFIG.json` (written by `init` into the state dir): release tag,
  creation stamp, world list, tasks run. Human-readable; the API
  re-reads only `worlds.json` + `ledger.jsonl`.

## 3. Inputs / outputs

Task input JSON (see `accept/*.json` for frozen examples):

```
{"task_id": "S2", "slots": {...}, "tasks": {...}, "precedence": [...],
 "prefs": {...}, "holdings": {"SC-L": {...}, "SC-S": {...}},
 "adapter": "list2slot/v1", "expected_rounds": 4, "split_state": true}
```

- `run` supports lane tasks S1/S2 (any task with `expected_rounds` +
  `split_state` routes through the same rule; S3 runs only via the
  kill-resume flow; S4/S6 follow-ups run via reuse/split-pair ops).
- Outputs per task: `artifacts/solution-<id>.json`
  (`{task_id, assignment, quality, prefs_total, valid, via}`),
  per-task verdicts under `state/<world>/verdicts/`, routing lines in
  `ROUTING-LOG.jsonl` + ledger `routing` entries.
- Expected results: `accept/EXPECTED.json` (exact vs reference fields
  documented in `accept/README.md`).

Programmatic API (`api.py`): `init_run`, `open_run`, `run_tasks`,
`fuse_op`, `fission_op`, `quarantine_op`, `revise_op`, `revoke_op`,
`reuse_op`, `split_pair_op`, `settle_op`, `kill_resume_op`,
`recover_op`, `create_proc_world`, `run_procedure`,
`explain_route_op`, `inspect_state_op`. Importable
with plain `sys.path` (no install step); signatures +
preconditions in `api.py` docstrings; promises in `ORG-OPS.md`;
interruption behavior in `INTERRUPTION-BOUNDARIES.md`.

## 4. Failure behavior (all loud, none silent)

| failure | signal |
|---|---|
| snapshot drift (any byte) | `SSTBoundary` naming the files; SST leg refused BEFORE import |
| wrong pydantic | `SSTBoundary` (pinned 2.13.5) |
| non-TEST provider / non-$0 | `SSTBoundary` |
| refused invoke (unknown/revoked/quarantined/withheld) | `ContractViolation` + recorded ledger `deny` |
| bad op preconditions (inactive world, bad partition, unfused reuse, unsettleable dissolve target) | `ValueError`/`RuntimeError`/`AssertionError`/`ContractViolation` BEFORE mutation (no partial effects) |
| settle refusal (unknown/unsettleable world, pre-existing unsettled terminal) | `ContractViolation` ("zero worlds dissolved"), ZERO partial dissolves, only a `deny` entry |
| partial fission needs input (recover) | `RuntimeError` with exact re-run steps; wrong partition/names/presets refused, never silently diverged |
| partial quarantine (recover) | detected + `OPERATOR REPAIR` steps; involved world blocked from settle, others proceed |
| conservation-failing / torn ledger (recover) | `ContractViolation` / `RuntimeError` refusal (fail-closed); `inspect` reports read-only |
| torn side file after a kill | IMPOSSIBLE on op paths by kill (R3 temp+`os.replace`, old-or-new) except the resume-skip carve-out: `scan_succeeded` skips unreadable args fail-safe instead of refusing (N1); a genuinely torn file elsewhere refuses as disk-loss, loudly |
| advertise refusal (bad bundle manifest) | `ValueError` naming the defect BEFORE any ledger write (zero ledger effect) |
| table-miss invoke (`proc.exec` for unadvertised procedure/bundle) | `deny` + `ContractViolation`, zero spawn (no `proc_begin`, no scratch dir) |
| idempotence-key collision across bundles | `deny` + `ValueError` (same key + different bundle never merges) |
| nonzero child exit / timeout / outside-scratch write / bundle tamper | error-`invoke` (never `result_ref`); timeout kills the child group; P9 names the files |
| direct `proc.exec` invoke without the procedure envelope | `deny` + `ContractViolation` (use `run_procedure`) |
| CLI error | `release: error: ...` on stderr, exit 1 |

There is no warn-and-proceed path anywhere: every check either passes
or aborts with the exact boundary.

## 5. State location

Every command takes an explicit `--state-dir`; NOTHING is written
anywhere else (no home-dir state, no temp spillover, no registry).
Release runs MUST keep the state dir inside `successor-005/`
(conventionally `successor-005/runs/<name>`). Procedure runs add
`state/<W>/procedures/<name>/` (staged bundles),
`state/proc-scratch/<key>/<step>-attempt<N>/` (per-step scratch),
`artifacts/proc-<key>/<step>/` (collected outputs + `RESULT.json`).
Layout: `ledger.jsonl`, `state/`, `ROUTING-LOG.jsonl`, `artifacts/`,
`worlds.json`, `CONFIG.json`, `sst-leg/` (SST runs only). Channels
are in-memory only and do not persist across CLI invocations (fuse
ensures the channel, then removes it — recorded in the fusion
record). Procedure readiness/verification runs use disclosed
throwaway roots (default `/tmp`) where the 600 s per-step ceiling
requires it (see EVIDENCE.md §Vehicle placement); sched release
runs MUST stay in-tree.

## 6. Recovery procedure (after a kill or crash)

1. Reopen through `api.open_run(state_dir)` (every CLI command does
   this): the ledger replays (registry/holdings/grants/lifecycle),
   creation lineage is restored from the ledger `create` payloads,
   and ledger `revoke` entries are re-applied (WITHOUT this step a
   revocation LAPSES — demonstrated in `TestRevocationConformance`).
2. Resume plan steps with `resume.execute_plan(host, plan)`:
   succeeded steps skip by the C1–C3 matcher; only new steps execute
   (`re_executed_invokes` must be 0 — assert it).
3. For the full S3 drill, use `ops kill-resume` (spawns a real child,
   kills it with `Popen.kill()`, reopens, finishes the adaptation).
4. Do NOT hand-edit `ledger.jsonl` or `worlds.json`: reopen verifies
   descriptors against the ledger and refuses mismatches loudly.
5. After a kill during settle/fusion/fission, run `ops recover`
   (repairs `worlds.json` specs from the ledger, completes
   interrupted births/fusions automatically, completes ONE
   interrupted fission once you supply
   `--fission/--left/--right/--partition`, settles exactly
   `--worlds` — default: settles NOTHING). Re-running after a kill
   during recovery converges. A `<name>.tmp-<pid>` file next to a
   side file is a benign replace orphan (never read; safe to
   delete). Full boundary map + procedures:
   `INTERRUPTION-BOUNDARIES.md`.
6. NOT covered (operator repair, see LIMITS.md + §4 table):
   kill-during-quarantine-transfer completion, disk loss,
   multi-writer.

## 7. What is NOT promised

See `ORG-OPS.md` §7 + `LIMITS.md`: no learning, no cross-host ops, no
new capabilities/representations after world creation, toy scale,
TEST fixtures only, `retired` unexercised, no OS sandbox/containment
for procedures (P11–P13 non-claims, §8). A consumer relying on any
of these is outside this contract.

## 8. Procedure runs (S5): the accountable executor

A world may advertise a creation-fixed procedure table (one entry per
bundled procedure: name + bundle sha256 pin + manifest ref + step
names) via `ops create-proc-world` / `api.create_proc_world`, and
execute table entries step by step via `ops run-procedure` /
`api.run_procedure`. The host is an accountable executor for
caller-supplied procedures — not a sandbox for adversaries' code.

Trust model (§8.1): callers supply procedures AND bear their content
risk. The host vouches ONLY that (a) executed bytes equal advertised
bytes (hash-pinned, re-verified pre/post-run), (b) every step ran as
a scoped invocation inside the §1.4 envelope with complete
accountability data (ledger `proc_begin` + `invoke.proc` +
`RESULT.json`, all cross-checkable), and (c) failures are loud and
typed (never silent, never `result_ref`).

ENFORCED envelope (each asserted by tests): P1 argv-list exec (no
shell); P2 fresh per-step scratch cwd; P3 allowlist env (proxies
stripped); P4 /dev/null stdin; P5 captured stdio with caps; P6
timeout kill of the child group; P7 interpreter pin (refuses
pre-spawn); P8 bundle re-verification (post-run tamper ⇒
error-invoke); P9 outside-scratch-write detection (inside-state
writes ⇒ step FAILED naming the files); P14 grant accounting
(invocations=1 + elapsed rounded UP 0.1 s per step).

Stated non-claims (normative, tested as non-claims): P11 writes
outside the state dir are CONTRACTUAL — the executor cannot prevent
or reliably detect them, the caller vouches, and no enforcement is
claimed (the posture is purely contractual); P12 network is
CONTRACTUAL (not isolated) — offline is a caller obligation plus P3
proxy hygiene, and the executor performs no network I/O itself (any
"network=none enforced" wording is forbidden); P13 memory/RSS caps
are NOT CLAIMED (no portable stdlib mechanism; P5 caps bound
exfiltration bytes, not RSS). P15 orphan handling is
TOLERATED-BY-CONSTRUCTION, not enforced cleanup: a killed parent may
orphan the child, which can only touch stale scratch the recovery
never reads except via the DONE rule (no PID auto-kill — PID reuse
is unsafe). Kill tests kill the process group (harness duty).

Advertise refuses bad bundles with `ValueError` before any ledger
write. Execution skip-matches completed steps by the ledger `proc`
block; a kill at any phase lands defined (L1/L2 re-run fresh, L3
DONE-adopt exactly-once or refuse-adopt + re-run, L4 loud disk-loss
refusal, L5 repeated kills converge) — see
INTERRUPTION-BOUNDARIES.md §8. `ops recover` adopts
ledger-conditional DONEs and reports adopted / re-runnable /
nothing-to-do; recovery never spawns. Durability scope (no fsync): process crash only — power/media loss stays the disk-loss class (LIMITS-2, out of scope).
