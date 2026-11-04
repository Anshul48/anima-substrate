# Use ANIMA with the coding agent you already have

ANIMA does not replace your coding agent. It sits next to it: your agent does the work, a hidden checker
judges the result, and if the answer is wrong a stronger helper gets a turn. Every decision goes into a record
you can check.

This page covers three agents, in this order: **Muse Code**, **Claude Code**, **Codex**. You need at least one
of them installed and logged in. ANIMA never logs in for you.

## The 60-second version

1. **Install** (one line; it prints exactly what it will do before it does it):

   ```sh
   curl -fsSL https://raw.githubusercontent.com/Anshul48/anima-substrate/main/install.sh | sh
   ```

   It copies the code into `~/.anima`, makes a Python environment (nothing to download: ANIMA uses only the
   Python standard library), and runs `anima init`, which looks for Muse Code, Claude Code and Codex on your
   machine and writes `~/.anima/anima.yaml`. No `sudo`. It does not touch your shell startup files. Run it
   again any time: it keeps your settings.

   > That web address exists only after the project owner publishes the repository. Until then the installer was
   > tested against a local copy (see the table at the bottom). To try it today, clone the repository and run
   > `sh install.sh` from inside it, or set `ANIMA_REPO_URL`.

2. **Check what it found:**

   ```sh
   anima doctor            # looks only: is each program there, does it have the flags ANIMA needs?
   anima doctor --live     # also makes one tiny real call per role, through your own login
   ```

   Without `--live`, an agent shows `READY (not live-tested)` at best, because nothing was tried. With `--live` it
   shows `PASS` or `NOT RUN`. `NOT RUN` means ANIMA could not try it (not installed, login expired, no network),
   and it prints the agent's own message so you can fix it. `FAIL` is kept for "it ran and gave a wrong result".
   ANIMA never prints `PASS` for something it did not run.

3. **Run a task** and let the hidden checker judge it:

   ```sh
   anima run --harness muse --task tiny-bug
   ```

## Three examples

Every example uses the same small task: a function `moving_average` that drops its last window. The agent is
told to fix it. A hidden test file the agent never sees decides pass or fail.

### 1. Muse Code (the default first choice)

```sh
anima harness test muse                 # one tiny real call; uses your own Muse Code login
anima run --harness muse --task tiny-bug
```

Behind the scenes ANIMA runs `muse exec --json`, hands the task over in a file (never on the command line),
and reads Muse's event stream. As a **worker** Muse may edit files. As an **architect** ANIMA adds
`--disable-write --disable-shell --approval-mode never`, so Muse can only read and plan.

Good to know:

- By default the worker runs with `--approval-mode never`. Muse can edit files but cannot run shell commands
  here: on the machine this was built on, Muse's shell sandbox could not start (`bwrap: No permissions to create
  a new namespace`). The tiny task still passes without a shell, but slower (169 s, against 25 s for Claude and 49 s for
  Codex in our run). For a worker that must run tests, set `yolo: true` for muse in `anima.yaml`; then ANIMA's
  own rule checks matter more.
- `muse --permission-profile` needs a profile defined by your organisation's policy. On the test machine none
  existed, so Muse printed `Permission profile 'default' is unavailable: profile does not exist.` and ANIMA
  does not use it.

### 2. Claude Code

```sh
anima harness test claude
anima run --harness claude --task tiny-bug
```

ANIMA runs `claude -p --output-format stream-json`. The architect role gets plan mode with read-only tools. The
worker gets edit permission for its workspace only. Claude Code is the one agent where ANIMA can also block a
single risky action *before* it happens (a per-action hook; see "What is checked while the agent works").

### 3. Codex

```sh
anima harness test codex
anima run --harness codex --task tiny-bug
```

ANIMA runs `codex exec --json` with the prompt on standard input and the sandbox set to `workspace-write`
(worker) or `read-only` (architect). If your Codex login has expired, `anima doctor` shows `NOT RUN` with
Codex's own message; run `codex login` yourself, then try again.

### Any other tool

```sh
anima harness add custom --name mytool --argv '["mytool","--prompt-file","{prompt_file}"]'
```

Placeholders: `{prompt_file} {workspace} {job_id} {model} {out_file} {role}`. A `--argv` that is not a JSON list of
strings is refused with a plain message. A run whose first step is a custom adapter is labelled `CUSTOM` in the
record instead of `REAL`, so a demo with a stand-in adapter can never pass for a real run.

## Choose who plans and who edits

Each agent can play either role. Set it once:

```sh
anima harness use --architect claude --worker muse
```

or edit `~/.anima/anima.yaml`:

```yaml
harness: muse
roles:
  architect: {harness: claude, may: [read_repo, review], must_not: [push]}
  worker:    {harness: muse, may: [write_workspace, run_tests], must_not: [secrets, push], budget: {timeout_s: 1800}}
ladder:
  - {on: gate_fail, do: run_with, harness: claude}
  - {on: gate_fail, do: run_with, harness: codex}
  - {on: still_failing, do: ask, role: architect}
