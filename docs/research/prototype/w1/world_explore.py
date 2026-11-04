"""E-explore world implementation (W1 prototype).

Exploration/constraint-like environment: local search state dir,
representations (formulation/v0, candidate/v0, score/v0), capabilities
search.propose / search.score.

Search engine behind ONE interface (SearchEngine.run): the real SST
SSTSearchController wiring when SST is importable (project-local .venv +
PYTHONPATH, TEST providers only, $0), else a documented deterministic stub
engine. The domain evaluator is world-local (LocalEvaluator, shaped per
SST's EvaluatorProtocol); SST's internal custody verifier only checks patch
application/scope, never the domain verdict.

This module imports SST lazily and only after setting
sys.dont_write_bytecode, so importing/using it never writes bytecode into
the read-only sst/ tree. Under a plain stdlib interpreter the stub path
engages automatically.
"""
from __future__ import annotations

import asyncio
import hashlib
import json
import sys
import tempfile
from dataclasses import dataclass
from pathlib import Path

from contract import Capability, Representation

WORLD_ID = "E-explore"

CAPABILITIES = [
    Capability(name="search.propose", version="1.0",
               inputs="formulation/v0 ref, policy {max_iterations?, max_depth?, branching?}",
               outputs="candidate/v0 refs + engine record",
               side_effects="writes search state under the world state dir",
               cost_model="cost_usd=0 (TEST/scripted providers); time_s bounded by policy",
               applicability="formulation must exist in world state",
               failure_modes="budget exhausted (no champion); unknown formulation",
               required_authority="search.sst"),
    Capability(name="search.score", version="1.0",
               inputs="candidate/v0 refs", outputs="score/v0 refs (world-local verdicts)",
               side_effects="none", cost_model="free",
               applicability="candidates must exist in world state",
               failure_modes="missing candidate",
               required_authority="search.sst"),
]

REPRESENTATIONS = [
    Representation(name="formulation/v0", version="1.0",
                   schema_ref="explore:formulation/v0",
                   meaning_note="goal + domain + constraints + budget for one search"),
    Representation(name="candidate/v0", version="1.0",
                   schema_ref="explore:candidate/v0",
                   meaning_note="one proposed variant + provenance (engine, parent, policy)"),
    Representation(name="score/v0", version="1.0",
                   schema_ref="explore:score/v0",
                   meaning_note="world-local verdict + deterministic score + rationale"),
]

CUSTODIANS = {"search-state": WORLD_ID, "formulations": WORLD_ID, "scores": WORLD_ID}

TOY_SOURCE_NAME = "toy.py"
TOY_SOURCE = 'def add(a, b):\n    return a + b\n'


# -- world-local evaluator (EvaluatorProtocol-shaped) -----------------------
@dataclass(frozen=True)
class GateResult:
    """World-local deterministic gate outcome. Field-compatible with SST's
    DeterministicGateResult (passed/exit_code/stdout/stderr/duration_seconds)
    plus the world's own score/verdict."""
    passed: bool
    exit_code: int
    stdout: str
    stderr: str
    duration_seconds: float
    score: float
    verdict: str


class LocalEvaluator:
    """World-local domain evaluator. NEVER SST's: it owns the authoritative
    verdict over candidates. Method shape mirrors SST EvaluatorProtocol
    evaluate(node, workspace_dir, test_command=None, baseline_metrics=None)
    so it can structurally satisfy that protocol; `node` here is a plain
    candidate dict (no SST import needed). Deterministic: same candidate ->
    same score, always."""

    def evaluate(self, node, workspace_dir, test_command=None,
                 baseline_metrics=None) -> GateResult:
        content = node.get("content", "") if isinstance(node, dict) else str(node)
        title = node.get("title", "") if isinstance(node, dict) else ""
        digest = hashlib.sha256(f"{title}\n{content}".encode("utf-8")).hexdigest()
        # Deterministic score in [0, 1): fixed rule, no randomness, no models.
        raw = int(digest[:8], 16) % 1000
        bonus = 0
        if "return" in content:
            bonus += 150
        if "def " in content:
            bonus += 100
        score = min(0.99, (raw + bonus) / 1250.0)
        passed = score >= 0.5
        return GateResult(
            passed=passed, exit_code=0 if passed else 1,
            stdout=f"world-local evaluation of {title!r}: score={score:.3f}",
            stderr="" if passed else "below world-local threshold 0.5",
            duration_seconds=0.0, score=score,
            verdict="APPROVE" if passed else "REJECT")


