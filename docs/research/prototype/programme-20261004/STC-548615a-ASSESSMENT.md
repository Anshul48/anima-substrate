# STC 548615a integration assessment (substrate read-only refresh, 2026-10-07)

Scope: refresh the STC integration assessment against frozen release `548615a`.
STC repo read at `../stc` (read-only; no writes made there). All identities
below were observed via `git rev-parse/log/show/status` and direct file reads
at STC HEAD.

## 1. Release identity (confirmed)

- Full hash: `548615aecb2ca368b5221b20cf90a701eda0acc2`
- Subject: `Freeze: bounded closeout recovery/durability/rendered (record-only over 1d1c535)`
- Author/committer: Anshul48 <anshulraj48@gmail.com>
- Date: 2026-10-07T04:11:44+00:00 (author == committer)
- Body: recovery fail-closed + explicit `stc_restart`, durability
  wipe-restore proof, UI-driven pixel journey j1–j11, independent audit
  with D1+R1 fixes applied; pins unchanged (SST df78f42, DSH 639ed01,
  prompt-kit 4f442a6); spend ~$3.41 of HARD $10 TOTAL.
- Worktree state: HEAD == `548615a`; porcelain = 12 lines, ALL untracked
  (`??`), ZERO tracked modifications. No tags on the commit
  (`git describe` returns bare `548615a`).
- Parent: `1d1c535f6c062e9f636440a087d76f9fc39ed93c` (recovery repair).
  The freeze delta is record-only: `docs/STC-DSH-RECORD.md` (+56) and
  `docs/STC-DSH-RELEASE.md` only. Code freeze = `1d1c535`; the release
  doc's "STC backend" pin row accordingly cites `1d1c535`. Cite both:
  code `1d1c535`, freeze record `548615a`.

Relation to COMPLETION-MAP §6 (which cites 62cf5e6-era): `62cf5e6` IS an
ancestor of `548615a`, 5 commits behind:

- `b4ffcd5` Scope mutmut derivation and mirror pre-seed to external targets
- `1f93f15` fix(stc): pre-seed unscoped .py siblings in external mutmut mirrors
- `2723822` docs(stc): freeze chapter — finalization A–G acceptance record
- `1d1c535` fix(stc): honest recovery contract — fail-closed recover + explicit stc_restart
- `548615a` Freeze: bounded closeout recovery/durability/rendered (record-only)

Diffstat 62cf5e6..548615a = 10 files: 2 freeze-chapter docs, recovery
tool layer (`dsh-plugin-stc/src/stc-recovery.ts`, `stc-run.ts` + 2 test
files), mutmut external-target scoping (`dialectic_runner.py`,
`selection.py`, `substrate/runner.py`, `tests/unit/test_mutmut_scope.py`).

## 2. Supported consumer-facing interface

Primary supported surface is the DSH plugin (local-production envelope,
single-user Linux/WSL, loopback browser). Entry points:

- Install: `dsh plugin --profile web add file:/path/to/stc/dsh-plugin-stc`
  (after `pnpm install --frozen-lockfile && pnpm build` in
  `dsh-plugin-stc/`; packaged installs load `lib/index.js`).
- Boot: `DSH_HOME` + `STC_ROOT` + `STC_DSH_STORE` + `STC_SST_ROOT` +
  `STC_PROMPT_KIT_ROOT` env, then `dsh web --no-open`.
- Tools (all `stc_*`, registered in `dsh-plugin-stc/src/`): `stc_run`,
  `stc_status`, `stc_log`, `stc_cancel`, `stc_interrupt`, `stc_recover`,
  `stc_restart`, `stc_redirect` (run lifecycle, `stc-run.ts` +
  `stc-recovery.ts`), plus `stc_ping`, `stc_dossier`, `stc_preview`
  (`stc-tools.ts`) and brief/exec/policy/present modules.
