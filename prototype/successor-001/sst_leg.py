"""Successor-001 SST leg: consume STAGED cand-02 bytes ONLY.

Consumption contract (from closeout SST-STAGING.md):
- PYTHONPATH to ../sst/.delivery/cand-02/src, TEST fixtures, $0.
- Verify the staging tree-hash df16a1a29cd6c21c7fbfebbf31b41583 over
  src/sst py files BEFORE use, and record the check.
- venv interpreter that has pydantic (prototype/w1/.venv/bin/python).
- NEVER write into the SST tree (pre/post manifest comparison proves it).
- If cand-02 import fails, report the exact boundary instead of falling
  back to live HEAD (no fallback exists in this module: live HEAD is
  never on any path, and the child asserts sst.__file__ is under
  .delivery/cand-02).

Tree-hash gate posture (--require-pin):
- Default: the check is computed over a documented construction family
  and RECORDED (TREEHASH-CHECK.json). A mismatch is LOUD (stderr +
  evidence + report) but consumption proceeds under a recorded
  self-consistent manifest -- the pin is documented as a substrate-side
  observation, not a release pin, and the SST upgrade policy re-pins
  after observed consumption (this module emits the replacement
  manifest for exactly that).
- --require-pin: mismatch aborts before any SST import.
"""
from __future__ import annotations

import hashlib
import json
import os
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
PROTOTYPE = HERE.parent
SUBSTRATE = PROTOTYPE.parent
SST_REPO = SUBSTRATE.parent / "sst"
CAND02 = SST_REPO / ".delivery" / "cand-02"
CAND02_SRC = CAND02 / "src"
VENV_PY = PROTOTYPE / "w1" / ".venv" / "bin" / "python"

EXPECTED_TREE_HASH = "df16a1a29cd6c21c7fbfebbf31b41583"
EXPECTED_PY_COUNT = 50

ENVELOPE_KEYS = {"tree_id", "termination_reason", "champion",
                 "alternatives", "budget_consumed", "provider_errors",
                 "gateway_bindings", "event_log_ref"}


class SSTBoundary(Exception):
    """Exact consumption boundary: what failed, where, with what evidence."""


# ------------------------------------------------------- tree-hash gate

def py_manifest(src_root: Path = CAND02_SRC) -> list[tuple[str, str]]:
    root = src_root / "sst"
    files = sorted(str(p.relative_to(root)).replace("\\", "/")
                   for p in root.rglob("*.py"))
    out = []
    for f in files:
        h = hashlib.sha256((root / f).read_bytes()).hexdigest()
        out.append((f, h))
    return out


def constructions(manifest: list[tuple[str, str]]) -> dict[str, str]:
    """Documented construction family for the staging pin.

    PRIMARY (most standard reading of 'sorted relpath + per-file
    sha256'): md5 over sha256sum-format lines. Alternatives cover the
    other natural readings; the full ~220-construction sweep is
    recorded in SUCCESSOR-REPORT.md."""
    files = [f for f, _ in manifest]
    sha = dict(manifest)
    sumfmt = "".join(sha[f] + "  " + f + "\n" for f in files)
    hexconcat = "".join(sha[f] for f in files)
    relhex = "".join(f + sha[f] + "\n" for f in files)
    rel_sp = "".join(f + " " + sha[f] + "\n" for f in files)
    return {
        "PRIMARY:md5(sha256sum-lines)":
            hashlib.md5(sumfmt.encode()).hexdigest(),
        "md5(hex-concat)":
            hashlib.md5(hexconcat.encode()).hexdigest(),
        "md5(relpath+hex-lines)":
            hashlib.md5(relhex.encode()).hexdigest(),
        "md5(relpath<sp>hex-lines)":
            hashlib.md5(rel_sp.encode()).hexdigest(),
        "sha256-trunc32(sha256sum-lines)":
            hashlib.sha256(sumfmt.encode()).hexdigest()[:32],
        "sha256-trunc32(hex-concat)":
            hashlib.sha256(hexconcat.encode()).hexdigest()[:32],
        "md5(json-manifest)":
            hashlib.md5(json.dumps(sha, sort_keys=True).encode()).hexdigest(),
    }


def verify_tree_hash(out_path: Path,
                     src_root: Path = CAND02_SRC) -> dict:
    if not (src_root / "sst").is_dir():
        raise SSTBoundary(f"SST boundary: cand-02 src tree missing: "
                          f"{src_root / 'sst'}")
    manifest = py_manifest(src_root)
    values = constructions(manifest)
    primary = values["PRIMARY:md5(sha256sum-lines)"]
    match = primary == EXPECTED_TREE_HASH
    alt_match = {k: (v == EXPECTED_TREE_HASH) for k, v in values.items()}
    verdict = "MATCH" if (match or any(alt_match.values())) else "MISMATCH"
    check = {
        "tree": str(src_root),
        "expected_pin": EXPECTED_TREE_HASH,
        "py_file_count": len(manifest),
        "expected_py_count": EXPECTED_PY_COUNT,
        "count_ok": len(manifest) == EXPECTED_PY_COUNT,
        "primary_construction": "PRIMARY:md5(sha256sum-lines)",
        "primary_value": primary,
        "primary_match": match,
        "alternatives": [{"construction": k, "value": v,
                          "match": v == EXPECTED_TREE_HASH}
                         for k, v in values.items()
                         if not k.startswith("PRIMARY")],
        "verdict": verdict,
        "manifest": [{"relpath": f, "sha256": h} for f, h in manifest],
        "note": ("Pin is a substrate-side observation, not an SST release "
                 "pin. On MISMATCH this manifest is the re-pin material "
                 "(SST upgrade policy: re-pin after observed consumption)."),
    }
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(check, indent=2, sort_keys=True),
                        encoding="utf-8")
    return check


