# PROVENANCE.md — successor-003 copy record

Source: `prototype/successor-002/` (NOT its `runs/` evidence, NOT
`.test-tmp/`).
Method: `cp -p` per file (bytes preserved), then per-file sha256
compared source-vs-copy: all 96 files IDENTICAL (source hashes also
match `successor-002/IDENTITY.sha256` for its 41 covered files).
Copy timestamp (UTC): 2026-10-04T14:40Z (file mtimes preserved from
source). `successor-002/` was not modified during or after the copy
(covered by this tree's `FROZEN-BASELINE.sha256`, which pins the whole
frozen r1 tree, plus the pre-work snapshot `/tmp/r1-frozen-pre-003.*`
— see EVIDENCE.md).

## Per-file sha256 at copy time (source == copy; top-level files)

| file | sha256 |
|---|---|
| api.py | 0465f5c72f1b6886fe1d3934f06de5c75bde1a148cb9f78d6b7be176c6881ecf |
| calibrate.py | 83e092181dafa5cd6124bff94c15ee20fcfd556b39da1e2cff6410b3aaee7544 |
| fusion.py | 07a7625135926653ad6febddca81e9435a13fba126855f507c0f9ba445267a33 |
| make_snapshot_manifest.py | 3f2f24eefaec08f1d8a0763f299238a68c3823a972d8d284e847c18db464ed99 |
| minihost.py | d01049a93b0e068e9e0384379cb26f509726f6a7ee659ff71dd0f0ec7bd4b206 |
| pipeline.py | 3fbe2df463400d3c8992c3359fee4ad5bdc1b604f884015dbb050039c0cee8de |
| release.py | 32f817a974141d8baaf68da869bf23a2ee499be8aeb85e9aeb7f4726468714d3 |
| resume.py | 6fa71154c0afc1a0d784ed65a3cdafe56d9b87476a708a4d0e6bf2baf188a300 |
| routing.py | f158ddacfa0e1d9130fe315cd21b16616e4cd3f2e081f9ccab8db7cc566013c4 |
| sched_checker.py | f4e63b0686f2b59e000928e0d255461ec1098a4cf4e7a3ca2efa56cd08cc7633 |
| sched_domain.py | 81a2041a57a1c7a65d80c524c765073eaf75b671ffcaefd0cfe7ccf7dbc0211c |
| sched_inputs.py | e92990fc478652b053b0e222bc7f2b728997e93ffa20b54d0f6102a88f71626b |
| sst_leg.py | ff7de2b7a226318c037c21eb8c0704e6c876f47694752f4a3578b4ced9f0e448 |
| successor_demo.py | 57c4f73980e30de8feec277d446946c53fb7f8339ddfec7e031da99290a480c3 |
| test_conformance.py | 480a2e1d099ea71f2524063204b13f4919bbc8c3dd5afe8d0128ac55dd2c6afb |
| test_fission.py | c3902cd43622e4b23b704ec9824e4b9fb11eb6b8110bc95fb657b1df7379fd61 |
| test_successor.py | d6187329c1f40de03b3c72f972abf8ac569684187b3a522226fa3c71578fadba |
| verify_snapshot.py | 205a87ad64f440ca220288ce721994feeb86299fc62180f3a9f2918ea1ed692b |
| CONSUMER.md | 3bf7a8012bbeb6f10a46639fb7ac57b6cd377feadebab71982a01a805fce6fd9 |
| CONTRACT-GAPS.md | a35c6c08631501940046252a4ebbd82794021dc4c9cfaacaf73230ee0d5e8b1c |
| FROZEN-BASELINE.sha256 | 9945084835712462b3144124872558aa7015d8e0e5040aceacddbcac100b8e9a |
| LIMITS.md | 5ad649fd10204acbe02659239a543a5c9dee1e38489a20aaf2b6cc34910a576f |
| OBLIGATIONS.md | 3424f34177d0209cb3efc101404cdaf333076807a44536b0c0f8d15bad907ad0 |
| ORG-OPS.md | 231439bcffbd268bc22f85d8b6cd194cd482cbc8009f2fa904d8fc5974f26073 |
| PROVENANCE.md | 1401c1471c009452e7480bad93cf8fc27e434aacb116065c25ffd6cd2fa4b12e |
| REPORT.md | 9d15c16f67f5576d094bac5622fecec366756ac258852097c253680f3600f0bc |
| REPRODUCE.md | 1e81f993a692a1d53b8b0d19d6f358300087aa32c8cd913ac300c2f6b926e837 |
| SEPARATION-PATHS.md | 4f2f2bac5e1abc89ed652528bd4cfca1b93e725ee5350e99e9225914af1da854 |
| SUCCESSOR-REPORT.md | eecfd3b5cfb60218ed8393be9bbe0fe195c13aa3d40993f1c6f74f557ffefb3c |
| VENDORING.md | 73804a2645dddc8e19d636454ae42ecb60fa78c3b1495f1a4895fc5e58ade8bd |

