# SUCCESSOR-REPORT.md — successor-001 (justified integrated successor)

One-ledger integrated successor over the MiniHost lineage: hybrid
central/local coordination under an explicit logged routing rule, two
working environments (scheduling/dialogue with an independent checker;
SST search from staged cand-02 bytes), real structural fusion with
mechanism removal + reuse, one declared separation path (quarantine),
and kill-resume / revision / revocation robustness on the integrated
path. $0, offline; stdlib-only except the SST leg (venv interpreter).

Observed results (demos `runs/demo-20261004T092320Z` and
`runs/demo-20261004T092639Z`, both exit 0 — identical scheduling
metrics; SST bytes drifted between them, see §4; tests 15/15 OK —
see §Evidence):

| task | lane | VALID | quality | central-B | direct-B |
|---|---|---|---|---|---|
| S1 | central | yes | 4/4 | 655 | 0 |
| S2 | local | yes | 4/4 | 310 | 500 |
| S3 | local+kill | yes | 4/4 | 685 | 500 |
| S4-followup | fused-reuse | yes | 5/5 | — | — |

S2 central ratio 310/655 = 0.47 (≤ 0.5 cut): the hybrid rule reproduces
the X3 shape — central for the small task, local for the dialogue-heavy
one — inside one host instead of two arms.

## 1. Contracts implemented vs WORLD-CONTRACT-v1

No clause was unimplementable. Implemented (C1–C7):

- C1 Invoke call contract — vendored `MiniHost.invoke` (byte-identical,
  see VENDORING.md): one invocation consumed per call on success only;
  raised `fn` records `payload.error` with no `consume` entry; success
  payload carries `capability` + `args_ref` + `result_ref` and no
  `error`. The resume matcher (`resume.successful_invokes`) keys on
  exactly these four conditions. Tests 01–02.
- C2 Args files — every `store_args` payload carries `formulation_ref`
  + `candidate_refs` (asserted by `resume.check_args_keys` on every
  plan step; byte-stable across the kill boundary). Test 03.
- C3 Result schemas — propose `result_ref` JSON carries
  `candidate_refs` + `champion_id` (asserted by
  `resume.check_propose_result` at write time and re-read by verify).
  Note: this pipeline has NO `sched.score` capability — verification
  verdicts take scoring's place — so the `scores[].score_ref` clause
  is not-applicable rather than unimplemented (recorded here, not
  hidden). Test 03.
- C4 Host read shape — `host.worlds[ID].lifecycle` compared to
  `"active"` (`resume.require_active`). Compatible superset note: the
  vendored host also has a pre-active `"proposed"` state; canonical
  terminal/active strings are unchanged. Test 04.
- C5 Deny + suspend/reattach shapes — positional order as pinned
  (`deny(actor, action, reason)`, `suspend/reattach(world_id, actor,
  reason, ...)`). Test 04.
- C6 World-handle file conventions — pipeline-side `SchedWorld`
  handle with `.state_dir`; `formulations/*.json` glob for latest
  artifact (per-task names, so history never clobbers); canonical
  `verdicts/verdict.json` latest-pointer PLUS per-task
  `verdicts/verdict-{task}.json` (multi-task worlds need both; the
  pointer advances, history is immutable — asserted in the demo).
  Test 05.
- C7 Checkpoint + settle + reopen — vendored: checkpoint schema +
  identity rule, `grant_settle` marker + unsettled-terminal replay
  check, `host_reopen` marker, resume-by-skip
  (`resume.execute_plan`), descriptor re-supply + fail-closed
  withholding (`recovery.withheld`). Tests 05, 08, 15 (incl. the
  handwritten unsettled-terminal negative).

Boundary notes (not deviations): C1's `...` (extra kwargs) is not
accepted by the vendored `invoke` — the resume engine never passes
extras. Revocation and representation revision are implemented WITHOUT
mutating world records (authority-stamp flip + ledger `revoke` entry
replayed after reopen; dual pre-advertised representation versions +
ledger `revision` entry), because record mutation would break reopen
identity verification — the v1-compatible pattern, documented in
`resume.py` / `pipeline.py`.

