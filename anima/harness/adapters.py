"""Harness adapters: drive a coding agent CLI you already have, headlessly.

One adapter per CLI (Muse Code, Claude Code, Codex) plus a `custom` adapter
for anything else. Each adapter turns (role, workspace, prompt file) into one
argv list, and turns the CLI's own JSON / JSONL output into a small Result.

Roles
  worker     may edit the workspace (this is the rung that fixes things)
  architect  read-only planning (writes a plan, must not change files)

How the command is launched (same rules as the dispatcher's CLI adapter that
ran the recorded nine-job ladder, see docs/HARNESSES.md):
  - argv list, never a shell; new session so a timeout kills the whole group
  - the task text goes in a file / stdin, never on the command line
  - the child sees only PATH, HOME, LANG and a short allow-list; any name that
    ends in _API_KEY or _TOKEN, or contains SECRET, is dropped
  - ANIMA never reads or writes a credential file. Login is the CLI's own.
"""
from __future__ import annotations

import json
import os
import re
import shutil
import signal
import subprocess
import time
from dataclasses import dataclass, field
from pathlib import Path

from .rules import ProcessWatch

KINDS = ("muse", "claude", "codex", "custom")
ROLES = ("worker", "architect")
# Order matters: Muse Code first (see docs/HARNESSES.md), then Claude Code, then Codex.
DETECT_ORDER = ("muse", "claude", "codex")
PLACEHOLDERS = {"prompt_file", "workspace", "job_id", "model", "out_file", "role"}

# Carried over from ~/owner-hub/bin/hand-run (the supervisor used for the recorded ladder).
AUTH_RE = re.compile(
    r"unauthori[sz]ed|refresh token|sign in again|log out and|\b401\b|\b402\b|\b403\b|quota|rate.?limit|usage limit|allowance|\b429\b|expired"
    r"|insufficient (credit|funds|balance)|credit balance|out of credit|not logged in|please log ?in|login required",
    re.I,
)
NET_RE = re.compile(
    r"ETIMEDOUT|ECONNRESET|ECONNREFUSED|ENOTFOUND|EAI_AGAIN|socket hang up|network (is )?unreachable"
    r"|Could not resolve|connection (reset|refused|closed)|\b50[234]\b|temporar(il)?y unavailable|overloaded",
    re.I,
)

SAFE_ENV = ("PATH", "HOME", "LANG", "LC_ALL", "TERM", "TMPDIR", "XDG_CONFIG_HOME", "XDG_DATA_HOME", "XDG_CACHE_HOME", "XDG_STATE_HOME")
KIND_ENV = {
    "claude": ("CLAUDE_CONFIG_DIR",),
    "codex": ("CODEX_HOME",),
    "muse": ("MUSE_AUTH_PATH", "MUSE_CHANNEL"),
    "custom": (),
}
CLAUDE_WORKER_TOOLS = ["Read", "Edit", "Write", "Glob", "Grep", "Bash(python3 *)", "Bash(python *)", "Bash(pytest *)", "Bash(git status*)", "Bash(git diff*)"]
CLAUDE_ARCHITECT_TOOLS = ["Read", "Glob", "Grep"]


class HarnessError(RuntimeError):
    pass


def sensitive_name(name: str) -> bool:
    u = name.upper()
    return u.endswith("_API_KEY") or u.endswith("_TOKEN") or "SECRET" in u


def scrubbed_env(kind: str, allow=()) -> dict:
    keep = list(SAFE_ENV) + list(KIND_ENV.get(kind, ())) + list(allow or ())
    bad = [n for n in (allow or ()) if sensitive_name(n)]
    if bad:
        raise HarnessError(f"env_allow may not forward secrets: {', '.join(bad)} (log in with the CLI itself)")
    return {k: os.environ[k] for k in keep if k in os.environ and not sensitive_name(k)}


