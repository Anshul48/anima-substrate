"""Successor-002 SST leg: consume the VENDORED snapshot ONLY.

Consumption contract (see vendor/PROVENANCE.md + REPORT.md):
- PYTHONPATH points at vendor/sst-snapshot/ (vendored df78f42 release bytes),
  TEST fixtures, $0. NO other SST tree exists on any path: this module
  contains no reference to any live or staged external tree, and the
  child refuses to run unless `sst` resolves inside the snapshot dir
  with no shadowing copy anywhere else on sys.path.
- verify_snapshot.verify() runs BEFORE every SST import and AFTER every
  SST consumption: ANY drift (changed/missing/extra file, count or
  hash change) raises SSTBoundary naming the files. There is no
  warn-and-proceed posture.
- venv interpreter with pinned pydantic==2.13.5 (default
  prototype/w1/.venv/bin/python, override via SST_VENV_PY). A different
  pydantic version aborts the leg (re-qualification required).
- NEVER write into the snapshot (pre/post verification proves it).

Label: SUBSTRATE-QUALIFIED SNAPSHOT — NO SST-OWNER RELEASE ACCEPTANCE.
"""
from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

from verify_snapshot import (SSTBoundary, verify as verify_snapshot,  # noqa: E402
                             DEFAULT_MANIFEST as SNAPSHOT_MANIFEST)

__all__ = ["SSTBoundary", "run_sst_test_search", "SNAPSHOT_SRC",
           "SNAPSHOT_MANIFEST", "VENV_PY", "ENVELOPE_KEYS",
           "PINNED_PYDANTIC"]

PROTOTYPE = HERE.parent
SNAPSHOT_SRC = HERE / "vendor" / "sst-snapshot"
VENV_PY = Path(os.environ.get(
    "SST_VENV_PY", str(PROTOTYPE / "w1" / ".venv" / "bin" / "python")))

PINNED_PYDANTIC = "2.13.5"

ENVELOPE_KEYS = {"tree_id", "termination_reason", "champion",
                 "alternatives", "budget_consumed", "provider_errors",
                 "gateway_bindings", "event_log_ref"}


# ------------------------------------------------------- TEST consumption

CHILD_SCRIPT = '''"""SST-TEST child: run_search against the vendored snapshot ONLY.

Modeled on the snapshot tests/unit/test_controller.py pattern (TEST
fixture gateway + deterministic code return), calling the frozen
run_search envelope. All disk writes go under RUNDIR (argv[1]); the
snapshot tree is read-only. Argv[2] is the snapshot src dir.
"""
import asyncio
import json
import sys
from pathlib import Path

RUNDIR = Path(sys.argv[1])
SNAPSHOT_SRC = Path(sys.argv[2]).resolve()

import sst  # noqa: E402  (import AFTER sys.argv read, on purpose)
SST_FILE = Path(sst.__file__).resolve()
try:
    SST_FILE.relative_to(SNAPSHOT_SRC)
except ValueError:
    raise AssertionError(
        f"SST boundary violated: sst imported from {SST_FILE}, "
        f"not from the vendored snapshot {SNAPSHOT_SRC}")
# Shadowing guard: no OTHER sys.path entry may provide an sst package.
for entry in sys.path:
    if not entry:
        continue
    cand = (Path(entry).resolve() / "sst" / "__init__.py")
    if cand.exists() and cand != SNAPSHOT_SRC / "sst" / "__init__.py":
        raise AssertionError(
            f"SST boundary violated: shadowing sst package at {cand}")

import pydantic  # noqa: E402
from sst.core.contracts import TaskPacket  # noqa: E402
from sst.gateway.contracts import (GatewayResponse, ModelCatalog,  # noqa: E402
    ModelCatalogEntry, ProviderKind, ProviderProfile)
from sst.gateway.gateway import ModelGateway  # noqa: E402
from sst.sandbox.custody import CandidateCustodyManager  # noqa: E402
from sst.search.controller import SSTSearchController  # noqa: E402
from sst.search.policy import SearchPolicy  # noqa: E402
from sst.storage.store import SQLiteSSTStore  # noqa: E402


class TestGateway(ModelGateway):
    def __init__(self) -> None:
        super().__init__()
        prof = ProviderProfile(
            name="test-prof", kind=ProviderKind.TEST, api_base="test://",
            catalog=ModelCatalog(models=[ModelCatalogEntry(
                id="fake-model", display_label="Fake")]))
        self.register_profile(prof)
        self.set_route("diverge", "test-prof", "fake-model")
        self.set_route("critique", "test-prof", "fake-model")

    def invoke(self, request):  # deterministic TEST fixture return
        if request.role == "critique":
            content = ('{"value_score": 0.95, "verdict": "APPROVE", '
                       '"rationale": "High quality solution"}')
        else:
            content = "def mul(a, b): return a * b\\n"
        return GatewayResponse(
            content=content, profile="test-prof", model="fake-model",
            prompt_tokens=50, completion_tokens=50, total_tokens=100)


def main() -> None:
    work = RUNDIR / "sst-work"
    repo = work / "repo"
    repo.mkdir(parents=True, exist_ok=True)
    (repo / "math_mod.py").write_text(
        "def mul(a, b): return a + b\\n", encoding="utf-8")
    (repo / "test_math.py").write_text(
        "from math_mod import mul\\nassert mul(3, 4) == 12\\n",
        encoding="utf-8")
    task = TaskPacket(
        task_id="t_successor_sst", goal="Implement correct multiplication",
        source_repo_root=str(repo), base_commit="c1", snapshot_hash="h1",
        allowed_paths=["math_mod.py"],
        acceptance_commands=["python test_math.py"])
    store = SQLiteSSTStore(work / "events.db")
    custody = CandidateCustodyManager(
        base_worktree_dir=work / "worktrees")
    ctl = SSTSearchController(
        task=task, gateway=TestGateway(), store=store,
        custody_manager=custody,
        policy=SearchPolicy(
            max_iterations=2, branching_factor=1, max_depth=3))
    res = asyncio.run(ctl.run_search("tree_successor_sst"))
    out = {
        "sst_file": str(SST_FILE),
        "pydantic_version": pydantic.VERSION,
        "provider_kind": "TEST",
        "envelope": res.model_dump(),
    }
    (RUNDIR / "sst-result.json").write_text(
        json.dumps(out, indent=2, sort_keys=True, default=str),
        encoding="utf-8")
    print(json.dumps({"termination_reason": str(res.termination_reason),
                      "champion": (res.champion.candidate_id
                                   if res.champion else None),
                      "cost_usd": res.budget_consumed.estimated_cost_usd,
                      "sst_file": str(SST_FILE)}))


if __name__ == "__main__":
    main()
'''


