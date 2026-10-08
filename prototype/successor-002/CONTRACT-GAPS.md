# CONTRACT-GAPS.md — G1–G8 gap → WORLD-CONTRACT-v1 clause mapping

Each reuse gap from `reuse-demo-001/REUSE-REPORT.md` (§Interface gaps)
is pinned by exactly one v1 clause from
`successor-contract/WORLD-CONTRACT-v1.md`. Verified clause-by-clause
against the successor-002 implementation (no duplication of v1, per the
finish-line contract): every gap maps, none is unmapped, none needed a
new clause.

## Mapping table

| Gap | Gap statement (short) | v1 clause | Consuming code path | Test(s) |
|---|---|---|---|---|
| G1 | `invoke` kwarg names + consume-on-success-only | C1 | `minihost.py:MiniHost.invoke`, `resume.py:execute_plan` | test_01, test_02 |
| G2 | invoke payload keys (`capability`/`args_ref`/`result_ref`, no `error`) | C1 | `resume.py:successful_invokes`, `resume.py:scan_succeeded` | test_01, test_02 |
| G3 | `store_args`/args-file keys + byte-compat across kill | C2 | `resume.py:check_args_keys`, `minihost.py:store_args` | test_03, test_08 |
| G4 | `result_ref` content schemas | C3 | `resume.py:check_propose_result`, `resume.py:SchedWorld.write_proposal`, `pipeline.py:build_verify` | test_03 |
| G5 | registry read shape `host.worlds[ID].lifecycle == "active"` | C4 | `resume.py:require_active`, `minihost.py:worlds` | test_04 |
| G6 | `deny(actor, action, reason)` positional order | C5 | `minihost.py:deny` + all refusal sites | test_04, test_09, test_11 |
| G7 | world-handle shape (`state_dir`, `verdicts/verdict.json`, `formulations/*.json`) | C6 | `resume.py:SchedWorld`, `resume.py:latest_formulation`, `resume.py:read_verdict` | test_05 |
| G8 | `suspend`/`reattach` arg shapes | C5 | `minihost.py:suspend`, `minihost.py:reattach`, `fusion.py:quarantine_world` | test_04, test_11 |

## Clause quotes + verification notes

### G1 → C1. Invoke call contract

v1 quotes: *"Signature: `invoke(caller, callee, capability, version,
args_ref, fn, *, cost_usd, time_s, ...)`; exactly one invocation is
consumed per call, ON SUCCESS ONLY. A raised `fn` records an `invoke`
entry with `payload.error` set and consumes nothing (no `consume`
entry)."*

Verified: `MiniHost.invoke` consumes exactly one invocation on success
(test_01 asserts the `consume` entry + holdings decrement) and records
`payload.error` with no `consume` entry on raised `fn` (test_02
asserts holdings untouched). `execute_plan` passes `cost_usd=`/
`time_s=` kwargs and never extras (v1's `...` is not accepted by the
vendored host — the engine never passes extras; carried boundary note).

### G2 → C1. Invoke call contract

v1 quotes: *"Success entry payload MUST carry: `capability`,
`args_ref`, `result_ref`, and MUST NOT carry `error`. The resume
matcher keys on exactly these four conditions."*

Verified: `successful_invokes` / `scan_succeeded` implement exactly
the four-condition matcher (test_01 asserts the success shape;
test_02 asserts a failed invoke is excluded from the matcher).

### G3 → C2. Args files

v1 quotes: *"`store_args` writes JSON with at least
`formulation_ref` and `candidate_refs` keys. Resume reads these keys;
byte-level compatibility is required across the kill boundary."*

Verified: `check_args_keys` runs on every plan step (test_03 asserts
the keys on built steps and on stored args files); test_08 asserts
pre-kill history bytes are identical post-resume across a real
`Popen.kill()` boundary.

### G4 → C3. Result schemas

v1 quotes: *"propose `result_ref`: JSON string with `candidate_refs`
and `champion_id`. score `result_ref`: JSON with
`scores[].score_ref`."* + *"version with the pipeline, not the host."*

Verified for propose: `SchedWorld.write_proposal` writes the schema;
`check_propose_result` asserts it at write time and `build_verify`
re-reads it (test_03). Score clause: NOT-APPLICABLE (not
unimplemented): this pipeline has no `sched.score` capability —
independent-checker verdicts take scoring's place. Recorded, not
hidden (carried from the successor-001 base report).

### G5 → C4. Host read shape

v1 quotes: *"Resume reads `host.worlds[ID].lifecycle` and compares to
the string `"active"`. ... Canonical lifecycle strings:
`active|suspended|dissolved|retired`."*

Verified: `require_active` implements exactly that read (test_04);
used by `execute_plan`, `fuse_worlds`, `fission_worlds`,
`reuse_composite`, `run_split_pair_task`. Compatible-superset note:
the host also has a pre-active `"proposed"` state; canonical strings
unchanged. `"retired"` is declared but never exercised (no test moves
a world to `retired`) — recorded here.

### G6 → C5. Deny shape

v1 quotes: *"`deny(actor, action, reason)` — positional order pinned."*

Verified: `MiniHost.deny` positional order asserted (test_04); every
refusal path (unknown capability, reattach-when-active, revoked
invoke, quarantined invoke, withheld descriptor) raises AND records a
deny (tests 04, 05, 09, 11).

### G7 → C6. World-handle file conventions

v1 quotes: *"Resume needs `world.state_dir` (path-like) plus pipeline
conventions: `verdicts/verdict.json` (phase_verdict) and
`formulations/*.json` glob (latest_artifact). A successor SHOULD
replace the glob with a manifest (`latest.json`); until then the glob
is normative."*

Verified: `SchedWorld.state_dir` + `read_verdict` +
`latest_formulation` glob (test_05); per-task `verdict-{task}.json`
history plus the advancing `verdict.json` latest-pointer (demo
asserts both). V1-SHOULD note: the `latest.json` manifest replacement
is NOT implemented — the glob remains normative per the clause's own
fallback. This is obedience to the stated fallback, not a deviation.

### G8 → C5. Suspend/reattach shapes

v1 quotes: *"`suspend(world_id, actor, reason, pending_effects)` /
`reattach(world_id, actor, reason)` — world_id first, actor second."*

Verified positionally (test_04 roundtrip + reattach refusal);
`quarantine_world` suspends with `pending_effects` naming the standby
transfer (test_11).

## Coverage claim

8/8 gaps mapped to a pinning v1 clause; every mapping has a consuming
code path in this tree and at least one asserting test. The two
carried notes (C3-score not-applicable, C6-glob fallback) and the
`retired`-unexercised note are the only qualifications; none changes
an implemented promise. C7 (checkpoint + settle + reopen, carried from
the pilot) has no gap number and is covered by tests 05, 08, 15.
