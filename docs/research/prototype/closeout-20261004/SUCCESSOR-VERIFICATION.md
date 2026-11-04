# Successor-001 coordinator verification (2026-10-04, direct — no new lanes)

Candidate: `prototype/successor-001/` (16 files + `runs/` evidence).
Builder: successor-build worker. Verifier: coordinator, fresh runs from
repo root, behavior checked against builder's SUCCESSOR-REPORT.md line
by line. Verdict: **ACCEPTED** with the SST staging-pin correction below
(which the builder already reported honestly and handled loudly).

## Identity (coordinator-hashed)

- fusion.py 170d47f36185bd5c6e4eca9244d21533fba214a2a3a7488c854c747f056768b1
- minihost.py d01049a93b0e068e9e0384379cb26f509726f6a7ee659ff71dd0f0ec7bd4b206 (= reuse-demo, = x3 vendored copy)
- pipeline.py 292c7f15c0f013aee1c851d93c64c4dead4915727e421ac751b49230889d7334
- resume.py 10d3eb220c58b323f02caa77d9f7bc10a2e6ff65c11a067ae286d85f578f6699
- routing.py 08fa3cdbf5c5fad0317cb56297a7b3b32f1c26fe8bc3fd477f245762cc356ce9
- sched_checker.py 5bf9f74fc6d947c659a1cd1ac41c1e46764cc73c111b109977ff9de06d2f8640
- sched_domain.py 44e66bdbbf861135ad85d5fa9ac30ea47f4d1c77f6181176c60a677238edb523
- sched_inputs.py 22e8e9acfa721e23054e938ce6c0750273962e9d111c16abd9ad8f566ca84171
- sst_leg.py 4932422fb2b11425342e19d22a9f4b45e67b75f6ab441bd9bafdde1915e2031e
- successor_demo.py a47f6cca6bcb40023928c5456103c3ae39d1b916d9b4160aa95f302af274b8ca
- test_successor.py e5daea491a5d9c8be7514296cd19e1ee531ee1ae46c40b4eae2ba544dd22f408
- SUCCESSOR-REPORT.md eecfd3b5cfb60218ed8393be9bbe0fe195c13aa3d40993f1c6f74f557ffefb3c
- REPRODUCE.md 029414335c46ac44ef36a92d306aa4897a8dc6c32bf5db3dd78371950308e4d3
- LIMITS.md 77001f45e32b823085e488405a72431c0b415bb0f7686967414565c4d8c72d75
- OBLIGATIONS.md 62297221c1eec3daaa8996112fa536ed7e801d607c5e478a9d09b7c10426254b
- VENDORING.md caa81d2c8128a0d5cf999cbf2270fec897a3343464cbd8afd0b72abd57b6384c

## Re-run results (coordinator, fresh)

- `test_successor.py`: **15/15 OK** (26.8s), incl. loud SST MISMATCH
  warning + recorded-manifest posture (expected per report).
- `successor_demo.py`: **exit 0**, new run dir `demo-20261004T093102Z`:
  S1 central 655B VALID 4/4; S2 local 310/500 VALID 4/4 (ratio 0.47);
  S3 local+kill VALID 4/4, child rc=-9, 3 skipped, 0 re-invokes,
  artifacts identical; ruling + void-notice flow; fusion SC-FUSED with
  `direct-channel` removal; S5 quarantine probe denied seq 14; SST
  champion_found $0 TEST; settle 3 markers, 0 stranded, 5 routing
  decisions. All match the builder's reported numbers exactly.
- Evidence artifacts inspected directly: EVIDENCE.json (12 keys),
  fusion-record.json (lineage derived_from×2 + fusion entry, 3 custody
  transfers, before 8/after 7 mechanisms), ROUTING-LOG.jsonl (5
  decisions, explicit rule), sst-result.json (8/8 envelope keys, TEST,
  cand-02 path, $0), TREEHASH-CHECK.json (verdict MISMATCH, 50/50,
  manifest preserved), S4 via SC-FUSED lineage_ok VALID 5/5.
- New code is `signal`-import-free (`Popen.kill()` only; SIGKILL
  mentions are comments). Frozen baseline: **1401/1401 OK** —
  w1-harden/w1/reuse-demo/x3 untouched by the build.

## SST staging-pin correction (coordinator-owned)

My staging hash `df16a1a2…` (SST-STAGING.md) is WITHDRAWN as a pin: it
does not reproduce under ~220 documented constructions, and the
underlying snapshot mutates underfoot (3 files changed between the
builder's two runs; porcelain 46→53). Causes: under-specified
construction on my side + concurrent external SST edits. No static pin
over `.delivery/cand-02/` is meaningful until SST lands a clean
commit/tag. The successor's posture is correct: loud MISMATCH, no
fallback, within-run self-consistency (`cand02_unchanged=true` in all
three runs), per-run 50-file manifests preserved as re-pin material.
SST-STAGING.md corrected accordingly; the SST-owner evidence request
(clean landing + stable `run_search`/`TEST` confirmation) stands and is
now stronger.

## Scope honesty

Single-host fusion, toy-scale deterministic domains, TEST fixtures
only, one kill boundary, quarantine (not fission) as the separation
path — all per LIMITS.md, which I endorse as accurate. No live-model,
learning, multi-writer, or cross-machine claims. Windows: new code is
`Popen.kill()`-based (safe by construction) but executed on Linux only.
