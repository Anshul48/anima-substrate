# Acceptance-to-Identity Tie (w1-harden closeout, 2026-10-04)

Candidate: `substrate/prototype/w1-harden/` (20 files).
Identity: `IDENTITY.json` / `IDENTITY.sha256` (same directory as this file).

## Non-backdating statement

The hashes in `IDENTITY.*` were computed at closeout from the live files.
H1 (builder acceptance) and H2 (independent verification) runs did NOT record
per-file hashes of the candidate they executed; they recorded behavior
(counts, exit codes, ledger shapes, champion names, wall times).
Therefore no hash can retroactively prove which exact bytes H1/H2 executed.

What IS established:

1. **Continuity of the tree.** H1/H2 both verified `w1/` 7/7 hashes and SST
   14/14 module hashes before and after their runs, and H2 verified
   `w1-harden/` contained exactly the reported files with no `__pycache__`
   or artifacts. No write to `w1-harden/` source files occurred between H1,
   H2, coordinator re-runs, and closeout except the three documented
   record-only corrections (RUN-REPORT §8 item 7: N1–N3, none behavioral).
2. **Independent re-execution.** The coordinator re-ran the full acceptance
   (33/33 × 3, stub demo, SST-TEST demo, SIGKILL recovery) fresh from the
   candidate after the N1–N3 corrections. The Windows architect hashed all
   20 files at the start of the Windows check; those hashes match
   `IDENTITY.json` exactly (see WINDOWS-INCORPORATION.md).
3. **Reproducibility from these bytes.** Any party can re-run REPRODUCE.md
   against the hashed bytes now. That is the operative tie: the evidence
   describes behavior reproducible from THIS identity, not behavior
   cryptographically bound to the original run.

## Evidence map (behavior → where to re-run)

| Claim | Preserved evidence | Re-run from this identity |
|---|---|---|
| 33/33 suites ×3 | `evidence-20261004/h1-acceptance/`, `h2-verification/` | REPRODUCE.md §1 |
| Stub demo 40 entries, $0 | same + ledgers in h1/h2 dirs | REPRODUCE.md §2 |
| SST-TEST demo, $0 | same (dirty-with-hashes SST) | REPRODUCE.md §3 |
| SIGKILL resume, 0 re-invokes | `h1-acceptance/evidence/`, `h2-verification/evidence/` | REPRODUCE.md §4 |
| Settle zero-stranded | ledgers + replay excerpts | REPRODUCE.md §5 |
| F3 mutation probe genuine | `h2-verification/mut/` | VERIFICATION.md §7 |
| X1/X2/X1G/X1H findings | `evidence-20261004/x1,x2,x1g,x1h,x12-preregs/` | each dir's RUN-LOG/RESULT |
| H0 baseline numbers | `evidence-20261004/h0-baseline/run.log` | `h0_run.py` (archived) |
| W1 repro 19/19 | `evidence-20261004/w1-repro/` | frozen w1 copy + logs |

## What remains honestly weaker

- H1/H2 ran against pre-closeout bytes that also included the N1–N3
  record corrections; source `.py` behavior is unchanged by those
  corrections (docs + FREEZE.json string only), but the claim rests on
  diff inspection, not on hash equality of run-time bytes.
- The Windows candidate is a SEPARATE 12-file identity (2 files patched);
  its evidence ties to `windows-check-20261004/CANDIDATE-SHA256.json`,
  not to `IDENTITY.json`.
