# Copyright 2026 Anshul48
# SPDX-License-Identifier: Apache-2.0
"""`anima voice`: speech -> text (local faster-whisper) -> one of a FIXED set of
commands -> shown to you -> run only after you confirm.

The command set is deliberately tiny (nothing else is ever run, whatever is said):

    show status                      -> anima status --tree                          (works)
    recall similar fixes             -> anima memory recall "<newest open task>"     (works; reads the TRACE memory)
    pause task <n> / resume task <n> -> anima cmd pause|resume <task>   RECOGNISED, DISABLED: nothing reads command files yet
    run the next job with <harness>  -> anima cmd run-next --harness ... RECOGNISED, DISABLED: same reason

<n> is the number printed by `anima status --tree`.  Input is an audio file
(any format ffmpeg reads; short clips) or, if the machine has one, the
microphone (--mic SECONDS; in WSL it only works through WSLg's RDPSource).
Stdlib only here; the speech-to-text runs in a child process using the Python
that has faster-whisper (ANIMA_STT_PYTHON, else ~/stt_venv/bin/python).
"""
from __future__ import annotations

import difflib
import importlib.util
import json
import os
import re
import shlex
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

HERE = Path(__file__).resolve().parent
NUMBER_WORDS = {w: i for i, w in enumerate(
    "zero one two three four five six seven eight nine ten eleven twelve thirteen fourteen fifteen "
    "sixteen seventeen eighteen nineteen twenty".split())}
# speech-to-text often writes these homophones; only trusted right after "task/job/number"
HOMOPHONES = {"to": 2, "too": 2, "for": 4, "won": 1, "ate": 8, "tree": 3}
HARNESS_ALIASES = {
    "muse": ("muse", "mews", "moose", "mus", "musa"),
    "claude": ("claude", "cloud", "clod", "clawed", "claud", "clode"),
    "codex": ("codex", "codecs", "codec", "kodex", "codeks"),
}
SET_HELP = ("show status | pause task N | resume task N | "
            "run the next job with muse / claude / codex | recall similar fixes")


COMMAND_FILE_NAMES = ("pause", "resume", "run-next")   # their effect is a command file; nothing reads those yet


class NoMatch(Exception):
    pass


# ------------------------------------------------------------------ grammar
def tokens(text):
    t = text.lower().replace("-", " ")
    t = re.sub(r"[^a-z0-9' ]+", " ", t)
    t = re.sub(r"\bcode x\b", "codex", t)
    return [w for w in t.split() if w]


def close(tok, word, cutoff=0.78):
    for cand in (tok, tok.rstrip("s")):
        if cand == word or difflib.SequenceMatcher(None, cand, word).ratio() >= cutoff:
            return True
    return False


def has(toks, word, cutoff=0.78):
    return any(close(t, word, cutoff) for t in toks)


def find_number(toks):
    """The task number after 'task'/'job'/'number', or the only number said."""
    for i, t in enumerate(toks):
        if t in ("task", "tasks", "job", "number", "no") and i + 1 < len(toks):
            n = toks[i + 1]
            if n.isdigit():
                return int(n)
            if n in NUMBER_WORDS:
                return NUMBER_WORDS[n]
            if n in HOMOPHONES:
                return HOMOPHONES[n]
    for t in toks:
        if t.isdigit():
            return int(t)
        if t in NUMBER_WORDS and t != "zero":
            return NUMBER_WORDS[t]
    return None


def find_harness(toks):
    best, best_r = None, 0.0
    for name, aliases in HARNESS_ALIASES.items():
        for t in toks:
            for al in aliases:
                r = 1.0 if t == al else difflib.SequenceMatcher(None, t, al).ratio()
                if r > best_r:
                    best, best_r = name, r
    return best if best_r >= 0.75 else None