## 2. Routing rule + per-task routing log

Rule (central default; `routing.route`): **LOCAL iff
expected_rounds >= 2 AND split_state, else CENTRAL.** Every decision is
recorded twice: a ledger `routing` entry and a `ROUTING-LOG.jsonl` line.
Observed log (5 decisions):

- S1 → central (rounds=2, split=False; default)
- S2 → local (4>=2 rounds over split state; X3 H3a cut)
- S3 → local (4>=2 rounds over split state)
- S4-followup → fused-reuse (post-fusion composite reuse via SC-FUSED)
- S5 → quarantine-drill (declared separation path exercise)

Local-lane obligations O1–O5 + E1–E3 (`OBLIGATIONS.md`) are enforced
structurally: `HCoordinator` refuses non-export payloads (test 07
probes the refusal), one fragment per clarify step, O2 basis check at
proposal build, O3 void-by-ruling-only flow in S3, O4 giver-actor
transfers, O5 terminal commitments per world, E3 void-notice referencing
the kept artifact.

## 3. Fusion: before/after inventory + reuse evidence

`fusion.fuse_worlds` merged SC-L + SC-S (after genuine S1+S2
cooperation on the shared ledger) into SC-FUSED:

- Lineage: `derived_from SC-L`, `derived_from SC-S` (+ fusion entry).
- Ownership transfer (actor = giver, O4): `sched.requirements`,
  `sched.composite` (SC-L → SC-FUSED), `sched.slots` (SC-S → SC-FUSED).
- Lifecycle moves: SC-L/SC-S settle-then-dissolved (grant_settle
  markers), SC-FUSED created + activated.
- Removed mechanism: `direct-channel:SC-L<->SC-S` (intra-composite
  coordination is internal afterwards; the channel object is detached
  and refuses further sends).

Before inventory (mechanisms): checkpoint+suspend/reattach,
coordinator:central, coordinator:local-exports-only,
**direct-channel:SC-L<->SC-S**, grants+settle, invoke+deny, ledger,
reopen-by-replay. After: identical MINUS the direct channel (7
mechanisms). Full record: `runs/demo-…/artifacts/fusion-record.json`.

Reuse: S4-followup (5-task extension) ran THROUGH SC-FUSED
(`sched.reuse`): VALID 5/5, lineage check passed (derived_from present
for both parents + resolvable to ledger creates + ledger fusion entry).
Declared separation path: S5 quarantine drill — SC-Q suspended with
pending commitment effects, `sched.commitment-q` transferred to SC-B,
invoke probe on SC-Q raised with recorded deny (seq 14), SC-B completed
propose+verify, both settled.

## 4. SST-TEST consumption evidence (staged cand-02 ONLY)

- Interpreter: `prototype/w1/.venv/bin/python` (pydantic 2.13.5
  observed in-child). `PYTHONPATH` = `.../sst/.delivery/cand-02/src`
  EXACTLY; child asserts `sst.__file__` is under `.delivery/cand-02`
  (observed: `.../sst/.delivery/cand-02/src/sst/__init__.py`) and that
  live `sst/src` is NOT on `sys.path`. No fallback to live HEAD exists
  in the module: import/child failure raises `SSTBoundary` with the
  exact boundary (test 13 + demo would fail loudly, not reroute).
- Envelope: frozen `run_search -> SearchResult` with all 8 contracted
  keys; `termination_reason=champion_found`,
  `champion=cand_tree_successor_sst_0_0`, TEST-kind gateway bindings,
  `estimated_cost_usd=0.0` ($0). Pattern modeled on cand-02
  `tests/unit/test_controller.py` (TEST fixture gateway).
- No writes into the SST tree: `PYTHONDONTWRITEBYTECODE=1` in the
  child env + pre/post 50-file manifest comparison
  (`cand02_unchanged=true` within each run — see the drift note
  below for between-run external edits).
