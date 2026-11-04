# Ancillary native Windows qualification - 2026-10-04

The user identified Linux/Ubuntu as the shipping target and authorized a small Windows check. This result closes that ancillary check for the TEST/stub pilot. It adds no Windows shipping requirement or broader host-adoption claim.

Native Windows Python 3.12.0 (`win32`, `C:\Program Files\Python312\python.exe`) passed:

- All 33 existing pilot tests, including actual child-process termination and resume.
- Stub demo: exit 0, observed `stub-deterministic-v1`, 40 ledger entries, $0 experiment spend.
- Standalone recovery exercise: exit 0, forced termination return code 1, zero re-executed invokes, conservation OK.
- Missing-checkpoint and identity-mismatch refusals with recorded denials.
- Terminal settlement: live holdings and replay balances all zero.

The Windows termination result is `TerminateProcess` behavior, not a POSIX SIGKILL result. The original Linux report's -9 is not the Windows expectation.

## Candidate and change

`candidate/` contains the 12 Python source/test files copied from `../w1-harden/`. Two files change: `recovery_exercise.py` and `test_recovery.py`. Both use `Popen.kill()` instead of `os.kill(..., signal.SIGKILL)`; unused imports and related test names/documentation were adjusted. The exact changes are in `WINDOWS-KILL.patch`.

The baseline defect was confirmed by native Python lacking `signal.SIGKILL` and the two original call sites. The broken unmodified child-process test was not executed.

All 20 original `w1-harden/` files were hashed before qualification and verified unchanged afterward. Linux shipping source and its acceptance record were preserved. This Windows candidate is separately identified and has not advanced any consumer pin.

## Evidence and identities

- `ORIGINAL-SHA256.json`: identity of the 20 source files observed at the start of this Windows check; this is not a backdated claim about earlier Linux acceptance bytes.
- `CANDIDATE-SHA256.json`: all 12 exact Windows candidate source/test hashes.
- `runs/attempt-001/RESULT.json`: environment, commands, candidate hashes, all ten qualification checks PASS, and recovery summaries.
- `runs/attempt-001/*.stdout.log` and `*.stderr.log`: complete suite, demo, and recovery command output.
- `runs/attempt-001/stub-demo/`: demo state and complete ledger.
- `runs/attempt-001/recovery/`: recovery state, ledgers, excerpts, and per-scenario summaries.

The candidate was also hash-verified unchanged by execution. All checks were offline with bytecode writes disabled; no SST owner tree, original W1 files, or live-model path was used or changed.

## Reproduce

From PowerShell, run:

```powershell
& 'C:\Program Files\Python312\python.exe' -B 'C:\Users\anshu\OneDrive\Documents\Code\Utilities\substrate\prototype\windows-check-20261004\QUALIFY.py'
```

The runner verifies the original source identity, uses the existing candidate, and creates a new numbered attempt directory. It preserves earlier results. Expected: suite/demo/recovery return codes 0, all ten checks true, child termination code nonzero (observed 1).

This check was performed by the native Windows architect, not an additional independent reviewer. The isolated modified candidate was not rerun on Linux. The earlier Linux artifact remains byte-for-byte unchanged; its existing acceptance scope and other documented limits remain applicable. This result qualifies TEST/stub recovery on the observed Windows interpreter, not live-model search, concurrency, disk-loss recovery, learning, or general substrate capability.
