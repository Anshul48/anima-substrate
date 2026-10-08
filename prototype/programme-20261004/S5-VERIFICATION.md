# S5-VERIFICATION.md — builder-side verification of successor-005 (S5-A1–S5-A11)

Follows the R1/R3 verification pattern. Builder: S5 BUILD subagent
(brief: implement the bounded procedure participant per S5-DESIGN +
prove the §6 bar; build complete pre-reboot). Coordinator verification:
shell punchlist §1–§8 (this file is part C, the closing record). All
commands from the substrate repo root with `PYTHONDONTWRITEBYTECODE=1`
unless noted.

## Standing

- successor-005 source: `prototype/successor-005/` (copy-verified from
  successor-004: 100 files byte-identical at 2026-10-05T01:38Z).
- In-tree records: `EVIDENCE.md` (S5 evidence + carried R3 record),
  `PROVENANCE.md` (copy + evolution), `REPRODUCE.md` (commands).
- Verification logs: `successor-005/runs/verify-20261005T1005Z/`
  (in-tree evidence; a host reboot mid-verification wiped /tmp
  scratch, so every number below is a post-reboot re-observation).
- Gate verdicts (builder side):

| gate | result |
|---|---|
| S5-A1 carried green | PASS (9/9, 7/7, 17/17, 39/39 + demo + 2.61x + MATCH-54) |
| S5-A2–A8 + A11-tests | PASS: 57 tests = 56/56 full suite (6095.2 s) + cross-key pin focused-green; loop L2=12 L3=28 |
| S5-A9 frozen both-ends | PASS (1161/1161 + 41/41 + 45/45 + 45/45 + 46/46) |
| S5-A10 readiness | PASS: READINESS-PASS re-observed post-reboot (host 175.8 s VALID, direct VALID, claims-diff 0) |
| S5-A11 wording | PASS (mechanical 3/3 + manual sweep + N1/N2 defined) |
| S5-A12 lane | QUEUED (brief staged; spawns after IDENTITY freeze) |

## Reds preserved (all red-first; none weakened)

1. test_14 pin mismatch → S5 re-pin (R1/R3 precedent), then 17/17.
2. `test_impossibility_bounded` FAIL on `procedure.py:1203`
   (`adoption-impossible` vs listed bounder) → one-word fix.
3. Readiness direct conjunct FAIL (`SSTBoundary`, scrubbed env) →
   forwarding fix → READINESS-PASS.
4. Stale `56` procedure counts (2 doc sites) → loader-verified 55.
5. Unverifiable `2.0.5/3.0.5 (56 scenarios)` shorthand DROPPED from
   the record (no source found); matrices evidenced by test names +
   loop logs instead.
6. Host reboot killed the in-flight full procedure run at ~17/40
   loop rounds (no verdict observed; residue cleaned; full re-run).
7. Full procedure run: 55 tests, 3 failures + 1 error. The error is a
   REAL product race (P9 orphan window, K09) → key-subtree exclusion
   fix + deterministic regression test. The 3 failures are wording-test
   trips on coordinator EVIDENCE prose (fixed by trigger-free rewrite)
   + generated pins paths (justified scan-set carve-out). Re-run after
   fixes: 56/56 OK. See EVIDENCE.md §Verification fixes.
8. Independent read-only audit of the P9 fix (subagent, no writes, no
   runs): 5/5 PASS — orphan-only cause, exclusion cannot escape,
   dead-scratch writes cannot affect adoption/collection (one
   qualification: DONE.json presence probes exist but cannot flip —
   folded into the code comment), no other dependents on the old
   exclusion, manifest carve-out removes only generated data. One gap
   noted (cross-key tightness unpinned) → closed with the cross-key
   pin test (first draft had a wrong relative depth; the test caught
   it; fixed; suite now 57 = 56 full-run + 1 focused). Lane re-runs
   all 57.

## Evidence pointers (all observed, quoted in EVIDENCE.md)

- Suites: 9/9 (9.3 s), 7/7 (8.4 s), 17/17 (40.0 s), 39/39
  (529.0 s), 56/56 (6095.2 s) + cross-key P9 pin focused-green (19/19
  Permissions+Wording, 39.4 s).
- Matrices: 9 staggered SIGKILL landings converged (1 window-miss,
  still converged); spec-window 50 kills / 0 torn (26/20/4, 1 benign
  orphan); L2/L3 loop 40 rounds, landings L2=12 L3=28, wall=131.50 s;
  repeated-kill 12 rounds, killed-live=12, l4-restored=0.
- R-A: demo sources differ 1 line (banner); canonical diff EMPTY.
- Pins: bundle `1fee2241…`, pins `2dbb0439…`; regen byte-identical 3/3.
- Negatives: 24/24 matrix, 7/7 checker, tampered-copy rc=1 loud.
- Readiness: 175.8 s host VALID + direct VALID; claims-diff 0;
  hygiene 234 clean; frozen pre/post clean.
- Padding: no sleeps/burn loops (manual attestation).

## Handoff to S5-A12

Lane brief: `S5-design/S5-A12-BRIEF-DRAFT.md` (copy into the lane dir
at spawn). The lane re-runs S5-A1–S5-A11 from byte-verified copies
with own kill params + own tamper legs; verdict
ACCEPT/ACCEPT-WITH-NOTES/REJECT required before U-execute prereg
(§7.8). Known lane advisories: (a) `muse.search` returned false-empty
on the s005 tree — use scoped `bash grep` for the wording re-audit;
(b) the procedure loop test is slow on slow disks (~90–140 s/round —
let it run, never deselect); (c) U-execute + CONTINUING-PROGRAMME are
live sibling files, excluded from pins by posture.
