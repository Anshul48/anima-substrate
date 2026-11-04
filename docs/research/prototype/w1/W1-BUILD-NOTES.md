# W1 build notes (builder B3, 2026-10-03)

Plan followed: `tracks/substrate/W1-PLAN.md` (frozen; not edited). All 9
files built under `substrate/prototype/w1/` (+ this notes file + `.venv`).

## Results

- `python3 -m unittest`: 19 tests OK.
- venv suite (`PYTHONPATH=sst/src .venv/bin/python -m unittest`): 19/19 OK.
- `demo_T.py` exit 0 BOTH ways: system python3 (stub engine) and venv python
  (real `sst-controller-v0`, `champion_found`, $0). Canonical ledger sample is
  from the venv run (spike PASS -> real SST per plan section 2 step 3 note).
- `w0-probes.sh`: exit 0 (re-verified post-build; see below).
- sst/ untouched by this track: no egg-info, no writes; `git status` drift
  (14M+9U -> 19M+10U during build) is peer `.py` edits, timestamps 16:52-16:53
  UTC. Re-frozen + re-verified after the drift (spike exit 0 on final bytes).

## Deviations from plan (minor, all within hard limits)

1. Demo runs under BOTH interpreters, not venv-only. `world_explore.py`
   selects real SST when importable, else the stub behind the same interface.
   Rationale: keeps `python3 demo_T.py` (plan section 2 step 3, system python)
   green while the venv run exercises real SST. No extra files.
2. `invoke` pre-checks affordability BEFORE running `fn` (plan implies refuse
   over-commit; post-hoc consume alone would run first and bill later).
3. Host extension: `grant_return` (child returns unused grant). Contract v0
   lacks grant revoke/return (V2 gap G6); the demo does not need it, but the
   ledger + conservation replay support it and one test covers it.
4. STC-backend stretch in `world_construct.py`: NOT attempted (plan: not
   required for W1).
5. Coalition lifecycle evidenced via an explicit `coalition-T` world record
   (proposed->active->dissolved), since relationships carry `state`, not the
   lifecycle vocabulary.
6. Test file contains 19 tests (plan names 6 areas; all covered plus world
   roundtrips, evaluator shape, allowlist/containment, version refusal).
   No real-SST test in the suite (stdlib-only hard limit); real-SST
   coverage is the spike probe + venv demo run.

## Open issues / W2 debt

- sst/ is drifting fast (5 more modified files landed mid-build). W2 should
  pin a clean SST release (commit + clean tree) instead of working-tree bytes.
- SST `run_search` prints `Memory provider 'none' reported error` (no memory
  provider wired; non-fatal). W2: wire explicit provider or accept the message.
- Contract gaps G1-G7 (V2 report section 6) carried: candidate/evaluator IDs,
  `runtime_placement`, evaluator declaration, state digest, `update_rules`,
  grant revoke/cancel (partial: return exists), incompatibility record.
- `AlternativeCandidate` wraps `CandidateProposal` (no flat fields); the
  world_explore adapter unwraps it — re-check if SST1 reshapes the envelope.
- No `__init__.py` in w1/ (plan lists 9 files exactly); imports assume CWD=w1
  as in plan section 2 commands.

## Appendix: full frozen SST sha256 (working tree ~16:54 UTC 2026-10-03)

- `3566e7bf2d5109c8b43dfafd7e85622259f71ee4a535096ea12744e86bdd7ccf` search/controller.py
- `53d59071ff832bc76f851df91dd792dccd1307c289d501b1ec9f5185d0287d22` search/policy.py
- `d8a60fc195e0416cd4f033429545c074cfa7c479b41ebbd2db997807dacb247b` gateway/gateway.py
- `26a62c2a1bc66797df478eaa6d4fb0a4c1846dc883774a089c5c52d24690b5a4` gateway/contracts.py
- `3909dc51e3800e7b06a38338aeec00883e153805266acc66db56df1981b4d411` gateway/backends.py
- `34ce576795dcba5c9cb52fe83a8c208d2f86fe34ad70d9cceaa0d410c020f4d3` core/contracts.py
- `65a6924fb83acc14cb5db3e1d04248a324cecb4e10f7ce928fb8a6bf8d06de0f` core/events.py
- `4f83df4a5f141a6525865ca523a011dfb1e9e1d835c7b9fad0081c49b3c9e1c2` core/models.py
- `b258880319ba6725feefada2cc5bce96a24ed74348f44b0e4d2a1b75189f57c1` sandbox/custody.py
- `850342c5ec7563c02fbc11584e9c72cd8d9972bf67b53e22c9cde305e01af133` storage/store.py
- `756ab900b33a19258b460e218c526d15d8efb307a508ef49f771b1a183c983bf` storage/projection.py
- `b6e11f8347714e3f257f7154fc5d98d0b3283af21ff70a84daeda65bc7dd7d47` context/capsule.py
- `c4b4c165ece497634074c893f1a0249624a6d61d5263b2c097ef03403c80439a` prompts/dialectic.py
- `9bde42e5f9a9ecb981a0458ba5a373fb528debea503a9b01fc099e814638eb49` protocols/evaluator.py

(All 14 hashes re-verified by re-hash after the final green runs; later
sst/ drift added only untracked `tests/unit/test_wave2_*` files, none of
them used modules.)
