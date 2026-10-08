# Review: repeated-kill test hardening (a16ec2d)

**Verdict: ACCEPT** — all pre-existing assertions preserved at full strength, no
silence-on-failure path introduced, hook is env-gated with zero default
behavior, rendezvous is race-free under the stated bounds, focused test
re-run green (12/12 live kills).

Commit: `a16ec2d` "harden repeated-kill test with child-side sync at
proc:recover-pre-adopt". Replaces fixed `time.sleep(delay)` in
`TestProcInterruption::test_repeated_kills_during_recover` with a
`SUBSTRATE_SYNC_AT` / `SUBSTRATE_SYNC_FILE` child-side rendezvous at
`proc:recover-pre-adopt` in `recover_op`. Original flake: CI run
37768629306, 3.11 leg, killed_live=0/12 on a fast runner.

Files touched (4): `PROVENANCE.md` (2 hash refreshes),
`src/anima_substrate/host/api.py` (+import, +1 call),
`src/anima_substrate/host/minihost.py` (+`maybe_sync_at`, +comment),
`tests/test_procedure.py` (one test rewritten).

## 1. Pre-existing assertions: all present, none weakened

Diffed `git show a16ec2d^:tests/test_procedure.py` (old `one_round` + loop)
against new code line by line. Every assertion survives verbatim:

| # | Assertion (old) | New location | Status |
|---|---|---|---|
| 1 | `create-proc-world` returncode == 0 | test_procedure.py:1896 | identical |
| 2 | per round: `len(proc_invokes(key)) == 1` | :1938 | identical |
| 3 | per round: `oks[0]["proc"]["recovered"]` is True | :1939 | identical |
| 4 | per round: exactly 1 `consume` with `evidence_ref == invoke_id` | :1940-1946 | identical |
| 5 | per round: `host.verify_conservation()["ok"]` | :1947-1948 | identical |
| 6 | per round: `run-procedure` returncode == CRASH_RC | :1966 | identical |
| 7 | aggregate: `killed_live >= 1` over 12 rounds | :1974 | identical, still `>=1` (not `==12`) |

Only deliberate semantic change: `one_round(key, delay)` lost its `delay`
param and the `time.sleep`; the kill is now gated on `wait_ready()`.
One assertion was ADDED (strictly stronger): `self.fail("recover child
never reached sync point")` (:1929) when the child never signals within
30s. The `guarded_round` wrapper is unchanged and still applied per round.

## 2. No skips / retries-to-green / silent timeouts

- Skips: only the pre-existing `os.name != "posix"` skip (:1880-1881),
  untouched. No new skip.
- Retries: `guarded_round` (ledger-backup restore on L4 disk-loss only,
  catching `(RuntimeError, json.JSONDecodeError)`) is pre-existing and
  unmodified. The new `self.fail` raises `AssertionError`, which
  `guarded_round` does NOT catch — a sync malfunction propagates and fails
  the test loudly. Verified by reading `guarded_round` (:236-253).
- Timeout bounds, both fail loudly, correctly ordered:
  - Parent `wait_ready`, 30s per round → `kill_group` + `communicate` +
    `self.fail`. A child that crashes early, hangs pre-sync, or never
    reaches the point fails the test (after ≤30s that round), never
    counts as a live kill.
  - Child `maybe_sync_at`, 120s default (`SUBSTRATE_SYNC_TIMEOUT_S`) →
    stderr note + proceed. In-test the child is SIGKILLed within ms of
    signalling, so this never fires; it is purely a backstop so a leaked
    env can never hang production forever. Ordering 30s < 120s means the
    parent always fails first and loudly.
- No weakened timeout: the old code had no timeout at all (blind sleep);
  the new code converts "child too fast/slow" from silent `killed=False`
  into either a guaranteed live kill or a loud failure.

Minor observation (not a defect): `wait_ready` does not break early if
the child exits before signalling, so a systematically-crashing child
costs the full 30s × 12 rounds before failing. Slow but loud; acceptable.

## 3. `maybe_sync_at` hook: gated, inert-by-default, bounded, contained

Traced `src/anima_substrate/host/minihost.py:151-181`:

- Env-gated, both vars required: returns at :162-163 unless
  `SUBSTRATE_SYNC_AT` AND `SUBSTRATE_SYNC_FILE` are both non-blank.
  Second gate at :165-166: the call-site `point` must be in the
  comma-separated armed set. Unset (production default) = two `getenv` +
  two `strip` calls, zero behavior change.
- Bounded wait, no infinite hang: deadline = `monotonic() +
  max(timeout, 1.0)` (:173); loop polls `target.exists()` every 5ms and
  returns with a stderr note on expiry (:174-181). Malformed timeout →
  `ValueError` caught → 120.0 (:167-170). Negative/zero → clamped to ≥1s.
  SIGKILL terminates unconditionally. (Pathological `NaN` timeout would
  defeat the deadline comparison — requires deliberately setting
  `SUBSTRATE_SYNC_TIMEOUT_S=nan` on an already-armed hook; out of scope
  for a test-only hook, noted for completeness.)
