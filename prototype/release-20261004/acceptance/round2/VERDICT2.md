# Acceptance verdict ROUND 2 — successor-002 release candidate (independent lane)

Date: 2026-10-04. Verifier state: fresh dirs under `/tmp/vrf2/*` (never
builder `runs/`, never round-1 `/tmp/vrf` state for pass/fail);
consumer interfaces only (`release.py` CLI + `api.py` incl.
`api.open_run` + `accept/` inputs); `PYTHONDONTWRITEBYTECODE=1`;
system `python3` = 3.12.3; `prototype/w1/.venv` pydantic = 2.13.5
(re-verified). `successor-002/` and frozen dirs never modified
(IDENTITY 41/41 OK before AND after all runs; FROZEN-BASELINE
200-file spot-check 200/200 OK before AND after; no `.test-tmp`,
no `__pycache__` in the candidate tree).

Scope per delegation: FULL rerun of A10 + A8, spot reruns of A1, A6,
A9 (no-regression check after the snapshot rebase). A2–A5, A7 were
PASS in round 1 on behavior this round's diff does not touch
(OP-4 validation is additive pre-mutation; snapshot bytes are
content-identical for all previously-pinned files — verified below).

## Verdict: ACCEPT-WITH-NOTES (3 record notes, no behavior change)

A10 now PASSES in full (8/8 sampled clauses, incl. the round-1 OP-4
FAIL which is fixed and verified fail-closed). A8 PASSES (54-file
scope, rebase verified byte-identical to the clean SST release
commit). A1/A6/A9 spot reruns PASS with values identical to round 1.
The 3 new findings are all low-severity record wording (builder fixes
records, no behavior change, coordinator confirms): a stale worked
check, stale suite counts, and an OP-6 error-type parenthetical that
still mislabels one case.

## Per-check results

- A10 PASS (8/8). C1 (success consumes exactly 1 invoc + 1.0s with
  capability/args_ref/result_ref and no error; raised fn records
  `error`, no result_ref, consumes nothing, holdings byte-equal), C2
  (store_args keys), C4 (lifecycle string), C5 (deny/suspend/reattach
  positional signatures + behavioral deny), C7 (checkpoint identity
  mismatch rc=1 AND descriptor mismatch rc=1, both exact errors, on
  tampered COPIES with originals still OK), OP-1 (fuse via CLI:
  3 transfers actor=giver, derived_from×2 resolvable, fusion rec;
  suspended-parent fuse → RuntimeError rc=1, zero fusion entries),
  OP-2 (unfused reuse → AssertionError rc=1, zero S4 ledger traces;
  fused reuse 5/5), OP-4 (below).
- A10/OP-4 PASS (was round-1 FAIL). The exact round-1 failing command
  on fresh state now fails closed:
  `ops revoke ... --new-owner SC-DOES-NOT-EXIST` →
  `release: error: ValueError: new_owner 'SC-DOES-NOT-EXIST' is not a
  known world`, rc=1. Known-but-non-advertising owner →
  `ValueError: new_owner 'SC-S' does not advertise list.provide@1.0`,
  rc=1. Zero partial effects: no `revoke` entries after either
  failure, all SC-L stamps unflipped (failures append only declared
  `host_reopen` markers). Valid revoke (SC-S advertises
  sched.propose) → `revoke recorded seq=12`, rc=0; later invoke of
  the revoked cap denied with `ContractViolation` + recorded deny.
  Validation precedes mutation in code order (`resume.py`: existence
  + new_owner checks before stamp flip / ledger append).
  Builder negative test `test_new_owner_must_advertise` passes
  (suite now 9/9 — see note N2).
- A8 PASS. Real snapshot MATCH (54 files, hash `5f1f3789…`, exact
  match to the delegated value); regenerated manifest byte-identical
  to frozen (sha256 `e5d8bb0a…` both); all 54 files pinned incl. the
  4 non-py (`py.typed` + 3 visualizer assets). Tamper of a COPY's
  `visualizer.js` refused rc=1 naming exactly
  `sst/visualizer/assets/visualizer.js` (round-1 note 2 fixed);
  py-tamper of a second COPY refused naming `sst/search/policy.py`;
  real snapshot still MATCH. Gate 1 verify precedes any SST import
  in code order (`sst_leg.py:166` before child spawn `:180`; parent
  never imports sst — all `import sst` lines sit inside the
  CHILD_SCRIPT string literal); zero `../sst|cand-02|.delivery` refs
  in `*.py` (remaining refs are docs/provenance records only).
  Live SST leg via consumer API: MATCH, `champion_found`,
  `cand_tree_successor_sst_0_0`, $0.0, 8/8 envelope keys, pydantic
  2.13.5, TEST-only; `sst_file` =
  `.../successor-002/vendor/sst-snapshot/sst/__init__.py` (inside
  the snapshot). SST tree + snapshot pre/post manifests identical
  across the leg; SST git porcelain 0 before and after.
