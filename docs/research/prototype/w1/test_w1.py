"""W1 host test suite (stdlib unittest). Run: python3 -m unittest (from w1/).

Covers: conservation (grants <= holdings), authority refusal, custody
transfer record, revision pinning, suspend/reattach identity, ledger
append-only. Stdlib-only.
"""
import inspect
import json
import tempfile
import unittest
from pathlib import Path

from HOST import Host
from contract import ContractViolation, WorldRecord
from relationship import task_spec_to_formulation, v1_record, v2_record
from world_construct import ConstructWorld
from world_explore import ExploreWorld, LocalEvaluator, StubSearchEngine

ROOT_HOLDINGS = {"max_cost_usd": 10.0, "max_time_s": 600.0, "max_invocations": 1000}


def make_host(tmp: str) -> Host:
    return Host(state_dir=Path(tmp) / "state", ledger_path=Path(tmp) / "ledger.jsonl",
                root_holdings=dict(ROOT_HOLDINGS))


def make_world(host: Host, wid: str, creator: str = "host",
               authorities=None, grant=None) -> WorldRecord:
    rec = WorldRecord(world_id=wid, lineage=[(creator, "created", "test")],
                      code_ref="test", instance_state_dir=str(
                          Path(host.state_dir) / wid),
                      custodians={"task-state": wid},
                      authorities=authorities or [])
    host.create_world(rec, creator,
                      grant_limits=grant or {"max_cost_usd": 1.0, "max_time_s": 60.0,
                                             "max_invocations": 10})
    host.transition(wid, "active", "host", reason="test")
    return rec


class TestConservation(unittest.TestCase):
    def test_grant_cannot_exceed_holding(self):
        with tempfile.TemporaryDirectory() as tmp:
            host = make_host(tmp)
            make_world(host, "w1", authorities=["grant.delegate"])
            make_world(host, "w2")
            with self.assertRaises(ContractViolation):
                host.grant("w1", "w2", {"max_cost_usd": 999.0}, [], "g-bad")
            # w1 holds 1.0; granting 0.4 twice is fine, third fails.
            host.grant("w1", "w2", {"max_cost_usd": 0.4}, [], "g-1")
            host.grant("w1", "w2", {"max_cost_usd": 0.4}, [], "g-2")
            with self.assertRaises(ContractViolation):
                host.grant("w1", "w2", {"max_cost_usd": 0.4}, [], "g-3")

    def test_conservation_replay(self):
        with tempfile.TemporaryDirectory() as tmp:
            host = make_host(tmp)
            make_world(host, "w1", authorities=["grant.delegate"])
            make_world(host, "w2")
            host.grant("w1", "w2", {"max_cost_usd": 0.25, "max_invocations": 2},
                       [], "g-1")
            host.consume("w2", cost_usd=0.1, invocations=1, evidence_ref="e1")
            host.return_grant("g-1", "w2", {"max_cost_usd": 0.05}, reason="unused")
            report = host.verify_conservation()
            self.assertTrue(report["ok"])
            # Global: held + consumed == initial.
            for key in ("max_cost_usd", "max_time_s", "max_invocations"):
                held = sum(b[key] for b in report["balances"].values())
                used = sum(c[key] for c in report["consumed"].values())
                self.assertAlmostEqual(held + used, ROOT_HOLDINGS[key])

    def test_consume_cannot_overdraw(self):
        with tempfile.TemporaryDirectory() as tmp:
            host = make_host(tmp)
            make_world(host, "w1")
            with self.assertRaises(ContractViolation):
                host.consume("w1", cost_usd=50.0)