# -- engine interface + implementations --------------------------------------
class SearchEngine:
    engine_name = "abstract"

    def run(self, formulation: dict, work_dir: Path, policy: dict) -> dict:
        raise NotImplementedError


class StubSearchEngine(SearchEngine):
    """Deterministic stub behind the SAME interface as the real SST engine.
    Used automatically when SST is not importable (e.g. system python3)."""
    engine_name = "stub-deterministic-v1"

    def run(self, formulation: dict, work_dir: Path, policy: dict) -> dict:
        n = max(1, min(4, int(policy.get("branching", 2))))
        seed = hashlib.sha256(
            json.dumps(formulation, sort_keys=True).encode("utf-8")).hexdigest()
        evaluator = LocalEvaluator()
        candidates = []
        for i in range(n):
            variant = f"stub-variant-{seed[:6]}-{i}"
            content = (f"# {variant}\ndef solve(x):\n    return x  # {seed[i * 4:i * 4 + 4]}\n")
            cand = {"candidate_id": variant, "title": variant,
                    "content": content, "parent_ids": ["root"],
                    "role": "DIVERGE", "engine": self.engine_name}
            gate = evaluator.evaluate(cand, work_dir)
            cand["world_score"] = gate.score
            cand["world_verdict"] = gate.verdict
            candidates.append(cand)
        champion = max(candidates, key=lambda c: c["world_score"])
        return {"engine": self.engine_name, "termination": "champion_found",
                "candidates": candidates, "champion_id": champion["candidate_id"],
                "cost_usd": 0.0, "policy": policy,
                "evidence": {"seed": seed[:16], "evaluator": "world-local"}}


class RealSSTSearchEngine(SearchEngine):
    """Real SST SSTSearchController wiring (spike: PASS). TEST providers only
    ($0). SST's custody verifier checks patch application/scope; the
    authoritative domain verdict stays world-local (LocalEvaluator)."""
    engine_name = "sst-controller-v0"

    def run(self, formulation: dict, work_dir: Path, policy: dict) -> dict:
        sys.dont_write_bytecode = True  # keep the sst/ tree read-only
        from sst.core.contracts import TaskPacket
        from sst.gateway.contracts import ProviderKind, ProviderProfile
        from sst.gateway.gateway import ModelGateway
        from sst.sandbox.custody import CandidateCustodyManager
        from sst.search.controller import SSTSearchController
        from sst.search.policy import SearchPolicy
        from sst.storage.store import SQLiteSSTStore

        work_dir.mkdir(parents=True, exist_ok=True)
        src = work_dir / "src"
        src.mkdir(parents=True, exist_ok=True)
        (src / TOY_SOURCE_NAME).write_text(
            formulation.get("toy_source", TOY_SOURCE), encoding="utf-8")
        tree_id = "w1-" + hashlib.sha256(
            json.dumps(formulation, sort_keys=True).encode("utf-8")).hexdigest()[:12]
        task = TaskPacket(
            task_id=f"{tree_id}-task",
            goal=formulation.get("goal", "toy search"),
            source_repo_root=str(src),
            base_commit="none", snapshot_hash="none",
            allowed_paths=[TOY_SOURCE_NAME],
            invariants=formulation.get("constraints", []),
            acceptance_commands=[],
        )
        gateway = ModelGateway()
        gateway.register_profile(ProviderProfile(
            name="test-local", kind=ProviderKind.TEST,
            api_base="test://local", selected_model="test-model-0"))
        for role in ("diverge", "refine", "critique", "synthesize"):
            gateway.set_route(role, "test-local", "test-model-0")
        store = SQLiteSSTStore(work_dir / f"{tree_id}.db")
        custody = CandidateCustodyManager(base_worktree_dir=work_dir / "worktrees")
        ctrl = SSTSearchController(
            task=task, gateway=gateway, store=store, custody_manager=custody,
            policy=SearchPolicy(
                max_iterations=int(policy.get("max_iterations", 2)),
                max_depth=int(policy.get("max_depth", 2)),
                branching_factor=int(policy.get("branching", 1)),
                max_time_seconds=int(policy.get("max_time_seconds", 120))))
        result = asyncio.run(ctrl.run_search(tree_id))
        events = store.get_events(tree_id)
        kinds: dict[str, int] = {}
        for e in events:
            kinds[str(e.kind)] = kinds.get(str(e.kind), 0) + 1
        # World-local authoritative verdicts over SST's candidates.
        evaluator = LocalEvaluator()
        sst_cands = []
        if result.champion is not None:
            sst_cands.append(result.champion)
        sst_cands.extend(a for a in result.alternatives)
        candidates = []
        seen: set[str] = set()
        for c in sst_cands:
            inner = getattr(c, "candidate", c)  # AlternativeCandidate wraps one
            if inner.candidate_id in seen:
                continue
            seen.add(inner.candidate_id)
            cid = inner.candidate_id
            title = getattr(inner, "title", cid)
            content = getattr(inner, "patch_diff", "") or ""
            role = str(getattr(inner, "role", "DIVERGE"))
            cand = {"candidate_id": cid, "title": title, "content": content,
                    "parent_ids": [f"root_{tree_id}"], "role": role,
                    "engine": self.engine_name}
            gate = evaluator.evaluate(cand, work_dir)
            cand["world_score"] = gate.score
            cand["world_verdict"] = gate.verdict
            candidates.append(cand)
        return {"engine": self.engine_name,
                "termination": str(result.termination_reason),
                "candidates": candidates,
                "champion_id": result.champion.candidate_id if result.champion else None,
                "cost_usd": float(result.budget_consumed.estimated_cost_usd),
                "policy": policy,
                "evidence": {"tree_id": tree_id, "event_kinds": kinds,
                             "sst_db": str(work_dir / f"{tree_id}.db"),
                             "evaluator": "world-local",
                             "tokens_consumed": result.budget_consumed.tokens_consumed}}


