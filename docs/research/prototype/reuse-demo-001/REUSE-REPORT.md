# REUSE-REPORT.md (reuse-demo-001)

Claim under test (from `../w1-harden/RECOVERY-REUSE.md`): the w1-harden
recovery capability is consumable by a separate host through the small
named interface in section 2. Verdict: **confirmed** -- a new
stdlib-only host drove the unmodified `resume_to_verdict` through a
kill boundary with 0 re-executed invokes.

## What was genuinely reused (w1-harden code, unmodified)

Loaded from the literal path `../w1-harden/recovery_lib.py` (235 lines
total) via `w1h_bridge.load_recovery_lib()` and executed as-is:

| Reused symbol | Lines in recovery_lib.py | Role in demo |
|---|---|---|
| `resume_to_verdict` | 142-235 (94 lines) | the resume engine itself, driven through MiniHost |
| `phase_formulate` | 68-73 (6) | pre-kill + fresh runs |
| `phase_propose` | 75-84 (10) | pre-kill + fresh runs |
| `phase_score` | 86-93 (8) | fresh runs |
| `phase_verdict` | 96-106 (11) | fresh runs |
| `successful_invokes` | 115-119 (5) | resume matcher, also asserted directly in tests |
| `latest_artifact`, `_artifacts_exist`, `_args_*` | 109-140 (32) | helpers resume depends on |
| `WORKER_ID`, `WORKER_CODE_REF`, `POLICY`, `GOAL` | 39-43 (5) | worker identity + pipeline vocabulary |
| `setup`, `worker_record` | 46-66 (21) | NOT reused (host-shaped constructors; see below) |

