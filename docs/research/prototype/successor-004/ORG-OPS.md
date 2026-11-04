# ORG-OPS.md — consumer clauses for org operations (successor-004)

Promises a consumer can rely on when calling the six implemented org
operations. Each clause below is implemented in this tree and asserted
by a conformance test (`test_conformance.py`, class per op). Anything
not listed here is NOT promised. Prospective learning and generality
are explicitly excluded (§7): these clauses cover only what the code
does today.

Common model: a WORLD is a record with capabilities, representations,
custodians (state classes it holds), and a lifecycle state. The LEDGER
is the append-only record of every op. CUSTODY of a state class sits
with exactly one world at a time and moves only by recorded transfer.
Grants are per-world resource holdings (`max_cost_usd`, `max_time_s`,
`max_invocations`); settle returns leftover holdings to zero and
leaves a `grant_settle` marker. Canonical lifecycle strings:
`proposed/active/suspended/dissolved/retired` (v1 C4; `retired` is
declared but never exercised — no promise attaches to it).

## OP-1 FUSE — `fusion.fuse_worlds(host, chans, a, b, fused_id, ...)`

1. Commitments. Both parents MUST be `active` (else `RuntimeError`
   before any mutation) AND settleable — `check_settleable` passes
   for both (else `ContractViolation` before any mutation; R1
   extension). On success: the composite holds EVERY state
   class from both parents; both parents are dissolved; the direct
   channel between the pair is removed and refuses further sends
   (`RuntimeError`); a ledger `fusion` entry records the whole op.
   The before/after mechanism inventory in the returned record shows
   exactly one removed mechanism: `direct-channel:<a><-><b>`.
2. State custody. Every state class moves giver → composite with
   transfer actor = the GIVER (O4), continuity `sha256-of-composite`.
   No class is duplicated or dropped: the composite's custodian set
   equals the union of the parents' sets.
3. Resource ownership. The composite receives a FRESH grant
   (`GRANT_LIMITS`); each parent's grant settles on dissolve (a
   `grant_settle` marker per parent). Holdings conservation holds at
   final settle (0 stranded).
4. Lifecycle transitions. Parents `active → dissolved`
   (settle-then-move); composite `proposed → active` at birth.
5. Lineage records. Composite lineage = `derived_from` (each parent) +
   `fusion{actor, reason}`; ledger `fusion` entry =
   `{fused_id, parents, transfers, removed_mechanism, reason}`.
   `derived_from` worlds resolve to ledger `create` entries.
6. Recovery behavior. Fusion is replay-safe: `create`, custody
   `transfer`, and `lifecycle` entries rebuild the same state on
   reopen; the recovery path is `api.open_run`, which additionally
   restores creation lineage from the ledger `create` payloads (raw
   `MiniHost.reopen` keeps supplied-descriptor lineage — see
   CONSUMER.md recovery procedure). Kill-DURING-fusion IS covered
   (R1): `ops recover` completes the interrupted fusion
   idempotently (parents + progress are ledger-derived; no extra
   input needed); kill-during-recovery converges on re-run. See
   INTERRUPTION-BOUNDARIES.md §4.

## OP-2 REUSE — `fusion.reuse_composite(root, host, fused_id, followup)`

1. Commitments. Runs a follow-up task through the composite's own
   capabilities (`sched.reuse`). BEFORE any work, the lineage check
   MUST pass: ≥2 `derived_from` entries resolving to ledger `create`
   entries AND a ledger `fusion` entry for the composite — else loud
   `AssertionError` with no work done. The propose result MUST carry
   the C3 schema (`candidate_refs` + `champion_id`), asserted.
2. State custody. NOTHING moves: all work happens inside the
   composite's existing custody.
3. Resource ownership. Invokes consume the COMPOSITE's grant (no new
   grant, no settle).
4. Lifecycle transitions. NONE: the composite must be `active` before
   and stays `active` after.
5. Lineage records. No new lineage is written; the returned evidence
   carries `derived_from` + `lineage_ok: true` for the caller to file.
6. Recovery behavior. Reuse invokes are ordinary ledger invokes:
   resume-by-skip covers them like any plan step (same matcher, same
   C1–C3 shapes).

## OP-3 REVISE — `pipeline.apply_revision` (+ the O3/E1–E3 flow)

1. Commitments. A revision is a ledger `revision` entry
   `{task_id, from, to, ...}` that switches the ACTIVE representation
   between PRE-ADVERTISED versions. World records are NEVER mutated
   (reopen identity would break). A stale proposal is void ONLY by
   coordinator ruling (O3, never unilaterally); the void-notice
   references the KEPT artifact (E3, no silent deletes); the
   re-proposal basis cites the revision (O2).
2. State custody. Unchanged by revision (no transfer).
3. Resource ownership. Unchanged (no grant movement).
4. Lifecycle transitions. NONE.
5. Lineage records. Ledger `revision` entry; downstream `void`,
   `escalation`, `resolution` entries reference the same `task_id`.
6. Recovery behavior. Revision entries replay as DATA on reopen (no
   host state to rebuild); post-reopen flows re-read them from the
   ledger. A kill between revision and re-propose resumes by skip
   like any plan (demonstrated: S3).

## OP-4 REVOKE — `resume.revoke_capability` + `resume.reapply_revocations`

1. Commitments. Revocation flips the capability's required-authority
   stamp to `revocation.quarantined` (a stamp nobody holds) AND writes
   a ledger `revoke` entry `{world_id, capability, version,
   new_owner, reason}`. From then on the invoke path DENIES that
   capability with a recorded `deny` (raises `ContractViolation`).
   Capability name@version sets are UNCHANGED (reopen descriptor
   verification still passes). The named `new_owner` MUST already
   advertise the capability — revocation flips usability, it does not
   grant new capabilities.
