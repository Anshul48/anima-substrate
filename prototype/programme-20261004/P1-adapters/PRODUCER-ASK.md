# PRODUCER-ASK.md — smallest concrete ask per owner (P1)

Each ask is the MINIMUM that unblocks a U-branch real-use acceptance
claim. Rationale + unblock stated per item. Nothing here authorizes
spend or execution; all verification stays $0/offline/read-only.

## Ask 1 — SST owner (smallest: owner contract + gate record at a pinned commit; no tag required)

RECONCILED 2026-10-04: byte identity is already citable (commit
`df78f42894a65c48f524337a498032617689a013` + verified manifest
`5f1f3789…`). No tag and no mandated filename — write in whatever
owner file fits, at df78f42 or any later clean commit (your call):

1. **Owner contract** (committed bytes): the consumed scope
   (`src/sst/**` or narrower), the consumer (substrate), and the
   consumer surface declared stable: `run_search(tree_id) ->
   SearchResult` 8 keys (`tree_id`, `termination_reason`,
   `champion`, `alternatives`, `budget_consumed`, `provider_errors`,
   `gateway_bindings`, `event_log_ref`) + `ProviderKind.TEST`
   fixture semantics, with a change policy (additive-only / bump).
   One sentence on `execute_search` vs `run_search` long-term
   direction. (why: converts "proposed" to promised; unblocks
   Q-SST-1).
2. **Gate record you already run** (command + counts, e.g.
   `pytest … 161/161`, ruff/mypy) committed alongside, naming the
   commit. (why: binds test evidence to pinned bytes; unblocks
   Q-SST-2. In-message claims don't count; committed bytes do.)

When it lands, substrate advances PINS.json deliberately and the
U-branch may claim real-SST consumption. No live model, no spend, no
new SST work beyond writing down what is true. (A tag remains welcome
as a convenience alias, never a gate.)

## Ask 2 — STC owner (smallest: clean commit, then a design answer)

Step A (mechanical — PARTLY LANDED 2026-10-04):

1. ~~Land-or-revert to a clean commit~~ DONE for the pin advance:
   `5c65427…` commits the SST adoption (`EXTERNAL_PINS["sst"]` =
   `df78f42…`). The full commit hash now suffices for byte identity
   (a tag remains optional). Note: the worktree is dirty again
   (owner active on pilot scripts/docs) — pin the commit, never the
   worktree. (Q-STC-0 now SATISFIABLE pending the artifact decision.)

Step B (one design answer, then the SST-shaped contract):

2. **Name the substrate-consumable artifact, if any**: today every
   STC contract is STC→SST or STC→DSH internal; "substrate" in STC
   docs means STC's internal quality gates. If substrate should ever
   consume STC material, state WHAT (doc set? dossier schema? verdict
   record?) in a committed owner note. If the answer is "nothing —
   STC is not a substrate producer", that sentence IS the deliverable
   (it retires Q-STC-1..2 and U-branch plans around SST-only).
   (why: unblocks Q-STC-1 and scopes everything after.)

When A+B land, substrate mirrors the SST pattern (owner contract +
gate record) for the named artifact; until then the STC adapter stays
a doc-reader + UNQUALIFIED gate, which is its honest terminal state.

## Ask 3 — TRACE owner: none (out of P1 scope; presence recorded only)

## What substrate does NOT need

- No live-model runs, no keys, no spend, no owner execution of
  substrate code, no changes to producer runtime behavior — only
  frozen identities + short written statements about bytes that
  already exist.
