# PROVENANCE.md — successor-002 copy record

Source: `prototype/successor-001/` (NOT its `runs/` evidence).
Method: `cp -p` per file (bytes preserved), then per-file sha256
compared source-vs-copy: all IDENTICAL (hashes also match the
coordinator-recorded identity in
`closeout-20261004/SUCCESSOR-VERIFICATION.md`).
Copy timestamp (UTC): 2026-10-04T09:53Z (file mtimes preserved from source).
`successor-001/` was not modified during or after the copy (covered by
the extended `FROZEN-BASELINE.sha256`, which now includes it).

## Per-file sha256 at copy time (source == copy)

| file | sha256 |
|---|---|
| fusion.py | 170d47f36185bd5c6e4eca9244d21533fba214a2a3a7488c854c747f056768b1 |
| minihost.py | d01049a93b0e068e9e0384379cb26f509726f6a7ee659ff71dd0f0ec7bd4b206 |
| pipeline.py | 292c7f15c0f013aee1c851d93c64c4dead4915727e421ac751b49230889d7334 |
| resume.py | 10d3eb220c58b323f02caa77d9f7bc10a2e6ff65c11a067ae286d85f578f6699 |
| routing.py | 08fa3cdbf5c5fad0317cb56297a7b3b32f1c26fe8bc3fd477f245762cc356ce9 |
| sched_checker.py | 5bf9f74fc6d947c659a1cd1ac41c1e46764cc73c111b109977ff9de06d2f8640 |
| sched_domain.py | 44e66bdbbf861135ad85d5fa9ac30ea47f4d1c77f6181176c60a677238edb523 |
| sched_inputs.py | 22e8e9acfa721e23054e938ce6c0750273962e9d111c16abd9ad8f566ca84171 |
| sst_leg.py | 4932422fb2b11425342e19d22a9f4b45e67b75f6ab441bd9bafdde1915e2031e |
| successor_demo.py | a47f6cca6bcb40023928c5456103c3ae39d1b916d9b4160aa95f302af274b8ca |
| test_successor.py | e5daea491a5d9c8be7514296cd19e1ee531ee1ae46c40b4eae2ba544dd22f408 |
| LIMITS.md | 77001f45e32b823085e488405a72431c0b415bb0f7686967414565c4d8c72d75 |
| OBLIGATIONS.md | 62297221c1eec3daaa8996112fa536ed7e801d607c5e478a9d09b7c10426254b |
| REPRODUCE.md | 029414335c46ac44ef36a92d306aa4897a8dc6c32bf5db3dd78371950308e4d3 |
| SUCCESSOR-REPORT.md | eecfd3b5cfb60218ed8393be9bbe0fe195c13aa3d40993f1c6f74f557ffefb3c |
| VENDORING.md | caa81d2c8128a0d5cf999cbf2270fec897a3343464cbd8afd0b72abd57b6384c |
| FROZEN-BASELINE.sha256 | dd484e42aed07adf8c73b0a9e6230287f378604c588c933b4fff2eb9b6a1ba5d |

Excluded: `successor-001/runs/` (evidence outputs, not source).

## Post-copy evolution (intended; this file is the before-record)

- `FROZEN-BASELINE.sha256` replaced by the extended baseline
  (adds `successor-001/` minus `runs/` and `.test-tmp/`).
- `fusion.py`: + fission (`fission_worlds`); docstring rebrand.
- `sst_leg.py`: repointed at `vendor/sst-snapshot/` (no `../sst`
  references at runtime); pin posture replaced by snapshot verification.
- `successor_demo.py`: + fission leg (S6); rebrand.
- `test_successor.py`: SST test repointed at the snapshot; rebrand.
- `routing.py`: `CODE_REF` + lineage default rebranded to successor-002.
- `pipeline.py`, `resume.py`, `sched_*.py`: docstring rebrand only.
- `minihost.py`: UNTOUCHED (byte-pinned vendored host; sha above holds).
- `SUCCESSOR-REPORT.md`: kept byte-identical as the successor-001
  base record. `OBLIGATIONS.md` / `VENDORING.md`: base text kept + a
  short successor-002 carry note each. `REPRODUCE.md` / `LIMITS.md`:
  REWRITTEN for successor-002 (copy-time hashes above are the before
  record). `REPORT.md` is the successor-002 report.
- New files: see `IDENTITY.sha256` + `REPORT.md`.
