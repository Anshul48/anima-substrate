# REPORT.md — successor-002 (freezable Linux release candidate)

One-ledger integrated successor over the MiniHost lineage, carrying
successor-001's full behavior and adding the finish-line items: fission
(R4 gap), consumer org-op clauses with conformance checks (R9 gap),
a vendored hash-pinned SST snapshot (no external tree at runtime), and
release packaging (CLI + programmatic API + acceptance pack). $0,
offline; stdlib-only except the SST leg (venv interpreter +
pydantic==2.13.5, both declared in CONSUMER.md).

Observed results (demo `runs/demo-20261004T100134Z`, exit 0; suites
17/17 + 7/7 + 9/9 OK — see §Evidence):

| task | lane | VALID | quality | central-B | direct-B |
|---|---|---|---|---|---|
| S1 | central | yes | 4/4 | 655 | 0 |
| S2 | local | yes | 4/4 | 310 | 500 |
| S3 | local+kill | yes | 4/4 | 685 | 500 |
| S4-followup | fused-reuse | yes | 5/5 | — | — |
| S6-followup | fission-reuse | yes | 4/4 | — | — |

S1/S2/S3/S4/S5 numbers are IDENTICAL to successor-001 (base behavior
preserved byte-for-byte on scheduling metrics); S6 + fission are new.

## 1. Contracts: v1 C1–C7 + G1–G8 mapping + ORG-OPS OP-1–OP-6

No clause was unimplementable. One deviation was found by acceptance
round 1 (OP-4 §1 `new_owner` MUST unenforced) and FIXED (pre-mutation
validation + negative test `test_new_owner_must_advertise`; see §8 for
the carried notes, all explicit).

- C1–C7 (WORLD-CONTRACT-v1): carried from successor-001, all still
  asserted by tests 01–05, 08, 15 (unchanged matcher, schemas, shapes,
  settle/reopen machinery; `minihost.py` byte-identical to base).
- G1–G8 → v1 mapping: verified clause-by-clause in
  `CONTRACT-GAPS.md` (8/8 gaps mapped; each row quotes the pinning
  clause and names the consuming code path + asserting test).
- ORG-OPS OP-1–OP-6 (`ORG-OPS.md`): consumer clauses for
  fusion/reuse/revision/revocation/quarantine/fission, each specifying
  commitments, state custody, resource ownership, lifecycle
  transitions, lineage records, and recovery behavior a consumer can
  rely on — implemented ops ONLY (§7 explicitly excludes prospective
  learning/generality). Asserted by `test_conformance.py` (9/9: one
  class per op + routing + API recovery + OP-4 new_owner negative).
- Recovery correction found by the CLI build: raw `MiniHost.reopen`
  keeps supplied-descriptor lineage, which drops fusion/fission
  lineage on reopen; the documented recovery path `api.open_run`
  restores creation lineage from the ledger `create` payloads (and
  re-applies revocations). Pinned by `TestApiRecovery`.

## 2. Routing rule + calibration (the 2–6x claim, bytes only)

Rule unchanged (central default; `routing.route`): **LOCAL iff
expected_rounds >= 2 AND split_state, else CENTRAL.** Six decisions
logged (ledger + `ROUTING-LOG.jsonl`): S1→central, S2→local,
S3→local, S4-followup→fused-reuse, S6-followup→fission-reuse,
S5→quarantine-drill.

CALIBRATED CLAIM (`calibrate.py`, reproducible): the SAME task (S2)
through BOTH lanes on fresh hosts — central lane: coordinator handles
810 canonical-JSON bytes; local lane: 310 bytes. Ratio **2.61x**.
This is a ratio of central-handled canonical-JSON bytes inside the
task envelope ONLY. Explicitly NOT claimed: token/attention/cost
equivalence, cross-task generality, learned routing. (`calibrate.py`
prints the numbers; `accept/EXPECTED.json` records per-task byte
references as eyeball-only fields.)

## 3. Fusion + fission + reuse evidence

