# PROVENANCE.md — successor-005 copy record

Source: `prototype/successor-004/` (NOT its `runs/` evidence, NOT
`.test-tmp/`).
Method: per-file copy, then per-file sha256 compared source-vs-copy:
all 100 files IDENTICAL (normalized src-vs-dst diff EMPTY; copy list +
hashes recorded at copy time).
Copy timestamp (UTC): 2026-10-05T01:38Z (pre-work marker + frozen
snapshot `/tmp/s5-frozen-pre-005.sha256`, since installed byte-exact as
this tree's `FROZEN-BASELINE.sha256`).
`successor-004/` was not modified during or after the copy (covered by
this tree's `FROZEN-BASELINE.sha256` plus the 45/45 IDENTITY re-check;
see EVIDENCE.md).

## Per-file sha256 at copy time (source == copy; top-level files)

| file | sha256 |
|---|---|
| CONSUMER.md | cc24fe61c91a1a68b76c2f4fad4bdf1fc155fcefefe21117b664325622e07230 |
| CONTRACT-GAPS.md | 459c6bbe2a08d52e5170f74aa2b1cd301aea532fd8657d8711eb2f758ac0bc70 |
| EVIDENCE.md | 84ca80ae62bc8febd11e50188c74fe55261217cfb24a3107a190dddc90309fa1 |
| INTERRUPTION-BOUNDARIES.md | 533434f700f13cccb36b9bea022ea4534ee212b2646ff665d33e7eb23b566335 |
| LIMITS.md | 4f7f571267ed61de8d9f053b358c26e2bc62a8a96fb85e3f7693f5cbdd3a75ea |
| OBLIGATIONS.md | 21082757ce4a124aa45a68961bd03adca960015213bf095caedd38a39a660f3f |
| ORG-OPS.md | 78367329196c5349c8a80633fca153d38eb9d3500ed5c6d50e2c87030eaaf9e0 |
| PROVENANCE.md | aa2e38095376415ec1865cf060cf9a747620bdaa334110b23d6506db4870b5b2 |
| REPORT.md | 9d15c16f67f5576d094bac5622fecec366756ac258852097c253680f3600f0bc |
| REPRODUCE.md | 26575cdedfd5d3edae3ff13ef141e9729771e54bf38d6362467dfdf67c71caeb |
| SEPARATION-PATHS.md | db6e3349d2544888fec7db5e2a1425fd268e52aa1f70e83ad07df448f2d0da21 |
| SUCCESSOR-REPORT.md | eecfd3b5cfb60218ed8393be9bbe0fe195c13aa3d40993f1c6f74f557ffefb3c |
| VENDORING.md | e19f2c70244804063fa6bf3bd10f38403ff5eef39422aa0783eb9ff2d68cf0c5 |
| api.py | 66ccfc4dd920b700f65ebf85d5b592b409c4c05ad7a6eca2156a5aa859f32dda |
| calibrate.py | 5f22d9b6f024e1eb7a64cbb7a3080bf5582357985423f96fd9d50c8f3075d541 |
| fusion.py | a2211a5de56c9553edac2dbe09c73c3ceb842549429bfb9b56f0e821b3031910 |
| make_snapshot_manifest.py | be937a7a7a9a00099613bfca95b94fcc4a05ca96e4d18e5c5bae0aac68fc07e9 |
| minihost.py | 8551ed92346d55a1624cfca815ce3cce7c43acdf3bcc190fadf2096c233d5757 |
| pipeline.py | b5f6ed5f4d9430305ed3b00d5b4b0ed4892644906618943ef05d594a5d7d5dd8 |
| recover.py | 5cce4e444d3f0b25c475673477bb7e53683a329386b61b13140008b6c1b8711b |
| release.py | 6a42c4b3822ff4660ad9776bf19ca3cc5077c9ec5d7285027f19b8fec7eebe96 |
| resume.py | f07111cd9dc33031bfb8b31e9cb668b1fde15b56d42205047c19892ee2f4bc5a |
| routing.py | db4074e1d2a0f4548a5228892a217bd63ae7364b493eeac7ff646fb4fda85639 |
| sched_checker.py | 465f8edc99cfd7b76d78a034c15acc1385e2e7777100be37ab8cd394ee18f244 |
| sched_domain.py | 55a4ad9cdfef35afad33fd9592726e06f35b6f330cfcbdd09a282c7a72bb8a6f |
| sched_inputs.py | b3bdbfafe8d97bf32d619fc250a7461f998d01c3eaa17a73ac98078f8c07f15b |
| sst_leg.py | 24d03c270fb5a148ace8d7088ce590ecb1bf5d6e3aefc52d31b31e02796431d1 |
| successor_demo.py | dc65122715ada26245068627ed3731058075fdb776942a56a3db68a11260bcef |
| test_atomicity.py | aad3d0371f7d5ec5faa7b58728fc7c4cf6e3d549a66ee5cf477f4c8080fbcd6e |
| test_conformance.py | d479ad1d5e3c25e1c4e1392ca0a95aa93e44cac373ab5a84ea384b8bfb483fd4 |
| test_fission.py | 9796b754ae7ec2fce0532927a54f74eab0d3fa5f44b5c1afd247891f3154f394 |
| test_successor.py | 3dcd759d9884f2ea7611f2388f48a85b7412ad66ebf493dbcf8454c797f6fc9f |
| verify_snapshot.py | 616d3c9c8db51541f6e8827d0772051c5796431d46824c797354b96f5396c335 |

Plus `accept/` (8 files) and `vendor/` (57 files: 3 docs + 54-file
SST snapshot), all identical at copy time (the snapshot still verifies
`MATCH hash=5f1f3789...`), plus the two carried manifests
(`IDENTITY.sha256`, `FROZEN-BASELINE.sha256` — both since replaced).

Excluded: `successor-004/runs/` (evidence outputs, not source),
`successor-004/.test-tmp/` (scratch; empty at copy time).

## Post-copy evolution (S5: bounded procedure participant + vehicle)

Builder delta (design: `programme-20261004/S5-design/S5-DESIGN.md`):

- NEW `procedure.py`: the accountable executor (advertise / run /
  recover, P1–P15 envelope, L1–L5 interruption classes, change flow).
- NEW `test_procedure.py`: 57 tests (advertise + construction, gates,
  accountability, interruption incl. real SIGKILLs, recovery/change,
  wording audit; 55 builder + P9 orphan-race regression + cross-key
  tightness pin).
- NEW `vehicle/`: `relcheck/` bundle (`bin/relcheck.py`, `pins.json`,
  `MANIFEST.json`) + `relcheck-pins.json` wrapper +
  `verdict_relcheck.py` (independent checker) + `direct_relcheck.py`
  (direct baseline) + `make_vehicle_pins.py` (pin generator) +
  `s5-readiness-check.py` (readiness aid) + `README.md`.
- `minihost.py`: proc-ledger support (`proc_begin` / `proc.exec`
  invokes, adopt paths) + `atomic_write_bytes`; carried writes keep
  R3 temp+replace routing.
- `release.py` / `api.py` / `recover.py`: `create-proc-world` /
  `run-procedure` / proc-aware `recover` (+ `nothing-to-do`,
  adopted, re-runnable classes); carried ops untouched.
- `test_successor.py`: S5 re-pin + S5 coverage (17 tests).
- Docs: CONSUMER §8 (accountable executor), LIMITS items 12–14,
  INTERRUPTION-BOUNDARIES §S5 (L1–L5), ORG-OPS proc clauses,
  REPRODUCE procedure/vehicle sections, N1/N2 narrowings.
- `SUCCESSOR-REPORT.md`, `REPORT.md`: kept byte-identical as the base
  records. `accept/` (8), `vendor/` (57): byte-identical.

Verification fixes (coordinator, red-first; see EVIDENCE.md):

- `test_successor.py`: S5 re-pin (`4cb3c1dd...095a4`).
- `procedure.py`: one wording-bounder spelling; P9 key-subtree
  exclusion (orphan-race fix).
- `test_procedure.py`: +P9 regression test; +cross-key tightness
  pin; generated-manifest carve-out in `_scoped_files` (wording
  scan set).
- `vehicle/make_vehicle_pins.py`: venv interpreter resolution +
  per-step `env_extra` record.
- `vehicle/direct_relcheck.py`: `SST_VENV_PY` forwarding.
- Record-only: two stale `56` procedure counts → loader-verified 55.

Throwaway split (never shipped as release): `s5-readiness-check.py`
and `direct_relcheck.py` are readiness aids; U-execute owns its own
direct arm. `EVIDENCE.md`: rewritten (S5 evidence + carried R3
record). `IDENTITY.sha256` + `FROZEN-BASELINE.sha256`: regenerated.
