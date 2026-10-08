# R3-VERIFICATION — independent acceptance record

- Verdict: **ACCEPT-WITH-NOTES** (all 8 checks PASS).
- Verifier: independent lane (byte-verified /tmp copies; in-tree
  successor-004/ never written; /tmp scratch removed; evidence
  quoted verbatim into the report).
- Date: 2026-10-04. successor-004/ bytes are exactly as the
  verifier checked them — this record lives here; tree FROZEN.

## Independent confirmation (observed, not trusted)

1. Authentic red reproduced independently: pristine s003 /tmp copy
   (45/45 + diff-clean) → real SIGKILL at _write_specs → 0-byte
   specs round 1 → recover rc=1 disk-loss RuntimeError verbatim.
   (Two void probe versions caught and fixed before concluding.)
2. New tests 11/11 OK (construction 4 + interior 7); own 18-kill
   loop (own delays, 10–110% of fission wall + fine tail) → 0 torn,
   every landing converged (50-loop not re-run; stated, Note N3).
3. Interior arbitrariness with own params: MID_APPEND=4 on fuse →
   24/24 prefix parse + torn tail → recover/inspect rc=1 disk-loss
   (CLI + API); MID_SIDE_WRITE on a builder-never-used basename →
   old bytes + orphan → bare recover rc=0 converged.
4. Soundness (own AST sweep): open("w") only in atomic_write_text;
   open("a") only ledger + ROUTING mirror; zero .write_text in
   shipped code; ledger single-line JSON (no strict-prefix tear can
   parse; {}-prefix + glued-append edges fail loud); only os.replace
   in helper; pid/orphan analysis safe; readers strict (1 fail-safe
   skip → N1).
5. Wording audit: zero unproven-impossibility hits tree-wide;
   old-or-new/never-torn repetitions kill-scoped + evidenced
   (construction + routing + statistics + interior tests); every R3
   durability sentence carries process/power + no-fsync separation;
   no fsync call exists. Gaps → N1/N2.
6. Left-non-atomic probed: parent SIGKILLed mid-SST-leg (child
   confirmed alive) → re-run rc=0 TEST/champion/$0/conservation ok,
   no SST state in ledger; stale CONFIG → follow-up run rc=0,
   extends, conservation ok, nothing branches on tasks_run.
7. Regression: 9/9 + 7/7 + FULL 17/17 (beyond 3-spot minimum);
   calibrate 2.61x + MATCH re-observed; s002 41/41, s003 45/45,
   s004 45/45 before→after; zero in-tree writes. ../sst gap:
   COORDINATOR CLOSED (porcelain 0 @df78f42, direct).
8. Scope honesty: F1/F2 corrections verified live (targeted recover
   refuses; direct settle dissolves per contract — documented
   footgun); withdrawn ledger claim gone (quoted once as withdrawn);
   checkpoint extension fail-closed; carried diffs docstring-only;
   minihost re-pin verified; no expectation changed.

## Notes (record-only, accepted; dispositions)

- N1: resume.py:70 silently skips unparseable args (fail-safe →
  re-execute; safe direction; tears there impossible by atomicity)
  but CONSUMER.md:93's universal "torn file refuses loudly" is
  slightly overbroad. Disposition: narrow the cell or document the
  skip in the NEXT successor/docs pass (frozen tree untouched).
- N2: four carried "durable/durably" wordings (api.py:271,
  resume.py:14/158, SUCCESSOR-REPORT.md:181) lack the explicit
  no-fsync/power-loss disclaimer (tree-level cover exists in
  LIMITS-2). Disposition: narrow in the next docs pass.
- N3: statistical leg corroborated at reduced scale (18 kills, not
  50). Disposition: none required (builder 50 + lane 18 + interior
  determinism converge); future loops may re-run full 50.

## User-correction compliance (mid-build amendments)

- No-tear withdrawn for ledger (tested loud landing): verified live.
- Interior-write testing (both media): verified with own params.
- Process/power separation in every guarantee: audited (N2
  carves the only exceptions, covered at tree level).
- F2 red-first discipline: authenticated independently.
- Focused regression in normal layout: 11 tests in test_atomicity.py.

## Acceptance mapping (R3 brief + amendments)

F2 window closed (construction + statistics + interior): yes.
Doc precision (F1/F2, evidenced-or-narrowed): yes. Tests pass
(39+17+9+7 builder; 11+18-kill+9+7+17 lane): yes. No unproven
durability sentence: yes (N1/N2 narrowings owned). Independently
verified: yes. r1/r2 intact: yes (41/41, 45/45).

**R3 status: ACCEPTED. successor-004/ FROZEN as-verified (45/45).**
R3 = atomic side writes + write-interior coverage + ledger-claim
honesty + F1/F2 doc precision. Owned follow-ups: N1/N2 wording
narrowings (next docs pass), r3 release cut (when justified),
quarantine-transfer/multi-writer/disk-loss/cross-host (deferred),
U-branch (producers), Q5 (user).
