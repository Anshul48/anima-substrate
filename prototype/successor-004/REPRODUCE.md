# REPRODUCE.md — successor-004

$0, offline. System `python3` for everything except the SST leg, which
uses a venv interpreter with pinned `pydantic==2.13.5` (default
`prototype/w1/.venv/bin/python`, override via `SST_VENV_PY`) and
`PYTHONPATH` pinned to the vendored snapshot
`successor-004/vendor/sst-snapshot/`. All commands from the
**substrate repo root**. `PYTHONDONTWRITEBYTECODE=1` is required.

## Tests (72 unittest tests)

    PYTHONDONTWRITEBYTECODE=1 python3 prototype/successor-004/test_successor.py
    PYTHONDONTWRITEBYTECODE=1 python3 prototype/successor-004/test_fission.py
    PYTHONDONTWRITEBYTECODE=1 python3 prototype/successor-004/test_conformance.py
    PYTHONDONTWRITEBYTECODE=1 python3 prototype/successor-004/test_atomicity.py

Expected: `Ran 17 tests ... OK` (~44 s, incl. kill + SST legs),
`Ran 7 tests ... OK` (fission), `Ran 9 tests ... OK` (ORG-OPS
conformance + routing + API recovery), `Ran 39 tests ... OK` (R1
atomicity: refusal proofs, kill-at-every-boundary matrices for
settle/fuse/fission via the CLI, pre-spec kills, repeated kills
incl. kill-during-recovery, real SIGKILLs, forensics; plus R3: 4
atomic-construction proofs + the 50-SIGKILL spec-window loop + 7
write-interior proofs). No warnings: the snapshot verifies MATCH
(any drift aborts loudly instead).

## Integrated demo (exit 0, ~60 s)

    PYTHONDONTWRITEBYTECODE=1 python3 prototype/successor-004/successor_demo.py

Expected: `successor-004 integrated demo: OK` + evidence summary,
exit 0. Run dir: `prototype/successor-004/runs/demo-<UTC>/` with
`EVIDENCE.json`, `ROUTING-LOG.jsonl`, `ledger.jsonl`,
`artifacts/{solution-*.json,fusion-record.json,fission-record.json}`,
`sst-leg/` (`SNAPSHOT-CHECK.json`, `sst-result.json`), `s5/`
(quarantine drill). Compare against `accept/EXPECTED.json` per
`accept/README.md` (all exact fields match; byte refs equal).

## Calibration (bytes-only 2.61x)

    PYTHONDONTWRITEBYTECODE=1 python3 prototype/successor-004/calibrate.py

Expected: S2-central 810 central bytes vs S2-local 310 → `2.61x`
(canonical-JSON bytes inside the task envelope; no token/cost claim).

## CLI smoke (incl. kill + recover)

    D=prototype/successor-004/runs/cli-smoke
    PYTHONDONTWRITEBYTECODE=1 python3 prototype/successor-004/release.py init --state-dir $D
    PYTHONDONTWRITEBYTECODE=1 python3 prototype/successor-004/release.py run --state-dir $D --tasks S1,S2
    PYTHONDONTWRITEBYTECODE=1 python3 prototype/successor-004/release.py ops fuse --state-dir $D --a SC-L --b SC-S --fused SC-FUSED --reason R
    ... reuse/fission/split-pair/inspect/settle, revise/revoke/quarantine,
    kill-resume, explain-route (see CONSUMER.md / REPORT.md §6)
    # kill during settle, then recover (R1):
    SUBSTRATE_CRASH_AFTER_APPENDS=4 PYTHONDONTWRITEBYTECODE=1 python3 prototype/successor-004/release.py ops settle --state-dir $D --worlds SC-L2,SC-S2 --reason R  # exit 42
    PYTHONDONTWRITEBYTECODE=1 python3 prototype/successor-004/release.py ops recover --state-dir $D --worlds SC-L2,SC-S2 --reason R
    # kill during fission, then recover with the partition of record:
    SUBSTRATE_CRASH_AFTER_APPENDS=8 PYTHONDONTWRITEBYTECODE=1 python3 prototype/successor-004/release.py ops fission --state-dir $D2 --composite SC-FUSED --left SC-L2 --right SC-S2 --partition sched.composite=SC-L2,sched.requirements=SC-L2,sched.slots=SC-S2 --reason R  # exit 42
    PYTHONDONTWRITEBYTECODE=1 python3 prototype/successor-004/release.py ops recover --state-dir $D2 --reason R  # refuses: needs --fission/--left/--right/--partition
    PYTHONDONTWRITEBYTECODE=1 python3 prototype/successor-004/release.py ops recover --state-dir $D2 --reason R --fission SC-FUSED --left SC-L2 --right SC-S2 --partition sched.composite=SC-L2,sched.requirements=SC-L2,sched.slots=SC-S2

Boundary maps + procedures: `INTERRUPTION-BOUNDARIES.md`.

## Snapshot checks

    PYTHONDONTWRITEBYTECODE=1 python3 prototype/successor-004/verify_snapshot.py
    # snapshot MATCH: files=54 hash=5f1f37893b0f5ab9...

Negative (tamper a COPY, never the snapshot):

    rm -rf /tmp/snapcopy && cp -r prototype/successor-004/vendor/sst-snapshot /tmp/snapcopy
    chmod -R u+w /tmp/snapcopy && echo '# x' >> /tmp/snapcopy/sst/search/policy.py
    PYTHONDONTWRITEBYTECODE=1 python3 prototype/successor-004/verify_snapshot.py /tmp/snapcopy
    # SST boundary: vendor snapshot drift — REFUSING SST import (exit 1)

## Checker self-check

    PYTHONDONTWRITEBYTECODE=1 python3 prototype/successor-004/sched_checker.py --self-check

## Identity + frozen-dir integrity

    cd prototype/successor-004 && sha256sum -c IDENTITY.sha256
    cd prototype && sha256sum -c successor-004/FROZEN-BASELINE.sha256

(expected: all OK). The baseline pins the frozen r1 tree
(`successor-002/` incl. its `runs/` evidence, `release-20261004/`)
plus the neighboring tracks (coverage + the live-sibling exclusion
documented in EVIDENCE.md §Frozen verification).
successor-002 was never modified after the copy. The SST tree is
never written (vendored snapshot consumed read-only; pre/post
verification proves it).
