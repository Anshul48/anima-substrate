# L1 PREREGISTRATION — frozen BEFORE execution

- Preregistered: 2026-10-04T14:14:10Z
- DESIGN.md written at the same stamp; task files generated
  2026-10-04T14:14Z (hashes below); harness runs AFTER this file.
- Order proof: file mtimes + embedded stamps + run-log timestamps in
  EVIDENCE.md. No L1-TR-*/L1-TE-* task was executed before this stamp
  (only throwaway PROBE-* tasks ran, §DESIGN-2).

## 1. Frozen inputs (sha256)

Generator `gen_tasks.py`:
`e579da25c723d007a771f31d74023d4c9394aeeead048650edad98bf1747b7eb`

Train tasks (`tasks/`):
- L1-TR-01.json `e2160b9e16fce6ff2974957b983a64986f019364aabb3e01ba056aa42b840e14`
- L1-TR-02.json `deac04f6524b6cfa10e474781bfa73802d09e30fd41f46b9c86d04fb7ec0add7`
- L1-TR-03.json `2e4c7d2702c289b147253ec51b1ff1948349a9ecafd0602724b96fe0b7140dac`
- L1-TR-04.json `3c767c415a0086cd6955b03d16d24d42816b10593fadb9dcde6f3a8598cf54a8`
- L1-TR-05.json `28e8e99fdf100d43c6d63db3c944e761ca26f64c4c5859983213d96cced90760`
- L1-TR-06.json `ba3b619e4b8d8089f59000e3e13440a7149c581caf7ea7b871051807bc81f9fb`

Held-out tasks (`tasks/`, NEVER executed before the transfer test):
- L1-TE-01.json `22c859faf22ea79d44b46ed8074ddf08d25daa4ac3b629b809ea5a9249b404d5`
- L1-TE-02.json `b2e0728b6fc287dbeb6aa97071968bdf7956125d9b6d2bf810d1c6e4756b887a`
- L1-TE-03.json `b19ddcd609ea2a11d1a3ec4edc0e7b7aafe0dec90efca8496be59128f43d7711`
- L1-TE-04.json `d19ce758716bde2b056401209ae96484d1f82d176af916cfc07147e4eb425429`
- L1-TE-05.json `0f30a3d05d49e90cd591baf0d2e081d6571e1c90ef3e2b6905ac0be86c78b934`
- L1-TE-06.json `8e470921f69dd03857187844a1d990a9d3adbb0bb7ae42857491834920f5e2bc`
- L1-TE-07.json `32bb53e5feff5c9dda4432478eb0568be4dfca2fa57a2cd2cac2df7654a1b459`
- L1-TE-08.json `d974c7eb979865602aaaa2b450880360b883e89a134cc28077b8f8372f345cbe`
- L1-TE-09.json `13630ef6981919fc3ed159220f1e99cad4d6dad65632d04e1cb1c9e958bb9396`
- L1-TE-10.json `6b56a1d2081ceaf3d2a740828887ebb21915a9bf5e2c7d33b3e380021de4f7d8`
- L1-TE-11.json `0c14a29eb8595e41edb57cae2023daed1f319be9cfbedb09b1abc4aab18701ba`
- L1-TE-12.json `ebef2ea5534439d67a08f6fbed4f42d2d3ca9edb45d5497b7ed9795bd782bd26`

Secondary descriptors `tasks/secondary-descriptors.json`:
`5d13a5d6f37a4cef2e2f5055aa2a2d8d39b3c629ac76b02fd28a5786dd01fe1f`

r1 consumed: `prototype/successor-002/`, `IDENTITY.sha256` 41/41 OK at
2026-10-04T14:12Z, via `release.py` CLI only. r1 + neighbors read-only.

Amendment 2026-10-04T14:23Z (transcription typo only, post-verdict):
the L1-TE-05 pin above originally contained a spurious `2d`
(`...baf0d2e2d081...`); corrected to `...baf0d2e081...`. The task FILE
never changed — its bytes hash identically at generation time
(14:13:58Z log) and now. No threshold, input, or procedure altered.

## 2. Primary pass/fail (headline verdict)

Cost unit: ledger entries (primary); invokes (secondary, must agree in
direction for a PASS). Success: VALID from solution artifacts.

- P1 (task-conditional content): the FROZEN recipe's held-out path
  choices differ from the always-reuse fixed path on ≥2 test tasks AND
  differ from the always-split-pair fixed path on ≥2 test tasks.
  Rationale: a recipe identical to a fixed path transfers no
  task-conditional knowledge.
- P2 (success parity): VALID rate on the 12 held-out tasks is EQUAL in
  recipe arm and baseline arm (expected 12/12 both). Any task failing
  in either arm is preserved and reported; differential failure FAILS P2.
- P3 (net gain, acquisition charged): (acquisition ledger entries +
  recipe-arm held-out ledger entries) STRICTLY LESS THAN (baseline-arm
  held-out ledger entries), AND the same strict inequality in invokes.
- OVERALL: PASS = P1 ∧ P2 ∧ P3. Anything else = NEGATIVE (a complete,
  publishable result). Predicted at prereg time: P1 FAIL, P2 PASS,
  P3 FAIL → OVERALL NEGATIVE (no tuning to force a positive; the
  verdict rule above is mechanical).

Calibration guard: S1/S2 setup observations must reproduce EXPECTED.json
lanes + bytes (S1 central 655/0, S2 local 310/500) on every setup run;
any deviation voids the run batch (method failure, not a transfer result).

## 3. Secondary (routing prediction; advisory, non-binding on headline)

- S-threshold: extracted-rule accuracy on the 8 frozen descriptors
  STRICTLY EXCEEDS the always-central baseline accuracy. Ground truth =
  r1 `explain-route`. Reported as predictive transfer ONLY — no
  performance-gain claim attaches (bytes need execution).
- Design-time expectation: extraction sees only (2,F)→central and
  (4,T)→local, so several rules fit; the preregistered tie-break
  (fewest literals, lexicographic) picks `local iff split`, predicting
  7/8 vs baseline 5/8 → S-PASS expected. The mechanical rule, not this
  expectation, governs.

## 4. Analysis rules (frozen)

- No task replacement, no re-rolls, no re-runs to "fix" failures.
  First-run results stand; harness bugs may be fixed ONLY before the
  transfer test starts, with the fix logged (extraction re-run after a
  harness fix is allowed; transfer/baseline runs are single-shot).
- Recipe frozen after extraction (`recipe.json` + sha256 in EVIDENCE.md);
  transfer test consumes it read-only.
- All commands, raw logs, ledger hashes preserved under
  `runs/` + `logs/`.
