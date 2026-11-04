# The state space tree screen, text mode, and voice

One screen that shows what every agent is doing and lets you change it; the same tree as plain text for a phone
chat; and a voice command that runs a small fixed set of commands after you confirm. Python 3 standard library
only for everything except speech-to-text (faster-whisper, see below).

Replay the real recorded run (the nine-job run in [`docs/evidence/flagship-run3`](evidence/flagship-run3/README.md)):

```bash
python3 -m anima.ui --demo            # then open http://127.0.0.1:8765/
python3 ui/bin/anima status --tree --demo
```

Nothing in `--demo` is made up: the screen is built from `decisions.jsonl` in the evidence folder. It replays the
655 seconds of the recorded run (default speed 40x, so about 17 seconds).

## What the screen shows

One tree, left to right: **owner -> workstream -> task -> attempt**. An attempt is one try of a task by one harness
(a rung of the ladder). An escalation (the hidden checker said no, so the next helper tries) is the dashed arrow
between two attempts of the same task.

Every node shows four things:

| Shown | Where it comes from |
|---|---|
| status (queued, running, verified, rejected, ...) | the decision record: `task.created`, `task.started`, `task.done`, `task.blocked`, and the gate verdict inside each attempt record |
| harness | the `pool` of the attempt (`laptop-muse` is shown as Muse Code, `claude-sonnet` as Claude Code, `codex-*` as Codex; the pool name is kept in the side panel) |
| cost so far | **wall seconds**, measured: the recorded `wall_seconds` of finished attempts, plus time since `task.started` for running ones (at replay speed the counters tick with the replay clock). Tokens and dollars are shown only if a record carries them; the nine-job record does not, and the screen says "not recorded" instead of guessing |
| last decision | the newest decision-type record of the node (`decision.made`, `task.done`, `task.blocked`, else the newest record), with its line number and seal |

Click a node and the side panel lists every record behind it (newest first); click a record to see the raw JSON.
Each record shows **linked** if its `prev` equals the SHA-256 of the line before it. The header badge says
`chain OK` only if every link in the file matches; this is re-checked each time the file is read. In replay,
scrubbing to record N checks records 1 to N. One broken byte shows as `CHAIN BROKEN at line N` (a unit test does
exactly this to a copy of the real record).

Keys in replay: space = play/pause, left/right = one record, Home/End. The bar at the bottom shows each record as
a tick (amber = decision, red = rejected, green = verified).

### Live mode

```bash
python3 -m anima.ui --state DIR            # DIR/decisions.jsonl, DIR/jobs/, DIR/commands/
python3 -m anima.ui --chain a.jsonl --chain b.jsonl --jobs ~/owner-hub/jobs --job-limit 20
```

The files are re-read from disk every 2 seconds, so a running ANIMA shows up without a restart (a missing
`decisions.jsonl` shows "waiting"). Job folders (`<id>/job.json` + `events.jsonl`, the layout of the `hand-run`
supervisor) are shown as tasks whose attempts are the job's attempts; their logs are **not** hash-chained, and the
screen marks them "unchained" and never shows a seal for them. Job folders are read-only here.

The record format this reads (the one the nine-job run wrote): one JSON object per line with `ts`, `kind`, `actor`,
`task`, `data`, `prev`. Unknown kinds are listed in the side panel and do not break the tree.

## Changing things: command files

The panel's "Change it" buttons (Pause, Resume, Reprioritise, Redirect, Cancel; "Run next job" on the owner or a
workstream) build a command, **show it**, and only write it after a second click. A command is one small JSON file
in `<state>/commands/`:

```json
{"schema": "anima.command/1", "id": "c6507fc7cf02", "verb": "pause",
 "target": {"task": "cachetools-stacked-decorators", "node": "task:cachetools-stacked-decorators"},
 "args": {}, "reason": "owner says wait", "issued_by": "ui", "issued_at": "2026-11-04T18:58:21Z", "state": "pending"}
```

