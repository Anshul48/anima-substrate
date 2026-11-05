# ANIMA integrated demo: what it is and how to show it

ANIMA plugs the coding agent you already use (Muse Code, Claude Code or Codex)
into a ladder with a checker it cannot see and a record of every step.
This tree joins three pieces: the ladder, the state-tree screen, and a memory
of past jobs. Every feature below was run from a fresh clone on 2026-11-04;
each section names the command, what it printed, and what it needs.

## The pain, in one sentence

You use an AI coding agent every day and it forgets: it fixes the same kind of
bug twice and shows you nothing of how it decided.

## Watch it work (about 60 seconds of screen)

1. A small bug, fixed by Muse Code, judged by a hidden checker: `VERDICT PASS`.
2. The decision record verifies: `CHAIN OK - 7 records, every link matches`.
3. The second run on the same bug starts with `1 similar past job(s) put in
   front of the prompt` — the fix from the first run, re-checked against its
   source just now (`source check: OK`).
4. The tree shows the run as verified. Voice control hears `show status` and
   the tree prints.

## How you use it (exact steps, from nothing)

```sh
# 1. Install (one line; prints its plan first; no sudo, no login needed).
curl -fsSL https://raw.githubusercontent.com/Anshul48/anima-substrate/main/install.sh | sh

# 2. Check what was found.
~/.anima/bin/anima doctor

# 3. Prepare the memory (needs the network once: packages plus a small model).
~/.anima/bin/anima memory setup

# 4. Fix a small bug with the memory in the loop (uses your Muse login).
~/.anima/bin/anima run --task tiny-bug --harness muse --memory trace

# 5. Watch the tree (text) and ask the memory directly.
~/.anima/bin/anima status --tree
~/.anima/bin/anima memory recall "<the bug in your own words>"

# 6. Browser screen (read-only) and voice (needs a Python with faster-whisper,
#    pointed to by ANIMA_STT_PYTHON; the clips ship in the repo checkout).
~/.anima/bin/anima ui
ANIMA_STT_PYTHON=/path/to/whisper/python ~/.anima/bin/anima voice ~/.anima/repo/voice/clips/show-status.wav --demo --dry-run
```

What each run showed on 2026-11-04 (fresh clone, rung 0, Muse Code): first run
159 seconds, `VERDICT PASS`, 1 passage recorded; second run 135 seconds,
`VERDICT PASS`, 1 past job recalled with similarity 0.733 and a clean source
check; voice clips transcribed in about 1 to 2 seconds on CPU. The state-tree
screen served the real run over HTTP with title `ANIMA state tree`.

Details per part: [harnesses](HARNESSES.md) (exact timings, what was and was
not tested live), [memory](MEMORY.md), [screen and voice](UI.md).

## Honest limits (one plain scene)

- Proven for ONE job type: fixing a small bug against hidden tests. It is not
  proven as a general scheduler. We make no claim about long runs, or about
  leaving it alone while you are away.
- Only the first rung (a Muse Code worker) ran live in the merged tree. The
  ladder to Claude Sonnet and Codex is built and prints its exact command
  lines with `--dry-run`; those rungs ran live only in the earlier harness
  slice runs, not in the merged tree.
- `anima cmd` writes command files that nothing reads yet. The screens and
  the voice commands label those buttons DISABLED instead of pretending.
- Recall is only as good as the runs it recorded, and a hit it cannot tie to
  its source is left out and named, not shown.
- Recall of a new, different bug is a small preliminary test: a 3-task held-out
  check found 0 hits at similarity 0.30 with the baseline passages, while two
  tuned variants cleared 0.30 on 2 of 3. The run above recalls the same bug,
  second run.
- The memory needs the network once (setup). The runs themselves need your
  agent login. Voice needs faster-whisper installed and downloads its model
  once; the demo clips ship with the repo.

## Next step

Try the commands above on the `tiny-bug` fixture, then point `anima run`
at your own small bug with `--allow-unapproved-task` (you accept the risk:
containment outside the tested fixtures is NOT tested).