2. State custody. Unchanged (no transfer; `new_owner` is a routing
   fact in the entry, not a custody move).
3. Resource ownership. Unchanged.
4. Lifecycle transitions. NONE.
5. Lineage records. Ledger `revoke` entry (see §1); the denied retry
   leaves a `deny` entry referencing the invoke action.
6. Recovery behavior. THE CALLER MUST CALL `reapply_revocations(host)`
   after EVERY reopen: reopen rebuilds capabilities from supplied
   descriptors (pre-revocation authorities), so without re-application
   a revocation silently LAPSES (demonstrated in the conformance
   test). Re-application writes no new ledger entries (idempotent
   replay of the existing `revoke` entries).

## OP-5 QUARANTINE — `fusion.quarantine_world(host, world, standby, ...)`

1. Commitments. Suspends the failed world with `pending_effects`
   naming each commitment's transfer to the standby, then transfers
   EVERY commitment to the standby. Invokes against the quarantined
   world are DENIED by the not-active rule with a recorded `deny`.
   The standby (which must exist and be `active`) completes the
   transferred commitments with its own capabilities. A ledger
   `quarantine` entry records `{world_id, standby, commitments,
   transfers, reason}`.
2. State custody. Every commitment class moves world → standby with
   transfer actor = `host` — the ONE documented O4 exception (the
   giver is suspended and cannot act; see OBLIGATIONS.md).
3. Resource ownership. The quarantined world's grant is NOT settled at
   quarantine time (it settles at finish); the standby spends its OWN
   grant on the transferred work.
4. Lifecycle transitions. World `active → suspended` (stays suspended
   until finish reattaches it for settle); standby unchanged
   (`active`).
5. Lineage records. Ledger `checkpoint` entry carries
   `pending_effects`; `lifecycle` entry records `active → suspended`;
   ledger `quarantine` entry (see §1).
6. Recovery behavior. Suspend + transfers replay on reopen; the world
   reopens SUSPENDED with its `pending_effects` intact in the ledger.
   Kill-during-quarantine-transfer is NOT covered (operator repair —
   but now DETECTED with explicit steps by `ops recover`, never
   silent; see INTERRUPTION-BOUNDARIES.md §6).

## OP-6 FISSION — `fusion.fission_worlds(host, chans, composite, ...)`

1. Commitments. Splits a RECORDED fused composite into two worlds per
   the partition record. ALL preconditions are validated BEFORE any
   host mutation (no partial effects on rejection): composite
   `active`; a ledger `fusion` entry names it; the partition covers
   EXACTLY the composite's state classes, each assigned to one of the
   two distinct children, BOTH sides non-empty. The composite MUST
   also be settleable (R1 extension: `ContractViolation` before any
   mutation otherwise). Rejections raise `ValueError` (bad
   partition/input, incl. active-but-non-fused targets),
   `RuntimeError` (inactive target), or `ContractViolation`
   (unsettleable target) naming the defect.
   On success a ledger `fission`
   entry records the whole op and the direct channel between the
   children is RESTORED (fresh, 0 bytes; sends flow again).
2. State custody. Every state class moves composite → its partitioned
   child with transfer actor = the COMPOSITE (the giver, O4),
   continuity `fission-partition`. Post-state: each child's custodian
   set equals its partition side exactly.
3. Resource ownership. Each child receives a FRESH grant; the
   composite's grant settles on dissolve (`grant_settle` marker).
   Holdings conservation holds at final settle (0 stranded).
4. Lifecycle transitions. Children `proposed → active` at birth;
   composite `active → dissolved` (settle-then-move).
5. Lineage records. Each child's lineage = `derived_from` (composite)
   + `fission-of{fusion, fusion_parents, side, partition}` (NAMES the
   fusion being split: composite id + its parents) +
   `fission{actor, reason}`; ledger `fission` entry =
   `{composite, children, partition, fusion, transfers,
   restored_mechanism, reason}`.
6. Recovery behavior. Fission is replay-safe (same entry classes
   as fusion) through the same `api.open_run` recovery path
   (lineage restored from ledger `create` payloads). Kill-DURING-
   fission IS covered (R1): `ops recover --fission C --left L
   --right R --partition ...` completes it idempotently — the
   operator supplies the partition of record, which MUST agree with
   pre-crash progress (else loud refusal, never silent divergence).
   Kill-during-recovery converges on re-run. See
   INTERRUPTION-BOUNDARIES.md §5.

## §7 Explicitly excluded (not promised, not implemented)

No local POLICY invention; no learned mappings, evaluators, or
revision; no developmental-recipe inheritance; no autonomous
adaptation discovery; no cross-host fusion/fission/quarantine/reuse;
no genuinely NEW capabilities or representation versions after world
creation (both sets are fixed at birth; revision/revocation only flip
which pre-advertised entry is usable); no multi-writer safety; no
disk-loss tolerance; no kill-during-QUARANTINE-transfer completion
automation (detection + steps only). Settle refusal-atomicity and
kill-during-settle/fusion/fission recovery ARE promised (R1; see
LIMITS.md items 3/11 + INTERRUPTION-BOUNDARIES.md), as is
crash-atomicity of every op-path side file (R3: temp+`os.replace`;
a kill leaves old-or-new, never torn — the F2 window is closed).
A consumer relying on any excluded item is outside this contract.

Successor-004 note (F1 warning kept): a direct `settle_op` / `ops
settle` on a composite with a partial fission does NOT refuse —
settle is custody-orthogonal by contract. Only `recover_op`'s
targeted settle withholds still-blocked worlds; complete the
fission through `recover_op` first (see
INTERRUPTION-BOUNDARIES.md §5).
