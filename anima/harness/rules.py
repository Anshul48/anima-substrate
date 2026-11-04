"""Small rule pack: commands an agent must not run, plus the process watch.

`check_command(text, packs)` answers allow / block for one command line.
`ProcessWatch` polls the agent's process group from outside while it runs and
applies the same rules to every command line it sees (and an optional
no-output stall rule). In mode `enforce` it kills the group; in `warn` or
`shadow` it only writes what it would have done to watch.jsonl.

Honest limits (also in docs/HARNESSES.md):
  - the watch polls every 0.1 s; a command that starts and ends faster than
    that can be missed. Claude Code additionally gets a per-action hook
    (`anima check --hook`), which cannot miss.
  - rules match command text; they are a safety net, not a sandbox.
"""
from __future__ import annotations

import json
import os
import re
import signal
import threading
import time
from dataclasses import dataclass
from pathlib import Path

# pack -> list of (rule id, regex, explanation)
PACKS: dict[str, list[tuple[str, str, str]]] = {
    "secrets": [
        ("SECRETS-READ",
         r"(\.ssh(/|\\|$|\s)|\.aws/|\.azure/|\.netrc|\.pgpass|\.git-credentials|\.docker/config\.json|\.npmrc"
         r"|(^|[\s/])\.env(\.[\w-]+)?(\s|$)|\.pem\b|id_(rsa|ed25519|ecdsa)|/etc/shadow"
         r"|\.claude/\.credentials|\.codex/auth\.json|\.config/muse/auth\.json|MUSE_AUTH_PATH)",
         "never read, print or copy key files or the login stores of coding agents; use key NAMES only"),
        ("SECRETS-ENV-DUMP",
         r"(?m)(?:^|[;&|(])\s*(env|printenv)\s*(?:$|[;&|)])|\bexport\s+-p\b|\bdeclare\s+-x\b|/proc/[\w$]+/environ",
         "never dump the environment; it can hold keys"),
    ],
    "sudo": [
        ("SUDO-NEVER", r"(?:^|[;&|(\s])(sudo|su|doas)(?:\s|$)", "no sudo / privilege escalation"),
    ],
    "push-public": [
        ("GIT-PUSH", r"\bgit\b[^\n;&|]*\bpush\b", "no git push from an agent run; a person publishes"),
        ("GH-PUBLISH", r"\bgh\s+(repo\s+(create|delete)|release\s+create|pr\s+(create|merge))", "no publishing from an agent run"),
        ("NPM-PUBLISH", r"\b(npm|yarn|pnpm)\s+publish\b|\btwine\s+upload\b", "no package publishing from an agent run"),
    ],
    "delete-protected": [
        ("RM-ROOT-HOME", r"\brm\s+(-[a-zA-Z]*[rf][a-zA-Z]*\s+)+(/|~|\$HOME|\.\.|/home|/mnt|\*)(\s|/?$)", "no recursive delete of root, home or parent folders"),
        ("GIT-WIPE", r"\bgit\s+(clean\s+-[a-z]*f|reset\s+--hard\s+origin)", "no destructive git cleanup"),
        ("DISK-WRITE", r"\b(mkfs\w*|dd\s+if=.*of=/dev/|shred)\b", "no disk-level writes"),
    ],
}
DEFAULT_PACKS = ["secrets", "sudo", "push-public", "delete-protected"]
# role `must_not` words that map to a pack
MUST_NOT_PACK = {"secrets": "secrets", "push": "push-public", "sudo": "sudo", "delete": "delete-protected"}
NOT_ENFORCED = ("spend", "bulk_edit", "message_owner", "edit_mission")


@dataclass
class Verdict:
    allowed: bool
    rule: str | None = None
    explain: str | None = None


def check_command(text: str, packs=None) -> Verdict:
    for pack in (packs or DEFAULT_PACKS):
        for rule_id, rx, explain in PACKS.get(pack, []):
            if re.search(rx, text):
                return Verdict(False, rule_id, explain)
    return Verdict(True)


def packs_for(profile_rules, must_not=()) -> list[str]:
    packs = [p for p in (profile_rules or []) if p in PACKS]
    for m in must_not or ():
        p = MUST_NOT_PACK.get(m)
        if p and p not in packs:
            packs.append(p)
    return packs


