# CONSUMER.md — successor-006 consumer guide

Repairs + J1 persistent-worlds journey over the carried successor-005
path. $0, offline, stdlib-only (the SST leg is NOT carried — see
PROVENANCE.md). All state via explicit `--state-dir`, always inside
`successor-006/` (conventionally `successor-006/runs/<name>`; tests
use `successor-006/.test-tmp/`).

## 1. Setup

```
cd <substrate-repo>
export PYTHONDONTWRITEBYTECODE=1   # REQUIRED
python3 prototype/successor-006/test_coupling.py           # 10/10
python3 prototype/successor-006/test_quarantine_repair.py  # 13/13
python3 prototype/successor-006/test_j1.py                 # 6/6
python3 prototype/successor-006/test_conformance.py        # 9/9 (carried)
python3 prototype/successor-006/test_fission.py            # 7/7 (carried)
python3 prototype/successor-006/test_procedure_smoke.py    # 3/3 (carried)
python3 prototype/successor-006/j1_demo.py                 # 10/10 stages
```

## 2. New API surface (`api.py`)

J1 journey (see RUNBOOK.md for the staged walkthrough):

- `j1_init(state_dir, project, reason)` — fresh run root with one
  persistent PROJECT world (custody `j1.plan` + `j1.budget`, fresh
  sched grant, `grant.delegate` authority).
- `nest_op(state_dir, project, child, delegate, custody, reason,
  child_preset="Q")` — nest an experiment world: birth with
  `derived_from` lineage, a NEVER-manufactured sub-grant from the
  project's live holdings, and O4 custody handoff; records a ledger
  `nest` entry. All preconditions validate before any mutation.
- `j1_work_op(state_dir, world, task_id="J1-T1", verifier=None,
  prekill=None)` — formulate -> propose -> verify through `world`
  (resume-by-skip included), verdict + `solution-<id>.json` +
  O5 commitments.
- `j1_kill_resume_op(state_dir, world, task_id, verifier, ...)` —
  real `Popen.kill()` drill: asserts killed (rc != 0),
  `re_executed_invokes == 0`, pre-kill artifacts byte-identical,
  ledger prefix intact.
- `j1_status_op(state_dir)` — read-only responsibilities (lifecycle,
  custody, holdings/consumed, capabilities, authorities, lineage,
  pending_effects, verdicts) + evidence (delegations, nests,
  fusions, solutions, conservation).
- `j1_export_op(state_dir, composite)` — verify-then-write
  `artifacts/j1-export-<composite>.json` (fusion entry +
  `derived_from` lineage + per-solution sha256).

Quarantine repair (R11 owed item, CLOSED in this tree):

- `quarantine_complete_op(state_dir, world, standby, reason)` —
  finish the recorded handoffs + append the `quarantine` entry.
- `quarantine_rollback_op(state_dir, world, standby, reason)` —
  reverse the recorded handoffs + reattach + append a
  `quarantine_rollback` resolution entry.

Carried API (`init_run`, `open_run`, `run_tasks`, `fuse_op`,
`fission_op`, `quarantine_op`, `revise_op`, `revoke_op`,
`reuse_op`, `split_pair_op`, `settle_op`, `recover_op`,
`kill_resume_op`, `create_proc_world`, `run_procedure`,
`explain_route_op`, `inspect_state_op`) behaves as in
successor-005, except `run_tasks(..., with_sst=True)` refuses loudly
(SST leg not carried) and `open_run` additionally restores
creation-fixed authorities from the ledger (sched worlds: `[]`,
unchanged behavior).

## 3. CLI (`release.py`)

Same commands as successor-005, plus:

```
release.py j1-init --state-dir DIR --project P --reason R
release.py ops nest --state-dir DIR --project P --child C \
    --delegate COST,TIME,INV --custody C1,C2 --reason R [--preset Q]
release.py ops j1-work --state-dir DIR --world W [--task T] [--verifier V]
release.py ops j1-kill-resume --state-dir DIR --world W [--task T] [--verifier V]
release.py ops j1-status --state-dir DIR [--json]
release.py ops j1-export --state-dir DIR --composite C
release.py ops quarantine-complete --state-dir DIR --world W --standby S --reason R
release.py ops quarantine-rollback --state-dir DIR --world W --standby S --reason R
```

Exit 0 on success; exit 1 with a `release: error:` line on any
failure (loud, no silent partial effects).

## 4. Failure behavior (all loud, none silent)

| failure | signal |
|---|---|
| nest over-delegation / unknown custody / dup id | `ContractViolation`/`RuntimeError` BEFORE any mutation (zero ledger effect beyond reopen markers) |
| partial quarantine detected by recover | reported + supported-op steps; involved world blocked from settle, others proceed |
| quarantine-complete wrong standby / custody moved / rollback-in-progress / nothing-to-resolve | `RuntimeError`/`ContractViolation` naming the recorded state, zero mutation |
| quarantine-rollback custody moved / unreattachable / nothing-to-resolve | `RuntimeError`/`ContractViolation`, zero mutation |
| j1 export of non-composite / unresolvable lineage | `RuntimeError`, nothing written |
| kill inside a ledger append / torn side file | loud disk-loss refusal (carried LIMITS-2 class) |
| `with_sst=True` / `run_demo` | `RuntimeError` (SST leg not carried) |
| carried failures (deny shapes, settle atomicity, fission input, proc envelope, torn ledger) | unchanged from successor-005 |

There is no warn-and-proceed path anywhere.

## 5. Recovery procedure

1. Reopen through `api.open_run` (every CLI command does this).
2. `ops recover` completes births/fusions/fissions/settles and
   DETECTS partial quarantines (never silently completes them —
   the complete-vs-rollback decision is the operator's).
3. Resolve a partial quarantine with `ops quarantine-complete` or
   `ops quarantine-rollback` (both validate-before-mutate and
   converge on re-run after a kill during repair).
4. Kill-during-repair converges: re-run the same command.
5. Never hand-edit `ledger.jsonl` or `worlds.json`.

## 6. What is NOT promised

See LIMITS.md. In short: no learning of any kind, no cross-host ops,
no new capabilities after world creation, toy scale, single-host
process-crash-only recovery (no fsync; power/media loss is the
disk-loss class), no procedure re-verification beyond byte-identity
+ smoke, no SST leg.
