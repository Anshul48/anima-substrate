# X3 run log

freeze: fresh FREEZE.json written
frozen_inputs.py sha256: 47634d68e05dfb49fc5776e401f78f8fd9dabafecff7521eb877a7ecec60fc45
checker self-check: known-good VALID q=4, known-bad INVALID (2 violations)

- freeze: FREEZE.json written; frozen_inputs sha=47634d68e05dfb49...
- checker self-check ok: good VALID q=4, bad INVALID (2 violations)
- [run1-C] run 1 arm C: start (assistance: none)
-   [run1-C] T1 done: VALID=True q=4 cbytes=1897 rounds=3
-   [run1-C] T2 crash injected: worker rc=-9 (real SIGKILL, mid-adaptation) -- recorded, reason: prereg T2
-   [run1-C] T2 done: VALID=True q=4 rework=0 esc=0 skipped=['formulate', 'adapt-propose'] cbytes=2193
-   [run1-C] T3 done: VALID=True q=5 lineage=True cbytes=761
- [run2-C] run 2 arm C: start (assistance: none)
-   [run2-C] T1 done: VALID=True q=4 cbytes=1897 rounds=3
-   [run2-C] T2 crash injected: worker rc=-9 (real SIGKILL, mid-adaptation) -- recorded, reason: prereg T2
-   [run2-C] T2 done: VALID=True q=4 rework=0 esc=0 skipped=['formulate', 'adapt-propose'] cbytes=2193
-   [run2-C] T3 done: VALID=True q=5 lineage=True cbytes=761
- [run3-C] run 3 arm C: start (assistance: none)
-   [run3-C] T1 done: VALID=True q=4 cbytes=1897 rounds=3
-   [run3-C] T2 crash injected: worker rc=-9 (real SIGKILL, mid-adaptation) -- recorded, reason: prereg T2
-   [run3-C] T2 done: VALID=True q=4 rework=0 esc=0 skipped=['formulate', 'adapt-propose'] cbytes=2193
-   [run3-C] T3 done: VALID=True q=5 lineage=True cbytes=761
- [run1-H] run 1 arm H: start (assistance: none)
-   [run1-H] T1 done: VALID=True q=4 cbytes=304 rounds=3
-   [run1-H] T2 crash injected: worker rc=-9 (real SIGKILL, mid-adaptation) -- recorded, reason: prereg T2
-   [run1-H] T2 done: VALID=True q=4 rework=0 esc=1 skipped=['formulate', 'adapt-propose'] cbytes=645
-   [run1-H] T3 done: VALID=True q=5 lineage=True cbytes=343
- [run2-H] run 2 arm H: start (assistance: none)
-   [run2-H] T1 done: VALID=True q=4 cbytes=304 rounds=3
-   [run2-H] T2 crash injected: worker rc=-9 (real SIGKILL, mid-adaptation) -- recorded, reason: prereg T2
-   [run2-H] T2 done: VALID=True q=4 rework=0 esc=1 skipped=['formulate', 'adapt-propose'] cbytes=645
-   [run2-H] T3 done: VALID=True q=5 lineage=True cbytes=343
- [run3-H] run 3 arm H: start (assistance: none)
-   [run3-H] T1 done: VALID=True q=4 cbytes=304 rounds=3
-   [run3-H] T2 crash injected: worker rc=-9 (real SIGKILL, mid-adaptation) -- recorded, reason: prereg T2
-   [run3-H] T2 done: VALID=True q=4 rework=0 esc=1 skipped=['formulate', 'adapt-propose'] cbytes=645
-   [run3-H] T3 done: VALID=True q=5 lineage=True cbytes=343
- [determinism-C] run 1 arm C: start (assistance: none)
-   [determinism-C] T1 done: VALID=True q=4 cbytes=1897 rounds=3
-   [determinism-C] T2 crash injected: worker rc=-9 (real SIGKILL, mid-adaptation) -- recorded, reason: prereg T2
-   [determinism-C] T2 done: VALID=True q=4 rework=0 esc=0 skipped=['formulate', 'adapt-propose'] cbytes=2193
-   [determinism-C] T3 done: VALID=True q=5 lineage=True cbytes=761
- determinism rerun arm C: MATCH (T1:same, T2:same, T3:same)

## Attempts (all recorded, incl. crashes/voids)
| run | arm | task | outcome | notes |
|---|---|---|---|---|
| run1-C | C | T1 | VALID=True q=4 |  |
| run1-C | C | T2 | VALID=True q=4 | worker rc=-9 (injected SIGKILL); resume skipped=['formulate', 'adapt-propose'] rework=0; 7 artifacts byte-identical |
| run1-C | C | T3 | VALID=True q=5 |  |
| run1-H | H | T1 | VALID=True q=4 |  |
| run1-H | H | T2 | VALID=True q=4 | worker rc=-9 (injected SIGKILL); resume skipped=['formulate', 'adapt-propose'] rework=0; 4 artifacts byte-identical |
| run1-H | H | T3 | VALID=True q=5 |  |
| run2-C | C | T1 | VALID=True q=4 |  |
| run2-C | C | T2 | VALID=True q=4 | worker rc=-9 (injected SIGKILL); resume skipped=['formulate', 'adapt-propose'] rework=0; 7 artifacts byte-identical |
| run2-C | C | T3 | VALID=True q=5 |  |
| run2-H | H | T1 | VALID=True q=4 |  |
| run2-H | H | T2 | VALID=True q=4 | worker rc=-9 (injected SIGKILL); resume skipped=['formulate', 'adapt-propose'] rework=0; 4 artifacts byte-identical |
| run2-H | H | T3 | VALID=True q=5 |  |
| run3-C | C | T1 | VALID=True q=4 |  |
| run3-C | C | T2 | VALID=True q=4 | worker rc=-9 (injected SIGKILL); resume skipped=['formulate', 'adapt-propose'] rework=0; 7 artifacts byte-identical |
| run3-C | C | T3 | VALID=True q=5 |  |
| run3-H | H | T1 | VALID=True q=4 |  |
| run3-H | H | T2 | VALID=True q=4 | worker rc=-9 (injected SIGKILL); resume skipped=['formulate', 'adapt-propose'] rework=0; 4 artifacts byte-identical |
| run3-H | H | T3 | VALID=True q=5 |  |

voids: none (every attempt completed; crashes were injected, resumed, and counted)
determinism rerun (arm C, fresh dir): MATCH -- T1:same, T2:same, T3:same
assistance: none in any run (fully scripted; no human-equivalent interventions)
