# SST spike record (W1, builder B3, 2026-10-03)

Verdict: **PASS** — E-explore uses the real `SSTSearchController` when SST is
importable; the deterministic stub stays as automatic fallback behind the same
interface (`world_explore.py: SearchEngine.run`).

## Wiring used

- Import: `PYTHONPATH=<ws>/sst/src`, project-local venv
  `substrate/prototype/w1/.venv` (deps only; sst/ source read-only, never
  `pip install -e`, `sys.dont_write_bytecode` before SST import).
- Seam: `SSTSearchController(task, gateway, store, custody_manager, policy)`
  per SST CONTRACT v0 (`run_search` typed envelope; `SSTEngine` untouched).
- Gateway: `ModelGateway` + one `ProviderKind.TEST` profile routed to all
  roles (diverge/refine/critique/synthesize), model `test-model-0`. No keys,
  no network, spend $0 (`estimated_cost_usd: 0.0` observed).
- Store/custody: `SQLiteSSTStore` + `CandidateCustodyManager`, both rooted
  under the world's own state dir (`search-work/`).
- Domain verdict: world-local `LocalEvaluator` (EvaluatorProtocol-shaped);
  SST's custody verifier only checks patch application/scope.

## Evidence (probe `/tmp/muse-w1-spike.py`, exit 0)

- Run 1 (2 iters, depth 2): termination `champion_found`, champion
  `cand_spike-tree-1_0_0`, 3 alternatives, 15 events
  (`TREE_CREATED/NODE_PROPOSED/VERIFIER_STARTED+FINISHED/SCORE_RECORDED/
  SYNTHESIS_PROPOSED/PROMOTION_RECOMMENDED/SEARCH_COMPLETED`), 0 provider
  errors, cost $0. -> bounded run + attributable scores.
- Run 2 (token budget 1): termination `budget_exhausted` + `BUDGET_EXHAUSTED`
  event. -> budgets enforced.
- Caveats: `ModelGateway` needs the TEST profile (else routing error);
  `run_search` prints `Memory provider 'none' reported error` (known SST
  limitation: no provider wired; non-fatal, no spend).

## Dep pins (w1/.venv, copied from sst/.venv read-only)

pydantic==2.13.5 click==8.5.0 rich==15.0.0 aiohttp==3.14.3 httpx==0.28.1
pyyaml==6.0.3 (plus transitive deps incl. pydantic-core==2.46.5,
yarl==1.25.1, multidict==6.9.1, aiosignal==1.4.0, frozenlist==1.8.0,
propcache==0.5.4, idna==3.20, anyio==4.15.1, h11==0.16.0, httpcore==1.0.9,
certifi==2026.7.22).

## Frozen SST identities (final bytes; all green runs above used these)

- HEAD: `079f4de6fd43881c2f1b529f0612f1df64a62f32` (dirty; peer work in
  progress — drift observed DURING this build: 14M+9U -> 19M+10U, incl.
  used modules policy.py/models.py/store.py; re-frozen + re-verified below)
- sha256 (working tree, 2026-10-03 ~16:54 UTC):
  - `3566e7bf...bdd7ccf` src/sst/search/controller.py (M)
  - `53d59071...0287d22` src/sst/search/policy.py (M)
  - `d8a60fc1...acb247b` src/sst/gateway/gateway.py
  - `26a62c2a...690b5a4` src/sst/gateway/contracts.py
  - `3909dc51...b4d411` src/sst/gateway/backends.py (not imported by spike)
  - `34ce5767...20f4d3` src/sst/core/contracts.py (M)
  - `65a6924f...06de0f` src/sst/core/events.py (M)
  - `4f83df4a...3c9e1c2` src/sst/core/models.py (M)
  - `b2588803...89f57c1` src/sst/sandbox/custody.py (M)
  - `850342c5...01af133` src/sst/storage/store.py (M)
  - `756ab900...83c983bf` src/sst/storage/projection.py (M)
  - `b6e11f83...7d7d47` src/sst/context/capsule.py (M)
  - `c4b4c165...80439a` src/sst/prompts/dialectic.py
  - `9bde42e5...38eb49` src/sst/protocols/evaluator.py
  (Full 64-hex hashes in W1-BUILD-NOTES.md appendix; `(M)` = dirty at freeze.
  sst/ never written by this track: no egg-info, status shows only peer `.py`
  edits + prior user work.)

## Decision

Real SST in the demo path (venv run: `engine=sst-controller-v0`,
`champion_found`, $0, exit 0); stub engages automatically under system
python3 (also exit 0). No W2 debt from the spike itself; W2 should pin a
clean SST release since sst/ is drifting under the prototype.