class TestAuthority(unittest.TestCase):
    def test_invoke_without_authority_denied_and_recorded(self):
        with tempfile.TemporaryDirectory() as tmp:
            host = make_host(tmp)
            from world_construct import CAPABILITIES
            rec = WorldRecord(world_id="builder", lineage=[], code_ref="test",
                              instance_state_dir=str(Path(host.state_dir) / "builder"),
                              custodians={}, capabilities=list(CAPABILITIES),
                              authorities=["execute.local"])
            host.create_world(rec, "host", grant_limits={"max_cost_usd": 1.0,
                                                              "max_time_s": 60.0,
                                                              "max_invocations": 10})
            host.transition("builder", "active", "host", reason="test")
            make_world(host, "caller", authorities=[])  # no execute.local
            with self.assertRaises(ContractViolation):
                host.invoke("caller", "builder", "build.run", "1.0", "args",
                            lambda: "x")
            last = host.ledger_entries()[-1]
            self.assertEqual(last["kind"], "deny")
            self.assertIn("execute.local", last["payload"]["reason"])

    def test_world_create_needs_authority(self):
        with tempfile.TemporaryDirectory() as tmp:
            host = make_host(tmp)
            make_world(host, "plain", authorities=[])
            rec = WorldRecord(world_id="child", lineage=[], code_ref="t",
                              instance_state_dir=str(Path(host.state_dir) / "child"),
                              custodians={})
            with self.assertRaises(ContractViolation):
                host.create_world(rec, "plain")


class TestLifecycle(unittest.TestCase):
    def test_suspend_reattach_identity(self):
        with tempfile.TemporaryDirectory() as tmp:
            host = make_host(tmp)
            make_world(host, "w1")
            host.suspend("w1", "host", reason="test", pending_effects=["e1"])
            self.assertEqual(host.worlds["w1"].lifecycle, "suspended")
            ckpt = json.loads((Path(host.state_dir) / "w1" / "checkpoint.json")
                              .read_text(encoding="utf-8"))
            self.assertEqual(ckpt["world_id"], "w1")
            self.assertEqual(ckpt["pending_effects"], ["e1"])
            host.reattach("w1", "host", reason="test")
            self.assertEqual(host.worlds["w1"].lifecycle, "active")
            kinds = [e["kind"] for e in host.ledger_entries()]
            self.assertIn("checkpoint", kinds)
            self.assertIn("reattach", kinds)

    def test_illegal_edge_refused(self):
        with tempfile.TemporaryDirectory() as tmp:
            host = make_host(tmp)
            make_world(host, "w1")  # active
            with self.assertRaises(ContractViolation):
                host.transition("w1", "proposed", "host", reason="backwards")

    def test_retired_id_never_reused(self):
        with tempfile.TemporaryDirectory() as tmp:
            host = make_host(tmp)
            make_world(host, "w1")
            host.transition("w1", "retired", "host", reason="test")
            rec = WorldRecord(world_id="w1", lineage=[], code_ref="t",
                              instance_state_dir=str(Path(host.state_dir) / "w1b"),
                              custodians={})
            with self.assertRaises(ContractViolation):
                host.create_world(rec, "host")


class TestCustodyTransfer(unittest.TestCase):
    def test_transfer_record_and_custodian_moves(self):
        with tempfile.TemporaryDirectory() as tmp:
            host = make_host(tmp)
            make_world(host, "w1", authorities=["custody.transfer"])
            make_world(host, "w2")
            host.transfer_custody("task-state", "w1", "w2", "w1",
                                  reason="test", continuity="w2 continues")
            self.assertNotIn("task-state", host.worlds["w1"].custodians)
            self.assertEqual(host.worlds["w2"].custodians["task-state"], "w2")
            transfers = [e for e in host.ledger_entries() if e["kind"] == "transfer"]
            self.assertEqual(len(transfers), 1)
            self.assertEqual(transfers[0]["payload"]["from"], "w1")

    def test_transfer_by_non_custodian_refused(self):
        with tempfile.TemporaryDirectory() as tmp:
            host = make_host(tmp)
            make_world(host, "w1")
            make_world(host, "w2")
            with self.assertRaises(ContractViolation):
                host.transfer_custody("w1s-task-state", "w2", "w1", "host",
                                      reason="theft", continuity="none")


class TestRevisionPinning(unittest.TestCase):
    def test_v1_stable_after_v2_declared(self):
        with tempfile.TemporaryDirectory() as tmp:
            host = make_host(tmp)
            make_world(host, "E-construct")
            make_world(host, "E-explore")
            host.declare_relationship(v1_record(), actor="host")
            spec = {"goal": "g", "acceptance": ["a"], "scope": ["f"]}
            before = task_spec_to_formulation(spec, "1.0")
            host.declare_relationship(v2_record(), actor="host")
            after = task_spec_to_formulation(spec, "1.0")
            self.assertEqual(before, after)
            v2 = task_spec_to_formulation(spec, "2.0")
            self.assertIn("assumptions", v2)
            self.assertEqual(host.get_relationship("rel-construct-explore", "1.0").version, "1.0")


