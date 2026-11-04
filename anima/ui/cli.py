# Copyright 2026 Anshul48
# SPDX-License-Identifier: Apache-2.0
"""`anima status | ui | cmd | voice` -- the UI-and-voice slice of the anima CLI.

    anima status --tree [--demo | --state DIR | --chain FILE --jobs DIR]
    anima ui [--demo | --state DIR ...] [--port 8765]        (same as python3 -m anima.ui)
    anima cmd pause|resume|reprioritise|redirect|cancel TARGET [...]
    anima cmd run-next --harness muse|claude|codex
    anima cmd list
    anima voice CLIP.wav | --mic SECONDS [--model base|small] [--yes]

The `anima` CLI forwards these four verbs to ``main`` here with the verb intact.
With no data-source flag the newest real run under $ANIMA_HOME/runs is shown.

Command files (`anima cmd ...`, the screen's buttons, spoken pause/resume/run-next): NOTHING READS THEM YET.
They are therefore off by default: `cmd` only previews, the screen shows no buttons, the voice command says
"recognised, disabled".  See docs/INTEGRATED-DEMO.md.
"""
from __future__ import annotations

import argparse
import importlib.util
import json
import sys
from pathlib import Path

from . import commands as cmdmod
from . import source as srcmod
from . import textmode


def add_source_args(p):
    p.add_argument("--demo", action="store_true",
                   help="replay the real recorded run in docs/evidence/flagship-run3 (read-only)")
    p.add_argument("--state", help="ANIMA state dir: decisions.jsonl, jobs/, commands/")
    p.add_argument("--chain", action="append", help="decision record (JSONL chain); repeatable")
    p.add_argument("--run", metavar="NAME|latest",
                   help="a real run folder under $ANIMA_HOME/runs (what `anima run` writes), or 'latest' (the default when no source is given)")
    p.add_argument("--jobs", help="job folders dir (job.json + events.jsonl per job)")
    p.add_argument("--job-limit", type=int, default=30, help="newest N job folders only (default 30)")
    p.add_argument("--job-prefix", help="only job folders whose name starts with this")
    p.add_argument("--commands", help="where command files go (default <state>/commands; demo: a temp dir)")


def source_from(a):
    chains = a.chain
    if a.run:
        chains = [str(srcmod.resolve_run(a.run))] + list(chains or [])
    elif not (a.demo or a.state or a.chain or a.jobs):
        chains = [str(srcmod.resolve_run("latest"))]   # the real run chain, not a recording
    return srcmod.Source.from_args(demo=a.demo, state=a.state, chains=chains, jobs=a.jobs,
                                   commands=a.commands, job_limit=a.job_limit, job_prefix=a.job_prefix)


def source_flags(a):
    """The flags that reproduce this source on another command line."""
    f = []
    if a.demo:
        f.append("--demo")
    if a.state:
        f += ["--state", a.state]
    for c in a.chain or []:
        f += ["--chain", c]
    if getattr(a, "run", None):
        f += ["--run", a.run]
    if a.jobs:
        f += ["--jobs", a.jobs]
    if a.commands:
        f += ["--commands", a.commands]
    return f


def cmd_status(a):
    src = source_from(a)
    snap = src.snapshot(upto=a.upto)
    if a.json:
        t = snap["tree"]
        print(json.dumps({"tree": t, "now": snap["now"], "n": snap["n"], "total": snap["total"]}, indent=1))
        return 0
    if not a.tree:
        c = snap["tree"]["counts"]
        ch = snap["tree"].get("chain") or {}
        print(f"{c['tasks']} tasks: {c['verified']} verified, {c['running']} running, "
              f"{c['escalated']} escalated; chain {'OK' if ch.get('ok') else 'n/a'} "
              f"({ch.get('records', 0)} records). Use --tree for the tree.")
        return 0
    print(textmode.render(snap, src.describe(), width=a.width, verbose=a.verbose))
    return 0


def resolve_target(src, target):
    """Task number (as printed by `status --tree`) or name -> task name."""
    if not target.isdigit():
        return target
    from . import model
    snap = src.snapshot()
    t = model.task_by_number(snap["tree"], int(target))
    if not t:
        n = sum(len(w["children"]) for w in snap["tree"]["children"])
        raise SystemExit(f"anima: no task number {target} (the tree has {n} tasks; see `anima status --tree`)")
    return t["label"] if t["id"].startswith("task:") else t["label"]