Fusion (carried): SC-L + SC-S → SC-FUSED, 3 custody transfers
(giver-actor), parents settle-then-dissolve, `direct-channel:SC-L<->SC-S`
removed (inventory 8→7 mechanisms), ledger `fusion` entry. S4 reuse
through SC-FUSED: VALID 5/5, lineage check passed.

Fission (NEW, `fusion.fission_worlds`): SC-FUSED → SC-L2 + SC-S2:

- Partition record: `{sched.requirements→SC-L2,
  sched.composite→SC-L2, sched.slots→SC-S2}` — exact coverage of the
  composite's custodian set enforced BEFORE any mutation (incomplete /
  unknown / outsider / one-sided partitions raise `ValueError` with
  zero partial effects; non-composites and dissolved composites
  refused likewise).
- Custody back-transfer per the partition (actor = the composite, O4);
  composite settle-then-dissolve; children born + activated.
- Lineage entries NAMING the fusion being split (`fission-of{fusion,
  fusion_parents, side, partition}` on both children + ledger
  `fission` entry); parents resolve to ledger creates.
- Direct channel RESTORED between the children
  (`direct-channel:SC-L2<->SC-S2`, fresh/0-byte; sends flow again).
- S6 follow-up through the split pair: VALID 4/4 (formulate+propose
  on SC-L2, cross-verify on SC-S2).
- Full record: `artifacts/fission-record.json` (partition, transfers,
  lineage, before/after inventories).

Separation paths: quarantine (failure-driven: suspend + standby
completes) vs fission (planned: composite → two peers) compared in
`SEPARATION-PATHS.md` with when-each-applies + a comparison table.
S5 quarantine drill still green (probe denied, seq 14).

## 4. SST snapshot (SUBSTRATE-QUALIFIED SNAPSHOT)

- Vendored bytes: `vendor/sst-snapshot/` = exact copy of the SST
  owner's clean release tree `../sst/src` at
  `df78f42894a65c48f524337a498032617689a013`
  (`df78f42 release(sst)`, porcelain 0 at copy; 54/54 files
  byte-identical, `diff -r` except `__pycache__`).
  Provenance: `vendor/PROVENANCE.md` (source path, clean HEAD,
  copy timestamp, 54-file manifest; the superseded cand-02
  staging snapshot is preserved as history). NO WRITES into SST or
  the snapshot ever (snapshot files mode 555; enforcement by
  verifier, §below).
- Hash: construction `substrate-snapshot-v1`
  (`vendor/HASH-CONSTRUCTION.md`, exact algorithm: sha256 over sorted
  `relpath LF hexdigest LF` groups) → `snapshot_hash`
  `5f1f37893b0f5ab9ff7dcf0ce2c60b287b51647e2f18f627eabf5510537cad96`
  over all 54 files (scope extended from 50 py-only per acceptance
  note 2; every vendored byte is pinned). Generator
  `make_snapshot_manifest.py`; verifier
  `verify_snapshot.py` runs BEFORE every SST import and AFTER every
  consumption — ANY drift raises `SSTBoundary` naming the files
  (tests 16–17 tamper a COPY three ways; CLI self-check tampers
  again; the real snapshot always verifies MATCH).
- Runtime: `PYTHONPATH` = the snapshot dir EXACTLY; the child asserts
  `sst.__file__` resolves INSIDE the snapshot and that NO other
  sys.path entry provides an `sst` package (shadowing guard). Zero
  `../sst` / `.delivery` / `cand-02` references at runtime
  (grep-verified). The withdrawn staging pin is gone: no pin, no
  warn-and-proceed — exact bytes or loud refusal.
- Qualification: import + TEST `run_search` → 8/8 envelope keys,
  `termination_reason=champion_found`,
  `champion=cand_tree_successor_sst_0_0`, TEST-only gateway bindings,
  `estimated_cost_usd=0.0` ($0), pydantic 2.13.5 (pinned; any other
  version aborts). Observed in-child `sst.__file__`:
  `.../successor-002/vendor/sst-snapshot/sst/__init__.py`.