- Backend CLI: `stc = stc.cli:main` (`pyproject.toml` `[project.scripts]`;
  click+rich dual-mode, `--json` for headless automation; command spec in
  `05_CLI_AND_INTERFACE_SPEC.md`).
- Backend Python packages: `stc.integration` (DialecticRunner, lease_git,
  custody, dossier), `stc.substrate` (receipt/runner quality gates).

Contracts / freeze-chapter docs:

- `docs/STC-DSH-RELEASE.md` — pins table, install/startup/verify, durable
  install, recovery contract, explicit limits.
- `docs/STC-DSH-RECORD.md` — `## Freeze: STC finalization A–G`
  (code candidate `1f93f15`, pins, A–G evidence, audit, spend, launch /
  upgrade / rollback, carried limits) and `## Bounded closeout:
  recovery/durability/rendered` (code `1d1c535`, recovery/durability/
  rendered closeout, D1+R1 audit fixes, spend, HALT).
- `docs/STC-SST-CALLER-CONTRACT.md` — STC→SST caller contract
  (deliberate pin, called surface, ownership split, pin-advance
  procedure). STC-owned; explicitly NOT SST-owner acceptance.
- `dsh-plugin-stc/DSH_PIN` — machine-readable upstream/toolchain pin file.

Critical scoping fact (UNCHANGED by this freeze): every STC contract
targets STC's own DSH/SST consumption. "Substrate" inside STC
(`src/stc/substrate/`, "the substrate fails the gate closed") is STC's
internal quality-gate engine, not this substrate project. There is still
NO substrate-facing envelope, no dossier/verdict schema offered to
substrate, no owner note naming a substrate-consumable artifact. The P1
`stc_adapter.py` docstring ("STC exposes NO substrate-facing runtime
envelope") remains accurate at `548615a`.

## 3. Exact dependency pins (at 548615a)

From `EXTERNAL_PINS` (`src/stc/integration/lease_git.py`), the caller
contract, the freeze chapter, and `DSH_PIN` (all mutually consistent):

| Component | Pin |
|---|---|
| STC code | `1d1c535f6c062e9f636440a087d76f9fc39ed93c` (freeze record `548615a…` over it) |
| SST | `df78f42894a65c48f524337a498032617689a013` |
| prompt-kit | `4f442a6c829bc06b60f9979fdc8d7585e30bac9a` |
| trace | `a24a937009fec41e6dcb6d2ca31d3c1783ac97f7` (in EXTERNAL_PINS; release table omits it) |
| DSH upstream | `639ed015397290b3745d163aafe02ffee4aa3f84` (short `639ed01`, v0.2.0-rc.2) |
| node / pnpm / esbuild | 22.23.3 (SHA256 tarball) / 11.7.0 (corepack) / 0.28.2 (lockfile) |
| Model route | `deepseek/deepseek-v4-pro-0813` via Sail x-api-key |
| csvledger seed | `6e34c38` |
| Run champions | run-1 `d6375dc218141a5a637eec2bd6b653bbd96ca814`; run-2 base `7c85740ef6655e7bd69f09cfa6f5c24c729a572d` + champion `2976169bb556d733837af73ef40b945367787c6b` |

SST integrity mechanics (unchanged): no vendoring; `STC_SST_ROOT` env
else sibling `../sst`; leases fail closed unless spot files
(`__init__.py`, `core/contracts.py`, `sandbox/custody.py`) match pin
blobs; dirty SST tree refused at lease time; `sst_compat_probe.py`
reports COMPATIBLE / DIRTY / MISSING-SURFACE / NO-GIT.

## 4. Recovery implications — explicit full replay VERIFIED

Implemented in `1d1c535` (`dsh-plugin-stc/src/stc-recovery.ts`,
`stc-run.ts`); documented in RELEASE.md "Recovery contract (frozen at
`1d1c535`)" and the closeout chapter. Verified by reading the
implementation, not just the docs.

