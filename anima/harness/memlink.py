"""The link between `anima run` and the TRACE memory (anima.memory).

Rules this file enforces:
  - one state root: the memory folder defaults to $ANIMA_HOME/memory (anima.yaml `memory.store` or
    `--memory-store` override it), never to a folder relative to the current directory;
  - memory runs in a CHILD process (`python -m anima.memory ...`, which re-launches itself inside the
    memory venv built by `anima memory setup`), so `anima run` works from any Python;
  - one writer at a time: ingest takes an exclusive lock on <store>.lock;
  - memory can never abort a coding job: every failure is caught, written to the decision record
    (kind decision.made, decision memory-recall / memory-record) and shown, and the run goes on.
"""
from __future__ import annotations

import contextlib
import os
import subprocess
import sys
from pathlib import Path

from .chain import Chain


def memory_cmd(*args) -> list:
    return [sys.executable, "-m", "anima.memory", *args]


def memory_env() -> dict:
    root = str(Path(__file__).resolve().parents[2])  # the folder that contains the `anima` package
    env = dict(os.environ)
    env["PYTHONPATH"] = os.pathsep.join(filter(None, [root, env.get("PYTHONPATH", "")]))
    return env


@contextlib.contextmanager
def store_lock(store, wait_s: float = 120.0):
    """Exclusive writer lock on <store>.lock (advisory; every ANIMA writer goes through here)."""
    import time
    try:
        import fcntl
    except ImportError:  # not POSIX: no lock available; say nothing, memory is optional
        yield False
        return
    lockfile = Path(str(store).rstrip("/") + ".lock")
    lockfile.parent.mkdir(parents=True, exist_ok=True)
    fh = open(lockfile, "a")
    got = False
    t0 = time.monotonic()
    try:
        while True:
            try:
                fcntl.flock(fh, fcntl.LOCK_EX | fcntl.LOCK_NB)
                got = True
                break
            except OSError:
                if time.monotonic() - t0 > wait_s:
                    break
                time.sleep(0.2)
        yield got
    finally:
        if got:
            with contextlib.suppress(OSError):
                fcntl.flock(fh, fcntl.LOCK_UN)
        fh.close()


def resolve(a, prof) -> dict | None:
    """Merge anima.yaml `memory:` with the --memory* flags (flags win). None = memory off."""
    cfg = prof.memory_cfg()
    backend = a.memory if a.memory is not None else cfg["backend"]
    if backend != "trace":
        return None
    return {"store": a.memory_store or cfg["store"], "k": a.memory_k or cfg["k"],
            "exclude_self": a.memory_exclude_self, "record": (not a.memory_no_record) and cfg["record"]}


def record_run(run_dir, task, mem: dict, say) -> dict:
    """After a run: add its attempts to the memory. Never raises; the outcome goes in the decision record."""
    rep: dict
    try:
        with store_lock(mem["store"]) as got:
            if not got:
                rep = {"recorded": False, "error": "another ANIMA process is writing the memory; not recorded"}
            else:
                r = subprocess.run(memory_cmd("ingest", str(run_dir), "--task", str(task.dir), "--store", mem["store"]),
                                   capture_output=True, text=True, timeout=300, env=memory_env())
                lines = (r.stdout if r.returncode == 0 else (r.stderr or r.stdout)).strip().splitlines()
                tail = (lines[-1] if lines else "")[:160]
                rep = {"recorded": r.returncode == 0, "detail": tail}
                if r.returncode != 0:
                    rep["error"] = tail or f"exit {r.returncode}"
    except (OSError, subprocess.SubprocessError) as exc:
        rep = {"recorded": False, "error": f"{type(exc).__name__}: {exc}"[:200]}
    try:  # append to the (already finished) chain and refresh its saved fingerprint
        ch = Chain(Path(run_dir) / "decisions.jsonl", actor="anima-memory")
        ch.append("decision.made", task.id, actor="anima-memory", decision="memory-record", **rep)
        ch.write_head()
    except OSError as exc:
        rep.setdefault("error", f"could not write the record: {exc}")
    say("memory: recorded this run -> " + str(rep.get("detail", "")) if rep.get("recorded")
        else "memory: NOT recorded (the coding result is unaffected): " + str(rep.get("error")))
    return rep
