"""Failure-injection tests F1-F5 (stdlib unittest, $0, no models).

Each case asserts BOTH the raised error AND its recorded ledger entry —
refusals are never silent. Two record shapes, following W1's convention:
- pre-check refusals (budget/authority/custody guards) -> kind "deny";
- execution failures inside host.invoke's fn() -> kind "invoke" with a
  typed payload.error ("TimeoutError: ...", "FileNotFoundError: ...",
  "ContractViolation: ...") and NO consume for the failed call.

Run from package dir:  python3 -m unittest test_failures -v
Run from repo root:    PYTHONPATH=prototype/w1-harden python3 -m unittest \\
                         test_w1_harden test_failures test_recovery
"""
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

try:
    from .HOST import Host
    from .contract import ContractViolation, WorldRecord
    from .relationship import task_spec_to_formulation
    from .world_construct import CAPABILITIES as C_CAPABILITIES
    from .world_construct import ConstructWorld
    from .world_explore import CAPABILITIES as E_CAPABILITIES
    from .world_explore import ExploreWorld, StubSearchEngine
except ImportError:  # running from the package dir
    from HOST import Host
    from contract import ContractViolation, WorldRecord
    from relationship import task_spec_to_formulation
    from world_construct import CAPABILITIES as C_CAPABILITIES
    from world_construct import ConstructWorld
    from world_explore import CAPABILITIES as E_CAPABILITIES
    from world_explore import ExploreWorld, StubSearchEngine

ROOT_HOLDINGS = {"max_cost_usd": 10.0, "max_time_s": 600.0, "max_invocations": 1000}


def make_host(tmp: str) -> Host:
    return Host(state_dir=Path(tmp) / "state", ledger_path=Path(tmp) / "ledger.jsonl",
                root_holdings=dict(ROOT_HOLDINGS))


def make_construct_world(host: Host, wid: str = "builder") -> ConstructWorld:
    rec = WorldRecord(world_id=wid, lineage=[("host", "created", "test")],
                      code_ref="test", instance_state_dir=str(
                          Path(host.state_dir) / wid),
                      custodians={"task-state": wid},
                      capabilities=list(C_CAPABILITIES),
                      authorities=["execute.local", "artifact.read"])
    host.create_world(rec, "host",
                      grant_limits={"max_cost_usd": 1.0, "max_time_s": 60.0,
                                    "max_invocations": 10})
    host.transition(wid, "active", "host", reason="test")
    return ConstructWorld(Path(host.state_dir) / wid)


