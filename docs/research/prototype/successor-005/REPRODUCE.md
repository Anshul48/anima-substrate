# REPRODUCE.md — successor-005

$0, offline. System `python3` for everything except the SST leg, which
uses a venv interpreter with pinned `pydantic==2.13.5` (default
`prototype/w1/.venv/bin/python`, override via `SST_VENV_PY`) and
`PYTHONPATH` pinned to the vendored snapshot
`successor-005/vendor/sst-snapshot/`. All commands from the
**substrate repo root**. `PYTHONDONTWRITEBYTECODE=1` is required.

## Tests (72 carried + 57 procedure tests)

    PYTHONDONTWRITEBYTECODE=1 python3 prototype/successor-005/test_successor.py
    PYTHONDONTWRITEBYTECODE=1 python3 prototype/successor-005/test_fission.py
    PYTHONDONTWRITEBYTECODE=1 python3 prototype/successor-005/test_conformance.py
    PYTHONDONTWRITEBYTECODE=1 python3 prototype/successor-005/test_atomicity.py
    PYTHONDONTWRITEBYTECODE=1 python3 prototype/successor-005/test_procedure.py

Expected: `Ran 17 tests ... OK` (~44 s, incl. kill + SST legs),
`Ran 7 tests ... OK` (fission), `Ran 9 tests ... OK` (ORG-OPS
conformance + routing + API recovery), `Ran 39 tests ... OK` (R1
atomicity: refusal proofs, kill-at-every-boundary matrices for
settle/fuse/fission via the CLI, pre-spec kills, repeated kills
incl. kill-during-recovery, real SIGKILLs, forensics; plus R3: 4
atomic-construction proofs + the 50-SIGKILL spec-window loop + 7
write-interior proofs), `Ran 57 tests ... OK` (S5: advertise +
construction, gates incl. the P1–P15 envelope + P11–P13 non-claims,
accountability, L1–L5 interruption incl. real SIGKILLs,
recovery/change flow, wording audit). No warnings: the snapshot
verifies MATCH (any drift aborts loudly instead).

## Integrated demo (exit 0, ~60 s)

    PYTHONDONTWRITEBYTECODE=1 python3 prototype/successor-005/successor_demo.py

Expected: `successor-005 integrated demo: OK` + evidence summary,
exit 0. Run dir: `prototype/successor-005/runs/demo-<UTC>/` with
`EVIDENCE.json`, `ROUTING-LOG.jsonl`, `ledger.jsonl`,
`artifacts/{solution-*.json,fusion-record.json,fission-record.json}`,
`sst-leg/` (`SNAPSHOT-CHECK.json`, `sst-result.json`), `s5/`
(quarantine drill). Compare against `accept/EXPECTED.json` per
`accept/README.md` (all exact fields match; byte refs equal).

## Calibration (bytes-only 2.61x)

    PYTHONDONTWRITEBYTECODE=1 python3 prototype/successor-005/calibrate.py

Expected: S2-central 810 central bytes vs S2-local 310 → `2.61x`
(canonical-JSON bytes inside the task envelope; no token/cost claim).

## CLI smoke (incl. kill + recover)

    D=prototype/successor-005/runs/cli-smoke
    PYTHONDONTWRITEBYTECODE=1 python3 prototype/successor-005/release.py init --state-dir $D
    PYTHONDONTWRITEBYTECODE=1 python3 prototype/successor-005/release.py run --state-dir $D --tasks S1,S2
    PYTHONDONTWRITEBYTECODE=1 python3 prototype/successor-005/release.py ops fuse --state-dir $D --a SC-L --b SC-S --fused SC-FUSED --reason R
    ... reuse/fission/split-pair/inspect/settle, revise/revoke/quarantine,
    kill-resume, explain-route (see CONSUMER.md / REPORT.md §6)
    # kill during settle, then recover (R1):
    SUBSTRATE_CRASH_AFTER_APPENDS=4 PYTHONDONTWRITEBYTECODE=1 python3 prototype/successor-005/release.py ops settle --state-dir $D --worlds SC-L2,SC-S2 --reason R  # exit 42
    PYTHONDONTWRITEBYTECODE=1 python3 prototype/successor-005/release.py ops recover --state-dir $D --worlds SC-L2,SC-S2 --reason R
    # kill during fission, then recover with the partition of record:
    SUBSTRATE_CRASH_AFTER_APPENDS=8 PYTHONDONTWRITEBYTECODE=1 python3 prototype/successor-005/release.py ops fission --state-dir $D2 --composite SC-FUSED --left SC-L2 --right SC-S2 --partition sched.composite=SC-L2,sched.requirements=SC-L2,sched.slots=SC-S2 --reason R  # exit 42
    PYTHONDONTWRITEBYTECODE=1 python3 prototype/successor-005/release.py ops recover --state-dir $D2 --reason R  # refuses: needs --fission/--left/--right/--partition
    PYTHONDONTWRITEBYTECODE=1 python3 prototype/successor-005/release.py ops recover --state-dir $D2 --reason R --fission SC-FUSED --left SC-L2 --right SC-S2 --partition sched.composite=SC-L2,sched.requirements=SC-L2,sched.slots=SC-S2

