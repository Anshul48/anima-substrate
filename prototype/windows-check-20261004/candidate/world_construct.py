"""E-construct world implementation (W1-hardened copy, stdlib-only).

Adapted copy of prototype/w1/world_construct.py (frozen per FREEZE.w1).
Deltas vs w1:
- relative-with-fallback import of contract (CWD-independent);
- Windows-safe argv allowlist: the running interpreter's own program name
  (Path(sys.executable).name, e.g. python.exe) is admitted, and argv[0] is
  matched by basename too, so absolute interpreter paths work;
- subprocess.run passes shell=False explicitly (no behavior change on
  POSIX; documents the no-shell invariant on Windows).
"""
from __future__ import annotations

import hashlib
import json
import subprocess
import sys
from pathlib import Path

try:
    from .contract import Capability, Representation
except ImportError:  # running from the package dir
    from contract import Capability, Representation

WORLD_ID = "E-construct"

CAPABILITIES = [
    Capability(name="build.run", version="1.0",
               inputs="argv(list), timeout_s(float)",
               outputs="receipt/v0 ref",
               side_effects="spawns a subprocess confined to the world state dir",
               cost_model="cost_usd=0.01/invocation, time_s=wall time",
               applicability="argv[0] in allowlist; cwd forced to state dir",
               failure_modes="allowlist refusal; timeout; nonzero exit (recorded)",
               required_authority="execute.local"),
    Capability(name="build.verify", version="1.0",
               inputs="receipt ref, assertions {exit_code?, files_exist?[]}",
               outputs="pass/fail + detail",
               side_effects="none", cost_model="free",
               applicability="receipt must exist in world state",
               failure_modes="missing receipt; failed assertion",
               required_authority="execute.local"),
    Capability(name="artifact.read", version="1.0",
               inputs="relative path", outputs="bytes",
               side_effects="none", cost_model="free",
               applicability="path must stay inside the state dir",
               failure_modes="containment refusal; missing file",
               required_authority="artifact.read"),
]

REPRESENTATIONS = [
    Representation(name="task-spec/v0", version="1.0",
                   schema_ref="construct:task-spec/v0",
                   meaning_note="goal + acceptance list + file scope for a build task"),
    Representation(name="diff/v0", version="1.0",
                   schema_ref="construct:diff/v0",
                   meaning_note="unified diff text applied or proposed"),
    Representation(name="receipt/v0", version="1.0",
                   schema_ref="construct:receipt/v0",
                   meaning_note="exit code + argv + wall time + stdout/stderr refs of one run"),
]

CUSTODIANS = {"task-state": WORLD_ID, "artifacts": WORLD_ID, "run-records": WORLD_ID}

# argv[0] allowlist for build.run. No shells, no network tools.
# SYS_PYTHON admits the running interpreter itself (python.exe on Windows,
# python/python3 on POSIX) so callers can pass sys.executable portably.
SYS_PYTHON = Path(sys.executable).name
ARGV_ALLOWLIST = (SYS_PYTHON, "python3", "python", "python.exe",
                  "ls", "cat", "echo", "true", "false", "sleep",
                  "mkdir", "touch")


def _argv_allowed(argv0: str) -> bool:
    if argv0 in ARGV_ALLOWLIST:
        return True
    # Admit absolute/relative interpreter paths by program name so that
    # sys.executable works on every platform (still no shells, no tools).
    return Path(argv0).name in ARGV_ALLOWLIST


class ConstructWorld:
    def __init__(self, state_dir: str | Path) -> None:
        self.state_dir = Path(state_dir)
        self.state_dir.mkdir(parents=True, exist_ok=True)
        self._counter = 0

    # -- representation helpers -------------------------------------------
    def _write_json(self, subdir: str, payload: dict) -> str:
        self._counter += 1
        path = self.state_dir / subdir / f"{self._counter:04d}.json"
        path.parent.mkdir(parents=True, exist_ok=True)
        payload = {"contract_version": "0", **payload}
        path.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")
        return str(path)

    def write_task_spec(self, goal: str, acceptance: list, scope: list) -> str:
        return self._write_json("task-specs", {
            "representation": "task-spec/v0",
            "goal": goal, "acceptance": acceptance, "scope": scope})

    # -- capabilities ------------------------------------------------------
    def build_run(self, argv: list, timeout_s: float = 30.0) -> dict:
        if not argv or not _argv_allowed(argv[0]):
            raise PermissionError(
                f"build.run refused: argv[0]={argv[0] if argv else None!r} not in allowlist")
        try:
            proc = subprocess.run(argv, cwd=self.state_dir, capture_output=True,
                                  text=True, timeout=timeout_s, shell=False)
            timed_out = False
        except subprocess.TimeoutExpired as exc:
            self._counter += 1
            raise TimeoutError(f"build.run timed out after {timeout_s}s: {argv}") from exc
        self._counter += 1
        tag = f"{self._counter:04d}"
        (self.state_dir / f"stdout-{tag}.txt").write_text(proc.stdout, encoding="utf-8")
        (self.state_dir / f"stderr-{tag}.txt").write_text(proc.stderr, encoding="utf-8")
        receipt = {"contract_version": "0", "representation": "receipt/v0",
                   "argv": argv, "exit_code": proc.returncode,
                   "timeout_s": timeout_s, "timed_out": timed_out,
                   "stdout_ref": f"stdout-{tag}.txt", "stderr_ref": f"stderr-{tag}.txt"}
        path = self.state_dir / "receipts" / f"{tag}.json"
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(receipt, indent=2, sort_keys=True), encoding="utf-8")
        return {"receipt_ref": str(path), "exit_code": proc.returncode,
                "timed_out": timed_out}

    def build_verify(self, receipt_ref: str, assertions: dict) -> dict:
        receipt_path = Path(receipt_ref)
        if not receipt_path.exists():
            raise FileNotFoundError(f"build.verify: missing receipt {receipt_ref}")
        receipt = json.loads(receipt_path.read_text(encoding="utf-8"))
        failures = []
        if "exit_code" in assertions and receipt.get("exit_code") != assertions["exit_code"]:
            failures.append(f"exit_code {receipt.get('exit_code')} != {assertions['exit_code']}")
        for rel in assertions.get("files_exist", []):
            if not (self.state_dir / rel).exists():
                failures.append(f"missing file {rel}")
        detail = {"passed": not failures, "failures": failures,
                  "receipt_ref": receipt_ref, "assertions": assertions}
        self._write_json("verdicts", {"representation": "construct-verdict/v0", **detail})
        return detail

    def artifact_read(self, rel_path: str) -> bytes:
        target = (self.state_dir / rel_path).resolve()
        if target != self.state_dir.resolve() and self.state_dir.resolve() not in target.parents:
            raise PermissionError(f"artifact.read refused: {rel_path!r} escapes state dir")
        return target.read_bytes()

    @staticmethod
    def sha256_file(path: str) -> str:
        h = hashlib.sha256()
        with open(path, "rb") as fh:
            for chunk in iter(lambda: fh.read(65536), b""):
                h.update(chunk)
        return h.hexdigest()
