"""The `anima.yaml` profile: load, validate, write, and resolve roles to adapters.

Format = the contract in READY/anima-build/ROLES-AND-CONSTRAINTS.md section 3,
trimmed to what ANIMA can run today, plus one block the design doc did not
have (`harnesses:`, where `anima init` records the binaries it found).

What is run (see `anima doctor` for the live list):
  version, harness, harnesses, enforce, roles.<r>.{harness,model,may,must_not,budget},
  rules, watches (stall only), ladder (retry_with_failure_line, run_with, ask)
  memory.{backend: off|trace, store, k, record}  (run: `anima run` recalls before and records after; CLI flags override)
What is read and kept but NOT run here: mission,
  watches other than stall, budget keys other than timeout_s / attempts / max_turns.
"""
from __future__ import annotations

import os
import shlex
import sys
from pathlib import Path

from . import miniyaml
from .adapters import DETECT_ORDER, KINDS, HarnessError, make_adapter
from .rules import DEFAULT_PACKS, NOT_ENFORCED, PACKS

ROLE_NAMES = ("architect", "manager", "worker")
LADDER_DO = ("retry_with_failure_line", "run_with", "ask")
RUN_BUDGET_KEYS = ("timeout_s", "attempts", "max_turns")
HEADER = (
    "# anima.yaml: written by `anima init`. Edit freely; `anima doctor` says what is run and what is not.\n"
    "# Format follows READY/anima-build/ROLES-AND-CONSTRAINTS.md section 3 (trimmed), plus a `harnesses:` block."
)

WRITE_MAY = {"write_workspace", "write_repo", "bulk_edit"}


def anima_home() -> Path:
    return Path(os.environ.get("ANIMA_HOME") or (Path.home() / ".anima"))


def memory_default_store() -> Path:
    """One state root: the memory folder lives under ANIMA_HOME, not under whatever the current directory is."""
    return anima_home() / "memory"


def find_profile(explicit: str | None = None) -> Path | None:
    if explicit:
        return Path(explicit)
    env = os.environ.get("ANIMA_PROFILE")
    if env:
        return Path(env)
    for cand in (Path.cwd() / "anima.yaml", anima_home() / "anima.yaml"):
        if cand.exists():
            return cand
    return None


def load(path) -> dict:
    p = Path(path)
    try:
        data = miniyaml.loads(p.read_text("utf-8"))
    except miniyaml.YamlError as exc:
        raise HarnessError(f"{p}: {exc}") from exc
    if not isinstance(data, dict):
        raise HarnessError(f"{p}: top level must be a mapping")
    problems = validate(data)
    if problems:
        raise HarnessError(f"{p}: " + "; ".join(problems))
    return data


