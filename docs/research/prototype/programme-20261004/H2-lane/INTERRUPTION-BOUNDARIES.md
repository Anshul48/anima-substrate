# INTERRUPTION-BOUNDARIES.md — successor-003 (R1)

> H2-lane carry note (2026-10-04): base text below is the byte-identical successor-003 record; only this note was added. The H2 delta (task-JSON lane path, derived routing inputs, lane-override hook) does not change the behaviors documented here.

Defined behavior for kills during settle/fusion/fission, and the
recovery + operator-repair procedures. No silent partials: every
interrupted state is either completed idempotently by
`release.py ops recover` / `api.recover_op`, or refused loudly with
exact operator steps.

## 1. Kill model

Single machine, local disk, no multi-writer, no disk loss (LIMITS-2).
Every op persists as a sequence of ledger appends; `MiniHost.append`
closes the file before returning, so a kill (SIGKILL, or the
test-only `os._exit` hook) between two appends leaves an
ENTRY-GRANULAR PREFIX of the op's appends: entries on disk are whole,
entries not yet appended are absent. Kill CANNOT tear a ledger line
(buffered bytes are either fully on disk or fully lost) — a torn
line is the disk-loss class (LIMITS-2, out of scope; recovery
refuses it loudly, see §6).

Test hooks (test-only; unset = zero behavior change):
`SUBSTRATE_CRASH_AFTER_APPENDS=N` (exit 42 after the Nth `append()`
of the process — `open_run`'s `host_reopen` is append #1, so N=1 is
"kill before the op's first append") and `SUBSTRATE_CRASH_AT`
(named points for the ledger-complete-but-side-file-missing
boundaries: `api:fuse:pre-spec`, `api:fission:pre-spec`,
`recover:pre-spec`). The hook's ledger effect is IDENTICAL to a
SIGKILL at the same boundary; real SIGKILLs are additionally
exercised (staggered delays, all landings converge).

## 2. Append maps (2-world settle, 3-class fuse/fission)

`ops settle --worlds A,B` (7 appends): `host_reopen`,
per world: `grant_return`(s, one per grant with funds to move),
`grant_settle`, `lifecycle(->dissolved)`.

`ops fuse --a A --b B --fused F` (14 appends): `host_reopen`,
`create(F)`, `grant(->F)`, `lifecycle(F proposed->active)`,
`transfer` x3 (A's classes sorted, then B's), per parent:
`grant_return`, `grant_settle`, `lifecycle(->dissolved)`,
`fusion` entry; THEN `worlds.json` spec + `artifacts/fusion-F.json`.

`ops fission --composite C ...` (14 appends): `host_reopen`,
per child: `create`, `grant`, `lifecycle(->active)`,
`transfer` x3 (C->child per partition), `grant_return`,
`grant_settle`, `lifecycle(C->dissolved)`, `fission` entry;
THEN specs + `artifacts/fission-C.json`.

Counts are asserted by the kill-matrix tests (a drift fails loudly).

## 3. Settle: refusal vs interruption

REFUSAL (no kill) is atomic: `finish_worlds` rehearses the WHOLE
batch first (ledger conserves NOW + `check_settleable` per world:
known, active/suspended, reattachable, zero residual) and raises
`ContractViolation` ("...; zero worlds dissolved") before ANY
dissolve. Only a `deny` entry is recorded. Single-world
settle-then-move carries the same guarantee (`settle_grants`
pre-validates; previously partial `grant_return`s could precede a
refusal — the one behavior extension, fail-closed-earlier).

INTERRUPTION (kill during phase-2 execution) leaves per-world
prefixes: some worlds dissolved+settled (complete records), at most
one world mid-settle (`grant_return`(s) without marker, or marker
without `lifecycle`). All prefixes conserve (replay holds; a marker
without terminal is benign). Recovery: re-run the settle —
`ops recover --state-dir DIR --worlds A,B` (idempotent: dissolved
worlds are reported `settle_already_terminal`, the remainder
settles). A re-settle after a marker-without-terminal crash leaves a
second `grant_settle` marker for that world: markers are
SET-semantic (`verify_conservation` treats them as one), documented
here, asserted in tests.

Kill BEFORE the first append (N=1): no trace — recovery reports
nothing to complete; the settle simply runs (via recover+`--worlds`
or a fresh `ops settle`).

## 4. Fusion: partial states + completion

Kill points produce (all conserving, all detected):
- no trace (pre-create): re-run the op.
- created, no grant (kill inside `create_world`): composite
  `proposed`, unfunded. Recovery grants `g-init-F` + activates.