The same command from a shell: `anima cmd pause cachetools-stacked-decorators --reason "owner says wait"`
(a task number from `status --tree` also works: `anima cmd pause 3`). Pending commands show on their node
("pause requested"). `anima cmd list` shows the folder.

Contract with the scheduler (the `anima` that runs jobs): it reads `commands/*.json`, applies or refuses each,
moves the file to `commands/applied/` or `commands/refused/`, and appends its own decision to the record. **That
reader is not part of this slice** (it belongs to the harness side), so today a command file is a request that
nothing consumes. The one exception: `cancel` on a job folder can be forwarded to the existing `hand-run cancel
<job>` with `--forward` (the screen offers a checkbox in live mode when `hand-run` is found, via `ANIMA_HAND_RUN`
or `PATH`). Pause, reprioritise, redirect and run-next have no CLI to call yet; for them, writing the file is the
whole effect. In `--demo` nothing is ever written to the evidence folder: command files go to a temp folder.

The server binds 127.0.0.1 only, checks the Host and Origin headers, and requires a per-process token for the one
write endpoint, which can only write a command file.

## Text mode (for Telegram or a terminal)

```bash
anima status --tree --demo            # or --state DIR, --jobs DIR
anima status --tree --state DIR -v    # adds each task's last decision and seal
```

Narrow (under 50 columns), plain ASCII, no colour. Tasks are numbered; the number is what voice and `anima cmd`
use. `anima` here is the launcher `ui/bin/anima`; the main `anima` CLI is expected to forward
`status | ui | cmd | voice` to `anima.ui.cli:main`.

## Voice

```bash
anima voice clip.wav --demo                 # transcribe, show the command, ask, run
echo y | anima voice voice/clips/pause-task-3.wav --demo
anima voice clip.wav --demo --dry-run       # show only
anima voice --mic 4 --demo                  # microphone (see limits)
```

Speech-to-text is **faster-whisper on CPU** (int8), model `base` (default) or `small` (`--model small`), run in a
child process by the Python that has it (`ANIMA_STT_PYTHON`, default `~/stt_venv/bin/python`). Whatever it hears is
mapped by a fixed grammar to exactly these commands; nothing else can ever run:

| You say | It runs |
|---|---|
| "show status" | `anima status --tree` |
| "pause task 3" / "resume task 3" | `anima cmd pause|resume <name of task 3>` (writes a command file) |
| "run the next job with muse / claude / codex" | `anima cmd run-next --harness ...` (writes a command file) |
| "recall similar fixes" | `anima recall --similar` (needs the memory link; see below) |

Before running, it prints what it heard, the command it matched and the exact command line, then asks `Run it?
[y/N]`. Anything but `y` runs nothing (exit 3). `--yes` skips the question for scripts. A phrase that matches
nothing, or matches two commands, runs nothing (exit 2). Small speech-to-text slips are tolerated ("recalls similar
fixes", "cloud" for Claude, "code x"); number words and digits both work.

Limits, stated plainly: the test clips are synthetic speech from the local Kokoro voice, not human recordings, so
accent and noise robustness are untested. The microphone path (`--mic`) records through ffmpeg from WSLg's
`RDPSource`; on the author's machine it records but captured silence (the Windows microphone was not feeding it),
so `--mic` with real speech has **not** been run, and the command refuses a silent recording rather than guessing.
File input always works. `recall similar fixes` calls `anima.memory.recall_main` if that module exists in the
checkout and says "not wired" otherwise.

## Tests

```bash
python3 -m unittest anima.ui.tests.test_ui     # chain, tamper, tree, commands, server (16 tests)
python3 -m unittest discover -s voice/tests    # grammar
python3 -m anima.ui.replay_feed --to DIR       # test tool: feeds the real record into DIR for live mode
```

`replay_feed` re-seals a time-shifted copy of the real record so the live screen can be tested; it is a test tool,
never evidence of a run.