def cmd_cmd(a):
    if a.verb == "list":
        src = source_from(a)
        pend = cmdmod.list_commands(src.commands)
        if not pend:
            print(f"no pending command files in {src.commands}")
        for p in pend:
            tgt = (p.get("target") or {}).get("task", "-")
            print(f"{p['_file']}: {p['verb']} {tgt} {json.dumps(p.get('args') or {})} by {p.get('issued_by')}")
        return 0
    src = source_from(a)
    target = resolve_target(src, a.target) if a.target else None
    args = {}
    if a.priority:
        args["priority"] = a.priority
    if a.harness:
        args["harness"] = a.harness
    try:
        cmd = cmdmod.build_command(a.verb, target, args, a.reason or "", a.issued_by)
    except cmdmod.CommandError as e:
        print(f"anima cmd: {e}", file=sys.stderr)
        return 2
    print("command:  " + cmdmod.cli_line(cmd))
    if a.dry_run:
        print("dry run: nothing written")
        print(json.dumps(cmd, indent=1, sort_keys=True))
        return 0
    if not a.write_file:
        print("NOT WRITTEN, NOT APPLIED: nothing reads command files yet, so this could not change any run.")
        print("          (--write-file writes the file anyway; that tests the file format only)")
        print(json.dumps(cmd, indent=1, sort_keys=True))
        return 3
    path = cmdmod.write_command(src.commands, cmd)
    print(f"written:  {path}")
    print("effect:   NONE YET. A command file only; no part of `anima` reads this folder, so nothing will happen")
    if a.forward:
        ran, msg = cmdmod.forward_cancel(cmd, a.jobs or (src.jobs and str(src.jobs)))
        print(("forwarded to hand-run cancel: " if ran else "not forwarded: ") + msg)
        if not ran:
            return 3
    return 0


def cmd_ui(a):
    from . import server
    return server.serve(source_from(a), host="127.0.0.1", port=a.port, open_browser=a.open,
                        commands_enabled=a.enable_command_files)


def cmd_voice(a):
    spec = importlib.util.spec_from_file_location(
        "anima_voice", srcmod.REPO_ROOT / "voice" / "anima_voice.py")
    mod = importlib.util.module_from_spec(spec)
    sys.modules["anima_voice"] = mod
    spec.loader.exec_module(mod)
    return mod.run(a, source_flags(a), lambda argv: main(argv))


def build_parser():
    ap = argparse.ArgumentParser(prog="anima", description=__doc__.split("\n\n")[0])
    sub = ap.add_subparsers(dest="cmd", required=True)

    s = sub.add_parser("status", help="show the state space tree as text")
    add_source_args(s)
    s.add_argument("--tree", action="store_true", help="the tree (Telegram-friendly text)")
    s.add_argument("--json", action="store_true", help="machine-readable")
    s.add_argument("-v", "--verbose", action="store_true", help="add each task's last decision")
    s.add_argument("--width", type=int, default=46)
    s.add_argument("--upto", type=int, help="replay: only the first N records")
    s.set_defaults(fn=cmd_status)

    u = sub.add_parser("ui", help="serve the SST screen on 127.0.0.1 (read-only view of the newest real run unless told otherwise)")
    add_source_args(u)
    u.add_argument("--port", type=int, default=8765)
    u.add_argument("--open", action="store_true", help="try to open a browser tab")
    u.add_argument("--enable-command-files", action="store_true",
                   help="show the command buttons and let them write command files. Off by default: nothing reads those files yet, "
                        "so a button could not change a run")
    u.set_defaults(fn=cmd_ui)

    c = sub.add_parser("cmd", help="preview a command file (pause, reprioritise, redirect, ...). DISABLED by default: nothing reads these files yet")
    c.add_argument("verb", choices=sorted(cmdmod.VERBS) + ["list"])
    c.add_argument("target", nargs="?", help="task name or the number shown by `status --tree`")
    c.add_argument("--priority", choices=cmdmod.PRIORITIES)
    c.add_argument("--harness", choices=cmdmod.HARNESSES)
    c.add_argument("--reason")
    c.add_argument("--issued-by", default="cli", choices=("cli", "ui", "voice"))
    c.add_argument("--dry-run", action="store_true")
    c.add_argument("--write-file", action="store_true",
                   help="write the command file even though nothing reads it (tests the file format only)")
    c.add_argument("--forward", action="store_true",
                   help="cancel only: also run the real `hand-run cancel` for a job folder (needs --jobs)")
    add_source_args(c)
    c.set_defaults(fn=cmd_cmd)

    v = sub.add_parser("voice", help="speak a command (audio file; microphone if available)")
    v.add_argument("audio", nargs="?", help="short audio file (wav, mp3, m4a, ...)")
    v.add_argument("--mic", type=float, metavar="SECONDS", help="record this many seconds from the microphone")
    v.add_argument("--model", default="base", choices=("base", "small"))
    v.add_argument("--yes", action="store_true", help="confirm without asking (for scripts and tests)")
    v.add_argument("--dry-run", action="store_true", help="show the command, never run it")
    v.add_argument("--text", help="skip speech-to-text and use this text (tests only)")
    add_source_args(v)
    v.set_defaults(fn=cmd_voice)
    return ap


def main(argv=None):
    a = build_parser().parse_args(argv)
    return a.fn(a)


if __name__ == "__main__":
    sys.exit(main())