def hook_decision(stdin_text: str, packs=None) -> tuple[int, str]:
    """Claude Code PreToolUse hook: read the hook JSON, return (exit code, message).
    Exit code 2 blocks the action and shows the message to the model."""
    try:
        data = json.loads(stdin_text)
    except ValueError:
        return 0, ""
    tool = data.get("tool_name", "")
    inp = data.get("tool_input") or {}
    if tool == "Bash":
        text = inp.get("command", "")
    elif tool in ("Read", "Edit", "Write", "NotebookEdit"):
        text = "cat " + str(inp.get("file_path") or inp.get("path") or "")
    elif tool in ("Grep", "Glob"):
        text = "cat " + str(inp.get("path") or "") + " " + str(inp.get("pattern") or "")
    else:
        return 0, ""
    v = check_command(text, packs)
    if v.allowed:
        return 0, ""
    return 2, f"ANIMA blocked this action ({v.rule}): {v.explain}"


# ------------------------------------------------------------------ watch
def _pgrp_children(sid: int, skip: int):
    """(pid, cmdline) of live processes in session `sid`, excluding `skip`."""
    out = []
    for name in os.listdir("/proc"):
        if not name.isdigit():
            continue
        pid = int(name)
        if pid == skip:
            continue
        try:
            stat = Path(f"/proc/{pid}/stat").read_text()
            rest = stat[stat.rindex(")") + 2:].split()
            if int(rest[3]) != sid:  # field 6 (session id)
                continue
            raw = Path(f"/proc/{pid}/cmdline").read_bytes()
        except (OSError, ValueError, IndexError):
            continue
        out.append((pid, raw.replace(b"\0", b" ").decode("utf-8", "replace").strip()))
    return out


class ProcessWatch(threading.Thread):
    def __init__(self, root_pid: int, log_path, packs, mode="warn", stall_s=None, stall_mode="shadow",
                 progress_paths=(), interval=0.1):
        super().__init__(daemon=True)
        self.root_pid, self.log_path = root_pid, Path(log_path)
        self.packs, self.mode = packs, mode
        self.stall_s, self.stall_mode = stall_s, stall_mode
        self.progress_paths, self.interval = [Path(p) for p in progress_paths], interval
        self.stop_flag = threading.Event()
        self.seen: set[int] = set()
        self.violations: list[dict] = []
        self.killed = False
        self.stalled = False
        self._last_size, self._last_change = -1, time.monotonic()
        self._stall_logged = False

    def _log(self, row):
        row = {"ts": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()), **row}
        with self.log_path.open("a") as f:
            f.write(json.dumps(row, sort_keys=True) + "\n")

    def _kill(self):
        self.killed = True
        try:
            os.killpg(self.root_pid, signal.SIGKILL)
        except ProcessLookupError:
            pass

    def run(self):
        while not self.stop_flag.is_set():
            for pid, cmd in _pgrp_children(self.root_pid, self.root_pid):
                if pid in self.seen or not cmd:
                    continue
                self.seen.add(pid)
                v = check_command(cmd, self.packs)
                if v.allowed:
                    continue
                action = "killed" if self.mode == "enforce" else "would_kill"
                row = {"kind": "violation", "rule": v.rule, "pid": pid, "cmd": cmd[:200], "mode": self.mode, "action": action}
                self.violations.append(row)
                self._log(row)
                if self.mode == "enforce":
                    self._kill()
                    return
            if self.stall_s:
                size = sum(p.stat().st_size for p in self.progress_paths if p.exists())
                now = time.monotonic()
                if size != self._last_size:
                    self._last_size, self._last_change = size, now
                elif now - self._last_change >= self.stall_s and not self._stall_logged:
                    self._stall_logged = True
                    self.stalled = True
                    action = "killed" if self.stall_mode == "enforce" else "would_kill"
                    self._log({"kind": "stall", "after_s": round(now - self._last_change, 1), "mode": self.stall_mode, "action": action})
                    if self.stall_mode == "enforce":
                        self._kill()
                        return
            self.stop_flag.wait(self.interval)

    def finish(self):
        self.stop_flag.set()
        self.join(timeout=2)