class TestFailures(unittest.TestCase):
    def test_F1_timeout_recorded_and_unbilled(self):
        with tempfile.TemporaryDirectory() as tmp:
            host = make_host(tmp)
            world = make_construct_world(host)
            argv = [sys.executable, "-c", "import time; time.sleep(30)"]
            # Direct: TimeoutError, no receipt confusion.
            with self.assertRaises(TimeoutError):
                world.build_run(argv, timeout_s=0.2)
            # Via host.invoke: recorded invoke+error, holdings unchanged.
            before = dict(host.holdings["builder"])
            with self.assertRaises(TimeoutError):
                host.invoke("builder", "builder", "build.run", "1.0",
                            "args-f1",
                            lambda: world.build_run(argv, timeout_s=0.2),
                            cost_usd=0.01, time_s=1.0)
            last = host.ledger_entries()[-1]
            self.assertEqual(last["kind"], "invoke")
            self.assertTrue(
                last["payload"]["error"].startswith("TimeoutError:"),
                last["payload"])
            self.assertEqual(host.holdings["builder"], before)

    def test_F2_missing_file_verify_and_read(self):
        with tempfile.TemporaryDirectory() as tmp:
            host = make_host(tmp)
            world = make_construct_world(host)
            out = world.build_run(
                [sys.executable, "-c", "open('o.txt','w').write('x')"])
            # build_verify: passed=False + verdict file written (not a raise).
            detail = world.build_verify(out["receipt_ref"],
                                        {"exit_code": 0,
                                         "files_exist": ["nope.txt"]})
            self.assertFalse(detail["passed"])
            self.assertEqual(detail["failures"], ["missing file nope.txt"])
            verdicts = list((Path(host.state_dir) / "builder" / "verdicts").glob("*.json"))
            self.assertEqual(len(verdicts), 1)
            # artifact_read: FileNotFoundError, recorded via host.invoke.
            with self.assertRaises(FileNotFoundError):
                world.artifact_read("nope.txt")
            with self.assertRaises(FileNotFoundError):
                host.invoke("builder", "builder", "artifact.read", "1.0",
                            "args-f2", lambda: world.artifact_read("nope.txt"))
            last = host.ledger_entries()[-1]
            self.assertEqual(last["kind"], "invoke")
            self.assertIn("FileNotFoundError", last["payload"]["error"])

    def test_F3_budget_exhausted_second_invoke_denied(self):
        with tempfile.TemporaryDirectory() as tmp:
            host = make_host(tmp)
            world = make_construct_world(host)
            # Tighten to exactly 1 invocation (ledger-recorded, replay-honest).
            host.consume("builder", invocations=9, evidence_ref="tighten-f3")
            host.invoke("builder", "builder", "build.run", "1.0", "args-f3a",
                        lambda: "ok-once")
            self.assertEqual(host.holdings["builder"]["max_invocations"], 0)
            with self.assertRaisesRegex(ContractViolation, "grant exceeded"):
                host.invoke("builder", "builder", "build.run", "1.0",
                            "args-f3b", lambda: "never")
            last = host.ledger_entries()[-1]
            self.assertEqual(last["kind"], "deny")
            self.assertEqual(last["payload"]["action"], "invoke")
            self.assertIn("would exceed grant", last["payload"]["reason"])

    def test_F4_unknown_mapping_version_refused_and_pinned_runs_safe(self):
        with tempfile.TemporaryDirectory() as tmp:
            host = make_host(tmp)
            explore = ExploreWorld(Path(host.state_dir) / "explorer",
                                   engine=StubSearchEngine())
            rec = WorldRecord(
                world_id="explorer", lineage=[("host", "created", "test")],
                code_ref="test",
                instance_state_dir=str(Path(host.state_dir) / "explorer"),
                custodians={"search-state": "explorer"},
                capabilities=list(E_CAPABILITIES),
                authorities=["search.sst"])
            host.create_world(rec, "host",
                              grant_limits={"max_cost_usd": 1.0,
                                            "max_time_s": 60.0,
                                            "max_invocations": 10})
            host.transition("explorer", "active", "host", reason="test")
            spec = {"goal": "g", "acceptance": ["a"], "scope": ["f"]}
            before = task_spec_to_formulation(spec, "1.0")
            with self.assertRaisesRegex(ContractViolation,
                                        "unknown mapping version '9.9'"):
                host.invoke("explorer", "explorer", "search.propose", "1.0",
                            "args-f4",
                            lambda: task_spec_to_formulation(spec, "9.9"))
            last = host.ledger_entries()[-1]
            self.assertEqual(last["kind"], "invoke")
            self.assertIn("unknown mapping version", last["payload"]["error"])
            # Pinned runs unaffected: v1 re-derivation identical.
            self.assertEqual(task_spec_to_formulation(spec, "1.0"), before)
            form_ref = explore.write_formulation(
                goal=before["goal"], domain=before["domain"],
                constraints=before["constraints"], budget=before["budget"])
            run = explore.search_propose(form_ref, {"branching": 1})
            self.assertTrue(run["champion_id"])
            _ = run  # world-local run only; host.invoke refusal above is the test

    def test_F5_double_custody_transfer_second_refused(self):
        with tempfile.TemporaryDirectory() as tmp:
            host = make_host(tmp)
            for wid in ("w1", "w2"):
                rec = WorldRecord(
                    world_id=wid, lineage=[("host", "created", "test")],
                    code_ref="test",
                    instance_state_dir=str(Path(host.state_dir) / wid),
                    custodians={"task-state": wid},
                    authorities=["custody.transfer"])
                host.create_world(rec, "host",
                                  grant_limits={"max_cost_usd": 1.0,
                                                "max_time_s": 60.0,
                                                "max_invocations": 10})
                host.transition(wid, "active", "host", reason="test")
            host.transfer_custody("task-state", "w1", "w2", "w1",
                                  reason="first", continuity="w2 continues")
            transfers = [e for e in host.ledger_entries()
                         if e["kind"] == "transfer"]
            self.assertEqual(len(transfers), 1)
            # Second transfer from w1 (no longer custodian) is refused.
            with self.assertRaisesRegex(ContractViolation, "not custodian"):
                host.transfer_custody("task-state", "w1", "w2", "w1",
                                      reason="double", continuity="none")
            last = host.ledger_entries()[-1]
            self.assertEqual(last["kind"], "deny")
            self.assertEqual(last["payload"]["action"], "custody.transfer")


if __name__ == "__main__":
    unittest.main()