- Label: SUBSTRATE-QUALIFIED SNAPSHOT with explicit NO SST-OWNER
  RELEASE ACCEPTANCE (in PROVENANCE.md, the manifest label, sst_leg
  docstring, and here). The SST-owner evidence request (clean landing
  + stable `run_search`/`TEST` confirmation) stands.

## 5. Robustness on the integrated path

- Real forced termination: `Popen.kill()` (child rc=-9), resume with
  3 skipped + **0 re-invokes**; pre-kill history bytes identical;
  `host_reopen` markers (3 on the consumer path: pre-flight open +
  child attach + parent resume).
- S3 adaptation unchanged: revision v1→v2 + revocation SC-L→SC-S +
  denied retry + escalation → ruling → void (artifact kept) → v2
  re-propose → cross-verify. VALID 4/4.
- Refusal paths raise with recorded deny (unknown cap,
  reattach-when-active, revoked, quarantined, withheld) + the four
  fission rejections (non-composite, bad partition ×4, dissolved).
- Settle: all terminals settled, conservation verified, **0 stranded**
  (5 `grant_settle` markers: SC-L/SC-S/SC-FUSED/SC-L2/SC-S2).

## 6. Packaging

- CLI `release.py`: `init/run/explain-route/inspect/ops` (ops:
  fuse/fission/quarantine/revise/revoke/kill-resume + reuse/
  split-pair/settle). Smoke-tested end-to-end (init→run→fuse→reuse→
  fission→split-pair→inspect→settle + revise/revoke/quarantine/
  kill-resume/explain-route on separate roots).
- Programmatic API `api.py` (all state via explicit state-dir args) —
  documented with setup/config/inputs/outputs/failure/state/recovery
  in `CONSUMER.md` (Ubuntu apt/pip lines, pinned pydantic==2.13.5).
- `IDENTITY.sha256`: all impl + contracts + config + vendor manifest
  + acceptance inputs (verify: `cd successor-002 && sha256sum -c`).
- `accept/`: frozen task inputs + `EXPECTED.json` (exact VALID/
  quality/routing expectations; byte refs eyeball-only) + README
  acceptance procedure.

## 7. Evidence

- `runs/demo-20261004T100134Z/` (exit 0): `EVIDENCE.json` (13 keys),
  `ledger.jsonl`, `ROUTING-LOG.jsonl` (6 decisions), `artifacts/` (5
  solutions + fusion + fission records), `s5/`, `sst-leg/`
  (`SNAPSHOT-CHECK.json`, `sst-result.json`). Reproduced by a second
  fresh run `runs/demo-20261004T101257Z/` (exit 0, all metrics
  identical, 13/13 acceptance fields match `accept/EXPECTED.json`).
- Suites: `test_successor.py` 17/17 (~59 s), `test_fission.py` 7/7,
  `test_conformance.py` 9/9 — 33 tests total, all OK.
- `FROZEN-BASELINE.sha256`: 1878 files (1401 carried + 477
  successor-001 incl. its runs/, excl. `.test-tmp/`) — all OK at
  handoff; successor-001 never modified after the copy.
- `calibrate.py` → 2.61x (bytes-only).

## 8. Contract deviations: NONE (carried notes, all explicit)

- C3-score not-applicable (no `sched.score`; verdicts take its place).
- C6-glob fallback obeyed (`latest.json` manifest not implemented;
  the clause's own fallback keeps the glob normative).
- `retired` declared but unexercised (no promise attaches).
- C1-`...` extras not accepted by the vendored host (engine never
  passes extras).
- Quarantine O4 exception (actor=`host`, giver suspended) — documented
  in OBLIGATIONS.md and ORG-OPS OP-5.
- Snapshot label is substrate qualification ONLY (no SST-owner
  release acceptance).

Limits: see `LIMITS.md`. Reproduce: see `REPRODUCE.md`.
