# Reuse calibration (Q3 resolved, 2026-10-04)

Prior claim: `w1-harden/RECOVERY-REUSE.md` §2 names an interface through
which another host could reuse the checkpoint/settle capability. Status
then: architectural assessment, untested.

## Demonstration

`prototype/reuse-demo-001/` (identity, coordinator-hashed):
- minihost.py d01049a93b0e068e9e0384379cb26f509726f6a7ee659ff71dd0f0ec7bd4b206
- reuse_demo.py bf3a49fa68f41da173f8b28a02bc3826e184935e0b5f8b03d685f7ac2295aea1
- test_reuse.py 814688431d71b4f9aa1e8b38e7b55b2b96794428f52d0d84e6de4beb268c0cc0
- w1h_bridge.py c015e8a3aafb5505ec90cc97eca61c9e0122eb4292ce790806b3d47f9b8f7cea
- REUSE-REPORT.md 5f9b88046b96243aecd0a22a38adeb8692ee39db2ed48f42936caa8997a0f3ad

A NEW stdlib-only host (MiniHost, 838 lines, zero w1-harden imports —
verified by test_10 + coordinator grep: only a docstring mentions the
bridge) drove the UNMODIFIED `resume_to_verdict` (+ phase helpers,
~171/235 lines of `recovery_lib.py`, loaded by explicit file path via
importlib) through:

- drop-kill resume AND real-SIGKILL resume (child rc=-9), both with
  0 re-executed invokes and byte-identical reused artifacts;
- second resume executing nothing; suspend/reattach roundtrip;
- terminal settle with 0 stranded holdings + conservation ok;
- hand-written unsettled-terminal ledger rejected;
- missing-checkpoint + identity-mismatch refusals raising with deny.

Coordinator independently re-ran: 10/10 tests OK, demo exit 0 with the
same evidence lines. `w1-harden/` 20/20 + `w1/` 7/7 hashes OK after.

## Calibrated claim (what Q3 now means)

- CONFIRMED: the resume engine + checkpoint/settle conventions are
  consumable by a separate host through the §2 interface shape.
- NARROWED: §2 alone is NOT a complete porting contract. Driving the
  reused (not rewritten) function required 8 unpinned coupling details
  (invoke kwarg names + consume-on-success-only, invoke payload keys,
  args-file keys, result_ref schemas, worlds/lifecycle read shape, deny
  signature order, world-handle file conventions, suspend/reattach arg
  shape). Full list: REUSE-REPORT.md "Interface gaps". A porter must
  either read `recovery_lib.py` line by line or be given the
  resume-coupling list §2 should gain. §2 + that list = complete contract.
- PRESERVED LIMITS: transitive module-load closure (executing
  recovery_lib.py executes its own w1-harden imports — dependency
  closure, not the demo's host); single worker, single grantor;
  same-machine path refs; toy pipeline side (engine-agnostic resume
  decisions only).

Q3 verdict: DEMONSTRATED-WITH-COUPLING-LIST (was: architectural
assessment). The recovery limitations in `w1-harden/LIMITS.md` are
unchanged and still apply.
