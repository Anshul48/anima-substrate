# WORLD-CONTRACT-v1 draft (PROPOSAL, successor to v0 + reuse coupling list)

v0 (pilot): world record, grant, invoke, versioned relationship, custody
transfer, lifecycle + checkpoint/reattach, lineage. No universal
ontology/evaluator/hierarchy. V1 keeps v0 and pins the resume-coupling
details the reuse demo proved necessary (gaps G1–G8 from
`closeout-20261004/REUSE-CALIBRATION.md`). A host implementing v0+v1
can drive the reused resume engine; a host implementing v0 alone must
also read the engine source.

## C1. Invoke call contract (pins G1, G2)

- Signature: `invoke(caller, callee, capability, version, args_ref, fn,
  *, cost_usd, time_s, ...)`; exactly one invocation is consumed per
  call, ON SUCCESS ONLY. A raised `fn` records an `invoke` entry with
  `payload.error` set and consumes nothing (no `consume` entry).
- Success entry payload MUST carry: `capability`, `args_ref`,
  `result_ref`, and MUST NOT carry `error`. The resume matcher keys on
  exactly these four conditions.

## C2. Args files (pins G3)

`store_args` writes JSON with at least `formulation_ref` and
`candidate_refs` keys. Resume reads these keys; byte-level
compatibility is required across the kill boundary.

## C3. Result schemas (pins G4)

- propose `result_ref`: JSON string with `candidate_refs` and
  `champion_id`.
- score `result_ref`: JSON with `scores[].score_ref`.
World-side artifact vocabulary; version with the pipeline, not the host.

## C4. Host read shape (pins G5)

Resume reads `host.worlds[ID].lifecycle` and compares to the string
`"active"`. Hosts exposing worlds differently MUST provide a
`worlds` mapping view with `.lifecycle` string state. Canonical
lifecycle strings: `active|suspended|dissolved|retired`.

## C5. Deny + suspend/reattach shapes (pins G6, G8)

- `deny(actor, action, reason)` — positional order pinned.
- `suspend(world_id, actor, reason, pending_effects)` /
  `reattach(world_id, actor, reason)` — world_id first, actor second.

## C6. World-handle file conventions (pins G7)

Resume needs `world.state_dir` (path-like) plus pipeline conventions:
`verdicts/verdict.json` (phase_verdict) and `formulations/*.json` glob
(latest_artifact). A successor SHOULD replace the glob with a manifest
(`latest.json`); until then the glob is normative.

## C7. Checkpoint + settle + reopen (carried from pilot, unchanged)

Checkpoint schema + identity rule (`world_id` + `code_ref` +
`contract_version`), `grant_settle` marker + `unsettled terminal`
replay check, `host_reopen` marker, resume-by-skip rule, descriptor
re-supply + fail-closed withholding (`recovery.withheld`).

## Non-goals (still deferred)

Per-grant siloed balances, content-addressed refs (paths retained),
relationship-evidence persistence, multi-writer safety, kill-during-settle
atomicity (operator repair), disk loss. See `w1-harden/LIMITS.md`.