Semantics (code-confirmed):

- `recover()` NEVER relaunches. Outcomes: `reattached` (job still live
  in-process — the ONLY outcome that persists a recovery stamp and the
  only true resume); `needs-decision` + blockers + evidence (every
  gone-job case); `already-terminal`; `refused-redirected`. Status
  queries are pure reads and never mutate records.
- Even FULLY attested runs (identity verified, every ledger effect
  `completed` with proof) report `needs-decision`: the backend
  re-executes argv identically and has NO skip mechanism, so an
  automatic resume would repeat completed effects. The fully-attested
  branch says so explicitly (`stc-recovery.ts` recover() tail).
- `stc_restart` is the SOLE continuation path: typed `confirm="RUN"`;
  interrupted-state only; refuses live jobs, terminal/cancelled/
  redirected/never-interrupted runs (their proof stands — start a new
  run instead). It spawns a linked child run with the IDENTICAL argv and
  stamps the parent `restartedFrom` + `replay=full` + `skipped: []`.
  Ledger effects recorded on the parent MAY REPEAT — nothing is skipped.
- `stc_interrupt` accepts an optional `effects` claim (JSON array of
  `{id, kind, status, proof?}`), validated BEFORE anything records; a
  bad claim fails closed with no partial ledger. `completed` without
  `proof` is rejected.

Cost: every restart pays FULL recompute (time/compute of the entire
command again) plus repeated side effects. The kill-drill (SIGKILL
mid-run, external counter 1→2, distinct pids) proves the repeat is
explicit-by-design, not idempotent: the counter advances because the
effect re-executes. Checks: unit 31/31, e2e 3/3, battery 99/99.

Implications for substrate interruption/recovery composition:

1. STC recovery is restart-from-scratch with effect-repeat, never
   checkpoint-resume. Any composition where substrate delegates
   execution to STC runs must budget full re-execution cost on every
   interruption and must tolerate (or externally dedupe) repeated
   ledger effects. `recover()` output is decision support
   (blockers + evidence), not resumption.
2. If substrate needs resume-with-skip (partial progress preserved),
   STC CANNOT provide it at this freeze — that is a genuine capability
   gap, not a configuration detail. Do not plan a composition that
   assumes skip lists; the stamp literally records `skipped: []`.
3. Interruption requires a DECLARED checkpoint (`markInterrupted`
   refuses empty checkpoints; never-interrupted runs refuse both
   recover-resume and restart). Substrate-driven flows must route all
   stops through `stc_interrupt` with a checkpoint + effects claim, or
   the run is unrecoverable-by-restart.
4. Terminal/cancel/redirect proofs are sticky and refuse restart;
   composition must start a NEW run (new run id, no `restartedFrom`
   link) after any of those — lineage breaks there by design.
5. Portability caveat (durability chapter): replay-after-wipe of frozen
   runs needs `/tmp/stc-rt` restaged from pins because argv paths are
   absolute. A substrate composition that moves run stores across hosts
   must restage identical absolute paths or replay breaks.

## 5. Compatibility deltas vs what substrate consumes/pins

What substrate consumes today (P1-adapters, deliberately pinned):

- `sst_adapter`: SST snapshot at `df78f42`, 54 files, snapshot hash
  `5f1f3789…`, observed (NOT owner-declared) `run_search -> SearchResult`
  8-key envelope; `qualified_for_substrate_consumption: false`
  (Ask 1 open).
- `stc_adapter`: vendored STC DOCS ONLY at 8fa8ac3-era hashes; a
  doc-reader + UNQUALIFIED gate by design. `substrate_facing_envelope:
  "NONE"`.

Deltas at 548615a:

- SST pin CONVERGED, no action: STC `EXTERNAL_PINS["sst"]` =
  `df78f42…` == substrate's SST `tree_commit`. prompt-kit `4f442a6…`
  and trace `a24a937…` also match PINS.json `external_pins_at_head`.
  (COMPLETION-MAP §6 already noted sst=df78f42 unchanged; still true.)
