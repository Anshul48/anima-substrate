# Windows-check incorporation (accurate record, 2026-10-04)

Source: `prototype/windows-check-20261004/WINDOWS-REPORT.md` (+ patch,
hashes, `runs/attempt-001/` logs), produced by the native Windows
architect on native Windows Python 3.12.0 (`win32`).

## What was qualified

A SEPARATE 12-file candidate (`windows-check-20261004/candidate/`):
10 files byte-identical to Linux `w1-harden/`, 2 files patched
(`recovery_exercise.py`, `test_recovery.py`: `Popen.kill()` instead of
`os.kill(..., signal.SIGKILL)`; see `WINDOWS-KILL.patch`).

Results on that candidate: 33/33 tests (incl. real child-process
termination + resume), stub demo exit 0 / 40 entries / $0, standalone
recovery exit 0 with termination code 1 and 0 re-executed invokes,
refusal + settle checks PASS. Full logs in `runs/attempt-001/`.

## What this does and does not change

- ADDS: TEST/stub recovery is now also qualified on one Windows
  interpreter against the separately-identified candidate. LIMITS.md
  item 10 ("Windows execution is untested") is superseded for the
  stub path only, and only for the patched candidate identity — the
  unmodified Linux bytes still contain the POSIX-only `SIGKILL` call
  sites and will fail on native Windows (baseline defect confirmed,
  unmodified test not executed, per the report).
- PRESERVES: the Linux artifact is byte-for-byte unchanged — the
  report's `ORIGINAL-SHA256.json` (20 files, hashed before
  qualification) matches `closeout-20261004/IDENTITY.json` exactly
  (coordinator verified 20/20). No consumer pin advanced; the
  Windows candidate was not rerun on Linux.
- DOES NOT establish: live-model search, concurrency, disk-loss
  recovery, learning, or general substrate capability on either OS.
- Per user direction, no further Windows work is a completion
  dependency unless a concrete requirement changes.
