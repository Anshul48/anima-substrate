# Roles and enforced rules

**State: Prototype.** The hidden checker, the escalation ladder and the tamper-evident record exist in some form (see [`status.json`](status.json)). Roles, the mission file and the rule pack are a design, written from how we actually run our own work. Nothing in this document is built unless `status.json` says so; this file is the evidence path for the "Roles and rules" part.

**Harness** means the coding tool an agent runs inside (Muse Code, Claude Code, Codex). A **hook** is a small program the harness calls before each action; it can block the action. A **watch** is a timed program that checks agents from outside.

## 1. Roles

| Role | May | Must not | Checked by |
|---|---|---|---|
| Owner (the human) | Set the mission, deadlines and budgets. Alone approves spending, anything public, and administrator access | Be pinged for small things; asks are batched, each with a default | Nobody; reads a digest |
| Architect | Decide design, rule on conflicts, review at gates, ask a read-only second opinion | Do bulk work, publish, read secrets, use a model outside the pinned list | Hooks, the second opinion, the owner |
| Coordinator | Routine operations: pick up briefs, re-issue blocked results, keep queues stocked | Decide design, spend, publish, cancel workers | The architect, through a digest |
| Manager (one per project) | Split the mission into cards whose acceptance is a file; accept or reject output | Change the mission, publish | The architect; a written verdict file |
| Worker | One job in one folder: read the brief, write in its workspace, run tests | Read secrets, message the owner, start services, push, cancel others | A hook, a supervisor, the manager's acceptance file, the hidden checker |

## 2. Controls we use on our own work, and whether ANIMA has them

We run these on our own hub. Where we ran a control and saw it work, the row says so; "read" means we read the code or log and did not run it.

| Control | How we do it | Evidence | In ANIMA today? |
|---|---|---|---|
| Secret rules: never read, print or copy key files or dump the environment | A rule registry checked by a hook on file and shell calls | Ran it: a command that reads a private key file was blocked, exit code 3 | No |
| Danger and git rules: no administrator commands, wipes or protected deletes; no push to named public repositories | The same registry | Ran it: an administrator command was blocked in enforce mode, exit code 2. A generic push was allowed, because the rule names specific repositories | No |
| Model pins | A policy file plus a hook rule | Read. Dry run by default, so violations are logged, not stopped | No |
| Token and credit budgets | Pools with a floor and a cap on live workers; timeouts and attempt limits | Read. A person types the balance in; no tool reports it | No |
| Escalation ladder for work | A Muse Code worker first (in the recorded runs), then Claude Sonnet, then Codex | Ran it on one kind of job: [recorded run](evidence/flagship-run3/README.md) | Yes, one job type |
| Verification gates | Hidden tests judge each answer; decisions go into a hash-chained log | Ran the chain check: [`check_chain.py`](evidence/flagship-run3/check_chain.py) | Yes, one job type. The checker's own code and self-test are not in this repository yet |
| Relay guard: owner messages must not depend on a model remembering a tool | A 60-second loop that files any unfiled message | Ran it (it was down for a stretch, which we recorded) | No |
| Watchdog prompts | Timed checks that nudge a frozen or errored agent | Read | No |
| Stall and crash handling | Backoff retries, a waiting-for-network state, a no-output progress gate | Read. The gate runs in shadow mode: it logs what it would kill | No |
| Disk and memory guards | Floors that pause new work | Recorded in notes only; the files were not visible when this was written | No |

**ANIMA has two of those ten today: the work ladder and the verification gate.**

## 3. The mission file: `anima.yaml` (design)

One file per project. Roles, permissions, budgets, watches and the ladder are data, so one file works on any harness. Only the `harness` line and the way rules are enforced change.

How rules are enforced differs by harness, and we say so plainly. Claude Code has per-action hooks, so a forbidden action can be blocked before it runs; we have seen that work. Muse Code and Codex start with a wrapper and a process watch instead, which can stop a run but cannot veto a single action. Muse Code's help text also lists permission and approval options that we have not tested.

```yaml
version: 1
harness: muse                # muse | claude | codex
mission: MISSION.md          # the manager enforces it
memory: {kind: trace, store: .anima/trace, write: [decisions, failures]}
enforce: {mode: warn, via: wrapper}    # warn first, then enforce
roles:
  manager:
    may: [read_repo, write_cards, accept_or_reject]
    must_not: [push, edit_mission]
    budget: {max_workers: 4}
  worker:
    may: [read_workspace, write_workspace, run_tests]
    must_not: [secrets, push, message_owner]
    budget: {timeout_s: 3000, attempts: 3}
rules: [secrets, sudo, push-public, delete-protected]
ladder:                      # first match wins
  - {on: gate_fail, do: retry_with_failure_line, times: 1}
  - {on: gate_fail, do: run_with, harness: claude}
  - {on: still_failing, do: ask, role: architect}
```

No program reads this file yet.

## 4. Ideas that are not in the status table

1. A mission file the manager enforces: every card cites a line of the mission and names a file as its acceptance test; cards that do neither are parked.
2. A cost ledger: one line per job with role, harness, wall time and attempts, plus a warning at 90% of a budget. Time and attempts are easy; money depends on what each tool reports.
3. A watchdog that restarts stalled workers and pauses during a network outage, started in shadow mode.

## 5. Limits

- Design only, except the checker, the ladder and the record, which are limited to one kind of job (fix a bug, judged by hidden tests).
- Blocking before an action runs is proven only on Claude Code.
- Budgets in the design are not in the first rule pack.