@dataclass
class Result:
    ok: bool
    summary: str = ""
    returncode: int | None = None
    timed_out: bool = False
    wall_seconds: float = 0.0
    failure_class: str | None = None  # auth_quota | network | timeout | error | not_found
    error: str | None = None
    cost_usd: float | None = None
    turns: int | None = None
    session_id: str | None = None
    model_seen: str | None = None
    events_path: str | None = None
    stdout_path: str | None = None
    stderr_path: str | None = None
    argv: list = field(default_factory=list)
    usage: dict | None = None
    watch: dict | None = None  # {violations: n, killed: bool, stalled: bool}


@dataclass
class Invocation:
    argv: list
    stdin_file: str | None
    cwd: str
    env: dict


class Adapter:
    kind = ""
    version_args = ["--version"]
    needs = ()  # (help-args, [flags that must appear in that help])
    streams = True

    def __init__(self, name: str, cfg: dict):
        self.name = name
        self.cfg = dict(cfg or {})
        self.bin = self.cfg.get("bin") or ""
        self.model = self.cfg.get("model") or None
        self.effort = self.cfg.get("effort") or None
        self.extra = [str(x) for x in (self.cfg.get("extra_args") or [])]
        self.env_allow = [str(x) for x in (self.cfg.get("env_allow") or [])]
        self.timeout_s = int(self.cfg.get("timeout_s") or 1800)

    # -- discovery -------------------------------------------------------
    def resolve_bin(self) -> str | None:
        cand = self.bin or self.kind
        p = shutil.which(cand) if os.sep not in cand else (cand if os.access(cand, os.X_OK) else None)
        return p

    def version(self) -> str | None:
        b = self.resolve_bin()
        if not b:
            return None
        try:
            r = subprocess.run([b, *self.version_args], capture_output=True, text=True, timeout=45,
                               stdin=subprocess.DEVNULL, env=scrubbed_env(self.kind, self.env_allow))
        except (OSError, subprocess.TimeoutExpired):
            return None
        out = (r.stdout or r.stderr or "").strip().splitlines()
        return out[0][:120] if out else None

    def login_state(self) -> str:
        """'logged-in', 'not-logged-in' or 'unknown'. Asks the CLI; never reads credential files."""
        return "unknown"

    def check_flags(self) -> list[str]:
        """Return the required flags that the installed CLI's help no longer shows."""
        b = self.resolve_bin()
        if not b or not self.needs:
            return []
        help_args, flags = self.needs
        try:
            r = subprocess.run([b, *help_args], capture_output=True, text=True, timeout=60,
                               stdin=subprocess.DEVNULL, env=scrubbed_env(self.kind, self.env_allow))
        except (OSError, subprocess.TimeoutExpired):
            return list(flags)
        text = (r.stdout or "") + (r.stderr or "")
        return [f for f in flags if f not in text]

    # -- launching -------------------------------------------------------
    def build(self, role: str, workspace: str, prompt_file: str, out_file: str, job_id: str = "job") -> Invocation:
        raise NotImplementedError

    def parse(self, role: str, stdout_path: str, out_file: str, rc: int | None) -> Result:
        text = Path(stdout_path).read_text("utf-8", "replace") if Path(stdout_path).exists() else ""
        return Result(ok=rc == 0 and bool(text.strip()), summary=text.strip()[-2000:], returncode=rc)

    def run(self, role: str, workspace: str, prompt_file: str, run_dir: str, job_id: str = "job",
            timeout_s: int | None = None, watch: dict | None = None) -> Result:
        if role not in ROLES:
            raise HarnessError(f"unknown role {role!r}")
        d = Path(run_dir)
        d.mkdir(parents=True, exist_ok=True)
        out_file = str(d / "out.txt")
        inv = self.build(role, workspace, prompt_file, out_file, job_id)
        res = execute(inv, d, timeout_s or self.timeout_s, watch)
        parsed = self.parse(role, str(d / "stdout.log"), out_file, res["returncode"])
        parsed.watch = res.get("watch")
        parsed.argv = inv.argv
        parsed.returncode = res["returncode"]
        parsed.timed_out = res["timed_out"]
        parsed.wall_seconds = res["wall_seconds"]
        parsed.stdout_path = str(d / "stdout.log")
        parsed.stderr_path = str(d / "stderr.log")
        if res["not_found"]:
            parsed.ok, parsed.failure_class, parsed.error = False, "not_found", f"binary not found: {inv.argv[0]}"
        elif res.get("watch") and res["watch"]["killed"]:
            parsed.ok, parsed.failure_class = False, "watch_blocked"
            parsed.error = "stopped by the process watch: " + (res["watch"].get("first") or "stall")
        elif res["timed_out"]:
            parsed.ok, parsed.failure_class, parsed.error = False, "timeout", f"timed out after {timeout_s or self.timeout_s}s"
        elif not parsed.ok or res["returncode"] != 0:
            parsed.ok = False
            tail = tail_text(d / "stderr.log") + "\n" + tail_text(d / "stdout.log")
            cls = "auth_quota" if AUTH_RE.search(tail) else "network" if NET_RE.search(tail) else "error"
            parsed.failure_class = cls
            if cls == "auth_quota":  # show the CLI's own words about the login problem
                hit = next((ln.strip() for ln in tail.splitlines() if AUTH_RE.search(ln)), "")
                parsed.error = re.sub(r"^\S+Z\s+ERROR\s+\S+:\s*", "", hit)[:300]
            else:
                parsed.error = parsed.error or first_line(tail_text(d / "stderr.log")) or first_line(tail_text(d / "stdout.log")) or f"exit {res['returncode']}"
        return parsed

    def describe(self, role: str = "worker") -> list:
        """The exact argv this adapter would run (for dry runs and docs)."""
        inv = self.build(role, "<workspace>", "<prompt_file>", "<out_file>", "<job_id>")
        return inv.argv + (["<", "<prompt_file>"] if inv.stdin_file else [])


