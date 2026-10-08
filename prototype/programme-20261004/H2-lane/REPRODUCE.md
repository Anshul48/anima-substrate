# REPRODUCE.md — H2-lane (experimental; NOT a release)

$0, offline. System `python3` for everything except the SST leg, which
uses a venv interpreter with pinned `pydantic==2.13.5` (REQUIRED here:
this tree sits one level deeper than `successor-003/`, so export
`SST_VENV_PY=prototype/w1/.venv/bin/python` — absolute path — and
`PYTHONPATH` is pinned to the vendored snapshot
`H2-lane/vendor/sst-snapshot/`). All commands from the
**substrate repo root**. `PYTHONDONTWRITEBYTECODE=1` is required.

## Tests (78 unittest tests)

    PYTHONDONTWRITEBYTECODE=1 python3 prototype/programme-20261004/H2-lane/test_successor.py
    PYTHONDONTWRITEBYTECODE=1 python3 prototype/programme-20261004/H2-lane/test_fission.py
    PYTHONDONTWRITEBYTECODE=1 python3 prototype/programme-20261004/H2-lane/test_conformance.py
    PYTHONDONTWRITEBYTECODE=1 python3 prototype/programme-20261004/H2-lane/test_atomicity.py
    PYTHONDONTWRITEBYTECODE=1 python3 prototype/programme-20261004/H2-lane/test_lane_tasks.py

Expected: `Ran 17 tests ... OK` (~65 s, incl. kill + SST legs;
`SST_VENV_PY` set), `Ran 7 tests ... OK` (fission),
`Ran 9 tests ... OK` (ORG-OPS conformance + routing + API recovery),
`Ran 27 tests ... OK` (R1 atomicity: refusal proofs,
kill-at-every-boundary matrices for settle/fuse/fission via the CLI,
pre-spec kills, repeated kills incl. kill-during-recovery, real
SIGKILLs, forensics), `Ran 18 tests ... OK` (H2 novel-lane: schema
refusals + no partials, pinned hand-computed derivation,
S1/S2-by-JSON == S1/S2-by-name, 655/0 + 310/500 + 2.61x, override
recording, unset-hook byte-identity, novel conservation + settle,
novel kill-resume). No warnings: the snapshot verifies MATCH (any
drift aborts loudly instead).

## Integrated demo (exit 0, ~60 s)

    export SST_VENV_PY=$PWD/prototype/w1/.venv/bin/python
    PYTHONDONTWRITEBYTECODE=1 python3 prototype/programme-20261004/H2-lane/successor_demo.py

Expected: `H2-lane integrated demo: OK` + evidence summary,
exit 0. Run dir: `prototype/programme-20261004/H2-lane/runs/demo-<UTC>/`
with `EVIDENCE.json`, `ROUTING-LOG.jsonl`, `ledger.jsonl`,
`artifacts/{solution-*.json,fusion-record.json,fission-record.json}`,
`sst-leg/` (`SNAPSHOT-CHECK.json`, `sst-result.json`), `s5/`
(quarantine drill). Compare against `accept/EXPECTED.json` per
`accept/README.md` (all exact fields match; byte refs equal;
routing entries carry the additive H2 fields — see EVIDENCE.md).

## Calibration (bytes-only 2.61x)

    PYTHONDONTWRITEBYTECODE=1 python3 prototype/programme-20261004/H2-lane/calibrate.py

Expected: S2-central 810 central bytes vs S2-local 310 → `2.61x`
(canonical-JSON bytes inside the task envelope; no token/cost claim).

