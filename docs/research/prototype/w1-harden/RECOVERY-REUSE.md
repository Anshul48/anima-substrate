# Recovery Retention/Reuse Assessment (w1-harden)

Question: can the checkpoint/settle capability be retained/reused independently of the
rest of the W1 Host, e.g. by another host implementation? Answer: **yes, with a small,
named interface** — checkpoint/identity is already ledger-schema-level (portable), settle
is a ledger convention + one replay check (portable), and only the `reopen` *registry
rebuild* is Host-shaped (needs a per-host adapter, ~60 lines here).

## 1. What is portable as-is (ledger schema level)

These survive a host rewrite untouched because they are bytes-on-disk conventions:

- `checkpoint.json` schema: `{contract_version, world_id, code_ref, capability_versions[],
  representation_versions[], ledger_position, pending_effects[], at}`. Identity rule:
  `world_id` + `code_ref` + `contract_version=="0"` must match the live record, else refuse.
  Any host that writes this file before suspending and checks it on reattach gets R2/R3
  behavior for free.
- `grant_settle` marker schema:
  `{seq, at, kind: "grant_settle", contract_version: "0", actor,
  payload: {world_id, grants[], reason, amounts_total{...}}}`. Rule: marker is
  balance-neutral (funds move only in `grant_return` entries); conservation replay ignores
  it for balances but REQUIRES one per terminal world (`unsettled terminal` refusal).
- `host_reopen` marker schema:
  `{... kind: "host_reopen", payload: {reason, ledger_entries_replayed, worlds[],
  descriptors_supplied[], descriptors_withheld[]}}`. Balance-neutral; proves a crash
  boundary was crossed honestly (replay, not re-init — a second `host_init` would corrupt
  conservation, which is why reopen exists instead of re-constructing).
- Resume rule (idempotent-by-skip): skip a phase iff a ledger-successful invoke for the
  CURRENT inputs exists AND all output artifacts exist on disk; else execute. This rule
  lives in `recovery_lib.resume_to_verdict` (~90 lines) and depends on the host only
  through `ledger_entries()` + `invoke()` + `deny()` (see interface below).

## 2. Minimal interface another host would need

To reuse checkpoint/settle/reopen against a different host, that host must provide:

Functions (host side):
- `ledger_entries() -> list[dict]` — full ordered ledger read (JSONL rows with
  `seq/kind/contract_version/actor/payload` envelope).
- `append(kind, payload, actor) -> entry` — monotonic-seq append (for `host_reopen`,
  `grant_settle`, `deny` markers).
- `invoke(caller, callee, capability, version, args_ref, fn, costs...)` — accountable
  call that records success (`result_ref`) vs failure (`error`) distinctly, so resume can
  tell "ran ok" from "ran and failed" from "never ran". Pre-check refusals must record
  `deny`-shaped entries (or an equivalent the resume matcher is told about).
- `suspend(world, pending_effects)` — writes `checkpoint.json` (schema above) then moves
  active->suspended; `reattach(world)` — verifies identity then moves suspended->active.
- `transition(world, terminal)` hook point running `settle_grants` BEFORE the terminal
  move (settle-then-move order), else a failed settle cannot refuse the transition.

State (rebuilt by replay, not trusted from memory):
- worlds registry (ids, code_refs, lifecycle last-states, custodians, retired ids),
  holdings + consumed totals, grants_out table, relationships. All are derivable from the
  ledger rows `host_init/create/lifecycle/grant/grant_return/consume/transfer/relationship`
  (see `Host.reopen`); a new host replays the same rows into its own structures.
- Full capability descriptors (authority metadata etc.) are NOT in the ledger (create rows
  carry name@version only) and must be re-supplied by the recovering process from its own
  code constants, then verified against the ledger (world known, code_ref equal, name@version
  sets equal) — or the host must accept ledger-only skeletons with authority withheld
  (fail-closed), as this implementation does via `recovery.withheld`.

Ledger schema (rows the replay must understand): `host_init, create, lifecycle, grant,
grant_return, consume, transfer, relationship` (balance/registry effects) plus the three
marker rows `grant_settle, host_reopen, checkpoint/reattach` (audit only). Unknown future
rows must be IGNORED by balance replay (current behavior) but should ideally be surfaced
by strict audit replays — not implemented here.

## 3. What stays coupled to the W1 Host and why

- `reopen`'s registry rebuild (~120 lines) is Host-shaped: it constructs `WorldRecord` /
  `Capability` / `Relationship` dataclasses and the `holdings/consumed/grants_out` tables.
  A new host keeps the replay ORDER and the verification RULES but rewrites the
  constructors — an adapter, not a redesign. (Estimated port: the replay loop is generic;
  only the per-row state updates are host-specific.)
- `settle_grants` distribution (per-grant `min(held, grant_limits)`) assumes the W1
  fungible-holdings model (one holding pool per world across grants). A host with
  per-grant siloed balances would settle per-silo instead; the MARKER + replay check stay.
- Checkpoint *contents* (`pending_effects` strings like "score"/"verdict") are pipeline
  vocabulary, not host vocabulary — reuse requires the resuming pipeline to interpret the
  same effect names (here: `recovery_lib` phase names). The host treats them as opaque.
- `invoke_id`/`args_ref`/`result_ref` refs are host-local path conventions; resume matches
  invokes to artifacts through them, so a reusing host must keep stable, re-readable refs
  (content-addressed refs would be strictly better; paths were kept for W1 fidelity).
- Relationship `evidence` (in-memory invoke-id list) is NOT ledger-persisted in W1 and is
  therefore LOST across reopen (rebuilt empty). Any host reusing this recovery path must
  either persist evidence rows or accept the loss (documented; verdicts do not depend on it).

## 4. Retention verdict

Retain: checkpoint schema + identity rule, `grant_settle` marker + `unsettled terminal`
replay check, `host_reopen` marker, resume-by-skip rule, descriptor re-supply + verify
(incl. fail-closed withholding). These are the recovery capability, and they are all
independently reusable through the interface in section 2.
Rewrite-per-host: the replay-to-registry adapter and any holdings-model-specific settle
distribution. Do NOT retain without change: path-shaped refs (fragile across machines)
and in-memory-only relationship evidence (does not survive the crash it is supposed to
help recover from).