- A8/rebase challenge: the df78f42 rebase was the RIGHT call.
  Independently verified: SST HEAD is exactly
  `df78f42894a65c48f524337a498032617689a013`, porcelain 0;
  `diff -r` source-vs-snapshot identical except `__pycache__`;
  own 54-file hash cross-check: source==snapshot==manifest, zero
  mismatches, zero extras. Round 1 proved staging mutates underfoot
  (7 files drifted); a clean owner-landed release commit is strictly
  more stable and auditable. Snapshot mtimes (10:35–10:36Z) predate
  the recorded copy completion (10:37:17Z) — consistent, no repeat
  of round-1 note 5. Label `SUBSTRATE-QUALIFIED SNAPSHOT — NO
  SST-OWNER RELEASE ACCEPTANCE` remains accurate: the bytes ARE the
  owner's release commit, but the owner has not accepted substrate's
  snapshot/qualification as a release vehicle (PROVENANCE says the
  evidence request stands). Conservative and correct.
- A1 PASS (spot). Fresh `/tmp/vrf2/A1`: S1→central 4/4 (655/0 B),
  S2→local 4/4 (310/500 B) — identical to round 1. Own checker:
  both VALID, 0 violations, quality matches. Routing matches the
  logged rule incl. boundary S1 (rounds=2, split=False → central).
- A6 PASS (spot, kill/resume only). `child_rc=-9 valid=True
  quality=4/4 re_executed=0`; ledger: 9 invokes, 0 duplicate
  args_refs, 3 host_reopen markers (pre-flight + child attach +
  parent resume, matching the corrected count); child.READY
  cleaned; S3 VALID 4/4. Identical to round 1.
- A9 PASS (spot). Whole-tree copy to `/tmp/vrf2/succopy`:
  init→run→fuse→reuse→fission→split-pair→settle identical
  (VALID/quality/routing/bytes/5 markers/0 stranded); snapshot
  MATCH and 2.61x (810 vs 310) reproduce from the copy;
  `test_conformance.py` 9/9 from the copy (incl. the new negative
  test); system python only for core; no builder state touched.
  (One self-inflicted probe error on the way: settling already-
  dissolved parents refuses loudly with `ContractViolation`, as
  designed — the correct consumer usage is settling only the
  still-active worlds, which then reports all 5 terminals +
  5 markers, exactly as round 1.)
- Record-correction spot-checks (from the delegation): reopen
  count 3 ✓ (REPORT §5), PROVENANCE cand-02 history ✓
  (vendor/PROVENANCE.md superseded-source section), calibrate
  cleanup ✓ (no `.test-tmp` residue in copy or tree after suite +
  calibrate), LIMITS settle-atomicity ✓ (item 11), OP-6 error
  types — BEHAVIOR correct, wording still off (note N3).

## New findings (all record-only notes)

- N1. `vendor/HASH-CONSTRUCTION.md` "Worked check (by hand)" FAILS
  as written: it globs `*.py` only and asserts count MUST be 50
  and hash MUST equal `snapshot_hash`. Executed verbatim it prints
  `50 2abfd43b…` ≠ manifest `5f1f3789…`. The normative algorithm
  section (§1–6) is correct, and the corrected 54-file hand-check
  prints `54 5f1f3789…` = manifest. Fix: glob all files (excl.
  `__pycache__`), expect 54. Same-file line 5 parenthetical "(the
  vendored copy of staged cand-02 `src/`…)" is stale after the
  rebase (now: df78f42 release `src/`); likewise `sst_leg.py`
  docstring "(vendored staged bytes)". No behavior change.
- N2. Suite counts stale after the added negative test: observed
  `Ran 9 tests … OK` (9 methods incl.
  `test_new_owner_must_advertise`; 17+7+9 = 33 total), but
  REPORT.md (:12, :43 incl. the "one class per op" parenthetical,
  :180 "32 tests total"), CONSUMER.md (:18 "8/8 OK"), and
  REPRODUCE.md (:10 "32 unittest tests", :16–17 "Ran 8 tests")
  still say 8/8 and 32. Fix the counts to 9/9 and 33.
- N3. OP-6 §1 parenthetical still mislabels the split (round-1
  note 4 overshot): it reads "`ValueError` (bad partition/input)
  or `RuntimeError` (inactive/non-fused target)", but an ACTIVE
  non-fused target raises `ValueError` ("not a recorded fusion
  composite", pinned by `test_fission_rejects_non_composite`,
  confirmed via CLI rc=1) — only INACTIVE targets raise
  `RuntimeError` (via `require_active`, confirmed via CLI on the
  dissolved composite). Correct wording: ValueError = bad
  partition/input incl. active-but-non-fused; RuntimeError =
  inactive target. `fusion.py:167` docstring "(all loud
  ValueError…)" is likewise stale. Behavior is correct,
  test-pinned, and CONSUMER.md-accurate; wording fix only. (Not
  an A10 FAIL: OP-6 was not in the A10 sample set — covered
  behaviorally by round-1 A4 PASS — and this repeats round-1's
  NOTE-level treatment.)

## Evidence

`acceptance/round2/logs/`: `A10-init/op4/core/oppos/c7/op6.log`
+ `check_A10r2.py`, `A8-manifest/tamper/sourcecheck/sstleg/grep/
workedcheck.log`, `A1-run.log` + `own_check_r2.py` +
`A1-owncheck.log`, `A6-killresume.log`, `A9-run/sst-cal.log`,
`IDENTITY-check/post.log`, `FROZEN-spot.log`. Failing-then-fixed
artifact: `/tmp/vrf2/A10b` ledger (2 refused bogus-owner revokes
+ 1 valid revoke at seq 12). Round-1 `/tmp/vrf` state was not
used for any pass/fail.
