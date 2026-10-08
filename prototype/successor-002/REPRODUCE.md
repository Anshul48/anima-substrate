# REPRODUCE.md — successor-002

$0, offline. System `python3` for everything except the SST leg, which
uses a venv interpreter with pinned `pydantic==2.13.5` (default
`prototype/w1/.venv/bin/python`, override via `SST_VENV_PY`) and
`PYTHONPATH` pinned to the vendored snapshot
`successor-002/vendor/sst-snapshot/`. All commands from the
**substrate repo root**. `PYTHONDONTWRITEBYTECODE=1` is required.

## Tests (33 unittest tests)

    PYTHONDONTWRITEBYTECODE=1 python3 prototype/successor-002/test_successor.py
    PYTHONDONTWRITEBYTECODE=1 python3 prototype/successor-002/test_fission.py
    PYTHONDONTWRITEBYTECODE=1 python3 prototype/successor-002/test_conformance.py

Expected: `Ran 17 tests ... OK` (~59 s, incl. kill + SST legs),
`Ran 7 tests ... OK` (fission), `Ran 9 tests ... OK` (ORG-OPS
conformance + routing + API recovery). No warnings: the snapshot
verifies MATCH (any drift aborts loudly instead).

## Integrated demo (exit 0, ~60 s)

    PYTHONDONTWRITEBYTECODE=1 python3 prototype/successor-002/successor_demo.py

Expected: `successor-002 integrated demo: OK` + evidence summary,
exit 0. Run dir: `prototype/successor-002/runs/demo-<UTC>/` with
`EVIDENCE.json`, `ROUTING-LOG.jsonl`, `ledger.jsonl`,
`artifacts/{solution-*.json,fusion-record.json,fission-record.json}`,
`sst-leg/` (`SNAPSHOT-CHECK.json`, `sst-result.json`), `s5/`
(quarantine drill). Compare against `accept/EXPECTED.json` per
`accept/README.md`.

## Calibration (bytes-only 2.61x)

    PYTHONDONTWRITEBYTECODE=1 python3 prototype/successor-002/calibrate.py

Expected: S2-central 810 central bytes vs S2-local 310 → `2.61x`
(canonical-JSON bytes inside the task envelope; no token/cost claim).

## CLI smoke

    D=prototype/successor-002/runs/cli-smoke
    PYTHONDONTWRITEBYTECODE=1 python3 prototype/successor-002/release.py init --state-dir $D
    PYTHONDONTWRITEBYTECODE=1 python3 prototype/successor-002/release.py run --state-dir $D --tasks S1,S2
    PYTHONDONTWRITEBYTECODE=1 python3 prototype/successor-002/release.py ops fuse --state-dir $D --a SC-L --b SC-S --fused SC-FUSED --reason R
    ... reuse/fission/split-pair/inspect/settle, revise/revoke/quarantine,
    kill-resume, explain-route (see CONSUMER.md / REPORT.md §6)

## Snapshot checks

    PYTHONDONTWRITEBYTECODE=1 python3 prototype/successor-002/verify_snapshot.py
    # snapshot MATCH: files=54 hash=5f1f37893b0f5ab9...

Negative (tamper a COPY, never the snapshot):

    rm -rf /tmp/snapcopy && cp -r prototype/successor-002/vendor/sst-snapshot /tmp/snapcopy
    chmod -R u+w /tmp/snapcopy && echo '# x' >> /tmp/snapcopy/sst/search/policy.py
    PYTHONDONTWRITEBYTECODE=1 python3 prototype/successor-002/verify_snapshot.py /tmp/snapcopy
    # SST boundary: vendor snapshot drift — REFUSING SST import (exit 1)

## Checker self-check

    PYTHONDONTWRITEBYTECODE=1 python3 prototype/successor-002/sched_checker.py --self-check

## Identity + frozen-dir integrity

    cd prototype/successor-002 && sha256sum -c IDENTITY.sha256
    cd prototype && sha256sum -c successor-002/FROZEN-BASELINE.sha256

(expected: all OK). The extended baseline covers `w1-harden/`, `w1/`,
`reuse-demo-001/`, `x3-20261004/` (1401 files, carried) plus all of
`successor-001/` except `.test-tmp/` (477 files incl. its `runs/`
evidence): 1878 total. successor-001 was never modified after the
copy. The SST tree is never written (vendored snapshot consumed
read-only; pre/post verification proves it).
