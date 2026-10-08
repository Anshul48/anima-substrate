# LIMITS.md — successor-005

What this release candidate does NOT claim. Verdicts hold only inside
these (carried from successor-004; S5 adds the bounded procedure
participant: items 12–14; N1/N2 narrowings applied).

1. Toy scale, deterministic stubs. Scheduling grids are 4–5 tasks /
   4–5 slots; one deterministic backtracking solver is shared by both
   lanes (solution quality cannot differ by solver, only VALID + bytes
   + lane behavior are measured).
2. Single machine, local disk. `args_ref`/`result_ref` are host-local
   paths; kill-resume is proven across `Popen.kill()` on one machine,
   not across machines. No multi-writer concurrency, no disk loss.
   R3 narrows the SIDE-FILE kill-tear exposure to zero on op
   paths: every whole-file side write is temp+`os.replace`
   (old-or-new, never torn — mechanism + write-interior tests, see
   INTERRUPTION-BOUNDARIES.md §1). The LEDGER is explicitly NOT
   covered by that claim: a kill inside an append may tear the
   tail line, and the specified landing is a loud disk-loss
   refusal (tested), not recovery. What stays out of scope:
   genuine media/power loss, multi-writer races, and fsync-grade
   durability (no fsync is issued).
3. One injected kill per S3 run, mid-adaptation, on local disk.
   Kill-during-settle and kill-during-fusion/fission are COVERED
   (defined behavior + `ops recover` completion, proven by kill-at-
   every-boundary tests incl. repeated kills — see
   INTERRUPTION-BOUNDARIES.md). Kill during QUARANTINE transfer
   remains operator repair (detected + explicit steps via recover,
   never silent; completion automation out of scope).
4. Central-bytes = canonical-JSON bytes of messages the coordinator
   handles (fragments in the central lane; commitments + escalations +
   resolutions in the local lane); direct-channel bytes counted
   separately. Both are recomputed from durable state (LIMITS-2 scope: receipts +
   ledger), so they survive the kill boundary. The 2.61x calibration
   is a serialized-bytes ratio inside the task envelope ONLY — no
   token/attention/cost equivalence, no cross-task generality.
5. Fusion AND fission are structural but single-host: worlds on one
   ledger fuse into one composite / split back into two children on
   the same ledger. Cross-host fusion/fission/quarantine are NOT
   implemented. Quarantine (failure-driven) and fission (planned)
   are the two separation paths (see SEPARATION-PATHS.md).
6. Revocation is an authority-stamp flip + ledger `revoke` entry,
   replayed after reopen ONLY if the caller runs
   `reapply_revocations` (raw reopen lapses — demonstrated in
   conformance). Capability sets are fixed at world creation;
   genuinely NEW capabilities still require a new world.
   Representation revision switches the ACTIVE version between
   pre-advertised versions via a ledger `revision` entry; the world
   record itself is never mutated.
7. SST leg: TEST fixtures only ($0, offline). The frozen
   `run_search -> SearchResult` envelope is consumed from the
   vendored snapshot (`snapshot_hash 5f1f3789...`, all 54 files) with
   pinned `pydantic==2.13.5`. Label is SUBSTRATE-QUALIFIED SNAPSHOT:
   NO SST-owner release acceptance is claimed or implied; the
   SST-owner evidence request (clean landing + stable
   `run_search`/`TEST` confirmation) stands. Live-model behavior is
   unqualified; nothing here inherits it.
8. Ledger timestamps (`at` fields) are wall-clock and excluded from
   byte-identity comparisons (artifact bytes are timestamp-free and
   ARE compared). Run dirs embed a UTC timestamp; reruns create new
   dirs rather than overwriting.
9. No per-grant siloed balances, no content-addressed refs (paths
   retained), no relationship-evidence persistence across reopen.
   Lifecycle `retired` is declared but never exercised. Channels are
   in-memory only (never persisted; CLI fuse ensures-then-removes).
10. No learning of any kind: no local POLICY invention, no learned
    mappings/evaluators/revision, no recipe inheritance, no
    autonomous adaptation discovery (see ORG-OPS.md §7).
11. CLOSED by R1. `settle` (routing.finish_worlds, api.settle_op,
    `ops settle`) is ATOMIC on refusal: the whole batch is rehearsed
    (ledger conserves + every world settleable) before the first
    dissolve, so a refusal raises ContractViolation with ZERO
    partial dissolves and ZERO partial grant_returns — only a `deny`
    entry is recorded. The ledger stays consistent and fail-closed
    (as before). Single-world settle-then-move (dissolve/fuse/fission
    paths) carries the same guarantee via check_settleable. Kill-
    DURING settle execution is the defined interruption boundary
    (recovery via `ops recover --worlds ...`, idempotent).
12. Bounded procedure participant (S5): the host is an accountable
    executor for caller-supplied procedures — not a sandbox for
    adversaries' code. Callers supply procedures AND bear their
    content risk; the host vouches only executed-bytes-equality,
    scoped-invocation accounting, and loud typed failures (see
    CONSUMER.md §8, ORG-OPS.md OP-7). No procedure correctness,
    usefulness, determinism, or general-compute qualification is
    claimed; no cost/speed superiority over direct execution.
13. Procedure non-claims, normative (P11–P13): writes outside the
    state dir are CONTRACTUAL (cannot be prevented or reliably
    detected stdlib-only; the caller vouches; no enforcement
    claimed); network is CONTRACTUAL, not isolated (offline is a
    caller obligation plus proxy hygiene; the executor performs no
    network I/O itself); memory/RSS caps are NOT CLAIMED (P5 output
    caps bound exfiltration bytes, not RSS). Orphan handling is
    tolerated-by-construction, not enforced cleanup. Every durability sentence here carries its process-crash / power-loss + no-fsync separation (no fsync is issued on proc paths).
14. Procedure interruption scope: defined landings L1–L5 (re-run /
    DONE-adopt exactly-once / loud disk-loss refusal / convergence)
    for process crashes only — power/media loss stays the disk-loss
    class, and no checkpoint-resume exists inside steps. Recovery
    never spawns; `revise_op` is never used for procedure revision
    (new content ⇒ new world).