def parse(text):
    """-> dict(name, verb, number, harness, phrase)  or raise NoMatch(reason)."""
    toks = tokens(text)
    if not toks:
        raise NoMatch("heard nothing")
    is_pause, is_resume = has(toks, "pause", 0.8), has(toks, "resume", 0.8)
    is_run = has(toks, "run", 0.99) and has(toks, "next", 0.8)
    is_recall = has(toks, "recall", 0.78) and has(toks, "similar", 0.78)
    is_status = has(toks, "status", 0.8) or (has(toks, "show", 0.99) and (has(toks, "tree") or has(toks, "state")))
    hits = [n for n, f in (("pause", is_pause), ("resume", is_resume), ("run-next", is_run),
                           ("recall", is_recall), ("status", is_status)) if f]
    if len(hits) != 1:
        raise NoMatch("no command recognised" if not hits else f"ambiguous ({' and '.join(hits)})")
    name = hits[0]
    if name in ("pause", "resume"):
        n = find_number(toks)
        if n is None:
            raise NoMatch(f"{name} which task? say a number, e.g. '{name} task 3'")
        return {"name": name, "verb": name, "number": n, "phrase": f"{name} task {n}"}
    if name == "run-next":
        h = find_harness(toks)
        if h is None:
            raise NoMatch("run the next job with which harness? say muse, claude or codex")
        return {"name": name, "verb": "run-next", "harness": h, "phrase": f"run the next job with {h}"}
    if name == "recall":
        return {"name": name, "phrase": "recall similar fixes"}
    return {"name": name, "phrase": "show status"}


# ------------------------------------------------------------------ audio in
class AudioError(RuntimeError):
    pass


def stt_python():
    cands = [os.environ.get("ANIMA_STT_PYTHON"), str(Path.home() / "stt_venv" / "bin" / "python"), sys.executable]
    for c in cands:
        if c and os.access(c, os.X_OK):
            return c
    raise AudioError("no Python with faster-whisper found (set ANIMA_STT_PYTHON)")


def transcribe(path, model="base"):
    py = stt_python()
    r = subprocess.run([py, str(HERE / "transcribe_worker.py"), str(path), "--model", model],
                       capture_output=True, text=True, timeout=300)
    lines = [ln for ln in r.stdout.splitlines() if ln.startswith("{")]
    if r.returncode != 0 or not lines:
        tail = (r.stderr.strip().splitlines() or ["no output"])[-1]
        raise AudioError(f"speech-to-text failed ({py}): {tail}")
    return json.loads(lines[-1])


def record_mic(seconds, out):
    """Record from the default PulseAudio source with ffmpeg.  Refuses silence."""
    if not shutil.which("ffmpeg"):
        raise AudioError("ffmpeg not found; use an audio file instead")
    r = subprocess.run(["ffmpeg", "-hide_banner", "-loglevel", "error", "-f", "pulse", "-i", "default",
                        "-t", str(seconds), "-ac", "1", "-ar", "16000", "-y", str(out)],
                       capture_output=True, text=True, timeout=seconds + 20)
    if r.returncode != 0 or not Path(out).exists():
        raise AudioError("no microphone available here (" + (r.stderr.strip().splitlines() or ["ffmpeg failed"])[-1]
                         + "). In WSL the microphone only exists through WSLg; use an audio file.")
    v = subprocess.run(["ffmpeg", "-hide_banner", "-i", str(out), "-af", "volumedetect", "-f", "null", "-"],
                       capture_output=True, text=True, timeout=30).stderr
    m = re.search(r"max_volume: (-?[\d.]+) dB", v)
    if m and float(m.group(1)) < -55:
        raise AudioError(f"the microphone recorded silence (peak {m.group(1)} dB). Check the Windows "
                         "microphone permission for WSL, or use an audio file.")


# ------------------------------------------------------------------ run
def build_argv(m, tasks_by_number, flags, heard, recall_query=None):
    """The argv (after `anima`) that carries out the matched command, plus a note."""
    why = f"voice: {m['phrase']}"
    if m["name"] == "status":
        return ["status", "--tree"] + flags, "prints the tree; changes nothing"
    if m["name"] in ("pause", "resume"):
        t = tasks_by_number.get(m["number"])
        if t is None:
            raise NoMatch(f"there is no task {m['number']} (the tree has {len(tasks_by_number)} tasks)")
        return (["cmd", m["verb"], t, "--issued-by", "voice", "--reason", why] + flags,
                "would write one command file; nothing reads command files yet (disabled)")
    if m["name"] == "run-next":
        return (["cmd", "run-next", "--harness", m["harness"], "--issued-by", "voice", "--reason", why] + flags,
                "would write one command file; nothing reads command files yet (disabled)")
    return (["memory", "recall", recall_query], "asks the memory link for past fixes like this task; read-only")