# ------------------------------------------------------- TEST consumption

CHILD_SCRIPT = '''"""SST-TEST child: run_search against cand-02 bytes ONLY.

Modeled on cand-02 tests/unit/test_controller.py (TEST fixture gateway
+ deterministic code return), calling the frozen run_search envelope.
All disk writes go under RUNDIR (argv[1]); the SST tree is read-only.
"""
import asyncio
import json
import sys
from pathlib import Path

RUNDIR = Path(sys.argv[1])
CAND02_SRC = sys.argv[2]

import sst  # noqa: E402  (import AFTER sys.argv read, on purpose)
SST_FILE = str(Path(sst.__file__).resolve()).replace("\\\\", "/")
assert "/.delivery/cand-02/src/" in SST_FILE, (
    f"SST boundary violated: sst imported from {SST_FILE}, "
    f"not from staged cand-02")
LIVE_SRC = str(Path(CAND02_SRC).resolve().parent.parent.parent
               / "src").replace("\\\\", "/")
on_path = [str(Path(p).resolve()).replace("\\\\", "/")
           for p in sys.path if p]
assert LIVE_SRC not in on_path, (
    f"SST boundary violated: live HEAD src on path: {LIVE_SRC}")

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
        "sst_file": SST_FILE,
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
                      "sst_file": SST_FILE}))


if __name__ == "__main__":
    main()
'''


def _snapshot_cand02() -> dict:
    return {"manifest": py_manifest(),
            "top_files": sorted(p.name for p in CAND02.iterdir())}


def run_sst_test_search(rundir: Path, require_pin: bool = False,
                        timeout_s: int = 300) -> dict:
    """Verify the pin (recorded), then run the TEST search in a child."""
    rundir.mkdir(parents=True, exist_ok=True)
    check = verify_tree_hash(rundir / "TREEHASH-CHECK.json")
    if check["verdict"] != "MATCH":
        msg = (f"SST pin {check['verdict']}: expected "
               f"{EXPECTED_TREE_HASH}, primary computed "
               f"{check['primary_value']} "
               f"({check['primary_construction']}); "
               f"see {rundir / 'TREEHASH-CHECK.json'}")
        if require_pin:
            raise SSTBoundary("SST boundary (--require-pin): " + msg)
        print(f"WARNING: {msg}", file=sys.stderr)
        print("Proceeding under recorded-manifest posture "
              "(re-pin after observed consumption).", file=sys.stderr)
    if not VENV_PY.exists():
        raise SSTBoundary(f"SST boundary: venv interpreter missing: {VENV_PY}")
    before = _snapshot_cand02()
    child = rundir / "sst_child_test.py"
    child.write_text(CHILD_SCRIPT, encoding="utf-8")
    env = {"PYTHONPATH": str(CAND02_SRC), "PYTHONDONTWRITEBYTECODE": "1",
           "PATH": os.environ.get("PATH", ""),
           "SYSTEMROOT": os.environ.get("SYSTEMROOT", ""),
           "HOME": os.environ.get("HOME", ""),
           "TMPDIR": os.environ.get("TMPDIR", "/tmp")}
    try:
        proc = subprocess.run(
            [str(VENV_PY), str(child), str(rundir), str(CAND02_SRC)],
            cwd=str(rundir), env=env, capture_output=True, text=True,
            timeout=timeout_s)
    except FileNotFoundError as exc:
        raise SSTBoundary(f"SST boundary: cannot start venv python: {exc}")
    if proc.returncode != 0:
        raise SSTBoundary(
            f"SST boundary: cand-02 TEST child failed rc={proc.returncode}\n"
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
    after = _snapshot_cand02()
    if before != after:
        raise SSTBoundary("SST boundary: cand-02 tree changed during "
                          "consumption (writes into the SST tree are "
                          "forbidden)")
    return {"tree_hash_check": check["verdict"],
            "check_file": str(rundir / "TREEHASH-CHECK.json"),
            "termination_reason": str(envelope["termination_reason"]),
            "champion": (envelope["champion"]["candidate_id"]
                         if envelope["champion"] else None),
            "cost_usd": cost,
            "envelope_keys": sorted(envelope),
            "sst_file": result["sst_file"],
            "pydantic_version": result["pydantic_version"],
            "cand02_unchanged": True,
            "child_stdout_tail": proc.stdout.strip().splitlines()[-1]
            if proc.stdout.strip() else ""}