- Production path unaffected: single call site, `api.py:845` in
  `recover_op`, immediately before `PROC.proc_recover`. All `recover_op`
  callers considered: `cli.py:793` (`ops recover`) and in-process test
  callers including the parent's own `api.recover_op(root)` at
  test_procedure.py:1936. The parent test process never sets
  `SUBSTRATE_SYNC_*` in its own environ (only in the spawned child's via
  `child_env`), so the parent's in-process recover and every other test
  take the early-return path. `child_env` scrubs crash vars; sync vars
  are only ever added for this test's recover children.
- Release semantics: only file REMOVAL releases (content ignored, per
  header comment :98-106, matching the loop which tests `exists()` only).
  The test parent never removes the file while the child lives (removal
  only pre-spawn and in `finally` after `communicate`), so in-test the
  kill is the sole release path.

## 4. Race analysis

**Rendezvous invariant:** `ready` is written by the child immediately
before entering a wait loop whose only live exits are (a) sync-file
removal or (b) the 120s timeout; the parent removes the file only when
no child is alive, and kills within milliseconds of observing `ready`
with the default 120s child bound — so observing `ready` + `poll() is
None` implies the child is blocked pre-adopt, and the ensuing SIGKILL is
a genuine live kill at the intended phase boundary.

- False live-kill (ready observed, child already dead)? `killed =
  child.poll() is None` is evaluated AFTER `wait_ready` returns. A child
  that died post-`ready` yields `poll() → rc`, counted as NOT live. No
  false positive. The residual window (child timing out between `poll()`
  and `kill_group`) requires the 120s deadline to land in a
  microsecond-scale window ~120s after a signal the parent acts on in
  ms — not credible.
- Missed kill (child proceeds past the point unkilled)? Requires the
  child to exit the wait loop alive before the kill: only via removal
  (parent never removes while the child lives — pre-spawn unlink targets
  a reaped/previous child; `finally` unlink runs after `communicate`) or
  via the 120s timeout (parent kills in ms; would need a >120s stall in
  straight-line parent code). Neither is reachable in-test; empirically
  12/12 live kills.
- Stale-signal / cross-talk? Sync file is per-key (`sync-{Kxx}`),
  unlinked before spawn, under a per-test root wiped in `setUp`
  (:189-194); `guarded_round` retry re-enters `one_round`, which
  re-unlinks. The child writes `ready\n` (pure ASCII, so a torn
  concurrent read is still valid UTF-8 and simply re-polled; `OSError`
  pre-creation is caught). No other test uses `SUBSTRATE_SYNC_*`
  (repo-wide search confirms the only producer/consumer pair).
- Kill placement: the sync point sits after births/fusions/fission
  completion and before `proc_recover` adopt (api.py:772-846). In this
  test's L3 scenario the pre-sync phases are no-ops; any partial
  pre-sync writes are ledger-conditional and idempotent per `recover_op`
  contract, and per-round asserts (invoke/consume/conservation) prove
  parent-side convergence after every kill.

Net: the test now exercises exactly what it claims — a SIGKILL landing
during `recover`, before proc adoption — deterministically, instead of a
sleep-based lottery.

## 5. Independent re-run

`PYTHONDONTWRITEBYTECODE=1 ./.venv/bin/python -m pytest
tests/test_procedure.py::TestProcInterruption::test_repeated_kills_during_recover -x -q -s`
(exit 0):

> `repeated-kill loop: 12 rounds, killed-live=12 l4-restored=0`
> wall time ~29.8s (~2.5s/round, spawn-dominated)

One run, as tasked: PASS, 12/12 live kills, 0 L4 restores.

## 6. Tags + failure record

- `git rev-parse v0.1.0 v0.1.1` →
  `9d07c11...` / `9a1c795...`; both are ancestors of `a16ec2d`
  (`merge-base --is-ancestor` confirmed), neither points at the new
  commit. Tags untouched.
- Failure record preserved: new comment (test_procedure.py:1874-1879)
  retains the CI run id `37768629306`, the 3.11 leg, the `killed_live=0`
  symptom, and the "Do NOT weaken" directive (extended to "do NOT
  reintroduce fixed sleeps"). Prior note commit `814b35f` intact in
  history.

## Recommendation

ACCEPT `a16ec2d`. Optional follow-ups (none blocking): break `wait_ready`
early if the child exits (fail-fast); scrub `SUBSTRATE_SYNC_*` in
`child_env` like the crash vars for hygiene; reject non-finite
`SUBSTRATE_SYNC_TIMEOUT_S`.

## Coordinator addendum (8055fd5, not reviewer-verified)

After this review, CI on `a16ec2d` failed
`test_no_direct_whole_file_writes_in_shipped_code`: the rendezvous
`target.write_text(...)` must route via `atomic_write_text`
(construction rule). Follow-up `8055fd5` makes exactly that 1-line
change (+ PROVENANCE hash refresh). Verified: construction +
coupling 14 passed, focused test 12/12 live kills locally, CI
matrix green on both 3.11 (7m06s) and 3.12 (7m21s), run
37780377193. Rendezvous semantics unchanged; this addendum (not the
review above) is the coordinator's record of it.
