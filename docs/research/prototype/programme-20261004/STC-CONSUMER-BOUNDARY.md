# STC consumer boundary for substrate (2026-10-07)

Scope: what Ask 2B blocks, what an explicitly EXPERIMENTAL (unqualified)
consumer adapter may still touch, and the composition rules it must
enforce. Design + boundary only — no adapter code changes.

Sources: `STC-548615a-ASSESSMENT.md` (STC freeze read at `../stc`,
read-only), `COMPLETION-MAP.md` P1-prod row (§5) + producer state (§6),
`P1-adapters/stc_adapter.py` + `sst_adapter.py` + `PRODUCER-ASK.md`,
`U-execute/` filed baseline (`direct_run.py` schema-3 is THE baseline
form; checker rev4; RULES-AMENDMENT-2(a)–(f)).

Freeze citation: STC code `1d1c535f6c062e9f636440a087d76f9fc39ed93c`,
freeze record `548615aecb2ca368b5221b20cf90a701eda0acc2`.
Note: STC HEAD has since moved one docs-only commit forward
(`55d74e7` "Docs: short STC operator guide"); the freeze identity and
all pins below are cited at `548615a` and are unaffected.

## 1. Blocked vs unblocked without Ask 2B

Ask 2B = STC owner names the substrate-consumable artifact, if any,
in a committed owner note (PRODUCER-ASK.md step B). Until that note
lands, the gating fact is: **every STC contract targets STC's own
DSH/SST consumption** — "substrate" inside STC (`src/stc/substrate/`)
is STC's internal quality-gate engine, not this project. There is no
substrate-facing envelope, no dossier/verdict schema offered to
substrate, no owner note naming a substrate-consumable artifact.

| # | Claim / consumption path | Status w/o 2B | Why |
|---|---|---|---|
| B1 | Claim STC material is "qualified for substrate consumption" (adapter verdict QUALIFIED) | BLOCKED | `qualification_report` requires a parsed OWNER-RELEASE.json; all four criteria gap without it. |
| B2 | Consume any STC schema as a STABLE envelope (dossier, verdict record, run/ledger record) | BLOCKED | No STC surface targets substrate consumption; nothing is frozen-to-pin. Any parse is observed-shape, owner-revocable. |
| B3 | U-branch real-use acceptance claim involving STC execution | BLOCKED | P1-prod row: "Consume qualified exports only." STC has no qualified export; U-execute filed baseline is SST-snapshot-confined (`p_sst_snapshot_confined`), STC absent. |
| B4 | Re-pin `stc_adapter` vendored docs to 548615a-era bytes | BLOCKED (deliberately deferred) | PINS.json STC section pins 8fa8ac3-era docs by design; "re-pin only when pursuing STC consumption." Re-pinning without 2B buys nothing and churns the gate. |
| B5 | Claim resume-with-skip / checkpoint-resume over STC execution | BLOCKED (capability gap, not paperwork) | `stc_restart` stamps `replay=full`, `skipped: []`; backend has NO skip mechanism. No owner sentence can grant what the code lacks. |
| U1 | Run STC's own tools/CLI against pinned bytes as an operator ( hands-on evaluation, probes) | UNBLOCKED | Operating STC's supported interface is ordinary use of STC; no substrate consumption claim attaches. |
| U2 | EXPERIMENTAL consumer adapter: invoke STC via §2 surface, label output UNQUALIFIED end-to-end | UNBLOCKED | Allowed iff the §2 contract (pins, env, labels, forbidden claims) and §3 composition rules hold. Produces engineering signal, never evidence. |
| U3 | Plan composition on the recovery contract (fail-closed recover, full-replay restart) | UNBLOCKED | Code-verified in `stc-recovery.ts`/`stc-run.ts` at 1d1c535; needs no owner action (assessment R3). |
| U4 | Cite byte identities and pin convergence (STC code/record hashes, SST df78f42 match) | UNBLOCKED | Byte identity is satisfiable now (Q-STC-0); pins converged, no conflict. |
| U5 | Negative / disqualification findings ("STC at 548615a is disqualified as an execution substrate for claim X because …") | UNBLOCKED | Negatives need no producer permission; record with the disqualifying reason (e.g. B5). |