def tail_text(path, n=4096) -> str:
    try:
        with open(path, "rb") as f:
            f.seek(0, os.SEEK_END)
            size = f.tell()
            f.seek(max(0, size - n))
            return f.read().decode("utf-8", "replace")
    except OSError:
        return ""


def first_line(text: str) -> str:
    for line in text.splitlines():
        if line.strip():
            return line.strip()[:300]
    return ""


def execute(inv: Invocation, run_dir: Path, timeout_s: int, watch: dict | None = None) -> dict:
    """Run one invocation: no shell, new session, timeout kills the whole group.
    `watch` = {packs, mode, stall_s, stall_mode} turns on the process watch."""
    start = time.monotonic()
    pw = None
    out = open(run_dir / "stdout.log", "wb")
    err = open(run_dir / "stderr.log", "wb")
    stdin = open(inv.stdin_file, "rb") if inv.stdin_file else subprocess.DEVNULL
    timed_out, not_found, rc = False, False, None
    try:
        try:
            proc = subprocess.Popen(inv.argv, cwd=inv.cwd, env=inv.env, stdin=stdin, stdout=out, stderr=err,
                                    start_new_session=True)
        except FileNotFoundError:
            not_found = True
            proc = None
        if proc is not None:
            if watch:
                pw = ProcessWatch(proc.pid, run_dir / "watch.jsonl", watch.get("packs"), watch.get("mode", "warn"),
                                  watch.get("stall_s"), watch.get("stall_mode", "shadow"),
                                  [run_dir / "stdout.log", run_dir / "stderr.log"])
                pw.start()
            try:
                rc = proc.wait(timeout=timeout_s)
            except subprocess.TimeoutExpired:
                timed_out = True
                for sig in (signal.SIGTERM, signal.SIGKILL):
                    try:
                        os.killpg(proc.pid, sig)
                    except ProcessLookupError:
                        break
                    try:
                        rc = proc.wait(timeout=10)
                        break
                    except subprocess.TimeoutExpired:
                        continue
            finally:
                try:
                    os.killpg(proc.pid, signal.SIGKILL)  # leftover children of the group
                except ProcessLookupError:
                    pass
    finally:
        if pw:
            pw.finish()
        out.close()
        err.close()
        if inv.stdin_file:
            stdin.close()
    wres = None
    if pw:
        first = pw.violations[0]["rule"] if pw.violations else None
        wres = {"violations": len(pw.violations), "killed": pw.killed, "stalled": pw.stalled, "first": first}
    return {"returncode": rc, "timed_out": timed_out, "not_found": not_found, "watch": wres,
            "wall_seconds": round(time.monotonic() - start, 3)}