class TestLedgerAppendOnly(unittest.TestCase):
    def test_ledger_grows_and_seq_monotonic(self):
        with tempfile.TemporaryDirectory() as tmp:
            host = make_host(tmp)
            n0 = len(host.ledger_entries())
            make_world(host, "w1")
            entries = host.ledger_entries()
            self.assertGreater(len(entries), n0)
            seqs = [e["seq"] for e in entries]
            self.assertEqual(seqs, sorted(seqs))
            self.assertEqual(len(set(seqs)), len(seqs))
            for e in entries:
                self.assertEqual(e["contract_version"], "0")

    def test_unknown_contract_version_refused(self):
        with tempfile.TemporaryDirectory() as tmp:
            host = make_host(tmp)
            rec = WorldRecord(world_id="w9", lineage=[], code_ref="t",
                              instance_state_dir=str(Path(host.state_dir) / "w9"),
                              custodians={}, contract_version="99")
            with self.assertRaises(ContractViolation):
                host.create_world(rec, "host")


class TestWorlds(unittest.TestCase):
    def test_construct_run_verify_roundtrip(self):
        with tempfile.TemporaryDirectory() as tmp:
            w = ConstructWorld(Path(tmp) / "c")
            out = w.build_run(["python3", "-c", "open('o.txt','w').write('x')"])
            self.assertEqual(out["exit_code"], 0)
            verdict = w.build_verify(out["receipt_ref"],
                                     {"exit_code": 0, "files_exist": ["o.txt"]})
            self.assertTrue(verdict["passed"])

    def test_construct_allowlist_refusal(self):
        with tempfile.TemporaryDirectory() as tmp:
            w = ConstructWorld(Path(tmp) / "c")
            with self.assertRaises(PermissionError):
                w.build_run(["rm", "-rf", "/"])

    def test_construct_containment_refusal(self):
        with tempfile.TemporaryDirectory() as tmp:
            w = ConstructWorld(Path(tmp) / "c")
            with self.assertRaises(PermissionError):
                w.artifact_read("../../etc/hostname")

    def test_stub_engine_deterministic(self):
        with tempfile.TemporaryDirectory() as tmp:
            form = {"goal": "g", "domain": "d", "constraints": [],
                    "budget": {}}
            r1 = StubSearchEngine().run(form, Path(tmp) / "w1", {"branching": 2})
            r2 = StubSearchEngine().run(form, Path(tmp) / "w2", {"branching": 2})
            self.assertEqual(r1["candidates"], r2["candidates"])
            self.assertEqual(r1["champion_id"], r2["champion_id"])

    def test_local_evaluator_shape_matches_protocol(self):
        sig = inspect.signature(LocalEvaluator.evaluate)
        self.assertEqual(list(sig.parameters),
                         ["self", "node", "workspace_dir", "test_command",
                          "baseline_metrics"])
        gate = LocalEvaluator().evaluate(
            {"title": "t", "content": "def f():\n    return 1\n"}, "/tmp")
        self.assertTrue(0.0 <= gate.score <= 1.0)

    def test_explore_world_roundtrip_stub(self):
        with tempfile.TemporaryDirectory() as tmp:
            w = ExploreWorld(Path(tmp) / "e", engine=StubSearchEngine())
            ref = w.write_formulation("g", "d", [], {})
            run = w.search_propose(ref, {"branching": 2})
            self.assertTrue(run["champion_id"])
            scored = w.search_score(run["candidate_refs"])
            self.assertEqual(len(scored["scores"]), 2)

    # NOTE: no real-SST test here — this file is stdlib-only per the W1
    # plan's hard limits. Real-SST coverage comes from the spike probe
    # (/tmp/muse-w1-spike.py, exit 0) and the venv demo_T.py run (exit 0).


if __name__ == "__main__":
    unittest.main()
