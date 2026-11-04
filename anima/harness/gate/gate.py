#!/usr/bin/env python3
"""Deterministic gate; trusted spec arrives on stdin AFTER the hand exits.

This generic file is the only gate code exposed to the hand. The parent pins
its exact bytes and gate.pins against a trusted manifest outside the workspace.
No task metadata, gold patch, node selectors or fix commit is embedded here.
"""
import hashlib
import json
import os
from pathlib import Path
import re
import signal
import stat
import subprocess
import sys
import time


def file_digest(path):
    if path.is_symlink() or not path.is_file():
        return None
    return hashlib.sha256(path.read_bytes()).hexdigest()


def protected_snapshot(workspace, named, roots=()):
    # Named paths may legitimately be absent at BASE. Distinguish absence from
    # symlinks, directories and files, including symlinks in a path's parents.
    paths = set(named) | set(roots)
    roots = {Path(p) for p in roots}
    ignored = set()
    for base, dirs, files in os.walk(workspace, followlinks=False):
        rel = Path(base).relative_to(workspace)
        if rel == Path("."):
            dirs[:] = [d for d in dirs if d not in {".git", ".flagship"}]
        # Only plain directories are disposable interpreter caches. lstat
        # keeps symlinks (including dangling links) and special nodes protected.
        for name in dirs[:]:
            p = rel / name
            if name == "__pycache__" and any(p == root or root in p.parents for root in roots) and stat.S_ISDIR((workspace / p).lstat().st_mode):
                dirs.remove(name)
                ignored.add(p)
        for name in dirs + files:
            p = rel / name
            if any(p == root or root in p.parents for root in roots):
                paths.add(p.as_posix())
    def state(p):
        for ancestor in reversed([p, *p.parents]):
            if ancestor == Path("."):
                continue
            target = workspace / ancestor
            if target.is_symlink():
                return "symlink:" + ancestor.as_posix() + ":" + os.readlink(target)
        target = workspace / p
        if target.is_dir():
            return "directory"
        if target.exists() and not target.is_file():
            return "special"
        return file_digest(target)
    return {p: state(Path(p)) for p in sorted(paths) if not any(Path(p).is_relative_to(d) for d in ignored)}


def first_failure(output):
    lines = [line.strip() for line in output.splitlines() if line.strip()]
    for line in lines:
        if re.search(r"^E\s+(?:assert\b|AssertionError\b)|^AssertionError\b|:\s*AssertionError\b", line):
            return line[:500]
    for pattern in (r"^E\s+", r"^FAILED", r"^ERROR", r"^FAIL:"):
        for line in lines:
            if re.search(pattern, line):
                return line[:500]
    return (lines[0] if lines else "target command failed without output")[:500]


def tests_untouched(workspace, baseline, roots=()):
    return protected_snapshot(workspace, baseline, roots) == baseline


def evaluate(spec):
    start = time.monotonic()
    workspace = Path(spec["workspace"])
    baseline = spec["protected"]
    result = {"mode": spec["mode"], "pool": spec["pool"], "hand": spec["hand"],
              "verdict": "FAIL", "failed_rule": None, "digest": "", "output": "", "returncode": 1}
    if not tests_untouched(workspace, baseline, spec.get("protected_roots", ())):
        result.update(failed_rule="tests-untouched", digest="protected test bytes or paths changed")
    else:
        env = {"PATH": "/usr/local/bin:/usr/bin:/bin", "LANG": "C.UTF-8",
               "HOME": spec["private_home"], "PYTHONDONTWRITEBYTECODE": "1",
               "PYTHONPATH": spec["eval_workspace"] + "/src:" + spec["eval_workspace"],
               "GIT_CONFIG_NOSYSTEM": "1", "GIT_CONFIG_GLOBAL": "/dev/null",
               "GIT_ALLOW_PROTOCOL": "", "GIT_TERMINAL_PROMPT": "0"}
        capture = Path(spec["capture"])
        with capture.open("wb") as out:
            proc = subprocess.Popen(spec["gate_argv"], cwd=spec["eval_workspace"],
                                    env=env, stdin=subprocess.DEVNULL, stdout=out,
                                    stderr=subprocess.STDOUT, start_new_session=True)
            try:
                rc = proc.wait(timeout=spec["timeout_s"])
            except subprocess.TimeoutExpired:
                rc = 124
            finally:
                try:
                    os.killpg(proc.pid, signal.SIGKILL)
                except ProcessLookupError:
                    pass
                proc.wait()
        # Keep the tail too: pytest prints the useful assertion near the end.
        with capture.open("rb") as f:
            raw = f.read(256 * 1024)
            if capture.stat().st_size > len(raw):
                f.seek(max(0, capture.stat().st_size - 256 * 1024))
                raw += b"\n[output truncated]\n" + f.read()
        output = raw.decode("utf-8", "replace")
        result.update(output=output, returncode=rc)
        if not tests_untouched(workspace, baseline, spec.get("protected_roots", ())):
            result.update(failed_rule="tests-untouched", digest="protected tests changed during evaluation")
        elif rc == 124:
            result.update(failed_rule="timeout", digest="target tests exceeded %.3gs" % spec["timeout_s"])
        elif rc != 0:
            result.update(failed_rule="target-tests", digest=first_failure(output))
        else:
            result.update(verdict="PASS", returncode=0)
    result["wall_seconds"] = round(time.monotonic() - start, 6)
    return result


if __name__ == "__main__":
    try:
        print(json.dumps(evaluate(json.load(sys.stdin)), sort_keys=True))
    except Exception as exc:
        print(json.dumps({"verdict": "FAIL", "failed_rule": "gate-error", "digest": type(exc).__name__}))
        raise SystemExit(1)
