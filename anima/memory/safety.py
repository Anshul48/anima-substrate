# Copyright 2026 Anshul48
# SPDX-License-Identifier: Apache-2.0
"""Small guards the memory uses on anything that came from a record file (stdlib only).

  safe_id      a record or job id that is going to become part of a file name
  safe_label   a task/library name that is going to be shown to a worker (no control characters, bounded)
  safe_dest    a destination file inside a folder we own, with no `..` and no symlink in the way
  inside       "this file really lives under that folder" (symlinks resolved)
  locked       one writer at a time per memory folder (shared lock for readers)
  record_failure   append one line to <store>/failures.jsonl; never raises
"""
from __future__ import annotations

import contextlib
import json
import os
import re
import time
from pathlib import Path

try:  # POSIX only; on other systems the lock is a no-op and docs/MEMORY.md says so
    import fcntl
except ImportError:  # pragma: no cover
    fcntl = None

_ID = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]{0,127}$")
_LABEL_BAD = re.compile(r"[^A-Za-z0-9._:/@+-]")


def safe_id(value, what="id") -> str:
    """Return value if it is safe to use as one path component; raise ValueError otherwise."""
    s = str(value)
    if not _ID.match(s) or ".." in s:
        raise ValueError(f"unsafe {what} {s[:60]!r}: use letters, digits, '.', '_' and '-' only (max 128 characters, no '..')")
    return s


def safe_label(value, default="unknown", n=100) -> str:
    """Make a task/library name harmless to show in a prompt: no spaces, newlines or control characters; at most n characters."""
    s = _LABEL_BAD.sub("_", str(value or ""))[:n].strip("_")
    return s or default


def inside(path, base) -> bool:
    try:
        Path(path).resolve().relative_to(Path(base).resolve())
        return True
    except ValueError:
        return False


def reject_escape(path, base, what="file"):
    """Raise ValueError if `path` is a symlink (or sits under one) that leads outside `base`."""
    if not inside(path, base):
        raise ValueError(f"{what} {path} resolves outside {base} (symlink escape); refusing to read it")


def safe_dest(folder, name) -> Path:
    """folder/name for writing. `name` must be a safe id plus an optional extension; `folder` must not be a symlink
    that leads elsewhere; the destination must not already be a symlink."""
    folder = Path(folder)
    if folder.is_symlink():
        raise ValueError(f"{folder} is a symlink; refusing to write through it")
    folder.mkdir(parents=True, exist_ok=True)
    stem, dot, ext = str(name).rpartition(".")
    safe_id(stem if dot else name, "file name")
    dest = folder / name
    if dest.is_symlink() or not inside(dest, folder):
        raise ValueError(f"{dest} would leave {folder}; refusing to write it")
    return dest


@contextlib.contextmanager
def locked(store_dir, exclusive=True, timeout=120.0):
    """Hold the memory folder's lock. One writer at a time; readers share. Times out with TimeoutError."""
    if fcntl is None:  # pragma: no cover
        yield
        return
    d = Path(store_dir)
    d.mkdir(parents=True, exist_ok=True)
    fd = os.open(str(d / ".lock"), os.O_RDWR | os.O_CREAT, 0o600)
    mode = (fcntl.LOCK_EX if exclusive else fcntl.LOCK_SH) | fcntl.LOCK_NB
    t0 = time.monotonic()
    try:
        while True:
            try:
                fcntl.flock(fd, mode)
                break
            except OSError:
                if time.monotonic() - t0 > timeout:
                    raise TimeoutError(f"memory at {d} is locked by another {'writer' if exclusive else 'process'} (waited {timeout:.0f} s)")
                time.sleep(0.1)
        yield
    finally:
        with contextlib.suppress(OSError):
            fcntl.flock(fd, fcntl.LOCK_UN)
        os.close(fd)


def record_failure(store_dir, op, error, extra=None):
    """Append {"ts","op","error",...} to <store>/failures.jsonl. Returns the path written or None. Never raises."""
    row = {"ts": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()), "op": op, "error": str(error)[:400], **(extra or {})}
    line = json.dumps(row, sort_keys=True) + "\n"
    for d in (Path(store_dir) if store_dir else None, _fallback_dir()):
        if d is None:
            continue
        try:
            d.mkdir(parents=True, exist_ok=True)
            with open(d / "failures.jsonl", "a") as f:
                f.write(line)
            return str(d / "failures.jsonl")
        except OSError:
            continue
    return None


def _fallback_dir():
    try:
        from .encoder import anima_home
        return anima_home() / "memory"
    except Exception:  # noqa: BLE001
        return None
