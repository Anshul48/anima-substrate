# LIMITS.md — successor-001

What this prototype does NOT claim. Verdicts hold only inside these.

1. Toy scale, deterministic stubs. Scheduling grids are 4–5 tasks /
   4–5 slots; one deterministic backtracking solver is shared by both
   lanes (solution quality cannot differ by solver, only VALID + bytes
   + lane behavior are measured). Same envelope as X3.
2. Single machine, local disk. `args_ref`/`result_ref` are host-local
   paths; kill-resume is proven across `Popen.kill()` on one machine,
   not across machines. No multi-writer concurrency, no disk loss
   (inherited non-goals from WORLD-CONTRACT-v1).
3. One injected kill per S3 run, mid-adaptation, on local disk. No
   kill-during-settle (operator repair, per v1 non-goals), no kill
   during fusion.
4. Central-bytes = canonical-JSON bytes of messages the coordinator
   handles (fragments in the central lane; commitments + escalations +
   resolutions in the local lane); direct-channel bytes counted
   separately. Both are recomputed from durable state (receipts +
   ledger), so they survive the kill boundary.
5. Fusion is structural but single-host: two worlds on one ledger fuse
   into one composite on the same ledger. Cross-host fusion,
   composite fission, and general reversibility are NOT implemented;
   the ONE declared separation path is failed-participant quarantine
   with commitment transfer.
6. Revocation is an authority-stamp flip + ledger `revoke` entry,
   replayed after reopen. Capability sets are fixed at world creation
   (reopen verifies name@version); genuinely NEW capabilities still
   require a new world. Representation revision likewise switches the
   ACTIVE version between pre-advertised versions via a ledger
   `revision` entry; the world record itself is never mutated (reopen
   identity would break otherwise).
7. SST leg: TEST fixtures only ($0, offline). The frozen
   `run_search -> SearchResult` envelope is consumed from staged
   cand-02 bytes, but the coordinator's staging pin
   `df16a1a29cd6c21c7fbfebbf31b41583` does NOT reproduce against current
   bytes under any of ~220 documented constructions (see
   SUCCESSOR-REPORT.md §SST): consumption proceeded under the
   recorded-manifest posture, and the emitted 50-file manifests (two
   runs preserved — the staged tree drifted by 3 files between them
   via concurrent external edits) are the re-pin material.
   Live-model behavior is unqualified (SST-owner
   track); nothing here inherits it.
8. Ledger timestamps (`at` fields) are wall-clock and excluded from
   byte-identity comparisons (artifact bytes are timestamp-free and
   ARE compared). Run dirs embed a UTC timestamp; reruns create new
   dirs rather than overwriting.
9. No per-grant siloed balances, no content-addressed refs (paths
   retained), no relationship-evidence persistence across reopen
   (carried v1 non-goals).