def save(path, data: dict, header: str = HEADER) -> None:
    p = Path(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    tmp = p.with_name(p.name + ".tmp")
    tmp.write_text(miniyaml.dumps(data, header), "utf-8")
    os.replace(tmp, p)


def validate(data: dict) -> list[str]:
    bad = []
    if data.get("version") not in (None, 1):
        bad.append(f"unknown version {data.get('version')!r} (this ANIMA reads version 1)")
    hs = data.get("harnesses") or {}
    if not isinstance(hs, dict):
        bad.append("harnesses must be a mapping")
        hs = {}
    for name, cfg in hs.items():
        kind = (cfg or {}).get("kind") or name
        if kind not in KINDS:
            bad.append(f"harnesses.{name}: unknown kind {kind!r}")
    main = data.get("harness")
    if main and main not in hs and main not in DETECT_ORDER:
        bad.append(f"harness: {main!r} is not defined under harnesses")
    for r, rc in (data.get("roles") or {}).items():
        h = (rc or {}).get("harness")
        if h and h not in hs and h not in DETECT_ORDER:
            bad.append(f"roles.{r}.harness: {h!r} is not defined under harnesses")
    for step in data.get("ladder") or []:
        if not isinstance(step, dict) or step.get("do") not in LADDER_DO:
            bad.append(f"ladder step needs do: one of {', '.join(LADDER_DO)} (got {step!r})")
        elif step["do"] == "run_with" and not step.get("harness"):
            bad.append("ladder step run_with needs harness:")
    for p in data.get("rules") or []:
        if p not in PACKS:
            bad.append(f"rules: unknown pack {p!r} (known: {', '.join(PACKS)})")
    mem = data.get("memory")
    if mem is not None:
        if not isinstance(mem, dict):
            bad.append("memory must be a mapping, e.g. memory: {backend: trace}")
        else:
            if mem.get("backend") not in (None, "off", "trace"):
                bad.append("memory.backend must be off or trace")
            k = mem.get("k")
            if k is not None and not (isinstance(k, int) and not isinstance(k, bool) and 1 <= k <= 5):
                bad.append("memory.k must be a whole number from 1 to 5")
    enf = data.get("enforce") or {}
    if enf.get("mode") not in (None, "warn", "enforce", "shadow"):
        bad.append("enforce.mode must be warn, shadow or enforce")
    return bad


def build_default(found: dict) -> dict:
    """The profile `anima init` writes for the CLIs it found (order: Muse, Claude, Codex)."""
    order = [k for k in DETECT_ORDER if k in found]
    if not order:
        return {"version": 1, "harness": None, "harnesses": {}, "enforce": {"mode": "warn", "via": "wrapper"},
                "memory": {"backend": "off"}, "rules": list(DEFAULT_PACKS)}
    main = order[0]
    ladder = [{"on": "gate_fail", "do": "run_with", "harness": k} for k in order[1:]]
    ladder.append({"on": "still_failing", "do": "ask", "role": "architect"})
    return {
        "version": 1,
        "harness": main,
        "harnesses": {k: {"kind": k, "bin": found[k]} for k in order},
        "enforce": {"mode": "warn", "via": "wrapper"},
        "roles": {
            "architect": {"harness": main, "may": ["read_repo", "review"], "must_not": ["push", "bulk_edit"]},
            "worker": {"may": ["read_workspace", "write_workspace", "run_tests"],
                       "must_not": ["secrets", "push", "message_owner"],
                       "budget": {"timeout_s": 1800}},
        },
        "memory": {"backend": "off"},
        "rules": list(DEFAULT_PACKS),
        "ladder": ladder,
    }


class Profile:
    def __init__(self, data: dict, path=None):
        self.data, self.path = data, (Path(path) if path else None)

    # -- harness / role resolution ---------------------------------------
    @property
    def main(self) -> str | None:
        return self.data.get("harness")

    def harness_cfg(self, name: str) -> dict:
        cfg = dict((self.data.get("harnesses") or {}).get(name) or {})
        cfg.setdefault("kind", name if name in KINDS else cfg.get("kind"))
        return cfg

    def names(self) -> list[str]:
        hs = list((self.data.get("harnesses") or {}).keys())
        return hs

    def role(self, role: str) -> dict:
        return dict((self.data.get("roles") or {}).get(role) or {})

    def role_harness(self, role: str) -> str | None:
        return self.role(role).get("harness") or self.main

    def adapter(self, name: str, role: str = "worker"):
        cfg = self.harness_cfg(name)
        rc = self.role(role)
        model = rc.get("model") or {}
        if isinstance(model, dict):
            if model.get("name"):
                cfg["model"] = model["name"]
            if model.get("effort"):
                cfg["effort"] = model["effort"]
        budget = rc.get("budget") or {}
        if budget.get("timeout_s"):
            cfg["timeout_s"] = budget["timeout_s"]
        if rc.get("allowed_tools"):
            cfg["allowed_tools"] = rc["allowed_tools"]
        enf = self.enforce()
        if enf.get("via") == "pretooluse_hook" and cfg.get("kind") == "claude":
            root = Path(__file__).resolve().parents[2]
            cfg["hook_cmd"] = (f"PYTHONPATH={shlex.quote(str(root))} {shlex.quote(sys.executable)} -m anima.harness "
                               f"check --hook --mode {enf['mode']}")
        if budget.get("max_turns") and cfg.get("kind") == "claude":
            cfg["extra_args"] = list(cfg.get("extra_args") or []) + ["--max-turns", str(budget["max_turns"])]
        return make_adapter(name, cfg)

    def memory_cfg(self) -> dict:
        """The resolved memory settings from anima.yaml (CLI flags override them in `anima run`)."""
        m = self.data.get("memory")
        m = dict(m) if isinstance(m, dict) else {}
        return {"backend": m.get("backend") or "off", "store": str(m.get("store") or memory_default_store()),
                "k": int(m.get("k") or 3), "record": m.get("record") is not False}

    def adapter_mode(self, role: str) -> str:
        """Adapter mode for a profile role: 'worker' (may edit the workspace) or
        'architect' (read-only). A role with no `may` list is a worker only if it is called worker."""
        may = set(self.role(role).get("may") or [])
        if not may:
            return "worker" if role == "worker" else "architect"
        return "worker" if may & WRITE_MAY else "architect"

    # -- enforcement ------------------------------------------------------
    def enforce(self) -> dict:
        e = dict(self.data.get("enforce") or {})
        e.setdefault("mode", "warn")
        e.setdefault("via", "wrapper")
        return e

    def watch_cfg(self, role: str) -> dict:
        from .rules import packs_for
        rc = self.role(role)
        stall = next((w for w in (self.data.get("watches") or []) if isinstance(w, dict) and str(w.get("check", "")).startswith("no_output_for")), None)
        cfg = {"packs": packs_for(self.data.get("rules"), rc.get("must_not")), "mode": self.enforce()["mode"]}
        if stall:
            secs = "".join(ch for ch in str(stall["check"]).split()[-1] if ch.isdigit())
            if secs:
                cfg["stall_s"] = int(secs)
                cfg["stall_mode"] = stall.get("mode", "shadow")
        return cfg

    def not_enforced(self) -> list[str]:
        out = []
        for r, rc in (self.data.get("roles") or {}).items():
            for m in (rc or {}).get("must_not") or []:
                if m in NOT_ENFORCED:
                    out.append(f"roles.{r}.must_not: {m}")
            for k in ((rc or {}).get("budget") or {}):
                if k not in RUN_BUDGET_KEYS:
                    out.append(f"roles.{r}.budget.{k}")
        if self.data.get("mission"):
            out.append("mission (read and kept; not run by the harness adapter)")
        for w in self.data.get("watches") or []:
            if isinstance(w, dict) and not str(w.get("check", "")).startswith("no_output_for"):
                out.append(f"watches.{w.get('name')}")
        if self.enforce().get("via") == "pretooluse_hook":
            pass  # implemented for claude only; the run log says whether it fired
        return out

    # -- ladder -----------------------------------------------------------
    def attempt_plan(self, start: str) -> list[dict]:
        """Expand the ladder into ordered attempts after the first one.
        Each: {"harness": name, "how": "retry"|"run_with"} or a final {"ask": role}."""
        plan = [{"harness": start, "how": "first"}]
        last = start
        for step in self.data.get("ladder") or []:
            do = step.get("do")
            if do == "retry_with_failure_line":
                for _ in range(int(step.get("times") or 1)):
                    plan.append({"harness": last, "how": "retry"})
            elif do == "run_with":
                last = step["harness"]
                plan.append({"harness": last, "how": "run_with"})
            elif do == "ask":
                plan.append({"ask": step.get("role") or "architect"})
                break
        return plan