def read_jsonl(path) -> list:
    rows = []
    try:
        for line in Path(path).read_text("utf-8", "replace").splitlines():
            line = line.strip()
            if line.startswith("{"):
                try:
                    rows.append(json.loads(line))
                except ValueError:
                    pass
    except OSError:
        pass
    return rows


# ---------------------------------------------------------------- Muse Code
class MuseAdapter(Adapter):
    kind = "muse"
    needs = (["exec", "--help"], ["--json", "--prompt-file", "--workspace", "--reasoning-effort"])

    def login_state(self):
        return "unknown"  # `muse usage` needs the network; the live test is the real check

    def build(self, role, workspace, prompt_file, out_file, job_id="job"):
        b = self.resolve_bin() or self.bin or "muse"
        argv = [b, "exec", "--json"]
        if self.model:
            argv += ["--model", self.model]
        argv += ["--reasoning-effort", self.effort or "high"]
        argv += ["--workspace", workspace, "--prompt-file", prompt_file]
        if role == "architect":
            argv += ["--disable-write", "--disable-shell", "--approval-mode", "never"]
        elif self.cfg.get("yolo"):
            argv += ["--yolo"]  # what the recorded ladder used: no approval, no sandbox. Opt-in only.
        else:
            argv += ["--approval-mode", "never"]
        argv += self.extra
        return Invocation(argv, None, workspace, scrubbed_env(self.kind, self.env_allow))

    def parse(self, role, stdout_path, out_file, rc):
        rows = read_jsonl(stdout_path)
        text, done, session, err, usage = [], False, None, None, None
        for r in rows:
            pt, pl = r.get("payload_type", ""), r.get("payload") or {}
            if not session:
                session = (r.get("stream") or {}).get("id")
            if pt == "run.output.delta" and isinstance(pl.get("text"), str):
                text.append(pl["text"])
            if pt == "run.usage":
                usage = pl
            if pt in ("run.lifecycle.completed", "task.lifecycle.completed") or pl.get("kind") == "run_completed":
                done = True
            if "failed" in pt or "error" in pt:
                err = err or json.dumps(pl)[:300]
        summary = "".join(text).strip()
        Path(out_file).write_text(summary + "\n", "utf-8")
        return Result(ok=rc == 0 and bool(summary), summary=summary[-4000:], returncode=rc, session_id=session,
                      events_path=stdout_path, error=None if rc == 0 else err, usage=usage)


