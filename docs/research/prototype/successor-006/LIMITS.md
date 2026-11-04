# LIMITS.md — successor-006

What this tree does NOT claim. Every verdict in this tree holds only
inside these limits. Items 1–11 are carried from successor-005
(LIMITS.md there); items 12–16 are new or narrowed in successor-006.

1. Toy scale, deterministic stubs. Scheduling grids are 4–5 tasks /
   4–5 slots; one deterministic backtracking solver is shared by all
   worlds (only VALID + bytes + lane behavior are measured).
2. Single machine, local disk. `args_ref`/`result_ref` are host-local
   paths; kill-resume is proven across `Popen.kill()` on one machine,
   not across machines. No multi-writer concurrency, no disk loss.
   Side files are crash-atomic (temp+`os.replace`, old-or-new); the
   LEDGER is explicitly NOT tear-proof (a kill inside an append may
   tear the tail line → loud disk-loss refusal, tested). No fsync is
   issued anywhere: the guarantee is atomicity across a PROCESS
   crash, never durability across power/media loss.
3. One injected kill per J1/S3 run, mid-task, on local disk.
   Kill-during-settle/fusion/fission/quarantine-transfer/procedure-
   step are covered (defined behavior + recovery completion, proven
   by kill-at-every-boundary tests incl. repeated kills and a real
   SIGKILL leg). Kill DURING repair converges on re-run.
4. Central-bytes accounting is a serialized-bytes ratio inside the
   task envelope ONLY (carried calibration claim, not re-proven
   here). J1 work plans claim NO lane bytes (no clarification
   dialogue by design).
5. Fusion/fission/quarantine/nest are structural but single-host.
   Cross-host anything is NOT implemented.
6. Revocation is an authority-stamp flip replayed after reopen ONLY
   via `reapply_revocations` (raw reopen lapses — demonstrated in
   carried conformance). Capability sets are fixed at world creation;
   genuinely NEW capabilities require a new world. Representation
   revision switches the ACTIVE version between pre-advertised
   versions only.
7. SST leg: NOT CARRIED in this tree (stdlib-only constraint).
   `with_sst=True` / `run_demo` refuse loudly. No SST behavior of
   any kind is claimed here.
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
    autonomous adaptation discovery. J1 delegation amounts are
    OPERATOR-SUPPLIED (passed to `nest_op`), never invented.
11. `settle` is ATOMIC on refusal (zero partial dissolves; only a
    `deny` entry). A DIRECT `settle_op` on a composite with a
    partial fission still does NOT refuse (custody-orthogonal by
    contract — carried F1 warning); only `recover_op`'s targeted
    settle withholds still-blocked worlds. Complete partial ops
    through `recover_op` first.
12. (NEW) Nesting is LEDGER-RECORDED, not OS-isolated: a nested
    experiment world is a peer world with `derived_from` lineage + a
    `nest` entry, sharing one ledger and one filesystem with its
    project. No containment, sandboxing, or resource policing beyond
    grant accounting is claimed.
13. (NEW) The quarantine complete-vs-rollback DECISION is not
    automated and never will be in this envelope: `recover_op`
    detects + points at the supported ops, and the operator chooses.
    A complete refused because a rollback started (or vice versa)
    must be finished in the started direction — the ops refuse to
    mix handoff directions rather than guess.
14. (NEW) J1 "reuse unmodified" means: the composite world record,
    custody, grants, lifecycle, and lineage are byte-identical
    between the two follow-up tasks (asserted). It does NOT mean
    cross-ledger portability: both reuses run on the SAME ledger.
    The export bundle (`j1-export-*.json`) is evidence, not a
    portable executable — consuming it on another host is
    unimplemented and unclaimed.
15. (NEW) Procedure participant: carried byte-identical, covered by
    byte-identity + a 3-test smoke ONLY. The full 57-test procedure
    suite was not re-run in this tree; procedure behavior beyond
    advertise/run/skip/deny-smoke is explicitly unverified here.
16. (NEW) J1 verify is single-checker: one `sched.verify` verdict per
    task (optionally cross-world). No independent second checker, no
    adversarial tasks, no quality bar beyond VALID + the toy
    prefs-total. The journey demonstrates mechanics, not task value.
