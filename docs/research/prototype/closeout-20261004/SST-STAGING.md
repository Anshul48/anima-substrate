# SST dependency: staged upgrade to cand-02 (substrate-side prep, 2026-10-04)

## Trigger

Pilot SST evidence was frozen dirty-with-hashes at HEAD 079f4de (38
porcelain lines, 14 module hashes). The live SST tree has since drifted
to 50 porcelain lines with 4/14 frozen modules changed
(`core/contracts.py`, `core/models.py`, `sandbox/custody.py`,
`search/controller.py`). Fresh runs against live HEAD no longer test
the frozen bytes. Live-HEAD tracking is rejected; a staged pin is needed.

## Staged target (inspected, not yet consumed)

SST owner delivery `../sst/.delivery/cand-02/` (runnable tree +
apply-checked `.patch`, frozen `uv.lock`, 5/5 verifier lanes per
SST FREEZE-MANIFEST.md):

- Base HEAD 079f4de6fd43881c2f1b529f0612f1df64a62f32 + 22-file tracked
  delta + documented untracked set.
- Coordinator-computed staging hash over `src/sst/**/*.py` (50 files):
  tree-hash `df16a1a29cd6c21c7fbfebbf31b41583` — **WITHDRAWN 2026-10-04**:
  unreproducible under ~220 documented constructions (successor
  builder evidence) and the snapshot mutates underfoot (3 files
  changed between two runs 3 min apart; porcelain 46→53). The
  construction was under-specified and the bytes no longer exist. No
  static pin over `.delivery/cand-02/` is meaningful. Re-pin material
  is now the per-run 50-file manifests preserved in
  `successor-001/runs/demo-*/sst-leg/TREEHASH-CHECK.json` (3 runs).
- Consumable contract: `SSTSearchController.run_search(tree_id)
  -> SearchResult` (frozen envelope: tree_id, termination_reason,
  champion, alternatives, budget_consumed, provider_errors,
  gateway_bindings, event_log_ref); `execute_search` unchanged and
  STC-compatible; `ProviderKind.TEST` fixture mode ($0 path).
- Non-stdlib: pydantic models — substrate consumes via the SST
  interpreter/venv + PYTHONPATH, same posture as the pilot SST-TEST run.

## Substrate plan

1. Successor SST-TEST demo path targets cand-02 bytes (PYTHONPATH to
   `.delivery/cand-02/src`), keeping the pilot's read-only,
   no-install, $0 posture. The frozen pilot keeps its dirty-with-hashes
   label; it is NOT re-pointed.
2. Advance the pin only after observed successful consumption (per
   SST owner's own upgrade policy: re-pin after observed consumption).

## Evidence request for the SST owner (via authorized coordination)

- A clean-commit landing of the cand-02 delta (or a content-hash release
  tag) that substrate can pin instead of a `.delivery/` snapshot.
- Confirmation that `run_search -> SearchResult` + `ProviderKind.TEST`
  fixture behavior is stable across that landing.
- Live-model qualification remains an SST-owner track (keys/budget);
  substrate does not inherit it.

Ownership intact: no SST source touched by this track; all reads.
Future obligation (TRACE SST integration, live caller qual) stays
with the respective owners.