def recall_query_from(tasks_info):
    """The text to recall against: the newest task that is not verified yet (running, rejected, blocked),
    else the newest task.  `tasks_info` is a list of (number, label, status) in tree order.  The query is
    shown in the command line before anything runs, so the choice is never hidden."""
    if not tasks_info:
        raise NoMatch("the tree has no tasks, so there is nothing to recall similar fixes for")
    open_ones = [t for t in tasks_info if t[2] != "verified"]
    num, label, _ = (open_ones or tasks_info)[-1]
    return label.replace("-", " ")


def run_recall(query):
    """Call `anima memory recall` through the main dispatcher, so the memory in the one state root ($ANIMA_HOME/memory) is used."""
    try:
        cli = importlib.import_module("anima.harness.cli")
    except ImportError:
        print("not wired: the anima command line is not importable here, so there is nothing to recall from. Nothing was run.")
        return 4
    return int(cli.main(["memory", "recall", query]) or 0)


def task_numbers(a):
    return {n: label for n, label, _ in task_list(a)}


def task_list(a):
    """[(number, label, status)] for every task in the tree, in tree order."""
    from anima.ui import cli as uicli
    snap = uicli.source_from(a).snapshot()
    return [(t["num"], t["label"], t.get("status")) for ws in snap["tree"]["children"] for t in ws["children"]]


def run(a, flags, cli_main):
    """Entry from `anima voice`.  Returns a process exit code."""
    heard, info = None, {}
    if a.text:
        heard, info = a.text, {"stt": "skipped (--text)"}
    else:
        tmp = None
        try:
            if a.audio:
                if not Path(a.audio).is_file():
                    print(f"anima voice: no such file: {a.audio}", file=sys.stderr)
                    return 2
                path = a.audio
            elif a.mic:
                tmp = tempfile.mkdtemp(prefix="anima-voice-")
                path = str(Path(tmp) / "mic.wav")
                print(f"recording {a.mic:g} s from the microphone ... speak now", flush=True)
                record_mic(a.mic, path)
            else:
                print("anima voice: give an audio file, or --mic SECONDS. (File input always works; "
                      "the microphone only if this machine has one.)", file=sys.stderr)
                return 2
            info = transcribe(path, a.model)
            heard = info["text"]
        except (AudioError, subprocess.TimeoutExpired) as e:
            print(f"anima voice: {e}", file=sys.stderr)
            return 4
        finally:
            if tmp:
                shutil.rmtree(tmp, ignore_errors=True)
    stt = (f"whisper {info['model']} on CPU, {info['audio_s']} s of audio, {info['transcribe_s']} s to transcribe"
           if "model" in info else info.get("stt", ""))
    print(f'heard:    "{heard}"   [{stt}]')
    try:
        m = parse(heard)
        tasks = task_numbers(a) if m["name"] in ("pause", "resume") else {}
        query = recall_query_from(task_list(a)) if m["name"] == "recall" else None
        argv, effect = build_argv(m, tasks, flags, heard, query)
    except NoMatch as e:
        print(f"no match: {e}")
        print(f"I only understand: {SET_HELP}")
        print("nothing was run.")
        return 2
    shown = "anima " + " ".join(shlex.quote(x) for x in argv)
    label = m["phrase"] + (f"  ->  {tasks[m['number']]}" if m["name"] in ("pause", "resume") else "")
    print(f"matched:  {label}")
    print(f"will run: {shown}")
    print(f"effect:   {effect}")
    if m["name"] in COMMAND_FILE_NAMES:
        print("DISABLED: nothing reads command files yet, so this could not change any run. Recognised, not run.")
        print("(works today: 'show status' and 'recall similar fixes')")
        return 5
    if a.dry_run:
        print("dry run: not running it.")
        return 0
    if a.yes:
        print("confirm:  yes (--yes)")
    else:
        try:
            ans = input("Run it? [y/N] ").strip().lower()
        except EOFError:
            ans = ""
        if ans not in ("y", "yes"):
            print("not confirmed: nothing was run.")
            return 3
    print("-" * 40, flush=True)
    if m["name"] == "recall":
        return run_recall(query)
    return cli_main(argv)