```

- `anima run --task tiny-bug --plan-first` asks the architect for a plan, then gives it to the worker.
- `anima run --harness muse --role architect --task tiny-bug` gets a read-only plan and runs no checker.
- `anima run --harness muse --ladder --task tiny-bug` follows the `ladder:`. This is the same escalation idea as
  the main ANIMA harness (wrong answer, next helper) driven by the same hidden checker (`gate.py`, copied
  unchanged).
- `anima run ... --dry-run` prints the exact command lines and starts nothing.

## What is checked while the agent works

Rules (the `rules:` list in `anima.yaml`): `secrets`, `sudo`, `push-public`, `delete-protected`. They look at
command text. `enforce.mode` is `warn` (default: only write down what would have been blocked), `shadow`, or
`enforce` (stop the agent).

- **Process watch (all agents).** While the agent runs, ANIMA looks at the agent's processes from the outside
  about ten times a second and applies the rules to every command line it sees. In `enforce` mode it kills the
  run. It follows child processes by parent id, because Muse starts each shell command in a new session.
  Limit: it polls, so a command that starts and ends within about a tenth of a second can be missed.
- **Per-action hook (Claude Code only).** `enforce.via: pretooluse_hook` makes Claude Code ask ANIMA before each
  tool call (`anima check --hook`). A blocked action never runs.
- **Quiet-run watch.** `watches: [{name: stall, check: "no_output_for 120s"}]` flags a run that stops producing
  output.
- These rules are a safety net, not a sandbox. They match text.

Declared in the profile but **not enforced** by this adapter layer: `spend`, `bulk_edit`, `message_owner`,
`edit_mission` in `must_not`; budget keys other than `timeout_s`, `attempts`, `max_turns`; `mission` and `memory`
(kept in the file, not run here); watches other than the quiet-run check. `anima doctor` lists these for your
actual profile.

## What ANIMA never does

- It never reads your login or key files. It runs each agent's normal command and lets that agent use its own
  login. Environment variables that look like keys (`*_API_KEY`, `*_TOKEN`, `*SECRET*`) are not passed on; you
  cannot add them to the allow list.
- It never uses `sudo`, never pushes to a repository, never installs system packages.
- The installer never calls a model. A model is called only by `anima harness test`, `anima doctor --live` and
  `anima run`, and always through your own agent and login (so your own plan or bill applies).

## What was tested, and what was not

Tested on one machine (Ubuntu on WSL2, Python 3.12.3, Muse Code 1.4.14, Claude Code 2.1.318, codex-cli 0.163.0),
from a fresh clone installed by `install.sh`. The commands and their real output are in `RUN-LOG.md`, which ships
with this change. Anything not in the left column was not run.

| Tested (real output in RUN-LOG.md) | Not tested |
|---|---|
| `install.sh` from a fresh clone, run twice (the second run kept the profile as it was); link step in a throwaway home | The `curl ... raw.githubusercontent.com` line itself: the address exists only after the owner publishes. It was run against a local `file://` copy |
| `anima init` found Muse, Claude and Codex and wrote `anima.yaml` | macOS, Windows, other Linux distributions, Python versions other than 3.12 |
| `anima harness list`, `anima doctor`, `anima doctor --live` | The login-expiry message of Muse Code and Claude Code (only Codex's was seen) |
| `anima harness test` for Muse, Claude, Codex (second login): both roles, one tiny real call each | Primary Codex login: **NOT RUN**, "refresh token was already used"; the owner must run `codex login` |
| Real runs of the seeded broken function through Muse, Claude and Codex (second login), each judged by the hidden checker: PASS | Any task beyond the seeded one; the nine real-library jobs were not driven through these adapters |
| Architect role (read-only plan) with Claude and with Muse; workspace unchanged | Codex as architect in a full `anima run` (only the tiny `harness test` call) |
| Plan first (Claude plans, Muse edits): PASS | Natural escalation Muse to Claude to Codex on real failures: the demo uses a do-nothing custom adapter as rung 0 and is labelled `CUSTOM` |
| Escalation: failing rung 0, then Claude passes at rung 1, with the checker's failure line passed along | The ladder's final "ask the architect" stop |
| `anima check`: secret read and `git push` blocked (exit 3), `ls` allowed | A custom adapter wrapping a real third-party tool (only a do-nothing `true`) |
| Claude per-action hook blocked a secret read, twice | `enforce.mode: shadow` (same code path as `warn`); the quiet-run (stall) watch and timeouts in a real agent run (unit tests only) |
| Muse process watch with `yolo: true`: `git push` killed in `enforce` mode, logged but not killed in `warn` mode | Muse process watch catching a secret read: Muse declined to `cat`, and its one-shot `ls` was too short to see (a polling limit) |
| Decision chain checked by `anima verify-log` and by the repository's own `check_chain.py` | Muse `--permission-profile` (profile does not exist here, so it cannot be used) |
| 40 unit tests pass (adapters, profile, chain, rules, watch, command line) | Cost and token counts: not measured |

Honest notes: the `claude` command on the build machine is a wrapper that adds `--dangerously-skip-permissions`, so
the Claude runs there say less about Claude's own permission prompts than they would on a plain install. The watch
polls and matches text; it is a safety net, not a sandbox.
