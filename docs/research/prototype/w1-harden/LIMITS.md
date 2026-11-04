# Limits: What Is NOT Claimed (w1-harden)

1. No live models. All search runs use TEST/scripted providers (`test://local`) or the
   deterministic stub. Spend is $0.0 by construction, not by measurement against a budget.
   Nothing here says anything about live-model behavior, cost, or latency.
2. No learned mapping. The task-spec<->formulation mapping is hand-written v1/v2 with a
   declared-loss revision rule. No learning, no inference, no mapping generality beyond
   the two pinned versions.
3. Toy evaluator. Domain verdicts come from `LocalEvaluator` (hash-score gate over
   `toy.py`-shaped content) with a fixed 0.5 threshold. It is deterministic and
   authoritative BY CONSTRUCTION for the pilot, not validated against any real domain.
4. Exists-family envelope. Evidence covers the pilot tasks only (hello.txt build, toy
   search, composite follow-up, recovery pipeline). Generality beyond these tasks is
   explicitly unclaimed; the X1G/X1H generality-gap history (+11 lines) is noted, not
   re-litigated.
5. Single-host. One process, one ledger file, no distributed coordination, no
   multi-writer story. Concurrent `Host` objects over one ledger are NOT safe (append
   interleaving + in-memory seq divergence); crash recovery assumes kill-then-reopen,
   never two live writers. Strict Host locking is deferred (plan section 4); no
   threading/concurrency test is included.
6. Assistance-(ii) untested. The delegated-assistance leg beyond the pilot's scripted
   invokes (open-ended helper behavior under a grant) has no exercise here.
7. Ledger is pure overhead except in recovery. Outside crash recovery and audit replay,
   the ledger buys nothing over direct calls — every invoke pays append + fsync-less
   write costs for entries only a future crash or auditor reads. Do not oversell it:
   the 40-entry demo ledger (vs H0's zero) is justified ONLY by (a) conservation audit,
   (b) resume-after-kill, (c) refusal evidence. Central-record wins elsewhere (X1/X2
   H1b/H2b history) do not transfer.
8. SST evidence is dirty-with-hashes, not a release. The SST-TEST run proves the adapted
   path against working-tree bytes at HEAD 079f4de (19 modified + 19 untracked files),
   with `search/controller.py` already drifted from the W1 freeze. Any SST-side change
   can invalidate the run; re-freeze on a clean pin is the SST owner's job.
9. Recovery scope: single kill boundary, artifacts on a surviving filesystem. Not covered:
   kill DURING an invoke's fn() with partial side effects (resume re-executes only when
   outputs are missing, and re-execution overwrites partial artifacts — ledger stays the
   audit trail, but phase side effects must be re-runnable); disk loss (refs are paths,
   not content hashes); kill during settle (settle is multi-append, not atomic — a crash
   between grant_return and grant_settle leaves funds moved but unmarked, and the replay
   check will then report unsettled terminal, which is honest but requires operator repair,
   not automatic healing); relationship evidence loss across reopen (in-memory only, see
   RECOVERY-REUSE.md).
10. Windows-safe is coded, not executed here. Paths/argv handling avoids POSIX assumptions
    (sys.executable allowlist + basename match, Path.resolve compares, shell=False, no
    /tmp literals in code — tests use tempfile, scripts take explicit dirs), but all runs
    in RUN-REPORT.md executed on Linux (WSL). Windows execution is untested.