def explore_engine() -> SearchEngine:
    """Real SST engine when importable, else the deterministic stub."""
    try:
        sys.dont_write_bytecode = True
        import sst.search.controller  # noqa: F401
        return RealSSTSearchEngine()
    except Exception:
        return StubSearchEngine()


class ExploreWorld:
    def __init__(self, state_dir: str | Path, engine: SearchEngine | None = None) -> None:
        self.state_dir = Path(state_dir)
        self.state_dir.mkdir(parents=True, exist_ok=True)
        self.engine = engine or explore_engine()
        self._counter = 0

    def _write_json(self, subdir: str, payload: dict) -> str:
        self._counter += 1
        path = self.state_dir / subdir / f"{self._counter:04d}.json"
        path.parent.mkdir(parents=True, exist_ok=True)
        payload = {"contract_version": "0", **payload}
        path.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")
        return str(path)

    def write_formulation(self, goal: str, domain: str, constraints: list,
                          budget: dict, toy_source: str = TOY_SOURCE) -> str:
        return self._write_json("formulations", {
            "representation": "formulation/v0", "goal": goal, "domain": domain,
            "constraints": constraints, "budget": budget, "toy_source": toy_source})

    def search_propose(self, formulation_ref: str, policy: dict | None = None) -> dict:
        formulation = json.loads(Path(formulation_ref).read_text(encoding="utf-8"))
        policy = policy or {"max_iterations": 2, "max_depth": 2, "branching": 1}
        work = self.state_dir / "search-work"
        result = self.engine.run(formulation, work, policy)
        cands = result["candidates"]
        refs = [self._write_json("candidates", {"representation": "candidate/v0", **c})
                for c in cands]
        if not cands:
            out = {"engine": result["engine"], "termination": result["termination"],
                   "candidate_refs": [], "champion_id": None,
                   "cost_usd": result["cost_usd"], "policy": policy,
                   "evidence": result["evidence"]}
            self._write_json("search-runs", {"representation": "search-run/v0", **out})
            return out
        champion = max(cands, key=lambda c: c["world_score"])
        out = {"engine": result["engine"], "termination": result["termination"],
               "candidate_refs": refs, "champion_id": champion["candidate_id"],
               "cost_usd": result["cost_usd"], "policy": policy,
               "evidence": result["evidence"]}
        self._write_json("search-runs", {"representation": "search-run/v0", **out})
        return out

    def search_score(self, candidate_refs: list) -> dict:
        evaluator = LocalEvaluator()
        scored = []
        for ref in candidate_refs:
            cand = json.loads(Path(ref).read_text(encoding="utf-8"))
            gate = evaluator.evaluate(cand, self.state_dir)
            sref = self._write_json("scores", {
                "representation": "score/v0",
                "candidate_id": cand.get("candidate_id"),
                "score": gate.score, "verdict": gate.verdict,
                "rationale": gate.stdout, "evaluator": "world-local"})
            scored.append({"candidate_id": cand.get("candidate_id"),
                           "score": gate.score, "verdict": gate.verdict,
                           "score_ref": sref})
        return {"scores": scored, "evaluator": "world-local"}