# -------------------------------------------------------------- Claude Code
class ClaudeAdapter(Adapter):
    kind = "claude"
    needs = (["--help"], ["--print", "--output-format", "--permission-mode", "--add-dir", "--effort"])

    def login_state(self):
        b = self.resolve_bin()
        if not b:
            return "unknown"
        try:
            r = subprocess.run([b, "auth", "status"], capture_output=True, text=True, timeout=45,
                               stdin=subprocess.DEVNULL, env=scrubbed_env(self.kind, self.env_allow))
            data = json.loads(r.stdout)
            return "logged-in" if data.get("loggedIn") is True else "not-logged-in"
        except (OSError, subprocess.TimeoutExpired, ValueError):
            return "unknown"

    def build(self, role, workspace, prompt_file, out_file, job_id="job"):
        b = self.resolve_bin() or self.bin or "claude"
        argv = [b, "-p", "--output-format", "stream-json", "--verbose", "--no-session-persistence"]
        if self.model:
            argv += ["--model", self.model]
        argv += ["--effort", self.effort or "high"]
        if role == "architect":
            argv += ["--permission-mode", "plan", "--tools", ",".join(self.cfg.get("architect_tools") or CLAUDE_ARCHITECT_TOOLS)]
        else:
            tools = self.cfg.get("allowed_tools") or CLAUDE_WORKER_TOOLS
            argv += ["--permission-mode", "acceptEdits", "--add-dir", workspace, "--allowedTools", ",".join(tools)]
        if self.cfg.get("hook_cmd"):  # per-action check (enforce.via: pretooluse_hook): Claude Code asks `anima check --hook` before each tool call
            hook = {"hooks": {"PreToolUse": [{"matcher": "Bash|Read|Edit|Write|Grep|Glob",
                                              "hooks": [{"type": "command", "command": self.cfg["hook_cmd"]}]}]}}
            argv += ["--settings", json.dumps(hook, separators=(",", ":"))]
        argv += self.extra
        return Invocation(argv, prompt_file, workspace, scrubbed_env(self.kind, self.env_allow))

    def parse(self, role, stdout_path, out_file, rc):
        rows = read_jsonl(stdout_path)
        final = next((r for r in reversed(rows) if r.get("type") == "result"), None)
        model_seen = next((r.get("model") for r in rows if r.get("type") == "system" and r.get("model")), None)
        if not final:
            return Result(ok=False, returncode=rc, events_path=stdout_path, error="no result event in claude output")
        text = (final.get("result") or "").strip()
        Path(out_file).write_text(text + "\n", "utf-8")
        is_err = bool(final.get("is_error"))
        return Result(ok=rc == 0 and not is_err and bool(text), summary=text[-4000:], returncode=rc,
                      cost_usd=final.get("total_cost_usd"), turns=final.get("num_turns"),
                      session_id=final.get("session_id"), model_seen=model_seen, events_path=stdout_path,
                      error=text[:300] if is_err else None)


# -------------------------------------------------------------------- Codex
class CodexAdapter(Adapter):
    kind = "codex"
    needs = (["exec", "--help"], ["--json", "--sandbox", "--cd", "--skip-git-repo-check", "--output-last-message"])

    def login_state(self):
        b = self.resolve_bin()
        if not b:
            return "unknown"
        try:
            r = subprocess.run([b, "login", "status"], capture_output=True, text=True, timeout=45,
                               stdin=subprocess.DEVNULL, env=scrubbed_env(self.kind, self.env_allow))
            text = (r.stdout + r.stderr).lower()
            if "logged in" in text and "not logged in" not in text:
                return "logged-in"
            return "not-logged-in" if r.returncode != 0 or "not logged" in text else "unknown"
        except (OSError, subprocess.TimeoutExpired):
            return "unknown"

    def build(self, role, workspace, prompt_file, out_file, job_id="job"):
        b = self.resolve_bin() or self.bin or "codex"
        sandbox = "read-only" if role == "architect" else "workspace-write"
        argv = [b, "exec", "--json", "--skip-git-repo-check", "-s", sandbox, "-C", workspace]
        if self.model:
            argv += ["-m", self.model]
        argv += ["-c", f'model_reasoning_effort="{self.effort or "high"}"']
        argv += self.extra
        argv += ["-o", out_file, "-"]
        return Invocation(argv, prompt_file, workspace, scrubbed_env(self.kind, self.env_allow))

    def parse(self, role, stdout_path, out_file, rc):
        rows = read_jsonl(stdout_path)
        text = ""
        try:
            text = Path(out_file).read_text("utf-8", "replace").strip()
        except OSError:
            pass
        if not text:  # fall back to the last agent message in the event stream
            for r in reversed(rows):
                item = r.get("item") or {}
                if r.get("type") == "item.completed" and item.get("type") == "agent_message" and item.get("text"):
                    text = item["text"].strip()
                    break
        session = next((r.get("thread_id") for r in rows if r.get("type") == "thread.started"), None)
        failed = next((r for r in rows if r.get("type") in ("error", "turn.failed")), None)
        return Result(ok=rc == 0 and bool(text) and not failed, summary=text[-4000:], returncode=rc,
                      session_id=session, events_path=stdout_path,
                      error=(json.dumps(failed)[:300] if failed else None))


