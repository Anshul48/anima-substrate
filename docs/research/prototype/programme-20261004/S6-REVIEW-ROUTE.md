# S6 review route (owed repairs + J1, successor-006, ACCEPTED 2026-10-07)

## Run it (from repo root, ~2 min, stdlib-only, offline, $0)

```
export PYTHONDONTWRITEBYTECODE=1
python3 prototype/successor-006/j1_demo.py        # expect: J1 journey: OK (10/10 PASS)
for t in test_coupling test_quarantine_repair test_j1 test_conformance test_fission test_procedure_smoke; do python3 prototype/successor-006/$t.py; done   # expect: 48/48 OK
```

Step-by-step CLI version (9 steps + quarantine drill): `prototype/successor-006/RUNBOOK.md`.

## Observe

- Persistent project world PROJ created on fresh state; experiment world
  EXP1 nested with a real sub-grant + custody transfer (delegation never
  manufactures resources — over-delegation is refused with zero mutation).
- Work runs through EXP1 with PROJ cross-verifying; a real SIGKILL
  (child_rc=-9) mid-task resumes byte-identical with 0 re-executed invokes.
- PROJ+EXP1 fuse into PROJ-FUSED with real ownership change (mechanism
  inventory before/after); the composite is reused UNMODIFIED in two
  follow-up tasks (identical derived_from lineage); settle strands 0.
- A kill during quarantine-transfer converges afterwards via either
  supported operator path (`quarantine-complete` or `quarantine-rollback`).
- The Q3 resume-coupling contract (CC1–CC9) pins every shape the host and
  resume engine share; the resume engine is byte-identical to frozen s005.

## Limitations (envelope, per LIMITS.md)

Single-host, local disk, process-crash-only (no fsync), toy scale.
No SST leg (loud refusal, not silent), no cross-host/multi-writer/disk-loss,
no learning of any kind. Outside the envelope behavior is unpromised.

## Evidence

- Independent acceptance: `programme-20261004/S6-ACCEPTANCE.md` (ACCEPT;
  48/48 + 10/10 re-observed, manual CLI journey, both repair paths,
  frozen predecessors untouched, 3 negative checks).
- Contract: `successor-006/COUPLING-CONTRACT.md`; provenance (carried-byte
  hashes): `successor-006/PROVENANCE.md`; builder log: `BUILDER-LOG.md`.
- Companion research (same round): `MECHANISM-REUSE-ASSESSMENT.md` (reuse
  candidates per gap), `ADAPT-EXPERIMENT-DESIGN.md` (discriminating protocol,
  design only — no runs authorized), `STC-CONSUMER-BOUNDARY.md` (Ask-2B
  blocked/unblocked table + experimental-adapter contract).

## Standing obligations (not interruptions)

- Q5 permanent host: open, non-blocking. Successor development and
  reversible host trials proceed without it; no architectural judgment
  needed until a permanent migration is actually proposed.
- Ask 2B / Ask 1: owner-side sentences; substrate cannot self-resolve.
  Independent work continues meanwhile.
- Banking: routine. successor-006 banked 2026-10-07 (IDENTITY.sha256,
  35/35 OK, manifest 48462368…); no freeze hold existed. Future
  banking proceeds the same way unless an explicit hold says otherwise.
- Any future adaptation experiment run needs a separate authorized
  objective + filed prereg; designs alone authorize nothing.

Nothing in this round needs your judgment.
