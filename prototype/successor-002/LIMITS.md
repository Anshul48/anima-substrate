# LIMITS.md — successor-002

What this release candidate does NOT claim. Verdicts hold only inside
these (carried from successor-001, updated for fission + snapshot).

1. Toy scale, deterministic stubs. Scheduling grids are 4–5 tasks /
   4–5 slots; one deterministic backtracking solver is shared by both
   lanes (solution quality cannot differ by solver, only VALID + bytes
   + lane behavior are measured).
2. Single machine, local disk. `args_ref`/`result_ref` are host-local
   paths; kill-resume is proven across `Popen.kill()` on one machine,
   not across machines. No multi-writer concurrency, no disk loss.
3. One injected kill per S3 run, mid-adaptation, on local disk. No
   kill-during-settle, no kill during fusion/fission/quarantine
   transfer (operator repair for all four).
4. Central-bytes = canonical-JSON bytes of messages the coordinator
   handles (fragments in the central lane; commitments + escalations +
   resolutions in the local lane); direct-channel bytes counted
   separately. Both are recomputed from durable state (receipts +
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
11. `settle` is NOT atomic on refusal: if settlement fails partway
    (e.g. the unsettled-terminal probe), already-dissolved worlds stay
    dissolved+settled while the op reports failure. The ledger stays
    consistent and fail-closed; do not rely on settle atomicity.
