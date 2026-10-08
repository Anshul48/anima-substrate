# S5-A12 independent verification lane — brief DRAFT (coordinator finalizes evidence pointers at spawn)

## Objective
S5-DESIGN §6 S5-A12: fresh-eyes re-run of S5-A1–S5-A11 from byte-verified
copies + own kill params + own tamper legs. Verdict ACCEPT /
ACCEPT-WITH-NOTES / REJECT with evidence. Required before any U-execute
prereg filing (§7.8). Successor acceptance is builder acceptance like
R3/r3 — EVIDENCE + lane verdict, NOT a PREREG-LOG entry.

## Authority and bounds
- READ-ONLY on: prototype/successor-002, -003, -004, H2-lane, all
  release-* trees, prototype/w1, and prototype/successor-005 itself.
  No writes outside the lane dir + scratch. Never weaken a gate; never
  narrow a suite (no -k/deselect/skip) to make green.
- WRITE: create exactly one lane dir `prototype/programme-20261004/S5-lane/`
  (VERDICT.md + logs). $0, offline, stdlib-only except the pinned SST
  venv interpreter. `PYTHONDONTWRITEBYTECODE=1` throughout. Persist lane
  logs in the lane dir (NOT /tmp — a host reboot mid-verification wiped
  /tmp scratch once already).
- NEVER run U-execute (needs this verdict + §7.8 filing). NEVER edit s005:
  defects go in the verdict as notes/reject reasons; the coordinator owns
  fix-the-successor deltas.

## Inputs (verify, don't trust)
- `prototype/successor-005/` + `EVIDENCE.md` (builder record) +
  `PROVENANCE.md` (copy record) + `REPRODUCE.md` (commands).
- `prototype/programme-20261004/S5-design/S5-DESIGN.md` §6 (S5-A1–S5-A12).
- Builder verification: `prototype/programme-20261004/S5-VERIFICATION.md`
  + suite logs under `successor-005/runs/verify-20261005T1005Z/`.

## Must do (all conjuncts)
1. Byte-verify: `sha256sum -c` s005 IDENTITY + the four predecessor
   IDENTITies + s005 FROZEN-BASELINE before ANY run. Copy s005 to scratch
   for destructive legs; confirm the copy hash.
2. Recount every suite via loader (`countTestCases`) and run each to a
   verdict from the repo root per REPRODUCE: conformance 9, fission 7,
   successor 17, atomicity 39, procedure 57. Quote Ran/OK lines + walls.
   The procedure loop test is slow (~90–140 s/round on slow disks — the
   builder's full run took 6095.2 s for 56 tests + loop wall 131.50 s);
   let it run.
3. Kill legs with OWN params: own delays/rounds for at least one op matrix
   (settle/fuse/fission) + own L2/L3 loop delays. Confirm ≥1 L2 + ≥1 L3.
4. Own tamper legs: own byte-flip sites (frozen copy + suite log + ledger
   argv + report verdict/bundle) → each must refuse loud with the
   axis-naming reason; clean control VALID.
5. Vehicle: regenerate pins (expect byte-identical), re-run readiness
   (expect READINESS-PASS), re-run R-A demo diff (expect EMPTY modulo
   banner/paths). Check MANIFEST env_extra venv pin.
6. Wording re-audit: run the tree's wording tests + own grep sweep for
   unnegated containment claims, unbounded impossibilities, unseparated
   durability sentences. Confirm N1/N2 definitions exist where pointed.
   (Advisory: `muse.search` returned false-empty on this tree; use scoped
   `bash grep`.)
7. Calibration 2.61x + snapshot MATCH + demo exit 0 + accept-fields check.
8. Frozen both-ends: re-hash predecessors before AND after the lane's runs.

## Report
`S5-lane/VERDICT.md`: per-gate PASS/FAIL table (S5-A1–S5-A11), every
number quoted from the lane's own runs (command + observed output),
all reds preserved (even fixed-by-retry), explicit ACCEPT /
ACCEPT-WITH-NOTES (numbered notes) / REJECT. Notes must say whether
each is record-only or behavior-gating.