Plus `accept/` (8 files) and `vendor/` (57 files: 3 docs + 54-file
SST snapshot), all identical at copy time (see this tree's
`IDENTITY.sha256` for the carried accept/vendor doc hashes; the
snapshot still verifies `MATCH hash=5f1f3789...`).

Excluded: `successor-002/runs/` (evidence outputs, not source),
`successor-002/.test-tmp/` (scratch; absent at copy time).

## Post-copy evolution (R1: atomic settle + interruption boundaries)

- `FROZEN-BASELINE.sha256` REPLACED: 3640 lines = the 1878
  carried lines (re-verified OK) + 1762 new lines pinning the frozen
  r1 tree (`successor-002/` incl. its `runs/` evidence,
  `release-20261004/`) plus neighboring tracks (closeout / evidence
  / windows-check / successor-contract / w0-probes.sh /
  CONTINUING-PROGRAMME.md; live sibling dir `L1-transfer/`
  excluded — see EVIDENCE.md §Frozen verification).
- `minihost.py`: + `check_settleable` (read-only settle rehearsal);
  `settle_grants` pre-validates BEFORE the first `grant_return`
  (refusal = `deny` only, zero partial returns); +
  test-only crash hooks (`SUBSTRATE_CRASH_AFTER_APPENDS`,
  `SUBSTRATE_CRASH_AT`; unset = zero behavior change; imports still
  stdlib-only). Re-pinned in `test_successor.py`
  (`a2b7ed59...05d3`; base `d01049a9...b206` above).
- `routing.py`: `finish_worlds` is two-phase (validate whole batch:
  ledger conserves + every world settleable — then execute), so
  refusal = `ContractViolation` with ZERO partial dissolves (only a
  `deny` entry); `CODE_REF` + lineage default rebranded.
- `fusion.py`: `fuse_worlds`/`fission_worlds` pre-validate
  settleability of every world they will dissolve before any host
  mutation (extends the no-partial-effects-on-rejection promise).
- `recover.py` (NEW): ledger forensics (`ledger_index`,
  `detect_partial_*`) + idempotent completion (`complete_fusion`
  with grant restoration, `complete_fission` with operator-supplied
  partition/names/presets, birth completion, `worlds.json` spec
  repair). Quarantine partials are detected with explicit operator
  steps, never auto-completed.
- `api.py`: + `recover_op` (repair + complete + targeted settle;
  default settles NOTHING); `settle_op` docstring notes atomicity;
  pre-spec crash points in `fuse_op`/`fission_op`; `RELEASE`
  rebranded.
- `release.py`: + `ops recover` (`--worlds/--reason/--fission/
  --left/--right/--partition/--left-preset/--right-preset`).
- `test_atomicity.py` (NEW): 27 tests — refusal atomicity (7),
  every-boundary kill matrices for settle/fuse/fission through the
  CLI + wrong-partition refusal (4), pre-spec kills (2), repeated
  kills incl. kill-during-recovery + full-flow-with-kills (5), real
  SIGKILLs (3), forensics/refusal paths (6).
- `test_successor.py`: minihost re-pin (above) + rebrand only; all 17
  tests pass unchanged. `test_conformance.py`, `test_fission.py`:
  rebrand only (9/9, 7/7 pass).
- `pipeline.py`, `resume.py`, `sched_*.py`, `sst_leg.py`,
  `verify_snapshot.py`, `calibrate.py`, `make_snapshot_manifest.py`,
  `successor_demo.py`: docstring/print/path rebrand only (clean-path
  behavior unchanged; demo EVIDENCE structurally identical to r1 —
  see EVIDENCE.md).
- `SUCCESSOR-REPORT.md`, `REPORT.md`: kept byte-identical as the
  successor-001/002 base records. `OBLIGATIONS.md`, `VENDORING.md`,
  `CONTRACT-GAPS.md`, `SEPARATION-PATHS.md`: base text kept + a short
  successor-003 carry note each. `REPRODUCE.md` / `LIMITS.md` /
  `CONSUMER.md` / `ORG-OPS.md`: updated for successor-003 (copy-time
  hashes above are the before record). `accept/`: FROZEN, byte-
  identical (inputs never edited to make a run pass).
- New docs: `INTERRUPTION-BOUNDARIES.md` (append maps, partial states,
  recovery + operator-repair procedures), `EVIDENCE.md` (commands,
  test output, kill-exercise logs, accept comparison).
