# L1 VERIFICATION — independent acceptance record

- Verdict: **ACCEPT-WITH-NOTES** (negative stands, method sound).
- Verifier: independent lane (read-only; wrote nothing; stateless re-runs only).
- Date: 2026-10-04. Builder files untouched by verification.

## Independent reproduction (from raw ledgers/artifacts, not harness summaries)

| phase | runs | entries | invokes | VALID |
|---|---|---|---|---|
| extract | 12 | 846 | 168 | 12 |
| transfer | 12 | 720 | 156 | 12 |
| baseline | 12 | 972 | 180 | 12 |

P1 FAIL (12/12 `*-reuse`), P2 PASS (12/12 both), P3 FAIL
(1566 vs 972 entries; 324 vs 180 invokes), secondary FAIL (tie 5/8,
all 8 ground-truth lanes re-derived via stateless `explain-route`
re-runs, matching exactly), calibration 36/36 byte-exact, 0 nonzero-rc
calls. Pins 19/19 match. r1 41/41 OK, 0 non-OK lines. Held-out
isolation: 0 TE refs in extract-phase artifacts; `cmd_extract` loops
TRAIN only; probes pre-prereg with throwaway IDs only.

## Note A (record-only, accepted)

`PREREG.md` mtime (14:22:51) post-dates the verdict because of the
declared TE-05 pin amendment, so the "PREREG.md 14:14:50" order claim
in EVIDENCE §2 is no longer mtime-verifiable and the original PREREG
bytes are unrecoverable (no git). Pre-specification credibility rests
on the unamended `DESIGN.md` anchor (14:14:32, exact P1-FAIL/P2-PASS/
P3-FAIL prediction) plus the wrong secondary guess (anti-post-hoc
signal). Residual single-host-mtime uncertainty is inherent and
recorded, not resolved. Lesson for L2+: commit prereg bytes to an
append-only, externally-anchored log (or git) before execution.

## Note B (record-only, accepted)

Coded P2 (`transfer==baseline==n`) is stricter than PREREG's literal
"equal rates" and ignores per-task failure correspondence; OVERALL
folds a calibration void into NEGATIVE rather than a separate VOID
label. Immaterial on observed data (12/12 both, guard OK). Lesson for
L2+: preregister the exact coded predicates verbatim.

## Acceptance mapping (CONTINUING-PROGRAMME L1)

Design+prereg before execution: credible (Note A). Held-out isolation:
yes. Cold competent baseline via same consumer interfaces: yes (fixed
split-pair, zero training knowledge). r1 untouched: yes. Honest
negative with sound method: yes. Independently verified: yes (this file
+ verifier report in coordinator session log).

**L1 status: ACCEPTED as a clean informative negative.**
Finding: r1's fixed follow-up pipelines leave no task-conditional
recipe surface (60 vs 81 entries at every size); transfer needs a host
with content-sensitive path costs or a learnable lane before re-test.