Standing rule: U-paths never graduate to B-paths by repetition. Ten
successful experimental runs are ten unqualified observations, not a
qualification record.

## 2. Experimental-adapter contract

An EXPERIMENTAL adapter may use STC's **supported interfaces only** —
the surfaces STC itself documents and freezes for its own operation.
It may NOT reach into internals (run-store files, ledger bytes,
in-process state) except through these interfaces.

### 2.1 Allowed surface (exact)

1. **DSH plugin tools** (primary; registered in
   `dsh-plugin-stc/src/`, packaged `lib/index.js`):
   `stc_run`, `stc_status`, `stc_log` (run lifecycle reads/exec),
   plus the recovery path `stc_interrupt`, `stc_recover`,
   `stc_restart`, `stc_cancel`, `stc_redirect` (governed by §3).
   Read-only auxiliaries `stc_ping`, `stc_dossier`, `stc_preview`
   are allowed as observation only — their outputs are NOT stable
   schemas (see B2).
2. **Backend CLI**: `stc = stc.cli:main` (`pyproject.toml`
   `[project.scripts]`; click+rich dual-mode, `--json` for headless
   automation; command spec in STC `05_CLI_AND_INTERFACE_SPEC.md`).
3. **Backend Python surface**: `stc.integration` (DialecticRunner,
   lease_git, custody, dossier) and `stc.substrate` (receipt/runner
   quality gates) — importable modules, but every value they return
   is observed-shape, unqualified input, never a pinned envelope.

Forbidden surface: direct run-store/ledger file reads, monkeypatching
or wrapping STC internals to simulate skip/resume, invoking STC at any
commit other than the pinned freeze, following STC HEAD.

### 2.2 Pins (all at freeze 548615a; cite code + record)

| Component | Pin |
|---|---|
| STC code | `1d1c535f6c062e9f636440a087d76f9fc39ed93c` |
| STC freeze record | `548615aecb2ca368b5221b20cf90a701eda0acc2` |
| SST (`STC_SST_ROOT` / sibling `../sst`) | `df78f42894a65c48f524337a498032617689a013` |
| prompt-kit | `4f442a6c829bc06b60f9979fdc8d7585e30bac9a` |
| trace | `a24a937009fec41e6dcb6d2ca31d3c1783ac97f7` |
| DSH upstream | `639ed015397290b3745d163aafe02ffee4aa3f84` (v0.2.0-rc.2) |
| node / pnpm / esbuild | 22.23.3 (SHA256 tarball) / 11.7.0 (corepack) / 0.28.2 (lockfile) |
| Model route | `deepseek/deepseek-v4-pro-0813` via Sail x-api-key |

SST integrity mechanics apply unchanged: no vendoring; leases fail
closed unless spot files match pin blobs; dirty SST tree refused at
lease time; `sst_compat_probe.py` reports COMPATIBLE / DIRTY /
MISSING-SURFACE / NO-GIT. The adapter MUST refuse to run on any
non-COMPATIBLE probe result.

### 2.3 Environment

- Install: `pnpm install --frozen-lockfile && pnpm build` in
  `dsh-plugin-stc/`; `dsh plugin --profile web add
  file:/path/to/stc/dsh-plugin-stc`.
- Boot env: `DSH_HOME` + `STC_ROOT` + `STC_DSH_STORE` +
  `STC_SST_ROOT` + `STC_PROMPT_KIT_ROOT`, then `dsh web --no-open`.
- Envelope: local-production only — single-user Linux/WSL, loopback
  browser. No multi-user, no remote-host, no cross-host run-store
  moves unless `/tmp/stc-rt` is restaged with identical absolute
  paths (argv paths are absolute; replay breaks otherwise).

### 2.4 Mandatory qualification labels

Every artifact an experimental adapter emits (logs, reports, derived
pins, verdicts) MUST carry, verbatim and machine-checkable:

- `consumer: EXPERIMENTAL`
- `qualified_for_substrate_consumption: false`
- `substrate_facing_envelope: "NONE"`
- `stc_code: 1d1c535…` + `stc_record: 548615a…` (both hashes)
- `replay: full` on any restarted run (mirroring STC's own stamp)

Omission of any label is a gate failure: the artifact is inadmissible
even as experimental signal.

### 2.5 Forbidden claims

An experimental adapter MUST NOT claim, imply, or let a downstream
reader infer: qualified consumption; envelope stability ("STC dossier
schema vX"); test evidence bound to substrate use; U-branch
acceptance support; resume-with-skip; idempotent effects; or that
repeated success constitutes qualification (§1 standing rule).

## 3. Composition rules (full-replay semantics preserved)

STC recovery is restart-from-scratch with effect-repeat, never
checkpoint-resume (code-verified at 1d1c535). An experimental adapter
MUST enforce:

1. **Interrupt routing**: route EVERY stop through `stc_interrupt`
   with a declared checkpoint + `effects` claim (`[{id, kind,
   status, proof?}]`, validated before anything records; `completed`
   without `proof` is rejected). `markInterrupted` refuses empty
   checkpoints; a never-interrupted run refuses both recover-resume
   and restart — an undeclared stop makes the run
   unrecoverable-by-restart, and the adapter must report it as such,
   not retry around it.
2. **Recover is decision support, not resumption**: `recover()`
   NEVER relaunches. Outcomes are `reattached` (job still live
   in-process — the ONLY true resume, and the only outcome that
   persists a recovery stamp), `needs-decision` + blockers +
   evidence (every gone-job case, INCLUDING fully-attested runs),
   `already-terminal`, `refused-redirected`. Status queries are pure
   reads. The adapter must surface `needs-decision` blockers to the
   operator and never auto-restart from them.
3. **Restart budgeting**: `stc_restart` (typed `confirm="RUN"`,
   interrupted-state only) is the SOLE continuation path. It spawns
   a linked child with IDENTICAL argv; ledger effects on the parent
   MAY REPEAT; nothing is skipped (`skipped: []`). The adapter must
   budget FULL recompute (entire command again, time + compute) plus
   repeated side effects on EVERY restart — the kill-drill
   (counter 1→2, distinct pids) proves the repeat is
   explicit-by-design, not idempotent. Composition must tolerate or
   externally dedupe repeated effects; assuming idempotence is a
   design violation.
4. **Refusal set**: restart refuses live jobs, terminal/cancelled/
   redirected/never-interrupted runs. The adapter must propagate
   these refusals, not translate them into fresh launches under the
   same run id.
5. **Lineage breaks**: terminal/cancel/redirect proofs are sticky
   and refuse restart — composition starts a NEW run (new run id,
   NO `restartedFrom` link) after any of those. Only an
   interrupted→restarted chain carries `restartedFrom` +
   `replay=full`. The adapter must never fabricate lineage across a
   break.
6. **Portability**: replay-after-wipe needs `/tmp/stc-rt` restaged
   from pins with identical absolute paths. Cross-host moves without
   restaging are unsupported; the adapter must fail closed, not
   attempt path rewriting.

## 4. Minimal owner sentences that retire each block

| Block | Retiring sentence (committed bytes, STC owner) |
|---|---|
| B1–B4 (Ask 2B, positive path) | "Substrate may consume [ARTIFACT: doc set / dossier schema / verdict record — name one] at [commit]; its stable envelope is [name + keys + change policy]; gate record [command + counts] at that commit." Then substrate mirrors the Ask-1 pattern (contract + gate record) for the named artifact. |
| B1–B4 (Ask 2B, negative path) | "Nothing — STC is not a substrate producer." This sentence retires Q-STC-1..2; U-branch plans SST-only; `stc_adapter`'s UNQUALIFIED doc-reader state becomes terminal rather than pending. |
| B5 (capability gap) | NO sentence retires B5 — it needs a code change (a skip mechanism in the backend + a restart variant that stamps `skipped: [...]`), a new freeze, and re-verification. An owner note can only acknowledge the gap, not waive it. |

## 5. Bottom line

Without Ask 2B, substrate may operate STC, probe it, plan on its
recovery contract, and cite its bytes — but may not consume anything
from it as qualified material, and `stc_adapter` correctly stays an
UNQUALIFIED doc-reader pinned at 8fa8ac3-era docs. An EXPERIMENTAL
adapter is permitted on the §2 surface/pins/env with §2.4 labels and
§3 composition rules, producing signal only. The single cheapest
unblock remains one committed owner sentence: name the artifact, or
state "nothing — STC is not a substrate producer."