Boundary maps + procedures: `INTERRUPTION-BOUNDARIES.md`.

## Procedure CLI (advertise + run + recover surface)

    D=/tmp/s5proc-smoke
    PYTHONDONTWRITEBYTECODE=1 python3 prototype/successor-005/release.py ops create-proc-world --state-dir $D --world RELCHECK --bundle prototype/successor-005/vehicle/relcheck --reason smoke
    # proc-world RELCHECK: procedure=relcheck bundle=<16hex>... steps=['identity', 'suite-r1', 'suite-r2', 'suite-r3', 'compat', 'package']
    # (bundle 16 must equal vehicle/relcheck-pins.json bundle_sha256[:16])
    # run-procedure stages --inputs DIR (every file under DIR becomes a step input):
    mkdir -p /tmp/s5proc-inputs && cp prototype/successor-005/vehicle/relcheck/bin/relcheck.py prototype/successor-005/vehicle/relcheck/pins.json /tmp/s5proc-inputs/
    # ... + params.json (mode/nonce/paths/bundle — see vehicle/README.md; s5-readiness-check.py assembles it)
    PYTHONDONTWRITEBYTECODE=1 python3 prototype/successor-005/release.py ops run-procedure --state-dir $D --world RELCHECK --procedure relcheck --key smoke1 --inputs /tmp/s5proc-inputs
    # run-procedure relcheck/smoke1: skipped=[] executed=['identity', 'suite-r1', 'suite-r2', 'suite-r3', 'compat', 'package'] re_executed=[] child_executions={'identity': 1, 'suite-r1': 1, 'suite-r2': 1, 'suite-r3': 1, 'compat': 1, 'package': 1}
    PYTHONDONTWRITEBYTECODE=1 python3 prototype/successor-005/release.py ops recover --state-dir $D --reason smoke
    # proc_adopted=[] proc_rerunnable=[] on a clean world (nothing-to-do class);
    # after a mid-run kill: adopted or re-runnable entries per key (see test_recover_classes).

## Vehicle (relcheck) regen + readiness (S5-A10)

    PYTHONDONTWRITEBYTECODE=1 python3 prototype/successor-005/vehicle/make_vehicle_pins.py
    # gates 1-3 pass; prints bundle_sha256 + pins_sha256 (re-run is byte-identical)
    PYTHONDONTWRITEBYTECODE=1 python3 prototype/successor-005/vehicle/s5-readiness-check.py
    # READINESS-PASS: advertise ok, host wall >= 60 s, checker(host) + checker(direct)
    # RELCHECK-VALID, claims-diff 0, frozen pre/post clean

## Snapshot checks

    PYTHONDONTWRITEBYTECODE=1 python3 prototype/successor-005/verify_snapshot.py
    # snapshot MATCH: files=54 hash=5f1f37893b0f5ab9...

Negative (tamper a COPY, never the snapshot):

    rm -rf /tmp/snapcopy && cp -r prototype/successor-005/vendor/sst-snapshot /tmp/snapcopy
    chmod -R u+w /tmp/snapcopy && echo '# x' >> /tmp/snapcopy/sst/search/policy.py
    PYTHONDONTWRITEBYTECODE=1 python3 prototype/successor-005/verify_snapshot.py /tmp/snapcopy
    # SST boundary: vendor snapshot drift — REFUSING SST import (exit 1)

## Checker self-check

    PYTHONDONTWRITEBYTECODE=1 python3 prototype/successor-005/sched_checker.py --self-check

## Identity + frozen-dir integrity

    cd prototype/successor-005 && sha256sum -c IDENTITY.sha256
    cd prototype && sha256sum -c successor-005/FROZEN-BASELINE.sha256

(expected: all OK). The baseline is the pre-work frozen snapshot
(1161 files: successor-002/003/004 incl. runs/ evidence,
release-20261004/release-r2/release-r3, H2-lane, neighbors; test
scratch excluded — see EVIDENCE.md §Frozen verification).
successor-004 was never modified after the copy. Frozen trees are
never written (vehicle + suites run on scratch copies; pre/post
verification proves it).
