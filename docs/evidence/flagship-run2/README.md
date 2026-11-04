# flagship run 2 — VALID record (replaces run 1, which is INVALID: evidence/flagship-run1-INVALID-pycache-20261103/)

Run: 2026-11-03T21:30Z–21:39Z, mode REAL, 9 tasks of the anima-bugtasks kit (dateutil excluded by task-excludes.json), ladder laptop-muse -> claude-sonnet -> codex-main, parallel-rung0 6.
Command: FLAGSHIP_REAL=1 ./flagship/flagship.py run --tasks all --ladder laptop-muse,claude-sonnet,codex-main --root ./real-root2 --out ./real-out2 --parallel-rung0 6
Gate as run: gate.py.AS-RUN (sha256 0ac9c39c7e93f907...) = run-1 gate + fix "ignore plain __pycache__ dirs under protected roots" (selftest 63/63, realkit-check 27/27 fake hands incl. noop and test-editing cheater caught, --plant-fault exit 1).

## Recorded result (counts from recorded attempts only)
N=9; rung-0 hand = laptop-muse (Muse account 'muse'); said-done 9/9; gate-verified at rung 0 9/9; escalations 0; exhausted 0. decisions.jsonl hash chain: verify-log ok, 55 events (verify-log.out).
Wall seconds per task at rung 0: 65-397 (SUMMARY.md). Gate = tests-untouched + target-tests via the kit's own gate.sh on a private copy.

## Checks I made by execution
- Hand checkouts contain only the base commit (1 commit in object store, no refs, no remotes); the FIX commit object is absent in all 9.
- Non-test diff of each hand vs the upstream fix diff: 2/9 line-identical (humanize-naturaldelta-years 1 line, moreiter-chunked-even 4 lines; trivial fixes), 7/9 differ (Jaccard 0.00-0.56). No sign of wholesale copying.

## Limits (state them wherever the number is used)
- Public upstream repos and real upstream fix commits: training-data contamination CANNOT be excluded. Hand logs do not record tool calls, so network/web lookups by the hand are neither shown nor excluded.
- N=9, one hand per task, one run. No variance estimate. Muse rung 0 passing 9/9 means there is NO 'said done but not verified' gap on this set: do NOT claim the gate caught false-done claims from real hands. The only gate-catches evidence is the synthetic fake-hand table (noop / cheater / oracle, realkit-check), labelled synthetic.
- Run 1 (invalid) showed the verification infrastructure itself needs verification: its gate rejected valid work (10/19 attempts) because of __pycache__. That is a true, citable finding about the gate, not a capability number.
- Not a SWE-bench result; do not use that label. Not evidence about 10M-scale anything.
