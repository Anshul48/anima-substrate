# S5-DESIGN.md — Successor-005: bounded procedure participant (DESIGN ONLY)

- Status: design complete; verdict §0.
- Workdir: `prototype/programme-20261004/S5-design/` (only location written).
- All other trees read-only for this design (successors, releases, H2-lane,
  experiments, P1-adapters, RealUse-design, neighbors). No implementation,
  no runs, no host modification performed.
- Brief: design (only) the smallest procedure participant that executes
  caller-supplied useful procedures through truthful, declared capabilities,
  reopening the U-branch behind invariants I1–I6
  (`RealUse-design/REALUSE-DESIGN.md` §4b). User authorization context:
  design + implementation + acceptance together in one bounded successor
  (`prototype/successor-005/`, release-line); frozen releases intact;
  producer trees owner-held; permanent host (Q5) stays open;
  $0/offline/stdlib-only-except-SST-leg.
- Intended successor: `prototype/successor-005/` built as a delta on a
  frozen-verified copy of `successor-004/` (the s003→s004 pattern:
  rebrand + confined delta + carried suites green + new tests in the
  tree's normal layout).

## §0 Verdict (read first): I1–I6 CAN be satisfied honestly — conditionally

This design specifies a **bounded accountable procedure executor** that
reopens U-execute behind I1–I6 without breaking any frozen contract. The
load-bearing judgments:

1. **§7 fixity is preserved, not amended.** Worlds advertise an
   executable-procedure table AT CREATION (fixed at birth, exactly like
   capabilities); the `proc.exec` service capability may only execute
   table entries. New procedure content ⇒ new world (the LIMITS-6
   precedent: "genuinely NEW capabilities still require a new world").
   No generic arbitrary-code capability exists; no post-creation
   capability change is proposed. (§1.1)
2. **The participant is an accountable executor, NOT a sandbox.**
   stdlib-only + $0 + single-host cannot provide OS-level isolation
   (no netns/seccomp/jail), and this design does not claim it. Every
   permission is labeled ENFORCED (host guarantees, tested) or
   CONTRACTUAL (caller vouches, host detects where it can). Callers
   supply procedures AND bear their content risk; the host vouches
   execution accountability (pins, hashes, ledger, recovery). Any
   isolation demand stronger than §1.4 is out of envelope — escalated,
   not wished in. (§1.4, §8)
3. **Interruption = re-run current step fresh + adopt-if-complete.**
   Procedure internals are caller-opaque, so resume-inside-a-step is
   unsound (child-written bytes have no atomicity claim — the R3
   SST-child precedent). Step granularity + resume-by-skip gives
   make-style recovery honestly; the DONE-marker adoption argument
   (§1.7) closes the child-done-pre-ledger window without re-execution.
4. **The default vehicle is FIT only as strengthened in §2.**
   A bare sha256 identity checker fails U3 (no engineer wants it from
   a pipeline over `sha256sum -c`) and I4 (milliseconds; recovery
   value ~zero — the §2 breakage verbatim). The specified vehicle
   keeps the default's identity AND compat halves but defines compat
   as **re-executing each frozen release's conformance/atomicity
   suites fresh + emitting a ledger-cross-checked compat verdict** —
   minutes of honest expense, a real consumer (release lane
   pre-flight), machine-checkable validity. If the coordinator rejects
   the strengthening, the default as-stated is UNFIT and §9 names the
   one alternative (which loses). (§2, §9)
5. **No breakage point found in I1–I6 under this design** — but three
   conditions must hold at build, or U-execute re-aborts at the
   executability re-gate (§7.4): (a) honest expense reaches minutes
   without padding; (b) procedure-table verification composes with
   reopen without ledger-shape breakage; (c) the blind usefulness bar
   is met by the vehicle. Each has a coded abort predicate. If any
   fires, that re-abort is a complete result, not a failure.

## §1 The smallest procedure participant (delta spec — build from this)

### 1.1 Capability model + ORG-OPS §7 reconciliation (DECIDED)

Brief's options: (a) advertise procedure capabilities at world creation
with explicit command/argv pins; (b) capability-per-procedure-hash.
**Decision: (a), implemented as a creation-fixed procedure table gating
one honestly-named service capability.** (b) in its literal form
(hash inside the capability name/version string) is rejected: it abuses
the `name@version` match semantics, destroys readability, and buys
nothing over a table that the ledger pins anyway.

Mechanics (successor-004 terms):

- New service capability `proc.exec@v1`, advertised at world creation
  like any cap. Its documented semantics: "execute one step of a
  caller-supplied procedure bundle listed in this world's advertised
  procedure table, under the §1.4 invocation envelope, recording §1.6
  accountability data." The name describes the execution SERVICE; the
  executed CONTENT is pinned per invoke (§1.2). This is the SST-leg
  honesty pattern (name the envelope, pin the bytes), not the
  Candidate-B abuse (ledger names X, bytes do Y): the ledger will say
  `proc.exec` + procedure name + bundle sha256, and that statement is
  true and re-verifiable.
- New world-record field `procedures`: list of
  `{name, bundle_sha256, manifest_ref, steps: [step names]}`,
  FIXED AT CREATION, never mutated (same rule as caps/reps; world
  records are never mutated — OP-3.1). Empty list for all existing
  sched worlds.
- Advertise-time validation (before ANY ledger mutation, mirroring
  fuse/fission pre-validation): manifest well-formed; every step has
  `step/argv/declared_outputs/timeout_s`; no absolute paths or `..`
  in bundle or declared outputs; every `timeout_s ≤ TIMEOUT_CEILING_S`
  (600, the grant envelope); argv uses no shell (list form only);
  bundle hash recomputed MATCHES the staged bytes. Violation ⇒
  `ValueError` naming the defect, zero ledger effect.
- Invoke-time gate: `proc.exec` invoke with
  `(procedure, bundle_sha256)` ∉ table ⇒ recorded `deny` +
  `ContractViolation`, before any spawn (mirrors the
  "does not advertise" deny, `minihost.py:772-778`).
- **§7 status: UNCHANGED.** No new capabilities or table entries after
  creation. Genuinely new procedure content requires a new world —
  exactly the LIMITS-6 rule for capabilities. ORG-OPS §7 gains one
  sentence: "procedure tables are fixed at birth like capabilities;
  see S5 §1.1." No other §7 word changes.
- Contract version: NO bump. `CONTRACT_VERSION` stays `"0"`; the
  `procedures` field is additive with default `[]`; ledgers never
  cross successor trees (per-run ledgers, reopen within-tree), so no
  cross-version read exists. `MiniWorldRecord.validate()` requires
  the field present (defaulted, not None).

Why not a generic `proc.run` taking per-invoke bytes (the rejected
third option): the capability name would bound nothing, leaving the
ledger pin as the sole honesty carrier — one step from Candidate-B
territory ("the host can be made to execute bytes"). The table keeps
the fixity guarantee load-bearing: a world's executable set is known
at birth and auditable from the `create` payload alone.

### 1.2 Ledger shape

Three additions; all existing kinds/shapes byte-unchanged on clean
paths (carried suites must pass unmodified — §6 check S5-A1):

1. `create` payload gains `procedures: [{name, bundle_sha256,
   manifest_ref, steps}]`. Full manifests live as state-dir files
   (pinned by hash); the ledger carries the pins, not the bytes.
2. New kind `proc_begin`, appended BEFORE each step spawn:
   `{invoke_id, idem_key, world_id, procedure, bundle_sha256, step,
   scratch, argv_sha256, interpreter, interpreter_version, env_keys,
   input_hashes}`. This entry is what makes kill-mid-procedure a
   DEFINED landing (entry present + no matching `invoke` ⇒ killed
   mid-step; §1.7).
3. `invoke` entries with `capability == "proc.exec"` carry the
   standard fields (`invoke_id/caller/callee/capability/version/
   args_ref/result_ref/cost`) plus `proc: {procedure, bundle_sha256,
   idem_key, step, exit_code, stdout_sha256, stdout_bytes,
   stderr_sha256, stderr_bytes, truncated_stdout,
   truncated_stderr, artifacts: [{relpath, sha256, bytes}],
   undeclared_present: [{relpath, bytes}], outside_writes: [],
   elapsed_s, timed_out: false, recovered: bool}`.
   Failure legs use the EXISTING error-invoke shape
   (`{..., error}` — burns nothing, ledger-recorded;
   `minihost.py:798-806`): spawn failure, timeout kill,
   manifest-mismatch, outside-write violation, adopt-refusal.
   `recovered: true` marks adopt-path entries (§1.7 landing 3).

`worlds.json` specs gain `procedures` per world; `api.open_run`
restores the table from the ledger `create` payloads (authoritative),
exactly as creation lineage is restored today (OP-1.6). Reopen
descriptor verification gains a table-equality check beside the
caps/reps set-equality checks (`minihost.py:456-467` pattern):
mismatch ⇒ `deny` + `ContractViolation`, refusing not guessing.

### 1.3 Explicit inputs/outputs (refs + hashes)

- Procedure bundle (caller-supplied at world creation): a directory
  tree staged by copy into `state/<W>/procedures/<name>/`; canonical
  manifest `MANIFEST.json` = `{files: {relpath: sha256},
  steps: [{step, argv, declared_outputs, timeout_s,
  env_extra}], inputs: [...]}`; `bundle_sha256` = sha256 over
  canonical-JSON manifest bytes. Staged copy is host-owned; source
  stays caller-owned (experiment dir, never a frozen tree).
- Step inputs: caller passes `{name: bytes}` or `{name: path}` at
  invoke; the host stages copies under `<scratch>/inputs/`,
  records `input_hashes` in `proc_begin`. No ambient file is
  implicitly visible except via reads (§1.4).
- Step outputs: declared relpaths collected from scratch into
  `artifacts/proc-<idem_key>/<step>/` (copies; new
  `atomic_write_bytes` helper for byte artifacts — temp+`os.replace`,
  same R3 semantics as `atomic_write_text`); every collected file
  hashed into the invoke `proc.artifacts` list. `result_ref` =
  `artifacts/proc-<idem_key>/<step>/RESULT.json`
  (atomic-written; contains exit code, hashes, artifact relpaths).
- Stdout/stderr: captured (never inherited), byte-capped
  (STDOUT_CAP = STDERR_CAP = 1 MiB; overflow ⇒ truncated flag +
  head bytes kept; caps recorded in the entry, never silent).

### 1.4 Permissions: what a procedure may touch (ENFORCED vs CONTRACTUAL)

The table below is the honesty core of this design. ENFORCED items are
host guarantees with conformance tests (§6 S5-A4). CONTRACTUAL items
are caller obligations the host cannot enforce stdlib-only; the host
detects what it can (stated) and never claims the rest.

| # | Permission | Status | Mechanism |
|---|---|---|---|
| P1 | argv exec, no shell | ENFORCED | `subprocess.Popen(argv-list)`; `shell=False` always; no string command path exists in the executor (construction test: AST sweep for `shell=True` = zero hits). |
| P2 | cwd = fresh per-step scratch | ENFORCED | `<state>/proc-scratch/<idem>/<step>-<attempt>/`, created empty per attempt; child `cwd` pinned there. |
| P3 | env = allowlist-built | ENFORCED | `PATH` inherited (recorded), `PYTHONDONTWRITEBYTECODE=1`, `HOME`+`TMPDIR`=scratch, `PYTHONPATH` unset, `*_PROXY/*_proxy` stripped, all else stripped; `env_extra` ⊆ {listed keys} from manifest only; `env_keys` recorded in `proc_begin`. |
| P4 | stdin | ENFORCED | `/dev/null` (or pinned `stdin_ref` staged file) — never the parent's stdin. |
| P5 | stdout/stderr capture + caps | ENFORCED | Piped + 1 MiB caps + truncation flags (§1.3). |
| P6 | timeout kill | ENFORCED | Parent `wait(timeout)`; on expiry kill child group (`start_new_session=True` + `killpg` SIGKILL on POSIX; `Popen.kill`+`wait` on Windows), record timeout error-invoke. Linux authoritative; Windows best-effort (documented). |
| P7 | interpreter pinning | ENFORCED-as-recorded | Manifest pins `python: "system"` (resolved via `shutil.which("python3")`) or explicit `PROC_PY` override (SST_VENV_PY precedent); resolved path + `sys.version` recorded in `proc_begin`; mismatch vs pin ⇒ refuse before spawn. |
| P8 | bundle immutability | ENFORCED-by-verify | Manifest re-verified pre-run AND post-run; mismatch ⇒ error-invoke, no result adopted. (POSIX `chmod 0o555` best-effort defense-in-depth; NOT the guarantee — the re-hash is.) |
| P9 | writes inside scratch | ENFORCED-detect | Pre/post listing snapshot of the state dir outside the step scratch: any new/modified file inside state-but-outside-scratch ⇒ step FAILED (error-invoke names the files). |
| P10 | reads | ALLOWED | Reads anywhere (frozen trees MUST be readable for §2; read-only enforced socially + by the frozen-intact guard, not by the executor). |
| P11 | writes outside state dir | CONTRACTUAL | stdlib cannot prevent or reliably detect these. Caller vouches; the executor never needs them; frozen-intact re-check (§6 S5-A9) detects frozen-tree damage after the fact. NOT CLAIMED as enforced. |
| P12 | network | CONTRACTUAL (not isolated) | No namespace/seccomp exists stdlib-only. Offline is a caller obligation + env hygiene (P3 proxy strip). The executor performs no network I/O itself. Any "network=none enforced" wording is FORBIDDEN (§6 S5-A11). |
| P13 | memory/RSS caps | NOT CLAIMED | No portable stdlib mechanism (`resource` is POSIX-only, no Windows). Output caps (P5) bound exfiltration bytes, not RSS. Stated, not claimed. |
| P14 | grant accounting | ENFORCED | Each step consumes `invocations=1` + `time_s=elapsed` (measured, rounded UP to 0.1 s) via the normal consume path; grant exhaustion ⇒ standard grant-exceeded deny. `cost_usd=0`. |
| P15 | orphan containment | TOLERATED-BY-CONSTRUCTION | Parent kill may orphan the child; orphans write only to stale scratch (P2), which recovery never reads except via the DONE rule (§1.7). No PID auto-kill (PID reuse unsafe). Kill TESTS kill the process group (harness duty, documented in test plan). |

"Escape refusal" tests (§6 S5-A4) cover the enforceable refusals:
manifest with absolute/`..` paths, `timeout_s` over ceiling,
table-miss invoke, idempotence-key collision across bundles,
outside-state-write violation (P9), timeout kill (P6). They do NOT
cover P11/P12/P13 containment — the tests assert the documented
non-claim instead (negative wording tests).

### 1.5 Operation identity (invoke linkage, idempotence keys)

- One invoke per step. Step matcher key (extends `scan_succeeded`):
  `(capability="proc.exec", bundle_sha256, idem_key, step)`.
  A step is SKIPPED iff a SUCCESS invoke (has `result_ref`, no
  `error`) with that key exists. Sched steps keep the C1–C3 matcher
  byte-unchanged (no regression — S5-A1).
- `idem_key`: caller-chosen per procedure RUN (all steps of one run
  share it; distinct runs use distinct keys). Same key + same bundle
  + prior success ⇒ skip (no re-execution). Same key + prior FAILURE
  ⇒ re-execution allowed (failures never skip — the existing
  success/error distinction, `minihost.py:755-759`).
- Same key + DIFFERENT bundle_sha256 + any prior entry ⇒ loud
  REFUSAL (`deny` + `ValueError`, "idempotence key collision across
  content") — a key may never silently skip different bytes.
- Attempt numbering: re-runs after a kill use a fresh scratch
  (`.../<step>-<attemptN>/`, N recorded); the invoke entry records
  `attempt`. `child_executions` per (key, step) = number of
  `proc_begin` entries; normally 1, ≤2 with one kill (§1.7 landings
  2–3), asserted by the interruption matrix.
- C2/C3 shapes do NOT apply to procedure steps (new documented step
  shape: `args = {task_id, step, procedure, bundle_sha256,
  idem_key, input_refs}`); `check_args_keys`/`check_propose_result`
  still gate every sched step. Conformance asserts both (S5-A1 +
  S5-A3).

### 1.6 Accountable results

Every successful step records (ledger `invoke.proc` + `RESULT.json`,
cross-checked by tests): exit code (nonzero ⇒ error-invoke, not
success — a nonzero child NEVER yields `result_ref`); stdout/stderr
sha256 + bytes + truncation flags; per-artifact sha256 + bytes;
`undeclared_present` names+sizes (accounted, not collected);
`outside_writes` (always `[]` on success — P9); `elapsed_s`;
`timed_out: false`; `recovered` bool; `attempt`. Completeness test
(S5-A5) asserts every field present on every success entry and
recomputes every hash from artifact bytes.

### 1.7 Interruption handling (DECIDED: re-run step fresh + adopt-if-complete)

**Decision: re-run, NOT resume-by-checkpoint.** Procedure internals are
caller-opaque: the host cannot verify a child-written checkpoint
(child bytes have no atomicity claim — the R3 SST-child precedent:
"child-side, no kill boundary across them",
INTERRUPTION-BOUNDARIES §1). Resume-inside-a-step would trust bytes
the kill may have torn. Step granularity + resume-by-skip is the
honest make-style equivalent: completed steps skip (0 re-execution),
the interrupted step re-runs in a FRESH scratch.

DONE-marker rule (closes the child-done-pre-ledger window without
re-execution): the PARENT, after `wait()` returns, atomically writes
`DONE.json` {exit_code, artifact hashes recomputed, at} into the step
scratch, THEN writes `result_ref`, THEN appends the invoke entry.
Load-bearing correctness argument: DONE present ⇒ the parent reaped
the child ⇒ the child is dead ⇒ scratch bytes are stable ⇒ adoption
is sound. No DONE ⇒ re-run fresh (even if the child is dead and its
outputs look complete — wasteful, correct).

Landing table (kill = SIGKILL-class, process-crash only; R3
guarantees cited per landing):

| # | Kill point | Defined landing | Recovery (all via `ops recover` + re-invoke) | R3 citation |
|---|---|---|---|---|
| L1 | before `proc_begin` | no trace; step never ran | re-invoke runs it (attempt 1) | entry-granular prefix, INT-§1 |
| L2 | after `proc_begin`, no DONE | `proc_begin` without `invoke` ⇒ killed mid-step | recover REPORTS re-runnable (never spawns); re-invoke re-runs fresh scratch (attempt N+1); stale scratch kept as evidence, never read | prefix property; fresh-scratch quarantine (new, S5-A6) |
| L3 | DONE present, no `invoke` | side-complete, ledger-missing | recover VERIFIES (DONE + artifact re-hash + bundle post-hash MATCH) then ADOPTS: atomic `result_ref` + ONE `invoke` (`recovered:true`); any mismatch ⇒ refuse-adopt + re-run path | mirrors fusion pre-spec repair (INT-§4: recovery appends the missing entry from authoritative state — here the verified side files are authoritative) |
| L4 | inside the ledger append | torn tail possible | loud disk-loss refusal, restore from backup — NOT recovery | INT-§1/§6, LIMITS-2 ledger half (unchanged) |
| L5 | during adopt (kill-during-recovery) | adopt is ledger-conditional (checks invoke-exists first) | re-run recover converges | INT-§6 kill-during-recovery |
| L6 | timeout (no kill) | parent kills child group, error-invoke recorded | caller retries same key (allowed: failures never skip) or new key | P6; invoke failure semantics |

Recovery itself NEVER spawns children (adopt + report only) — keeps
`ops recover` idempotent and safe; all execution flows through the
single `run_procedure` entry point. New crash hooks (test-only,
unset = zero behavior change, INT-§1 pattern):
`SUBSTRATE_CRASH_AT=proc:post-done-pre-invoke` (L3 deterministically);
`SUBSTRATE_CRASH_AFTER_APPENDS` covers L1/L2 boundaries
(`proc_begin` is an append); `SUBSTRATE_CRASH_MID_APPEND` covers L4.
Real-SIGKILL legs (staggered delays, process-group kill by the
harness) prove L2/L3 statistically; repeated-kill legs prove L5.

### 1.8 New consumer surface (exact)

- `api.create_proc_world(state_dir, world_id, bundle_dir, reason)`
  — validates (§1.1 advertise-time checks), stages the bundle copy,
  creates the world with `caps=[proc.exec@v1]` (+ requested sched
  caps if a hybrid world — allowed, table still gates proc.exec) and
  the `procedures` table, activates it. CLI:
  `ops create-proc-world --world W --bundle DIR --reason ...`.
- `api.run_procedure(state_dir, world_id, procedure, idem_key,
  inputs=None)` — executes all steps in order with skip-match,
  returns `{skipped, executed, re_executed_steps, child_executions,
  results}`. CLI: `ops run-procedure --world W --procedure P
  --key K [--inputs DIR]`.
- `api.recover_op` / `ops recover` extended: adopt-if-complete (L3)
  + report re-runnable steps (L2) alongside existing settle/fusion/
  fission completion. No new recovery verb (CONSUMER §6 shape kept).
- `atomic_write_bytes` helper (bytes twin of `atomic_write_text`).
- `worlds.json` spec: `+ procedures` per world. `CONFIG.json`:
  unchanged shape (staleness still benign).

### 1.9 What is NOT built (exclusions — load-bearing)

No generic arbitrary-code capability; no post-creation table/cap
change; no amend to §7 beyond the one sentence; no OS sandbox
(P11–P13 stated non-claims); no checkpoint-resume inside steps; no
spawning inside recover; no SST-leg involvement in the vehicle;
no STC involvement (§8); no fsync/power-loss claim; no multi-writer;
no cross-host; no `retired` exercise. N1/N2 wording narrowings (next
docs pass, R3 record) SHOULD ride along in successor-005 docs since
fresh wording is being written anyway — builder handoff item, not a
frozen-tree edit.

## §2 Default task as acceptance vehicle (SPECIFIED, with mandatory strengthening)

### 2.1 Verdict on the default as-stated: UNFIT in the minimal reading

"Pinned sha256 identity checker" alone fails U3 (a competent engineer
reaches for `sha256sum -c`, not a pipeline) and I4 (45-file hashing
is milliseconds — kill-recovery value ~zero, the REALUSE §2 breakage
verbatim). Specifying it bare would repeat Candidate A/E's error with
more steps. The design therefore specifies the default WITH the
strengthening below as part of the vehicle — same two halves
(identity + compat), with compat CONCRETELY defined as re-execution
work. If the coordinator strips the strengthening, §9's alternative
applies instead — do not run the bare checker as U-execute.

### 2.2 Specified vehicle: `relcheck` — cross-release acceptance utility

Purpose (U1): release-lane pre-flight over frozen r1/r2/r3
(successor-002/release-20261004, successor-003/release-r2,
successor-004/release-r3): verify frozen identities, FRESHLY
re-execute each release's conformance + atomicity suites, emit a
compat verdict. Named consumer: the release acceptance lane;
named purpose: pre-freeze/pre-cut confidence + upgrade compat
evidence. (Consumed, not graded-and-discarded: the lane files the
report with the cut record.)

Steps (each one `proc.exec` invoke; suite steps are the honest long
pole — minutes of real subprocess test execution, no padding):

1. `identity`: recompute `IDENTITY.sha256` (`sha256sum -c` equivalent
   in stdlib) for successor-002/003/004 from frozen bytes (READ-ONLY;
   frozen trees never written — P10/P11 + guard S5-A9). Declared
   outputs: `IDENTITY-RESULT.json` {per-file ok/mismatch}.
2. `suite-r1`: run successor-002 carried suites fresh
   (`test_conformance.py` + demo-equivalent per its CONSUMER doc).
3. `suite-r2`: run successor-003 suites fresh (9/9 + 27/27 layout).
4. `suite-r3`: run successor-004 suites fresh (9/9 + 39/39 layout).
5. `compat`: emit `COMPAT-REPORT.json` {identities: per-release
   MATCH/MISMATCH, suites: per-release {test, rc, counts}, surface:
   {per-release CLI verbs + api.py function lists + ledger kinds
   observed}, verdict: ACCEPT/PARTIAL/FAIL per frozen rule below}.

All step programs are caller-supplied stdlib-only Python inside the
bundle (argv-pinned); suite steps shell out to the frozen trees'
own test files with `PYTHONDONTWRITEBYTECODE=1` and state dirs under
scratch (never in-tree — frozen discipline). Inputs: release root
paths (pinned at freeze) + suite file lists. Outputs: per-step
RESULT + logs + final report.

### 2.3 Checker program + pins (independent artifact acceptance, U2)

Builder-written, frozen at prereg, verifier re-run:
`verdict_relcheck.py <report> <ledger> <artifacts> <pins>` → prints
exactly one line `RELCHECK-VALID` or `RELCHECK-INVALID: <reason>`
(exit 0 / exit 1). It MUST NOT trust the report: it (a) recomputes
all identity hashes from frozen bytes itself and compares to the
report's claims; (b) cross-checks every suite rc/count claim against
the LEDGER-recorded `proc.exec` invoke entries (exit codes) + log
artifact hashes (recomputed); (c) validates report schema keys;
(d) recomputes the verdict rule: ACCEPT iff identities all MATCH
AND every suite rc==0 AND surface lists superset the pinned minimum
verb/function sets; PARTIAL/FAIL per frozen mapping. Pins frozen at
prereg: r1/r2/r3 `IDENTITY.sha256` full bytes (current pins cited in
the r3 record §2 for s004; r1/r2 pins re-taken from frozen bytes at
freeze — never trusted from prose), suite file lists + expected
counts, minimum surface sets, bundle sha256 of `relcheck` itself.

U2/U3 status: U2 SATISFIED (checker decides from bytes + ledger
without trusting either arm). U3 scored blind per §7 rubric; honest
prior: moderate usefulness (release engineering niche, real but
narrow — the frank assessment lives in §9).

### 2.4 I4 (honest expense) pre-analysis

Suite re-execution across three releases is minutes of real compute
(measured at build; executability re-gate §7.4 aborts if the honest
total is <60 s wall on the pinned machine — padding to reach it is
FORBIDDEN and detectable: the checker cross-checks suite counts, and
any sleep/burn loop in bundle bytes fails review). Kill-recovery
value is then genuine: a mid-`suite-r3` kill costs the direct
re-run minutes (or its checkpoint resume exacts stamp discipline),
while the host skips completed steps by ledger match.

## §3 Changed-requirement leg (I3: expressible through a named consumer op)

**Honest mechanism: procedure revision via NEW WORLD (re-advertisement
is creation, not mutation).** `revise_op` is EXPLICITLY not used: it
flips between pre-advertised representation versions only and never
mutates requirements (OP-3.1; REALUSE §2 breakage). The change flows
as follows — every step through a named consumer op:

1. Freeze pre-registers the CHANGE SHAPE: "one procedure revision:
   revised `relcheck` bundle (one step's program bytes change +
   one declared-output addition) + one added suite target."
   CONTENT (which step, which bytes, which target) is held out in a
   sealed envelope (sha256-committed at freeze, revealed mid-run).
2. At reveal, BOTH arms receive identical revised bytes.
   Host arm: `ops create-proc-world --world W2 --bundle DIR2`
   (advertise-time validation runs on the revised manifest) then
   `ops run-procedure --world W2 --procedure relcheck --key K2`.
   The ledger proves the chain: `create(W2)` with the revised table
   pins + `proc_begin`/`invoke` entries under K2; W1 history intact.
3. Direct arm: same revised bytes under its make-style runner (§5).
4. Measured: cost-to-adapt = step/invoke counts + new bytes executed
   to first VALID report under the revised bundle; final artifact
   validity via §2.3 checker (unchanged — the checker contract is
   content-agnostic within the schema).

I3 SATISFIED: the named ops are `create-proc-world` (advertise) +
`run-procedure` (execute); their honest semantics cover exactly this
(a new executable set for new content). The host is load-bearing in
this leg through advertise-time validation (revised manifest defects
refuse loudly before any work — the direct arm has no equivalent
gate) + accountable execution; the interrupt leg (§4) is where host
recovery machinery is primarily load-bearing (G5 needs at least one —
it has both, asymmetrically; stated, not oversold).

## §4 Interrupted-run leg (real kill + recovery through consumer ops)

- Kill: real `Popen.kill()` (SIGKILL class, process-crash only — the
  envelope; power-loss never claimed) at a pre-registered mid-task
  point: during step `suite-r3` (the long pole), fired by wall-clock
  delay scaled to measured step length (the r3-lane lesson: scale
  delays, confirm in-window landings). Harness kills the PROCESS
  GROUP (parent + any live child — P15). Kill-during-quarantine-
  transfer exclusion carried (never routed there; pre-registered).
- Host recovery (consumer ops only): `ops recover` (adopts NOTHING
  here — no DONE exists mid-step — reports step `suite-r3`
  re-runnable) then `ops run-procedure --key K` (SAME key): steps
  `identity/suite-r1/suite-r2` SKIP by ledger match
  (`re_executed_steps == 0` asserted), `suite-r3` re-runs in fresh
  scratch (attempt 2; `child_executions == 2` for that step,
  recorded honestly), `compat` runs.
- Direct recovery: `make resume` (stamp files per step): completed
  stamps skip, current step re-runs. Documented in the baseline spec;
  its re-work counted honestly (same granularity — symmetric).
- What the ledger proves afterward: `proc_begin(K, suite-r3)` × 2
  (attempts 1–2) + ONE success `invoke(K, suite-r3)` (attempt 2) +
  single success invokes for all other steps + `re_executed_steps ==
  0` in the run record + conservation holds + bundle post-hashes
  MATCH. Predicates in §7.6 code this verbatim.
- L3 (DONE-pre-ledger) is exercised in successor acceptance (S5-A6
  matrix), NOT in U-execute (U-execute kills mid-step; the matrix
  proves the other landings — separation of concerns, stated).

## §5 Direct baseline + matched resources + metrics

### 5.1 Competent direct procedure (make-style resume)

`direct-relcheck/`: the SAME `relcheck` step programs (byte-identical
bundle — inputs held equal, §5.2) driven by a `Makefile` (or
equivalent stdlib runner if make is unavailable on the pinned
machine — pinned at freeze): one target per step, stamp files
`.stamps/<step>.ok` (containing output hashes), `make all` builds,
`make resume` (= `make all`: completed stamps skip, current re-runs).
Timeouts identical (per-step `timeout` command or runner-enforced —
same values as the manifest). No ledger, no hash-chain theater beyond
what a competent engineer would honestly keep (stamps + a run log).
This is the baseline the host must beat-or-tie on usefulness and be
honestly compared against on cost — NOT a strawman (re-run-from-
scratch would be dishonest against a minutes-long task; REALUSE §2
symmetry note honored).

### 5.2 Matched resources (REALUSE §3 template, adopted with two refinements)

Held equal: (a) task input bytes — IDENTICAL bundle bytes both arms
(same sha256; host stages a copy, direct uses the original — copy
verified by hash); (b) change content + reveal point (identical sealed
envelope); (c) kill class (process-crash/SIGKILL) + plan-phase
(mid-`suite-r3`, same fractional point ± stated tolerance); (d) human
touches counted and capped (pre-register cap=2 per leg; every operator
input is a counted touch on H — recover+re-invoke = 2 — and D gets
the same budget: `make resume` = 1, leaving 1 spare; over-cap ⇒ guard
FAIL); (e) compute envelope ($0/offline/stdlib-only; suite steps run
the frozen trees' own stdlib tests — no SST leg anywhere in the
vehicle).
REFINEMENT R1 (granularity parity): both arms checkpoint at STEP
boundaries (host skip-match ≡ direct stamps) — without this the
recovery comparison is rigged either way; stated and enforced by the
predicates (step lists must match exactly).
REFINEMENT R2 (honest re-work counting): re-executed COMPLETED steps
must be 0 on H (predicate) and are counted exactly on D (stamp-miss
audit); CURRENT-step re-run is counted on both (H: `child_executions`;
D: stamp absence + log) — the kill's cost is never zeroed by
definition on either side.
NOT held equal (measured outcomes): ledger/artifact byte counts,
invoke/step counts, re-executed work, wall-clock (guard-only).
No wall-clock primaries (REALUSE §3 carried verbatim).

### 5.3 Metrics

- PRIMARY (joint): artifact VALID (§2.3 checker) AND blind usefulness
  ≥ bar (§7 rubric, frozen) — each arm graded separately; U-execute
  compares arm outcomes + costs. The host "wins" nothing by default:
  verdict rules in §7.7 decide DEMONSTRATED/NOT-DEMONSTRATED per
  value cell (recovery value, adapt cost, accountability value).
- Cost-to-adapt (§3 leg): invokes/steps to first VALID revised report.
- Recovery cost (§4 leg): re-executed completed steps (H: 0 asserted;
  D: counted) + current-step re-runs (both counted) + touches used.
- Guards: conservation holds on H; `re_executed_steps == 0` on H;
  frozen trees byte-intact (IDENTITY re-check pre/post every leg);
  bundle post-hashes MATCH; no wall-clock primaries; no TEST-stub
  content scored (no SST leg — vacuously satisfied, asserted by the
  absence of `sst-leg/` in run dirs); touch cap respected.

## §6 Acceptance bar for the SUCCESSOR ITSELF (before any U-execute)

All checks run on `prototype/successor-005/` after build, before any
U-execute run exists. Builder-written tests live in the tree's normal
test layout (new file `test_procedure.py` + doc updates); an
independent verification lane re-runs everything from byte-verified
copies (the R3 pattern). Frozen predecessors are NEVER written
(verified by IDENTITY re-check inside the checks themselves).

- S5-A1. Carried suites green, clean paths byte-identical: conformance
  9/9 + atomicity 39/39 + demo + calibrate 2.61x + snapshot MATCH on
  successor-005, all EXIT=0; C2/C3 gating still enforced on every
  sched step (negative legs kept); accept-field comparison vs
  successor-004 clean (same procedure as R3 regression).
- S5-A2. Declaration honesty: for every procedure test run, the ledger
  names match the executed bytes — `create.procedures[].bundle_sha256`
  == recomputed staged-bundle hash; `proc_begin.bundle_sha256` ∈
  table; executed argv == manifest argv for (procedure, step)
  (argv_sha256 recomputed); interpreter recorded == interpreter that
  ran (version cross-check). Mismatch-injection legs (tamper staged
  bundle post-advertise) refuse loudly pre-run.
- S5-A3. Service honesty: `proc.exec` invoke with
  `(procedure, bundle)` ∉ table ⇒ `deny` + ContractViolation with
  zero spawn (assert no child ran: no `proc_begin`, no scratch dir);
  idempotence-key collision across bundles ⇒ `deny` + ValueError;
  nonzero child exit ⇒ error-invoke, never `result_ref`; hybrid
  worlds (sched caps + proc.exec) enforce both matchers without
  interference.
- S5-A4. Permission enforcement incl. escape refusal: P1 (AST sweep:
  zero `shell=True`; string-command attempt has no code path);
  P2–P5 (scratch/env/stdin/caps observed on live runs incl.
  truncation flags on over-cap output); P6 (timeout leg: child
  killed, error-invoke names timeout, no result); P7 (wrong
  interpreter pin refuses pre-spawn); P8 (post-run tamper ⇒
  error-invoke); P9 (outside-scratch-but-inside-state write ⇒ step
  FAILED naming the files); advertise-time validation matrix (bad
  manifest × defect class ⇒ ValueError, zero ledger effect).
  Negative-wording legs assert P11/P12/P13 are never claimed.
- S5-A5. Accountability record completeness: every success entry
  carries ALL §1.6 fields; every hash recomputed from artifact
  bytes MATCHES; `RESULT.json` agrees with the ledger entry field
  for field; `undeclared_present` detection leg (extra file ⇒
  listed, not collected).
- S5-A6. Interruption matrix over procedure phases: L1/L2 via
  `SUBSTRATE_CRASH_AFTER_APPENDS` at every append boundary (counts
  asserted — append-map drift fails loudly, INT-§2 pattern); L3 via
  `proc:post-done-pre-invoke` (adopt path: exactly ONE invoke,
  `recovered:true`, `child_executions==1`) + adopt-refusal leg
  (tampered DONE/outputs ⇒ refuse-adopt + re-run);
  L4 via `SUBSTRATE_CRASH_MID_APPEND` (loud disk-loss refusal);
  L5 repeated kills during adopt converge; real-SIGKILL legs
  (staggered delays, group kill, in-window landings confirmed —
  the r3-lane lesson) over L2/L3; `re_executed_steps == 0` and
  per-step `child_executions ≤ 2` asserted on every leg.
- S5-A7. Conservation + recovery on procedure tasks: `verify_conservation`
  ok after every procedure run incl. post-kill; grant accounting exact
  (invocations + rounded-up elapsed per step); `ops recover` output
  classes asserted (adopted / re-runnable / nothing-to-do); recovery
  never spawns (construction + runtime proof: no `Popen` under
  recover paths).
- S5-A8. New-world change flow (§3 mechanism): revised bundle ⇒ new
  world advertises + runs; W1 history intact and still resumable;
  ledger chain proves both tables; cost-to-adapt counters emitted.
- S5-A9. Frozen predecessors intact: successor-002 41/41 +
  successor-003 45/45 + successor-004 45/45 + H2-lane 46/46 +
  release trees byte-identical before AND after the full S5 suite
  (IDENTITY re-check inside the run, both ends).
- S5-A10. Vehicle readiness (no U-execute yet): `relcheck` bundle
  builds, advertise-time validation passes, one clean host run is
  VALID per §2.3 checker, honest expense measured and ≥60 s without
  padding (bundle bytes reviewed: no sleep/burn loops), direct
  baseline produces a VALID report from identical bytes.
- S5-A11. Wording audit (tree-wide, the R3 §5 pattern): zero
  unproven-impossibility sentences; zero "sandbox/isolated/
  network-blocked/contained" claims for procedures (required terms:
  "accountable executor", "scoped invocation", "contractual" where
  §1.4 says so); every durability sentence carries the process-crash
  / power-loss + no-fsync separation; N1/N2 narrowings applied.
- S5-A12. Independent verification lane: fresh-eyes re-run of
  S5-A1–S5-A11 from byte-verified copies + own kill params + own
  tamper legs, verdict ACCEPT/ACCEPT-WITH-NOTES required before
  U-execute prereg may be filed. (Successor acceptance is builder
  acceptance like R3/r3 — EVIDENCE + lane verdict, NOT a PREREG-LOG
  entry; PREREG-LOG begins at U-execute, §7.8.)

Gating rule: U-execute prereg (§7) may be filed iff S5-A1–S5-A12 all
PASS. Any FAIL ⇒ fix-the-successor (bounded delta, frozen discipline
kept) or escalate; never proceed-to-U on a failed gate.

## §7 Full U-execute prereg DRAFT (I6 pattern)

Draft for coordinator review; frozen + filed per §7.8 only after
S5-A12. Follows the M1-redux pattern: frozen PREREG.md + verbatim
`predicates.py` (the verdict imports it, never reimplements).

### 7.1 Task pins plan (frozen at prereg)

`relcheck` bundle sha256; r1/r2/r3 IDENTITY.sha256 full bytes;
suite file lists + expected counts per release; minimum surface
sets (CLI verbs + api functions); sealed change envelope
(sha256 of revised bundle + reveal point); kill spec (step
`suite-r3`, fractional point, delay-scaling rule); touch cap (=2);
pinned machine + interpreter; `verdict_relcheck.py` sha256;
`predicates.py` sha256 (this file's §7.6, verbatim).

### 7.2 Design freeze

Arms (H = successor-005 procedure worlds; D = §5.1 make-style),
legs (clean + change + kill, both arms), step lists (identical),
metrics (§5.3), rubric (§7.3), abort criteria (§7.4), analysis
rules (§7.7). No runs before PREREG-LOG countersign except S5-A10
readiness (throwaway state dirs, disclosed).

### 7.3 Blind usefulness rubric (frozen text, scored blind to arm)

Lane scores each arm's final `COMPAT-REPORT.json` + purpose statement
("release-lane pre-flight: would you file this with a cut record?")
on: R1 actionability (verdict + per-release evidence traceable to
pins/logs — 0/1/2); R2 trustworthiness (every claim independently
recomputable from attached evidence — 0/1/2); R3 completeness
(identities + suites + surface, no silent gaps — 0/1/2). Bar: total
≥4 AND R2 ≥1. The lane sees report bytes only (no arm labels, no
ledger — ledger cross-check is the checker's job, §2.3, not the
rubric's).

### 7.4 Abort criteria (incl. executability re-gate)

- G-RE (executability re-gate, applied to BUILT successor-005 before
  first non-throwaway run — G1..G5 re-applied with the vehicle):
  G1 real artifact+consumer (relcheck + release lane — PASS by §2.2
  unless pins fail); G2 not a grid re-skin (PASS — no scheduling
  content); G3 every step through honest consumer interfaces
  (PASS iff S5-A2/A3 green); G4 competent direct baseline exists
  (PASS iff S5-A10 direct VALID); G5 host load-bearing in ≥1 leg
  (PASS iff S5-A6/A8 green). Any re-gate FAIL ⇒ STEP0-ABORT-2
  (complete negative; no U runs; re-scope, do not execute).
- A-EXPENSE: honest clean-run wall <60 s on the pinned machine ⇒
  ABORT (I4 fails; padding forbidden).
- A-FROZEN: any frozen IDENTITY mismatch pre/post any leg ⇒ ABORT +
  investigate (frozen discipline breach).
- A-ENVELOPE: any network/key/cost/non-stdlib (outside SST leg —
  uninvolved) evidence ⇒ ABORT.
- A-TOUCH: touches over cap on either arm ⇒ guard FAIL for that leg
  (leg verdict VOID, not silently kept).

### 7.5 Analysis rules

Primaries are count/byte/validity predicates (§7.6) + rubric (§7.3);
wall-clock is guard-only (reported as observed durations, never a
superiority claim). Arm comparison is per value cell (§7.7), never a
single-race winner. Verdict code imports `predicates.py` verbatim;
any predicate edit after filing ⇒ new PREREG-LOG entry + re-freeze
(RULES-AMENDMENT-1 procedure).

### 7.6 predicates.py (VERBATIM — verdict imports this file)

```python
"""U-execute coded predicates (S5 design §7.6). Verdict imports verbatim."""
from __future__ import annotations

import hashlib
import json
from pathlib import Path

STEPS = ["identity", "suite-r1", "suite-r2", "suite-r3", "compat"]


def _ledger_entries(ledger: Path) -> list[dict]:
    out = []
    for line in ledger.read_text(encoding="utf-8").splitlines():
        if line.strip():
            out.append(json.loads(line))
    return out


def _success_invokes(entries: list[dict], key: str) -> dict[str, dict]:
    """step -> success invoke payload for proc.exec under idem key."""
    found: dict[str, dict] = {}
    for e in entries:
        if e.get("kind") != "invoke":
            continue
        p = e.get("payload", {})
        if p.get("capability") != "proc.exec" or "error" in p:
            continue
        proc = p.get("proc", {})
        if proc.get("idem_key") != key or "result_ref" not in p:
            continue
        found[proc.get("step", "")] = p
    return found


def _begins(entries: list[dict], key: str, step: str) -> list[dict]:
    return [e.get("payload", {}) for e in entries
            if e.get("kind") == "proc_begin"
            and e["payload"].get("idem_key") == key
            and e["payload"].get("step") == step]


def p_report_valid(checker_line: str) -> bool:
    """Checker verdict line (verdict_relcheck.py stdout, first line)."""
    return checker_line.strip() == "RELCHECK-VALID"


def p_steps_complete(entries: list[dict], key: str) -> bool:
    """Every step has exactly one success invoke under the key."""
    ok = _success_invokes(entries, key)
    return sorted(ok) == sorted(STEPS)


def p_no_completed_rerun(entries: list[dict], key: str) -> bool:
    """No step succeeded twice (resume skipped every completed step)."""
    seen: dict[tuple, int] = {}
    for e in entries:
        if e.get("kind") != "invoke":
            continue
        p = e.get("payload", {})
        if p.get("capability") != "proc.exec" or "error" in p:
            continue
        proc = p.get("proc", {})
        if proc.get("idem_key") != key or "result_ref" not in p:
            continue
        k = (proc.get("bundle_sha256"), proc.get("step"))
        seen[k] = seen.get(k, 0) + 1
    return all(v == 1 for v in seen.values())


def p_kill_leg_shape(entries: list[dict], key: str) -> bool:
    """Kill leg: suite-r3 began twice, succeeded once; rest began once."""
    for s in STEPS:
        n_beg = len(_begins(entries, key, s))
        if s == "suite-r3":
            if n_beg != 2:
                return False
        elif n_beg != 1:
            return False
    return p_steps_complete(entries, key) and p_no_completed_rerun(entries, key)


def p_ledger_report_agree(entries: list[dict], key: str,
                          report: dict) -> bool:
    """Every suite rc/count claim in the report matches ledger exit codes."""
    ok = _success_invokes(entries, key)
    suites = report.get("suites", {})
    for step in ("suite-r1", "suite-r2", "suite-r3"):
        claim = suites.get(step, {})
        if step not in ok:
            return False
        if ok[step].get("proc", {}).get("exit_code", -1) != 0:
            return False
        if claim.get("rc", -1) != 0:
            return False
    return True


def p_hashes_recompute(entries: list[dict], key: str,
                       artifacts_root: Path) -> bool:
    """Every ledger artifact hash recomputes from artifact bytes."""
    ok = _success_invokes(entries, key)
    for step, p in ok.items():
        for a in p.get("proc", {}).get("artifacts", []):
            fp = artifacts_root / f"proc-{key}" / step / a["relpath"]
            if not fp.exists():
                return False
            if hashlib.sha256(fp.read_bytes()).hexdigest() != a["sha256"]:
                return False
    return True


def p_change_leg_shape(entries: list[dict], key_new: str,
                       worlds: tuple[str, str]) -> bool:
    """Change leg ran under a NEW world with a distinct bundle pin."""
    creates = {e["payload"]["world_id"]: e["payload"]
               for e in entries if e.get("kind") == "create"}
    old_w, new_w = worlds
    if old_w not in creates or new_w not in creates:
        return False
    old_pins = {t["bundle_sha256"]
                for t in creates[old_w].get("procedures", [])}
    new_pins = {t["bundle_sha256"]
                for t in creates[new_w].get("procedures", [])}
    if not new_pins or new_pins & old_pins:
        return False
    return p_steps_complete(entries, key_new)


def p_conservation_ok(inspect_json: dict) -> bool:
    return inspect_json.get("conservation", {}).get("ok") is True


def p_rubric_bar(scores: dict) -> bool:
    """Blind rubric (§7.3): total>=4 and R2>=1."""
    return (scores.get("R1", 0) + scores.get("R2", 0)
            + scores.get("R3", 0)) >= 4 and scores.get("R2", 0) >= 1


def p_touch_cap(touches_used: int, cap: int = 2) -> bool:
    return touches_used <= cap


def p_no_sst_leg(run_dir: Path) -> bool:
    return not (run_dir / "sst-leg").exists()
```

### 7.7 Verdict rules (arm comparison per value cell)

- CELL-VALIDITY (per arm, per leg): `p_report_valid` AND
  `p_ledger_report_agree`(H only; D has no ledger — D's agreement is
  stamps-vs-report, audited by the same checker with `--no-ledger`
  mode, frozen) AND `p_hashes_recompute`(H). FAIL ⇒ arm-leg INVALID.
- CELL-RECOVERY (kill leg): H DEMONSTRATED iff `p_kill_leg_shape`
  AND `p_no_completed_rerun` AND VALID; D re-work counted from
  stamps+log (exact); comparison REPORTED (counts), with the
  preregistered directional claim: H re-executes 0 completed steps
  (predicate) while D's honest stamp-resume re-executes 0 completed
  steps too — EXPECTED TIE on counts; the discriminating H value is
  ledger accountability (`p_ledger_report_agree` +
  `p_hashes_recompute` have no D analogue — stated as the
  accountability cell, not as a recovery win).
- CELL-ADAPT (change leg): both arms must reach VALID under the
  revised bundle; cost-to-adapt counts REPORTED; preregistered claim:
  H's advertise-time validation refuses malformed revisions pre-work
  (demonstrated in S5-A8; in U-execute the revision is well-formed,
  so this cell measures parity honestly — no rigged defect).
- CELL-USEFUL (all legs): `p_rubric_bar` per arm, blind. Joint
  primary: arm must be VALID + meet the bar.
- Overall U verdict: HOST-VALUE-DEMONSTRATED iff H VALID + bar met
  on all legs AND guards hold AND ≥1 of (recovery accountability,
  adapt accountability) has its preregistered H-exclusive evidence
  present; else HOST-VALUE-NOT-DEMONSTRATED (with the failing cell
  named — a clean negative is complete). NO verdict claims H
  superiority on cost or speed — unclaimed by design.

### 7.8 PREREG-LOG entry plan

Standard entry (UTC stamp, PREREG.md sha, predicates.py sha (§7.6
verbatim), task pins (§7.1: bundle + IDENTITY bytes + suites +
surfaces + sealed envelope sha + kill spec + checker sha),
generator/harness shas, prev_hash chain, rule line) per
PREREG-LOG.md format; coordinator appends/countersigns BEFORE first
non-throwaway run (L1 lessons A+B; RULES-AMENDMENT-1). S5-A10
readiness runs are throwaway (own state dirs, disclosed, no verdict
implications).

## §8 Honesty section

### 8.1 Trust model (precise)

Callers supply procedures AND bear their content risk: the host never
asserts a procedure is correct, safe, useful, or meaningful. The host
asserts ONLY: (a) the executed bytes are exactly the advertised bytes
(hash-pinned, re-verified pre/post); (b) execution ran inside the
§1.4 envelope (enforced items guaranteed, contractual items labeled);
(c) the recorded accountability data (exit code, hashes, artifacts)
is complete and recomputable; (d) interruption landings are as
specified (§1.7). "Arbitrary-code trust" is NOT claimed: a malicious
or buggy caller procedure can do anything its OS privileges allow
(P11–P13) — the envelope detects some of it (P8/P9) and is silent on
the rest, BY STATED DESIGN. The procedure leg is a trustable
EXECUTOR for callers' own code, not a sandbox for adversaries'.

### 8.2 TEST/SST posture unchanged (SUBSTRATE-QUALIFIED)

The vehicle uses core only (stdlib; asserted by `p_no_sst_leg` +
no `SST_VENV_PY` in procedure env). No TEST-stub content is scored
as engineering value (I5 — vacuously satisfied, asserted anyway).
SST label stays SUBSTRATE-QUALIFIED SNAPSHOT per `sst_leg.py:18` +
LIMITS-7; Q-SST-1/2 still owner-open; nothing in this design consumes
or claims live SST.

### 8.3 STC excluded

STC stays EXCLUDED until Q-STC-0/1/2 close (REALUSE §5 carried
verbatim: no artifact, no immutable bytes, no contract — no argument
for inclusion exists). The STC adapter's honest terminal state is
unchanged.

### 8.4 Envelope limits carried (non-negotiable)

Single-host local disk; process-crash class only (no fsync; power/
media loss = disk-loss class, loud refusal); toy-adjacent scale for
sched (procedures are caller-scale — the vehicle's minutes are real
but modest; no scale claim beyond measured); deterministic host
plumbing (procedure determinism is the CALLER's property — the host
records bytes, never promises reproducibility of caller compute);
no learning; no cross-host; capabilities + procedure tables fixed at
birth; `retired` unexercised; kill-during-quarantine-transfer =
operator repair, excluded by pre-registration; frozen trees read-only.

### 8.5 What the procedure leg does NOT claim (explicit)

No sandbox/containment (P11–P13); no procedure correctness or
usefulness (caller property); no determinism of caller compute; no
general-compute qualification beyond the advertised table; no
producer acceptance of any kind; no durability beyond process-crash
atomicity; no cost/speed superiority over direct execution (unclaimed
by design — §7.7). Any sentence in successor-005 docs implying these
fails S5-A11.

## §9 Frank §: is the default the best vehicle, or does a stronger alternative exist?

The refined default (§2) is the best available vehicle, honestly but
narrowly. The one alternative carried to full comparison:

**ALT-1: programme evidence-claim re-verifier.** A procedure that
parses every VERDICT/RELEASE-RECORD/PREREG-LOG claim citing a hash,
recomputes each from frozen bytes, and emits a discrepancy report.
Real consumer (coordinator), real checkability (discrepancies are
mechanical). Why it LOSES: (a) I4 fails harder — hashing + parsing
~100 small files is seconds, and no honest long pole exists inside
it (unlike suite re-execution); (b) checker circularity is worse —
the independent checker must redo the same parse+recompute, so arm
agreement proves less; (c) the artifact is audit-shaped, pushing U
toward R-branch-adjacent "durable audit" (REALUSE §6 Option 2)
rather than useful software work. ALT-1 is a fine S5-A10-style
readiness probe, not a U vehicle.

Rejected without full carry: H2-content tasks (grid re-skin, G2);
SST-leg tasks (stub bar, I5); synthetic long tasks (padding =
theater, forbidden — detectable and disqualifying); identity-checker-
bare (§2.1). The §1 inventory (REALUSE §1) plus the new procedure
surface was re-walked: no interface was missed.

The honest weakness of §2 stands recorded: release-engineering
usefulness is real but niche, and the host's discriminating value is
accountability (ledger-cross-checked claims), not cost or speed. The
prereg (§7.7) is written to reward exactly that and nothing else. If
the coordinator wants a vehicle where the host wins on cost, no such
vehicle exists in this envelope — that would be a finding, and §7.4's
re-gate plus §7.7's verdict rules would record it cleanly.

## §10 Open questions + build authorization + recommendation dynamics

### 10.1 Open questions (resolve or escalate with options)

1. (Coordinator) Accept the §2 strengthening as part of the default
   (recommended), or direct ALT-1 (§9) / another vehicle? If neither,
   U stays BLOCKED — say so; do not run the bare checker.
2. (Coordinator) Is CONTRACTUAL network/fs-outside (P11/P12) acceptable
   for a release-line successor, or is OS isolation demanded? If
   demanded: out of envelope (needs namespaces/seccomp — new scope,
   new acceptance; escalate, do not smuggle).
3. (User, standing) Q5 permanent host stays open per authorization —
   no migration implied by successor-005 (reversible Python lineage,
   same as r3 Q5 row).
4. (Builder, at build) Pinned machine + interpreter pins (§7.1);
   `make`-vs-stdlib-runner choice for §5.1 (§5.1 allows either —
   pin one); measured honest expense (A-EXPENSE gate).

### 10.2 Exact build authorization restatement (what the builder gets)

Upon coordinator approval of THIS design (in whole; partial approval
re-specifies §1/§2 deltas explicitly):
- (a) Directory: create `prototype/successor-005/` ONLY, as a
  byte-verified copy of frozen `successor-004/` + rebrand
  (successor-004→successor-005 path/docstring map, disclosed) +
  the §1 delta (new files: procedure executor module, `test_procedure.py`;
  touched files: minihost/append-map-neutral additions, api, release,
  routing-world_record, resume-matcher extension, ORG-OPS/CONSUMER/
  LIMITS/INTERRUPTION-BOUNDARIES clauses, IDENTITY.regen).
- (b) Delta spec: §1 (all subsections, including the §7 one-sentence
  amend and the P11–P13 non-claims — the non-claims are normative).
- (c) Test plan: §6 checks S5-A1–S5-A12 (S5-A12 lane follows the
  builder; builder must not self-countersign).
- (d) Frozen discipline: r1 (successor-002 + release-20261004),
  successor-003 + release-r2, successor-004 + release-r3, H2-lane,
  P1-adapters — READ-ONLY (verify from byte-identical /tmp copies;
  demo/tests with state dirs under /tmp or in-tree runs/ per tree
  policy; `PYTHONDONTWRITEBYTECODE=1`; any content-neutral file
  event disclosed like r3 §4).
- (e) Envelope: $0, offline, stdlib-only except the untouched SST leg
  (vehicle asserts SST uninvolved); producer trees owner-held
  (no pin advances without owner evidence); Q5 open.
- (f) Vehicle + baseline + prereg: §2–§5 specified here travel WITH
  the build (bundle + checker + baseline + predicates drafted by the
  builder from this spec, frozen at prereg — builder drafts, lane +
  coordinator freeze).
- NOT authorized: any U-execute run (needs S5-A12 + §7.8 filing);
  any frozen-tree write; any §7 change beyond the one sentence;
  any isolation claim beyond §1.4; any padding of honest expense.

### 10.3 What evidence would change this recommendation

- I4 collapse: honest `relcheck` wall <60 s on any reasonable pinned
  machine, or suite-count shrinkage that removes the long pole ⇒
  re-abort (A-EXPENSE), vehicle unfit.
- Reopen breakage: procedure-table verification cannot compose with
  reopen/lineage-restore without breaking carried-suite ledger shapes
  ⇒ redesign-or-abort (§1.1/§1.2 decided shapes are load-bearing).
- Usefulness collapse: blind rubric bar missed on the S5-A10 readiness
  report by a wide margin with no vehicle-preserving fix ⇒ ALT-1 or
  re-scope (REALUSE §6 options stand behind this design).
- Isolation demand: any required P11/P12/P13 enforcement ⇒ out of
  envelope (escalate per Q2 — the design does not stretch there).
- A missed interface: a named-pointer challenge ("use interface X for
  step Y") answered by reading that yields a better vehicle ⇒
  re-walk §9 (cheapest next step, REALUSE §7 precedent).

---
*End of S5-DESIGN.md. Design-only: no code, runs, or host changes were
made or are authorized by this file — authorization flows only from
coordinator approval per §10.2.*