def run_sst_test_search(rundir: Path, timeout_s: int = 300) -> dict:
    """Verify the snapshot, then run the TEST search in a child process."""
    rundir = Path(rundir)
    rundir.mkdir(parents=True, exist_ok=True)
    # Gate 1 (BEFORE any SST import): exact-snapshot verification.
    pre = verify_snapshot(SNAPSHOT_SRC, SNAPSHOT_MANIFEST)
    (rundir / "SNAPSHOT-CHECK.json").write_text(
        json.dumps(pre, indent=2, sort_keys=True), encoding="utf-8")
    if not VENV_PY.exists():
        raise SSTBoundary(f"SST boundary: venv interpreter missing: {VENV_PY} "
                          f"(override with SST_VENV_PY)")
    child = rundir / "sst_child_test.py"
    child.write_text(CHILD_SCRIPT, encoding="utf-8")
    env = {"PYTHONPATH": str(SNAPSHOT_SRC), "PYTHONDONTWRITEBYTECODE": "1",
           "PATH": os.environ.get("PATH", ""),
           "SYSTEMROOT": os.environ.get("SYSTEMROOT", ""),
           "HOME": os.environ.get("HOME", ""),
           "TMPDIR": os.environ.get("TMPDIR", "/tmp")}
    try:
        proc = subprocess.run(
            [str(VENV_PY), str(child), str(rundir), str(SNAPSHOT_SRC)],
            cwd=str(rundir), env=env, capture_output=True, text=True,
            timeout=timeout_s)
    except FileNotFoundError as exc:
        raise SSTBoundary(f"SST boundary: cannot start venv python: {exc}")
    if proc.returncode != 0:
        raise SSTBoundary(
            f"SST boundary: snapshot TEST child failed rc={proc.returncode}\n"
            f"--- stdout ---\n{proc.stdout}\n--- stderr ---\n{proc.stderr[-4000:]}")
    res_path = rundir / "sst-result.json"
    if not res_path.exists():
        raise SSTBoundary("SST boundary: child exited 0 but wrote no "
                          f"sst-result.json\nstdout:\n{proc.stdout}")
    result = json.loads(res_path.read_text(encoding="utf-8"))
    envelope = result["envelope"]
    missing = ENVELOPE_KEYS - set(envelope)
    if missing:
        raise SSTBoundary(f"SST boundary: envelope keys missing: {missing}")
    if result.get("provider_kind") != "TEST":
        raise SSTBoundary("SST boundary: provider_kind is not TEST")
    kinds = {b.get("kind") for b in envelope["gateway_bindings"]}
    if kinds != {"TEST"}:
        raise SSTBoundary(f"SST boundary: gateway bindings not all TEST: "
                          f"{kinds}")
    cost = envelope["budget_consumed"]["estimated_cost_usd"]
    if cost != 0.0:
        raise SSTBoundary(f"SST boundary: non-$0 TEST run: cost {cost}")
    if result.get("pydantic_version") != PINNED_PYDANTIC:
        raise SSTBoundary(
            f"SST boundary: pydantic {result.get('pydantic_version')} != "
            f"pinned {PINNED_PYDANTIC} (re-qualification required)")
    # Gate 2 (AFTER consumption): the snapshot must be byte-identical.
    post = verify_snapshot(SNAPSHOT_SRC, SNAPSHOT_MANIFEST)
    if post["snapshot_hash"] != pre["snapshot_hash"]:
        raise SSTBoundary("SST boundary: snapshot changed during "
                          "consumption (writes into the snapshot are "
                          "forbidden)")
    return {"snapshot_check": post["verdict"],
            "check_file": str(rundir / "SNAPSHOT-CHECK.json"),
            "snapshot_hash": post["snapshot_hash"],
            "termination_reason": str(envelope["termination_reason"]),
            "champion": (envelope["champion"]["candidate_id"]
                         if envelope["champion"] else None),
            "cost_usd": cost,
            "envelope_keys": sorted(envelope),
            "sst_file": result["sst_file"],
            "pydantic_version": result["pydantic_version"],
            "snapshot_unchanged": True,
            "child_stdout_tail": proc.stdout.strip().splitlines()[-1]
            if proc.stdout.strip() else ""}
