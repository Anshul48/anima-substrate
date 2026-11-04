# Copyright 2026 Anshul48
# SPDX-License-Identifier: Apache-2.0
"""Command files: how the SST screen, the CLI and the voice command ask `anima`
to change something.  Stdlib only.

A command is one small JSON file in ``<state>/commands/``.  Writing it is the
whole action of this layer: the scheduler (``anima``) is the reader.  When it
has applied or refused a command it moves the file to ``commands/applied/`` or
``commands/refused/`` and appends its own decision to the tamper-evident
record.  This module never writes to the record (the record belongs to the
scheduler) and never kills or edits a running agent.

Only ``cancel`` on a job folder can be forwarded to a real, existing CLI
(``hand-run cancel <job-id>``); the other verbs have no CLI to call yet, so
for them the command file is the only effect.
"""
from __future__ import annotations

import json
import os
import re
import shlex
import shutil
import subprocess
import time
import uuid
from datetime import datetime, timezone
from pathlib import Path

SCHEMA = "anima.command/1"
HARNESSES = ("muse", "claude", "codex")
PRIORITIES = ("high", "normal", "low")
VERBS = {
    "pause": "stop scheduling new attempts for this task until resumed",
    "resume": "undo a pause",
    "reprioritise": "change this task's place in the queue (priority: high / normal / low)",
    "redirect": "send the next attempt of this task to a different harness",
    "cancel": "stop this task for good (job folders: forwarded to `hand-run cancel`)",
    "run-next": "start the next queued job on a chosen harness",
}
NEEDS_TARGET = {"pause", "resume", "reprioritise", "redirect", "cancel"}
_NAME = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_.:\-]{0,120}$")


class CommandError(ValueError):
    pass


def utc_now_iso():
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def build_command(verb, target=None, args=None, reason="", issued_by="cli"):
    """Validate and return the command dict (no file is written)."""
    if verb not in VERBS:
        raise CommandError(f"unknown verb {verb!r}; allowed: {', '.join(VERBS)}")
    args = dict(args or {})
    tgt = None
    if verb in NEEDS_TARGET:
        if not target or not isinstance(target, str) or not _NAME.match(target):
            raise CommandError(f"{verb} needs a target task name (letters, digits, - _ . :)")
        name = target.split(":", 1)[1] if target.startswith(("task:", "job:")) else target
        tgt = {"task": name, "node": target if target.startswith(("task:", "job:")) else f"task:{name}"}
    if verb == "reprioritise":
        if args.get("priority") not in PRIORITIES:
            raise CommandError(f"reprioritise needs priority in {PRIORITIES}")
    if verb in ("redirect", "run-next"):
        if args.get("harness") not in HARNESSES:
            raise CommandError(f"{verb} needs harness in {HARNESSES}")
    reason = " ".join(str(reason or "").split())[:300]
    return {
        "schema": SCHEMA, "id": uuid.uuid4().hex[:12], "verb": verb,
        "target": tgt, "args": args, "reason": reason,
        "issued_by": issued_by, "issued_at": utc_now_iso(), "state": "pending",
    }


def cli_line(cmd, state=None):
    """The `anima` command line that writes exactly this command."""
    parts = ["anima", "cmd", cmd["verb"]]
    if cmd.get("target"):
        parts.append(cmd["target"]["task"])
    for k, v in sorted((cmd.get("args") or {}).items()):
        parts += [f"--{k}", str(v)]
    if cmd.get("reason"):
        parts += ["--reason", cmd["reason"]]
    if state:
        parts += ["--state", str(state)]
    return " ".join(shlex.quote(p) for p in parts)


def write_command(commands_dir, cmd):
    """Atomically write the command file; returns its path."""
    d = Path(commands_dir)
    d.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S")
    seq = 1 + sum(1 for p in d.glob("*.json"))
    name = f"{stamp}Z-{seq:04d}-{cmd['verb']}-{cmd['id']}.json"
    path = d / name
    tmp = d / (name + ".tmp")
    with open(tmp, "w") as f:
        json.dump(cmd, f, indent=1, sort_keys=True)
        f.write("\n")
        f.flush()
        os.fsync(f.fileno())
    os.replace(tmp, path)
    return path


def list_commands(commands_dir):
    """Pending commands (top-level *.json), oldest first.  Unreadable files are skipped."""
    d = Path(commands_dir)
    out = []
    if not d.is_dir():
        return out
    for p in sorted(d.glob("*.json")):
        try:
            c = json.loads(p.read_text())
        except (OSError, ValueError):
            continue
        if isinstance(c, dict) and c.get("schema") == SCHEMA:
            c["_file"] = p.name
            out.append(c)
    return out


def hand_run_path():
    """The existing job CLI, if present: $ANIMA_HAND_RUN, else `hand-run` on PATH."""
    env = os.environ.get("ANIMA_HAND_RUN")
    if env and os.access(env, os.X_OK):
        return env
    return shutil.which("hand-run")


def forward_cancel(cmd, jobs_dir):
    """Forward a `cancel` for a job folder to the real `hand-run cancel`.

    Returns (ran, message).  Refuses anything but a cancel whose target is a
    job id that exists as a folder under ``jobs_dir``.
    """
    if cmd["verb"] != "cancel":
        return False, "only cancel is forwarded (no other verb has a CLI to call)"
    hr = hand_run_path()
    if not hr:
        return False, "hand-run not found (set ANIMA_HAND_RUN or put it on PATH)"
    jid = cmd["target"]["task"]
    if not jobs_dir or not (Path(jobs_dir) / jid / "job.json").is_file():
        return False, f"no job folder {jid!r} under {jobs_dir}"
    env = dict(os.environ, HAND_JOBS_DIR=str(jobs_dir))
    r = subprocess.run([hr, "cancel", jid], env=env, capture_output=True, text=True, timeout=30)
    if r.returncode == 0:
        return True, f"`hand-run cancel {jid}` exit 0 (it sets cancel_requested; its supervisor stops the job)"
    return False, (r.stderr.strip() or r.stdout.strip() or f"exit {r.returncode}")[:300]
