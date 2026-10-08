# X3 result (per frozen prereg X3-PREREG.md)

## Recovery implementation used
REUSED prototype/reuse-demo-001/minihost.py (vendored byte-copy; sha256 d01049a93b0e068e... pinned in FREEZE.json; verified identical). Both arms share it: checkpoint schema + identity rule (suspend/reattach exercised pre-kill on T2), resume-by-skip, grant_settle + unsettled-terminal check (finish_worlds + verify_conservation every task), host_reopen (exactly 1 per T2 resume).

## Freeze
- WRITTEN-OBLIGATIONS.md: 9411f905831dcd7e545f2b4904bf9a7419c904585b3015384561fee1f0e86571
- X3-PREREG.md: 4abbf73ebdc4d9e2c6e05112c7440bbd910cda764b0a2d8d73465a75d291e7af
- arm_c.py: fe82c8410a5700cba844488994e7b80cbe518598b47d16913a58e2b2dfd17f49
- arm_h.py: 3f2747f731e13fd652cac98f901ee40390ae7c339d865dab305d0acb2cbdd3ce
- checker.py: fa6d82413d6e5e8e700c19de7328e5202e3abe2d7bdf000e30589333c1478db1
- domain.py: b6b151b245047f498af60f8e945b4b27654345fe3bfd8f1aeb0eff8ab93ea29f
- frozen_inputs.py: 47634d68e05dfb49fc5776e401f78f8fd9dabafecff7521eb877a7ecec60fc45
- minihost.py: d01049a93b0e068e9e0384379cb26f509726f6a7ee659ff71dd0f0ec7bd4b206
- x3_run.py: e42a18e1362cb2adf4d3e40ac597e4662f6d90076599f64320ad9bd4cea9706e
- xcommon.py: b344c4268fb7a2532895f8dfc595c0bedce5c8dd52894cbd643f468830beb9e9

## Per-task tables (3 runs/arm)
### T1
| run | arm | VALID | quality | central-bytes | direct-bytes | rounds | rework | esc | extra |
|---|---|---|---|---|---|---|---|---|---|
| 1 | C | True | 4/4 | 1897 | 0 | 3 | 0 | 0 |  |
| 2 | C | True | 4/4 | 1897 | 0 | 3 | 0 | 0 |  |
| 3 | C | True | 4/4 | 1897 | 0 | 3 | 0 | 0 |  |
| 1 | H | True | 4/4 | 304 | 660 | 3 | 0 | 0 |  |
| 2 | H | True | 4/4 | 304 | 660 | 3 | 0 | 0 |  |
| 3 | H | True | 4/4 | 304 | 660 | 3 | 0 | 0 |  |
**T1 winner: H** -- VALID tie; H bytes 304 vs C 1897 (ratio 0.160); H rework 0.0 vs C 0.0

### T2
| run | arm | VALID | quality | central-bytes | direct-bytes | rounds | rework | esc | extra |
|---|---|---|---|---|---|---|---|---|---|
| 1 | C | True | 4/4 | 2193 | 0 | 3 | 0 | 0 | resume0=True skipped=formulate+adapt-propose |
| 2 | C | True | 4/4 | 2193 | 0 | 3 | 0 | 0 | resume0=True skipped=formulate+adapt-propose |
| 3 | C | True | 4/4 | 2193 | 0 | 3 | 0 | 0 | resume0=True skipped=formulate+adapt-propose |
| 1 | H | True | 4/4 | 645 | 802 | 3 | 0 | 1 | resume0=True skipped=formulate+adapt-propose |
| 2 | H | True | 4/4 | 645 | 802 | 3 | 0 | 1 | resume0=True skipped=formulate+adapt-propose |
| 3 | H | True | 4/4 | 645 | 802 | 3 | 0 | 1 | resume0=True skipped=formulate+adapt-propose |
**T2 winner: H** -- VALID tie; H bytes 645 vs C 2193 (ratio 0.294); H rework 0.0 vs C 0.0

### T3
| run | arm | VALID | quality | central-bytes | direct-bytes | rounds | rework | esc | extra |
|---|---|---|---|---|---|---|---|---|---|
| 1 | C | True | 5/5 | 761 | 0 | 2 | 0 | 0 | lineage=True |
| 2 | C | True | 5/5 | 761 | 0 | 2 | 0 | 0 | lineage=True |
| 3 | C | True | 5/5 | 761 | 0 | 2 | 0 | 0 | lineage=True |
| 1 | H | True | 5/5 | 343 | 111 | 2 | 0 | 0 | lineage=True |
| 2 | H | True | 5/5 | 343 | 111 | 2 | 0 | 0 | lineage=True |
| 3 | H | True | 5/5 | 343 | 111 | 2 | 0 | 0 | lineage=True |
**T3 winner: H** -- VALID tie; H bytes 343 vs C 761 (ratio 0.451); H rework 0.0 vs C 0.0

## Verdict
Task wins: H=3 C=0. Overall: **H (H3a supported)**.
Recovery parity: HELD (both arms resume-with-0-rework on every T2 run).

## Envelope / limits (verdict holds only inside these)
- Toy scale: 4-5 tasks, 4-5 slots; single deterministic stub solver shared by both arms (quality cannot differ by solver).
- One injected SIGKILL per T2 run, mid-adaptation, artifacts on local disk (no disk loss, no concurrency).
- $0/offline/stdlib-only; MiniHost ledger timestamps excluded from determinism comparison (measures only).
- Central-bytes = canonical-JSON bytes of messages the coordinator handles; direct world traffic counted separately.
- T1/T3 have no crash; their rework=0 ties do not satisfy any ratio clause (strict improvement required).

## Prereg readings / deviations
1. 'One SIGKILL per arm' read as one per run per arm (3/arm, 6 total): each run replicates the full crash+resume. All 6 resume with 0 rework.
2. Ratio clauses require STRICT improvement (0-vs-0 rework ties satisfy neither arm's clause); otherwise H would win every tie vacuously. Verdict is robust to this reading (bytes ratios decide).
3. minihost vendored as a byte-copy with pinned sha rather than imported from the sibling dir (frozen provenance; no writes outside x3-20261004/).
4. No other deviations: 3 runs/arm, frozen inputs (hash verified), all attempts recorded, checker independent (validates constraints, not hashes).

## Failures preserved
- None: no INVALID solutions, no stranded holdings, no unsettled terminals, no voids, no recovery failures. (Had any occurred they would be listed here with run/task and cause.)

Determinism: reran arm C fresh (T1:same, T2:same, T3:same) -> MATCH on all measures.
Run log: RUN-LOG.md. Metrics: runs/run*/metrics.json.