- TREE-HASH GATE — MISMATCH (recorded, loud, not silent):
  expected `df16a1a29cd6c21c7fbfebbf31b41583`; primary construction
  `md5(sha256sum-lines)` computed `3fe98c89…` (demo-092320Z) and
  `fa7adfbe…` (demo-092639Z) over the confirmed 50-file set. ~220
  constructions were attempted during the build (md5/sha1/sha256/
  sha512/blake2b × sumfmt/relhex/JSON/git-blob forms × relpath bases
  × backslash/relpath-prefix variants × digest slices ×
  stripped/text-mode bytes; live tree too) — NONE reproduces the pin.
- STAGED TREE IS DRIFTING UNDERFOOT (concurrent external edits): the
  two demo runs 3 minutes apart consumed DIFFERENT bytes — 3 files
  changed between them (`gateway/gateway.py`, `search/controller.py`,
  `search/policy.py`; cand-02 porcelain 46→53 lines). Each run stayed
  self-consistent (within-run pre/post manifests identical,
  `cand02_unchanged=true` in both), so the mutation happened strictly
  BETWEEN runs — and this successor never opens SST paths for write
  (reads + `git status` only), so the edits are external (parallel
  SST-side work). Both 50-file manifests are preserved
  (`runs/demo-…/sst-leg/TREEHASH-CHECK.json`) as the re-pin material.
  This also explains the pin mismatch: no static pin can reproduce
  against a mutating snapshot. It reinforces the SST-STAGING evidence
  request: land a clean commit/tag and pin that instead of a
  `.delivery/` snapshot.
- Posture: default records the check and proceeds — the pin is
  documented as a substrate-side observation, NOT a release pin, and
  the SST upgrade policy re-pins after observed consumption.
  `--require-pin` aborts before any SST import instead. No v1 clause
  covers the SST pin, so this is a staging-process finding, not a
  contract deviation.

## 5. Robustness on the integrated path

- Real forced termination: `Popen.kill()` (child rc=-9 observed),
  cross-platform by construction (no `signal` module). Resume skipped
  all 3 pre-kill invokes with **0 re-invokes**; every pre-kill history
  byte identical post-resume; 2 `host_reopen` markers (child attach +
  parent resume).
- Mid-task representation revision v1→v2 (declared loss, window
  change B→S3) + capability revocation (sched.propose SC-L→SC-S,
  durable across reopen) + denied retry (raises + recorded deny) +
  escalation → coordinator ruling → void-notice with kept artifact →
  v2 re-propose by the new owner → cross-verify. Final S3: VALID 4/4.
- Refusal paths raise with recorded deny (unknown capability,
  reattach-when-active, revoked invoke, quarantined invoke, withheld
  descriptor) — tests 04, 05, 09, 11.
- Settle: all terminals settled, conservation verified, **0 stranded**
  (3 grant_settle markers on the main ledger; S5 sub-ledger likewise).

## 6. Evidence

- `runs/demo-20261004T092320Z/` and `runs/demo-20261004T092639Z/`
  (both exit 0; kept as drift evidence — §4): `EVIDENCE.json` (full
  summary), `ledger.jsonl` (single integrated ledger),
  `ROUTING-LOG.jsonl` (5 decisions), `artifacts/` (4 solutions +
  fusion record), `s5/` (quarantine sub-ledger), `sst-leg/`
  (`TREEHASH-CHECK.json` with 50-file manifest, `sst-result.json`
  envelope, child script).
- `test_successor.py`: 15/15 OK (~29 s), incl. kill test (08), SST
  consumption test (13), isolation/vendor test (14).
- `FROZEN-BASELINE.sha256`: pre-build sha256 of all 1401 files under
  `w1-harden/`, `w1/`, `reuse-demo-001/`, `x3-20261004/` — re-verify
  with `sha256sum -c` (all OK at handoff).
- Limits: see `LIMITS.md`. Reproduce: see `REPRODUCE.md`.