- No SST-called-surface change in 62cf5e6..548615a affecting
  substrate: the `dialectic_runner.py`/`selection.py` delta only adds
  external-target mutmut scoping (`is_external_target_root`,
  `target_root`/`external_target` params); `execute_search` construction
  and the caller-contract §2 surface are untouched. `sst_adapter`
  unaffected (SST bytes unchanged — different repo, not moved).
- `stc_adapter` correctly stays UNQUALIFIED: 548615a docs
  (RELEASE/RECORD/caller-contract) hash-differ from the pinned
  8fa8ac3-era copies, but the adapter is deliberately pinned and must
  NOT be re-pinned until Ask 2B lands ("re-pin only when pursuing STC
  consumption"). No adapter change required or desired now.
- COMPLETION-MAP §6 refresh note: STC HEAD is now `548615a` (+5 since
  `62cf5e6`, Oct 7); porcelain back to 12 untracked-only, zero tracked
  modifications. The §6 "Ask 2A landed/stale" note stands; "2B genuinely
  missing" stands.

## 6. Asks: resolved vs genuinely remaining

Resolved independently (no owner action needed):

- R1. Freeze identity: `548615a` / code `1d1c535`, byte-exact, clean of
  tracked modifications. Q-STC-0 (byte identity) is SATISFIABLE.
- R2. Ask 2A (mechanical: clean commit + SST adoption): LANDED/STALE —
  `EXTERNAL_PINS["sst"]=df78f42…` committed since 5c65427, unchanged
  through the freeze; worktree dirt is untracked-only.
- R3. Recovery semantics: INDEPENDENTLY VERIFIED in code — explicit
  full replay confirmed, fail-closed recover confirmed, no hidden
  resume-with-skip. Substrate can plan composition on this contract
  without asking the STC owner anything.
- R4. Pin compatibility: STC's SST/prompt-kit/trace pins match
  substrate's pinned bytes; no pin conflict to reconcile.

Genuinely remaining (ownerexperienced, cannot self-resolve):

- A1 (Ask 2B, STC owner): NAME the substrate-consumable artifact, if
  any — doc set? dossier schema? verdict record? — in a committed owner
  note, or state "nothing — STC is not a substrate producer" (that
  sentence retires Q-STC-1..2). The freeze adds no substrate-facing
  surface, so this ask is unchanged and still the SOLE STC-side blocker.
- A2 (Ask 1, SST owner): owner contract + gate record at a pinned
  commit. The STC freeze does NOT supply this: the STC caller contract
  is STC→SST and its §5 marks live-model consumption at the STC tree
  UNQUALIFIED. Unchanged.
- A3 (compositional, substrate-internal): decide whether full-replay
  recovery is acceptable for any U-branch real-use claim involving STC
  execution, given §4 costs (full recompute + repeated effects + no
  skip). If resume-with-skip is required, STC at 548615a is disqualified
  as an execution substrate and the claim must be SST-only or
  differently architected. Recommend recording this decision in
  PRODUCER-ASK or the U-branch plan before any STC-execution design.

## 7. Bottom line

`548615a` is a genuine, byte-verified freeze: record-only over
`1d1c535`, clean worktree (12 untracked, 0 tracked mods), pins
converged with substrate's SST bytes, and an honest fail-closed
recovery contract with explicit full-replay restart — verified in
implementation, not just prose. It changes NOTHING about substrate's
consumption posture: `sst_adapter` unaffected, `stc_adapter` correctly
remains an UNQUALIFIED doc-reader, Ask 2A stays landed/stale, and the
only STC-side deliverable substrate still needs is the Ask 2B artifact
decision. The new load-bearing information for substrate is the
recovery contract: plan any STC-execution composition around
restart-from-scratch with effect-repeat, or rule STC execution out.