Reused executable lines: ~171 of 235 (everything except `setup` /
`worker_record`, which construct the old host's `WorldRecord` /
`ExploreWorld` types and are therefore host-shaped by design -- the
report's section 3 predicts exactly this split).

Nothing in `../w1-harden/` or `../w1/` was modified (read-only;
verified by sha256sum before/after -- see Self-check).

## What was rewritten (new code, this directory)

| File | Lines | Contents |
|---|---|---|
| `minihost.py` | 838 | NEW host: `MiniHost` (ledger/append/invoke/deny, grants+settle, conservation+unsettled-terminal check, transitions, suspend/reattach, reopen-by-replay with descriptor verify + fail-closed withholding, custody/relationship stubs) + `MiniWorld` (deterministic artifacts) + record dataclasses. Zero imports from the reference package (enforced by test_10). |
| `w1h_bridge.py` | 55 | explicit path importer (importlib on the literal file path; no package import, no copy). |
| `reuse_demo.py` | 255 | evidence runner incl. `--child-partial` SIGKILL-crash mode. |
| `test_reuse.py` | 226 | 10 unittest tests. |

The `minihost.py` line count is dominated by the section-2 adapter the
report budgets ("replay loop generic, per-row updates host-specific"):
reopen replay ~150 lines, conservation replay ~75, invoke ~55,
settle ~40, suspend/reattach ~55. The pipeline-side `MiniWorld` is ~60
lines. A production port reusing this pattern would keep the same shape.

## Exact import mechanism

```python
spec = importlib.util.spec_from_file_location(
    "w1h_recovery_lib", <repo>/prototype/w1-harden/recovery_lib.py)
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)   # w1-harden dir briefly on sys.path:
                                  # recovery_lib's HOST/contract/
                                  # world_explore fallback imports
```

No `sys.path` guessing, no package import, no vendored copy. Transitive
note: executing `recovery_lib.py` necessarily executes its own
module-level imports (its HOST.py, contract.py, world_explore.py).
That is `recovery_lib`'s dependency closure, not this demo's host:
`minihost.py` never imports or instantiates the old `Host` class --
`MiniHost` plays the entire host role (test_10 asserts the import
boundary; only `w1h_bridge.py`, `reuse_demo.py`, `test_reuse.py` touch
the reference tree, and read-only).

## Results (fresh run from repo root, `python3`)

- `test_reuse.py`: **10/10 pass** (`Ran 10 tests ... OK`), covering:
  drop-kill resume, SIGKILL-subprocess resume, second-resume skips all,
  failed-invoke exclusion, terminal settle (incl. settle-then-move
  ledger order), handwritten unsettled-terminal rejection, both
  reattach refusals with recorded deny, reused refuse-unknown-worker,
  host-separation check.
- `reuse_demo.py`: **exit 0**, evidence summary:
  - drop-kill: skipped formulate+propose, `re_executed_invokes=0`,
    3 pre-kill artifacts byte-identical;
  - SIGKILL (child rc=-9): same resume result, artifacts byte-identical;
  - second resume executes nothing; suspend/reattach roundtrip ok;
  - both refusals raised with recorded deny; terminal holdings all zero
    with conservation ok; handwritten unsettled ledger rejected.
- Cost: $0, offline, stdlib-only (imports: hashlib/json/os/dataclasses/
  datetime/pathlib/subprocess/signal/tempfile/unittest/importlib).

## Limits of this demonstration

1. Same-machine paths: `args_ref`/`result_ref` are host-local paths, so
   resume was proven across a kill on one machine, not across machines
   (the report's section 4 already flags path-shaped refs as fragile).
2. Single worker, single grantor: multi-grantor settle distribution and
   relationship-evidence loss across reopen were not re-exercised here
   (covered by the w1-harden suite, not by this demo).
3. `MiniWorld` is a toy pipeline side: deterministic stub artifacts, not
   the real SST engine. The resume *decisions* (ledger + artifacts) are
   engine-agnostic, which is exactly what the demo proves.
4. Only `resume_to_verdict` + phase helpers were reused; `setup` /
   `worker_record` were reimplemented as `setup_worker` /
   `worker_record` (~20 lines) because they construct old-host types.

## Interface gaps found in RECOVERY-REUSE.md section 2

Section 2 was sufficient to reimplement the host side, but driving the
REUSED `resume_to_verdict` (rather than a rewrite) required pinning
several things section 2 does not state. Each was discovered by hitting
it during implementation:

1. **`invoke` signature and budget semantics.** Section 2 says
   "`invoke(caller, callee, capability, version, args_ref, fn,
   costs...)`" but the reused call sites pass `cost_usd=`/`time_s=`
   kwargs and assume one invocation is consumed per call, on success
   only (a failed `fn` records `error` but consumes nothing). A port
   must match the kwarg names and the consume-on-success-only rule.
2. **Invoke payload keys.** The resume matcher needs
   `payload.capability`, `payload.args_ref`, `payload.result_ref`, and
   the *absence* of `payload.error`. Section 2 only pins the envelope
   (`seq/kind/contract_version/actor/payload`).
3. **`store_args` / args-file format.** Resume reads the args files
   (`formulation_ref`, `candidate_refs` keys). Section 2 never mentions
   `store_args`, yet byte-level args-file compatibility is required.
4. **`result_ref` content schema.** A successful propose `result_ref`
   must be a JSON string with `candidate_refs`/`champion_id`, and score
   with `scores[].score_ref` -- world-side artifact vocabulary section 2
   omits (section 3 hints at it via `pending_effects`, but not here).
5. **Registry read shape.** Resume reads `host.worlds[ID].lifecycle`
   directly and compares to `"active"`. Section 2 lists no worlds-access
   API; a host exposing worlds differently (getters, different state
   strings) would break the reused function.
6. **`deny` signature order** `deny(actor, action, reason)` is assumed
   positionally; section 2 does not pin it.
7. **World-handle shape.** Resume needs `world.state_dir` plus the
   `verdicts/verdict.json` filename convention (phase_verdict) and the
   `formulations/*.json` glob convention (latest_artifact) -- all
   unpinned in section 2.
8. **`suspend` arg shape.** Section 2 writes
   "`suspend(world, pending_effects)`"; the actual convention is
   `(world_id, actor, reason, pending_effects)` -- same for reattach.

Suggested fix: move the §3 "refs/pending_effects are shared vocabulary"
note INTO §2 as an explicit "resume-coupling" list (invoke kwargs +
payload keys, args-file keys, result_ref schemas, worlds/lifecycle read
shape, world-handle file conventions). With that list, §2 alone would
be a complete porting contract; without it, a porter must read
`recovery_lib.py` line by line (as this demo did).

## Self-check

- Fresh run from repo root: `python3
  prototype/reuse-demo-001/test_reuse.py` -> OK (10 tests);
  `python3 prototype/reuse-demo-001/reuse_demo.py` -> exit 0.
- `sha256sum -c` against the pre-demo baseline of `../w1-harden/*`:
  all OK (untouched). Same for `../w1/` (never opened for write).