- `proposed`, granted: recovery activates.
- `active`, k-of-3 transfers: custody split parents/composite.
  Recovery finishes the remaining transfers (giver actor), then
  settles+dissolves the parents, then appends the `fusion` entry
  (parents from the composite's recorded `derived_from` lineage;
  ALL transfers incl. pre-crash ones; `removed_mechanism` recomputed
  — channels are in-memory-only, nothing to remove after reopen).
- parents dissolved, no entry: recovery appends the entry.
- entry present, specs/artifact missing (pre-spec kill): recovery
  repairs `worlds.json` from the `create` payloads (authoritative)
  and writes `artifacts/recovery-fusion-F.json` (the ledger entry is
  authoritative; before/after inventories are not reconstructible
  and are NOT fabricated).

`ops recover` completes every partial fusion automatically (no extra
input: parents + progress are ledger-derived). Refusals (loud,
zero new partials): non-2-parent lineage, parents in odd states,
dissolved-without-marker, unsettleable parents, custody moved since
the kill. A completed fusion serves `reuse` immediately (descriptors
+ lineage restored — asserted per boundary in tests).

## 5. Fission: partial states + completion (operator supplies partition)

Same shape as fusion, except the partition is operator input (it is
NOT in the ledger until the `fission` entry lands):
- no trace (pre-create): re-run the op.
- children created/ungranted/`proposed`, k-of-3 transfers, composite
  dissolved-without-entry: recovery completes births (grant-if-
  missing + activate, incl. creating never-born children from the
  operator's presets), remaining transfers (actor = composite),
  composite dissolve, and the `fission` entry.
- entry present, specs/artifact missing: spec repair + recovery note.

Bare `ops recover` REFUSES with exact steps when a partial fission
exists (`--fission C --left L --right R --partition k=v,...` plus
presets when non-default). The supplied partition/names/presets are
the partition of record and MUST agree with pre-crash progress
(recorded transfers, created children's lineage sides/side-classes/
capabilities) or recovery refuses — never silently diverging.
Refusal classes: `ValueError` (bad partition shape, mirrors
`fission_worlds`), `RuntimeError` (progress contradiction / wrong
names+sides / wrong presets — message shows recorded progress),
`ContractViolation` (fail-closed state: non-fused composite,
unfundable grants, unsettleable composite, custody moved).

## 6. What stays operator repair (explicit, tested, never silent)

- PARTIAL QUARANTINE (LIMITS-3): `ops recover` detects
  (quarantine-reason transfers, or suspended + non-empty
  `pending_effects`, with no `quarantine` entry), prints exact steps,
  blocks settling the involved world, and still settles uninvolved
  worlds. Recipes (run with the tree on `sys.path`):
  - COMPLETE: `host, _ = api.open_run(DIR)`; for each missing
    commitment: `host.transfer_custody(sc, W, STANDBY, actor="host",
    reason="quarantine transfer: <why>",
    continuity="commitment-handoff")`; then `host.append(
    "quarantine", {"world_id": W, "standby": STANDBY,
    "commitments": [...], "transfers": [...],
    "reason": ...}, actor="host")`.
  - ROLL BACK: for each completed transfer (reverse):
    `host.transfer_custody(sc, STANDBY, W, actor=STANDBY,
    reason="quarantine rollback", continuity="rollback")`;
    then `host.reattach(W, "host", reason=...)`.
  Verify with `release.py inspect` (conservation ok) afterwards.
- CONSERVATION-FAILING LEDGERS: recover refuses (`ContractViolation`,
  names the violation: e.g. unsettled terminal). Fix the cause
  (hand-appended entries are outside the consumer contract — restore
  from backup), then re-run. `inspect --json` reports the error
  read-only without raising.
- TORN LEDGER / UNREADABLE worlds.json (disk-loss class, LIMITS-2):
  recover refuses (`RuntimeError`, "disk-loss"). Restore from
  backup; never hand-edit.
- KILL-DURING-RECOVERY: not operator repair — recovery is
  ledger-conditional, so re-running converges (proven by repeated-
  kill tests at every op + during spec repair).

## 7. Guarantees (R1 acceptance mapping)

- Refusal/failure ⇒ zero partial dissolves; ledger consistent +
  fail-closed (LIMITS-11 closed; `TestAtomicRefusal`).
- Kill at EVERY settle/fuse/fission boundary ⇒ defined partial
  state + recovery exercise, no silent partials (matrices +
  SIGKILLs + repeated kills; `TestCrash*`, `TestRepeatedKills`,
  `TestRealKill`, `TestPreSpecCrash`).
- Operator-repair paths (quarantine completion, conservation
  violations, fission input) are explicit, tested, documented
  (`TestDetection`, §5–§6).
- r1 behaviors unchanged on clean paths (conformance/demo/accept
  suites + accept field comparison — see EVIDENCE.md).
