# Acceptance verdict — successor-002 release candidate (independent lane)

Date: 2026-10-04. Verifier state: fresh dirs under `/tmp/vrf/*` (never
builder `runs/`); consumer interfaces only (`release.py` CLI + `api.py`
incl. `api.open_run` handles + `accept/` inputs); `PYTHONDONTWRITEBYTECODE=1`;
system `python3` = 3.12.3; `prototype/w1/.venv` pydantic = 2.13.5 (verified).
`successor-002/` and frozen dirs never modified (IDENTITY 41/41 OK after all
runs; FROZEN-BASELINE 200-file spot-check 200/200 OK; calibrate `.test-tmp`
residue removed by verifier).

## Verdict: REJECT (one clause deviation; trivial fix, rerun A10 only)

A1–A9 PASS. A10: 7 of 8 sampled clauses PASS; OP-4 §1 `new_owner` MUST is
not upheld — quoted below. Per ACCEPTANCE-PLAN ("any clause that fails as
specified is a FAIL"), A10 = FAIL, so the candidate cannot freeze as-is.
The fix is ~3 lines (validate before mutation) or a coordinator-accepted
record rewording; only A10 needs rerunning. All other findings are NOTES.

## Per-check results

- A1 PASS. Fresh `/tmp/vrf/A1`: S1→central 4/4 (655/0 B), S2→local 4/4
  (310/500 B). Own checker invocation: both VALID, 0 violations, quality
  matches artifacts and EXPECTED. Routing matches logged rule incl.
  boundary S1 (rounds=2, split=False → central).
- A2 PASS. Independent recompute from receipts+ledger: S1 655/0, S2 310/500
  — exact match. `calibrate.py --out=/tmp` reproduced 810 vs 310 = 2.61x.
  Full-tree wording audit: every 2–6x/2.61x mention is bytes-scoped with an
  explicit no-token/attention/cost disclaimer; no overclaim sentence found.
- A3 PASS. Fusion: lineage derived_from×2 + fusion record, both resolve to
  ledger creates; 3 custody transfers, all actor=giver; parents dissolved
  with 2 grant_settle markers; inventory 8→7 removing exactly
  `direct-channel:SC-L<->SC-S`; reuse VALID 5/5 via SC-FUSED with
  `lineage_ok:true`, derived_from=[SC-L,SC-S].
- A4 PASS. Fission: exact partition, 3 back-transfers actor=SC-FUSED,
  composite dissolved, both children lineage-name fusion+parents, channel
  restored, S6 VALID 4/4 via [SC-L2,SC-S2]; final settle 5 markers,
  0 stranded. All 7 rejection probes (non-composite ×2, incomplete, unknown,
  outsider, one-sided, dissolved) raise with zero partial effects
  (excluding declared host_reopen markers).
- A5 PASS. Ledger order revision(23) < revoke(26) < deny(27) <
  escalation(28) < resolution(29) < void(30); void references the kept
  artifact (file exists); `void_proposal` has exactly one caller, after
  `issue_ruling`; SC-S re-propose VALID 4/4 v2 (both S3 views). Standalone:
  revise+revoke via CLI, then 3 consecutive `run` denials (rc=1,
  `ContractViolation`, one deny each); post-reopen stamp still
  `revocation.quarantined`, cap sets unchanged.
- A6 PASS. Kill-resume: child rc=-9, 3 pre-kill invokes all skipped,
  0 re-invokes (ledger: 9 invokes, zero duplicate args_refs), 3 host_reopen
  markers for 3 opens (pre-flight + child attach + parent resume),
  child.READY cleaned. Quarantine drill: SC-L suspended, 2 commitment
  transfers actor=host (O4 exception), probe denied + recorded deny,
  standby invoke succeeds, both settle 0 stranded.
- A7 PASS. Verifier-own replay (not `verify_conservation`) over all 6
  acceptance ledgers: conservation ok, terminals settled, global
  held+consumed=initial, 0 stranded. Handwritten unsettled-terminal ledger
  rejected with the exact error via both `inspect` and `ops settle` (rc=1):
  `ContractViolation: unsettled terminal: world 'SC-L' ended in 'dissolved'
  with no grant_settle marker; holdings may be stranded`.
- A8 PASS. Real snapshot MATCH (50 files, hash 61f523a5…); regenerated
  manifest byte-identical to frozen (sha256 6c24adc0… both); py-tamper of a
  COPY refused rc=1 naming `sst/search/policy.py`; Gate 1 verify precedes
  any SST import in code order; zero `../sst|cand-02|.delivery` refs in
  `*.py`; SST staging + snapshot pre/post manifests identical across a live
  SST leg; `sst_file` inside the snapshot; pydantic 2.13.5; 8 envelope
  keys; champion_found; $0.
- A9 PASS. Whole-tree copy to `/tmp/succopy`: init→run→fuse→reuse→
  fission→split-pair→settle identical (VALID/quality/routing/bytes/5
  markers); snapshot MATCH and 2.61x reproduce from the copy;
  `test_conformance.py` 8/8 from the copy; system python only, no builder
  state touched.
- A10 FAIL (one sub-clause). PASS: C1 (success consumes exactly 1 invoc +
  1.0s with capability/args_ref/result_ref and no error; raised fn records
  `error`, no result_ref, consumes nothing, holdings byte-equal), C2
  (store_args keys), C4 (lifecycle string), C5 (deny/suspend/reattach
  positional signatures + behavioral deny), C7 (checkpoint identity
  mismatch rc=1; descriptor mismatch rc=1, both exact errors), OP-1
  (custody giver-actor, resolvable lineage, suspended-parent RuntimeError
  with zero partials), OP-2 (unfused reuse AssertionError rc=1, zero S4
  ledger traces; fused reuse 5/5). FAIL: OP-4 §1 new_owner (below).

## The A10 failure (exact)

ORG-OPS.md OP-4 §1 states: "The named `new_owner` MUST already advertise
the capability — revocation flips usability, it does not grant new
capabilities." Observed through the consumer CLI on fresh state:

    release.py ops revoke --state-dir /tmp/vrf/A10b --world SC-L
      --cap sched.propose --version 1.0 --new-owner SC-DOES-NOT-EXIST
    → `revoke recorded seq=10: SC-L:sched.propose@1.0`, rc=0

No validation exists in `revoke_capability` (`resume.py` records
`new_owner` unchecked). Fail-closed is preserved (a later invoke by a
non-advertising owner fails loudly), so severity is low, but the MUST as
written is not upheld. Recommended fix: validate pre-mutation
(`ValueError` naming the defect, same style as OP-1/OP-6), add a negative
test, rerun A10.

## What the builder's report got wrong / record notes

1. (Above) REPORT.md §1 "no contract deviation" misses the OP-4 MUST gap.
2. REPORT.md §4 "ANY drift raises `SSTBoundary`" overstates: the 4 non-py
   snapshot files are unpinned — tampering `visualizer.js` in a COPY still
   reports MATCH rc=0 (proven). PROVENANCE discloses the 50-py scope, but
   the ANY-drift sentences (REPORT + `verify_snapshot.py` docstring) read
   absolute. Fix the sentences or pin the 4 files.
3. REPORT.md §5 "(child attach + parent resume)" undercounts the consumer
   path: `kill_resume_op` appends 3 host_reopen markers (pre-flight open
   adds one). Behavior correct; count the pre-flight open.
4. OP-6 §1 "Rejections raise ValueError" is over-narrow: inactive/non-fused
   targets raise RuntimeError (pinned by builder tests, allowed by
   CONSUMER.md's failure table). Reword to ValueError/RuntimeError.
5. PROVENANCE "54/54 identical (recorded 09:55:01Z)" is stale: staging
   moved on (7 files differ, patch sha + SST HEAD advanced) and the copy
   timestamp postdates the snapshot mtimes (08:40) — the physical copy
   predates 09:48. Snapshot integrity itself is unaffected (own manifest
   MATCH); record the staging drift + correct the timestamp.
6. `calibrate.py` leaves an empty `.test-tmp/` dir inside the release tree
   (baselines exclude it; verifier removed it). Clean up after itself.
7. NOTE: `settle` is not atomic on refusal — the unsettled-terminal probe
   left SC-S dissolved+settled while the op failed rc=1. Ledger stays
   consistent and fail-closed; do not rely on settle atomicity (LIMITS.md
   candidate).

## Evidence

`acceptance/logs/` (per-check CLI logs + `own_check/own_bytes/own_replay.py`
+ `check_*.py` probes), `acceptance/ledger-excerpts.txt`. Failing artifact
preserved: `/tmp/vrf/A10b` ledger shows the bogus-owner revoke at seq 10.
