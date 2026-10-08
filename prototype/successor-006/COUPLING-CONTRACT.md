# COUPLING-CONTRACT.md — successor-006 recovery coupling contract

Closes the owed Q3 item (COMPLETION-MAP R9/Q3 rows): the 8-item
resume-coupling list behind the Q3 DEMONSTRATED-WITH-COUPLING-LIST
verdict (10/10 unmodified resume on a separate MiniHost), formalized
as a testable contract. Source of the 8 items: `reuse-demo-001/
REUSE-REPORT.md` §"Interface gaps" (+ `closeout-20261004/
REUSE-CALIBRATION.md` §"Calibrated claim"); clause pins:
`successor-contract/WORLD-CONTRACT-v1.md` C1–C6.

Each item below states the promise, the implementing code in THIS
tree, and the asserting test. All tests run through the consumer
surface (`api.py` / `release.py`, plus the documented `open_run`
host surface) on fresh state:

    PYTHONDONTWRITEBYTECODE=1 python3 prototype/successor-006/test_coupling.py

Envelope (same as the carried code): single-host, local disk,
process-crash-only (no fsync), toy scale. The contract pins the
shapes a host and the resume engine share; it does NOT promise
cross-host refs, multi-writer safety, or disk-loss tolerance.

## CC1. Invoke call contract (gap 1)

- Promise: `invoke(caller, callee, capability, version, args_ref, fn,
  *, cost_usd, time_s, ...)`. Exactly one invocation is consumed per
  call, ON SUCCESS ONLY. A raised `fn` records an `invoke` entry with
  `payload.error` set and consumes nothing (no `consume` entry).
- Code: `minihost.py:MiniHost.invoke` (kwargs `cost_usd=`/`time_s=`;
  `consume` only on the success leg).
- Test: `test_coupling.py::test_cc1_invoke_kwargs_and_consume_on_success_only`
  (signature pin + success consume-count equality + failed-invoke
  holdings-untouched).

## CC2. Invoke payload keys (gap 2)

- Promise: a success entry payload MUST carry `capability`,
  `args_ref`, `result_ref`, and MUST NOT carry `error`. The resume
  matcher keys on exactly these four conditions.
- Code: `resume.py:successful_invokes` / `resume.py:scan_succeeded`.
- Test: `test_coupling.py::test_cc2_invoke_payload_keys` (shape on a
  real consumer run + error-entry exclusion from the matcher).

## CC3. Args files (gap 3)

- Promise: `store_args` writes JSON with at least `formulation_ref`
  and `candidate_refs` keys. Resume reads these keys; byte-level
  compatibility is required across the kill boundary.
- Code: `minihost.py:MiniHost.store_args`,
  `resume.py:check_args_keys` (runs on every plan step).
- Test: `test_coupling.py::test_cc3_args_keys_and_byte_compat_across_kill`
  (missing-key refusal + real-SIGKILL resume with the args file
  byte-identical and still keying the matcher).

## CC4. Result schemas (gap 4)

- Promise: propose `result_ref` JSON carries `candidate_refs` and
  `champion_id`. (Score clause: NOT-APPLICABLE, not unimplemented —
  this pipeline has no `sched.score` capability; independent-checker
  verdicts take scoring's place. Carried from the successor-001 base
  report via successor-005 CONTRACT-GAPS.md.)
- Code: `resume.py:SchedWorld.write_proposal`,
  `resume.py:check_propose_result` (write-time assert + re-read).
- Test: `test_coupling.py::test_cc4_result_schemas` (schema on a real
  run + malformed-result refusal).

## CC5. Host read shape (gap 5)

- Promise: resume reads `host.worlds[ID].lifecycle` and compares to
  the string `"active"`. Canonical lifecycle strings:
  `active|suspended|dissolved|retired` (+ pre-active `"proposed"`;
  `"retired"` declared but never exercised — no promise attaches).
- Code: `resume.py:require_active`, `minihost.py:MiniHost.worlds`.
- Test: `test_coupling.py::test_cc5_lifecycle_read_shape` (active
  read + suspended refusal + denied invoke with recorded deny).

## CC6. Deny shape (gap 6)

- Promise: `deny(actor, action, reason)` — positional order pinned.
  Every refusal path raises AND records a deny.
- Code: `minihost.py:MiniHost.deny` + all refusal sites.
- Test: `test_coupling.py::test_cc6_deny_positional_order` (signature
  pin + recorded entry actor/action/reason).

## CC7. World-handle file conventions (gap 7)

- Promise: resume needs `world.state_dir` (path-like) plus
  `verdicts/verdict.json` (phase verdict) and the
  `formulations/*.json` glob (latest artifact). The v1 SHOULD
  (`latest.json` manifest replacing the glob) is NOT implemented —
  the glob remains normative per the clause's own fallback
  (obedience, not deviation; carried from successor-005).
- Code: `resume.py:SchedWorld`, `resume.py:latest_formulation`,
  `resume.py:read_verdict`.
- Test: `test_coupling.py::test_cc7_world_handle_shape` (dir +
  latest-glob + phase-verdict + per-task history on a real run).

## CC8. Suspend/reattach shapes (gap 8)

- Promise: `suspend(world_id, actor, reason, pending_effects)` /
  `reattach(world_id, actor, reason)` — world_id first, actor second.
- Code: `minihost.py:suspend` / `minihost.py:reattach`,
  `fusion.py:quarantine_world` (suspends with `pending_effects`
  naming the standby transfer).
- Test: `test_coupling.py::test_cc8_suspend_reattach_shapes`
  (signature pins + roundtrip + reattach-when-active refusal).

## CC9. Unmodified-engine reuse (the Q3 demonstration itself)

- Promise: the resume engine this contract couples to is carried
  byte-identical (not rewritten), and drives resume-by-skip on a
  fresh host: re-driving a finished plan skips every step with
  `re_executed_invokes == 0`.
- Code: `resume.py` (sha256-pinned against frozen
  `successor-005/resume.py` in PROVENANCE.md).
- Test: `test_coupling.py::test_cc9_engine_carried_unmodified_and_resumes`
  (byte-identity + full-plan second drive skips all).

## Coverage claim

9/9 items implemented in this tree, each with a consuming code path
and an asserting test above. The two carried qualifications
(CC4-score not-applicable, CC7-glob fallback) and the
`retired`-unexercised note are the only qualifications; none changes
an implemented promise.
