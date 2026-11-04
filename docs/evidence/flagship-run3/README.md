# flagship run 3 — VALID record: 9 NEW (harder, multi-part) tasks; first REAL escalations

Run: 2026-11-03T23:17Z-23:28Z, mode REAL, ladder laptop-muse -> claude-sonnet -> codex-main, fresh root, same gate as run 2 (gate.py.AS-RUN; run-1 pycache defect fixed).
Tasks: kit v2 (semver-bump-prerelease, packaging-licenseref-case, dateutil-tzstr-doy-rules, moreiter-peekable-slice, cachetools-cachedmethod-pickle, cachetools-unbound-keyword, cachetools-stacked-decorators, click-short-help-abbrev, click-pager-params). issue_text for each was authored by the coordinator from the fix commit message + failing-test bodies (observable behaviour, no code, no test names; leak check 0/491 gold lines, evidence/anima-bugtasks-20261103/issue-text-leak-check-20261103.txt). Offline fake-hand check on these 9 first: 27/27 (oracle accepted, noop and test-editing cheater rejected), realkit-check-v2-offline.log.

## Recorded result (counts from recorded attempts only)
N=9. Rung 0 (Muse, laptop): said-done 9/9, gate-verified 7/9, gate-rejected 2/9 (cachetools-unbound-keyword, click-short-help-abbrev), both rule target-tests (real assertion failures, NOT tests-untouched). Rung 1 (Claude Sonnet 5.5) fixed both (48.6 s and 57.5 s). Ladder-verified 9/9, exhausted 0, Codex rung not needed. decisions.jsonl chain: verify-log ok, 69 events. Rung-0 wall 105-478 s per task.
Failures checked by me: cachetools rung 0 -> "AssertionError: TypeError not raised" (hand bound a keyword receiver more broadly than the hidden test allows); click rung 0 -> assert 'Pick a fruit. 3...' == 'Pick a fruit.' (issue text states the digit-led sentence case explicitly). Hand summaries said "Fixed ..." in both.

## What this does support
On this set, 2 of 9 first-attempt "done" claims from a real hand were wrong by the project's own tests, caught by a deterministic gate that no hand can see or edit, and the next rung fixed both. Combined with run 2 (9/9 verified on 9 easier tasks): 18 tasks, 16 first-attempt verified, 2 caught.

## Caveats (state them wherever the number is used)
- Rung 1 is NOT a blind retry: its prompt contains the issue text plus the one-line failure digest from the gate (the failing assertion line), see rung1-prompt-example-click.txt. Do not say Claude "solved what Muse could not unaided".
- N=9 (+9), one run each, no variance estimate; one rung-0 hand family. Public repos: contamination cannot be excluded; hand tool calls and network use are not logged.
- Checks: no fix commit objects in any hand checkout; semver workspace holds 4 extra unreachable commits that are the hand's own git-stash WIP/index commits (parents = base, authored 23:21Z), not upstream history. Hand non-test diffs vs upstream fix: 0/9 identical, Jaccard 0.01-0.83 (semver 0.83, packaging 0.71: the issue texts pin exact outputs, so similar code is expected; see leak-and-similarity-check.txt).
- Issue texts are written to be behaviour specs, so these tasks measure fix implementation against a stated spec, not bug discovery. Not SWE-bench; no 10M claim; do not say the gate "strengthens" anything.