## CLI smoke (incl. kill + recover + H2 flags)

    D=prototype/programme-20261004/H2-lane/runs/cli-smoke
    PYTHONDONTWRITEBYTECODE=1 python3 prototype/programme-20261004/H2-lane/release.py init --state-dir $D
    PYTHONDONTWRITEBYTECODE=1 python3 prototype/programme-20261004/H2-lane/release.py run --state-dir $D --tasks S1,S2
    PYTHONDONTWRITEBYTECODE=1 python3 prototype/programme-20261004/H2-lane/release.py ops fuse --state-dir $D --a SC-L --b SC-S --fused SC-FUSED --reason R
    ... reuse/fission/split-pair/inspect/settle, revise/revoke/quarantine,
    kill-resume, explain-route (see CONSUMER.md / REPORT.md §6)
    # H2: novel lane task + lane override:
    PYTHONDONTWRITEBYTECODE=1 python3 prototype/programme-20261004/H2-lane/release.py init --state-dir $D2
    PYTHONDONTWRITEBYTECODE=1 python3 prototype/programme-20261004/H2-lane/release.py run --state-dir $D2 --task-json novel.json --lane-override central
    PYTHONDONTWRITEBYTECODE=1 python3 prototype/programme-20261004/H2-lane/release.py explain-route --task-json novel.json
    # kill during settle, then recover (R1):
    SUBSTRATE_CRASH_AFTER_APPENDS=4 PYTHONDONTWRITEBYTECODE=1 python3 prototype/programme-20261004/H2-lane/release.py ops settle --state-dir $D --worlds SC-L2,SC-S2 --reason R  # exit 42
    PYTHONDONTWRITEBYTECODE=1 python3 prototype/programme-20261004/H2-lane/release.py ops recover --state-dir $D --worlds SC-L2,SC-S2 --reason R
    # kill during fission, then recover with the partition of record:
    SUBSTRATE_CRASH_AFTER_APPENDS=8 PYTHONDONTWRITEBYTECODE=1 python3 prototype/programme-20261004/H2-lane/release.py ops fission --state-dir $D2 --composite SC-FUSED --left SC-L2 --right SC-S2 --partition sched.composite=SC-L2,sched.requirements=SC-L2,sched.slots=SC-S2 --reason R  # exit 42
    PYTHONDONTWRITEBYTECODE=1 python3 prototype/programme-20261004/H2-lane/release.py ops recover --state-dir $D2 --reason R  # refuses: needs --fission/--left/--right/--partition
    PYTHONDONTWRITEBYTECODE=1 python3 prototype/programme-20261004/H2-lane/release.py ops recover --state-dir $D2 --reason R --fission SC-FUSED --left SC-L2 --right SC-S2 --partition sched.composite=SC-L2,sched.requirements=SC-L2,sched.slots=SC-S2

Boundary maps + procedures: `INTERRUPTION-BOUNDARIES.md`.

## Snapshot checks

    PYTHONDONTWRITEBYTECODE=1 python3 prototype/programme-20261004/H2-lane/verify_snapshot.py
    # snapshot MATCH: files=54 hash=5f1f37893b0f5ab9...

Negative (tamper a COPY, never the snapshot):

    rm -rf /tmp/snapcopy && cp -r prototype/programme-20261004/H2-lane/vendor/sst-snapshot /tmp/snapcopy
    chmod -R u+w /tmp/snapcopy && echo '# x' >> /tmp/snapcopy/sst/search/policy.py
    PYTHONDONTWRITEBYTECODE=1 python3 prototype/programme-20261004/H2-lane/verify_snapshot.py /tmp/snapcopy
    # SST boundary: vendor snapshot drift — REFUSING SST import (exit 1)

## Checker self-check

    PYTHONDONTWRITEBYTECODE=1 python3 prototype/programme-20261004/H2-lane/sched_checker.py --self-check

## Identity + frozen-dir integrity

    cd prototype/programme-20261004/H2-lane && sha256sum -c IDENTITY.sha256
    cd prototype && sha256sum -c programme-20261004/H2-lane/FROZEN-BASELINE.sha256
    cd prototype/successor-003 && sha256sum -c IDENTITY.sha256

(expected: all OK). This tree's baseline pins the frozen trees
(`successor-002/`, `successor-003/`, `release-20261004/`,
`programme-20261004/L1-transfer/`, `programme-20261004/L2-design/`,
plus neighboring tracks — coverage documented in EVIDENCE.md
§Frozen verification). The frozen source was never modified after
the copy. The SST tree is never written (vendored snapshot consumed
read-only; pre/post verification proves it).