# ------------------------------------------------------------------- Custom
class CustomAdapter(Adapter):
    """Any other CLI. The profile gives an argv template; placeholders are
    {prompt_file} {workspace} {job_id} {model} {out_file} {role}. The prompt is
    never put in argv. `stdin: prompt_file` pipes it in; `result: out_file`
    reads the answer from {out_file}, otherwise stdout is the answer."""
    kind = "custom"

    def __init__(self, name, cfg):
        super().__init__(name, cfg)
        self.argv_t = [str(x) for x in (self.cfg.get("argv") or [])]
        self.arch_argv_t = [str(x) for x in (self.cfg.get("architect_argv") or [])]
        for t in (self.argv_t, self.arch_argv_t):
            validate_template(t)

    def resolve_bin(self):
        if not self.argv_t:
            return None
        exe = self.argv_t[0]
        return shutil.which(exe) if os.sep not in exe else (exe if os.access(exe, os.X_OK) else None)

    def version(self):
        return "custom" if self.resolve_bin() else None

    def build(self, role, workspace, prompt_file, out_file, job_id="job"):
        tmpl = self.arch_argv_t if role == "architect" else self.argv_t
        if not tmpl:
            raise HarnessError(f"custom harness {self.name!r} has no {'architect_argv' if role == 'architect' else 'argv'}")
        vals = {"prompt_file": prompt_file, "workspace": workspace, "job_id": job_id, "model": self.model or "",
                "out_file": out_file, "role": role}
        argv = [t.format(**vals) for t in tmpl]
        stdin = prompt_file if self.cfg.get("stdin") == "prompt_file" else None
        return Invocation(argv, stdin, workspace, scrubbed_env(self.kind, self.env_allow))

    def parse(self, role, stdout_path, out_file, rc):
        text = ""
        if self.cfg.get("result") == "out_file":
            try:
                text = Path(out_file).read_text("utf-8", "replace").strip()
            except OSError:
                pass
        if not text and Path(stdout_path).exists():
            text = Path(stdout_path).read_text("utf-8", "replace").strip()
        return Result(ok=rc == 0, summary=text[-4000:], returncode=rc)


def validate_template(argv: list) -> None:
    bad_flags = re.compile(r"^--?(api[-_]?key|token|password|secret)", re.I)
    for item in argv:
        if bad_flags.match(item):
            raise HarnessError(f"credential flag in argv template is not allowed: {item}")
        for m in re.finditer(r"\{([^{}]*)\}", item.replace("{{", "").replace("}}", "")):
            if m.group(1) not in PLACEHOLDERS:
                raise HarnessError(f"unknown placeholder {{{m.group(1)}}} (allowed: {', '.join(sorted(PLACEHOLDERS))})")


ADAPTERS = {"muse": MuseAdapter, "claude": ClaudeAdapter, "codex": CodexAdapter, "custom": CustomAdapter}


def make_adapter(name: str, cfg: dict) -> Adapter:
    kind = (cfg or {}).get("kind") or name
    if kind not in ADAPTERS:
        raise HarnessError(f"unknown harness kind {kind!r}; use one of {', '.join(KINDS)}")
    return ADAPTERS[kind](name, cfg or {})


def detect_installed() -> dict:
    """Which of the three known CLIs are on PATH (or in ~/.local/bin). Looks only for the binary."""
    found = {}
    for kind in DETECT_ORDER:
        path = shutil.which(kind)
        if not path:
            alt = Path.home() / ".local" / "bin" / kind
            path = str(alt) if alt.exists() and os.access(alt, os.X_OK) else None
        if path:
            found[kind] = path
    return found
