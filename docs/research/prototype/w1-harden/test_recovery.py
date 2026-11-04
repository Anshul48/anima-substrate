"""Checkpoint/recovery exercises (stdlib unittest, $0, stub engine pinned).

R1  kill-mid-run -> resume-to-verdict without restart (simulated kill by
    dropping the Host, AND a real SIGKILL of a child process): asserts 0
    re-executed invokes, formulation ref + prior artifacts reused byte-for-byte.
R2  missing-checkpoint reattach refusal (raise + deny).
R3  checkpoint identity-mismatch refusal, world_id and code_ref (raise + deny).
R3b reopen supply-record mismatch refusal (raise + deny).
R4  settle-on-terminal: single + multi-grantor, zero stranded holdings.
R4n negative: hand-written ledger without grant_settle -> "unsettled terminal".
R5  reopen without descriptors: ledger-only worlds fail closed for non-host
    invokes; host inspection path stays open.

Run from package dir:  python3 -m unittest test_recovery -v
"""
import hashlib
import json
import os
import queue
import signal
import subprocess
import sys
import tempfile
import threading
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

try:
    from .HOST import WITHHELD_AUTHORITY, Host
    from .contract import ContractViolation, WorldRecord
    from .recovery_lib import (WORKER_ID, ExploreWorld, phase_formulate,
                               phase_propose, resume_to_verdict, setup,
                               successful_invokes, worker_record)
    from .world_explore import StubSearchEngine
except ImportError:  # running from the package dir
    from HOST import WITHHELD_AUTHORITY, Host
    from contract import ContractViolation, WorldRecord
    from recovery_lib import (WORKER_ID, ExploreWorld, phase_formulate,
                              phase_propose, resume_to_verdict, setup,
                              successful_invokes, worker_record)
    from world_explore import StubSearchEngine

ROOT_HOLDINGS = {"max_cost_usd": 10.0, "max_time_s": 600.0, "max_invocations": 1000}
EXERCISE_SCRIPT = str(Path(__file__).resolve().parent / "recovery_exercise.py")


def make_host(tmp: str) -> Host:
    return Host(state_dir=Path(tmp) / "state", ledger_path=Path(tmp) / "ledger.jsonl",
                root_holdings=dict(ROOT_HOLDINGS))


def sha256_file(path: str) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()


def count_kind(entries: list[dict], kind: str) -> int:
    return sum(1 for e in entries if e.get("kind") == kind)


def _read_ready(proc: subprocess.Popen, timeout_s: float = 60.0) -> str:
    box: queue.Queue = queue.Queue()

    def _read() -> None:
        try:
            box.put(proc.stdout.readline())
        except Exception as exc:  # noqa: BLE001 - surfaced below
            box.put(exc)

    thread = threading.Thread(target=_read, daemon=True)
    thread.start()
    try:
        line = box.get(timeout=timeout_s)
    except queue.Empty:
        raise TimeoutError("recovery child produced no READY line in time")
    if isinstance(line, Exception):
        raise line
    if not line:
        raise RuntimeError("recovery child exited before READY")
    return line


class TestRecoveryResume(unittest.TestCase):
    def test_R1_simulated_kill_resume_to_verdict_no_rework(self):
        with tempfile.TemporaryDirectory() as tmp:
            host = make_host(tmp)
            world = setup(host, StubSearchEngine())
            form_ref = phase_formulate(world)
            run = phase_propose(host, world, form_ref)
            self.assertTrue(run["champion_id"])
            pre_bytes = {r: sha256_file(r)
                         for r in [form_ref, *run["candidate_refs"]]}
            holds_pre = {w: dict(h) for w, h in host.holdings.items()}
            ckpt_entry = host.suspend(WORKER_ID, "host",
                                      reason="R1 kill point",
                                      pending_effects=["score", "verdict"])
            self.assertEqual(ckpt_entry["payload"]["pending_effects"],
                             ["score", "verdict"])
            state_dir, ledger = host.state_dir, host.ledger_path
            del host, world  # simulated kill: no flush, no close, just gone

            host2 = Host.reopen(state_dir, ledger, records=[worker_record(state_dir)],
                                reason="R1 resume after kill")
            self.assertEqual(host2.worlds[WORKER_ID].lifecycle, "suspended")
            reattach_entry = host2.reattach(WORKER_ID, "host", reason="R1 resume")
            self.assertEqual(reattach_entry["payload"]["pending_effects_replayed"],
                             ["score", "verdict"])
            world2 = ExploreWorld(Path(state_dir) / WORKER_ID,
                                  engine=StubSearchEngine())
            report = resume_to_verdict(host2, world2)

            # Verdict reached; completed phases skipped, rest executed once.
            self.assertEqual(report["skipped"], ["formulate", "propose"])
            self.assertEqual(report["executed"], ["score", "verdict"])
            self.assertEqual(report["re_executed_invokes"], 0)
            verdict = json.loads(Path(report["verdict_ref"]).read_text(encoding="utf-8"))
            self.assertEqual(verdict["champion_id"], run["champion_id"])
            # Formulation ref + prior artifacts reused byte-for-byte.
            self.assertEqual(report["formulation_ref"], form_ref)
            self.assertEqual(report["candidate_refs"], run["candidate_refs"])
            for ref, digest in pre_bytes.items():
                self.assertEqual(sha256_file(ref), digest)
            # Exactly one successful invoke per accountable phase (0 rework).
            entries = host2.ledger_entries()
            self.assertEqual(len(successful_invokes(entries, "search.propose")), 1)
            self.assertEqual(len(successful_invokes(entries, "search.score")), 1)
            # No restart: single init, single reopen, worlds never recreated.
            self.assertEqual(count_kind(entries, "host_init"), 1)
            self.assertEqual(count_kind(entries, "host_reopen"), 1)
            self.assertEqual(count_kind(entries, "create"), 1)
            # Only the score invoke billed post-kill (1 invocation).
            self.assertEqual(
                holds_pre[WORKER_ID]["max_invocations"]
                - host2.holdings[WORKER_ID]["max_invocations"], 1)
            self.assertTrue(host2.verify_conservation()["ok"])

    def test_R1_real_sigkill_child_resume_to_verdict(self):
        with tempfile.TemporaryDirectory() as tmp:
            state_dir = str(Path(tmp) / "state")
            ledger = str(Path(tmp) / "ledger.jsonl")
            proc = subprocess.Popen(
                [sys.executable, EXERCISE_SCRIPT, "--child",
                 "--state-dir", state_dir, "--ledger", ledger],
                stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
            try:
                line = _read_ready(proc).strip()
            except Exception:
                proc.kill()
                proc.wait(timeout=30)
                raise
            self.assertTrue(line.startswith("READY "), line)
            form_ref = line.split("form=", 1)[1].split()[0]
            os.kill(proc.pid, signal.SIGKILL)  # the scripted kill-mid-run
            rc = proc.wait(timeout=30)
            _, stderr = proc.communicate(timeout=30)
            self.assertNotIn(rc, (None, 0), f"child exited 0, not killed: {stderr}")
            self.assertTrue(Path(form_ref).exists(), "formulation must survive the kill")

            host2 = Host.reopen(state_dir, ledger,
                                records=[worker_record(Path(state_dir))],
                                reason="R1-real resume after SIGKILL")
            host2.reattach(WORKER_ID, "host", reason="R1-real resume")
            world2 = ExploreWorld(Path(state_dir) / WORKER_ID,
                                  engine=StubSearchEngine())
            report = resume_to_verdict(host2, world2)
            self.assertEqual(report["formulation_ref"], form_ref)
            self.assertEqual(report["re_executed_invokes"], 0)
            verdict = json.loads(Path(report["verdict_ref"]).read_text(encoding="utf-8"))
            self.assertTrue(verdict["champion_id"])
            entries = host2.ledger_entries()
            self.assertEqual(len(successful_invokes(entries, "search.propose")), 1)
            self.assertEqual(len(successful_invokes(entries, "search.score")), 1)
            self.assertEqual(count_kind(entries, "host_init"), 1)
            self.assertEqual(count_kind(entries, "host_reopen"), 1)
            self.assertTrue(host2.verify_conservation()["ok"])


class TestRecoveryRefusals(unittest.TestCase):
    def _suspended(self, tmp: str) -> tuple[Path, Path]:
        host = make_host(tmp)
        world = setup(host, StubSearchEngine())
        form_ref = phase_formulate(world)
        phase_propose(host, world, form_ref)
        host.suspend(WORKER_ID, "host", reason="refusal fixture",
                     pending_effects=["score", "verdict"])
        return Path(host.state_dir), Path(host.ledger_path)

    def test_R2_missing_checkpoint_reattach_refused(self):
        with tempfile.TemporaryDirectory() as tmp:
            state_dir, ledger = self._suspended(tmp)
            (state_dir / WORKER_ID / "checkpoint.json").unlink()
            host2 = Host.reopen(state_dir, ledger, records=[worker_record(state_dir)],
                                reason="R2")
            with self.assertRaisesRegex(ContractViolation, "missing checkpoint"):
                host2.reattach(WORKER_ID, "host", reason="R2")
            last = host2.ledger_entries()[-1]
            self.assertEqual(last["kind"], "deny")
            self.assertIn("missing checkpoint", last["payload"]["reason"])

    def test_R3_checkpoint_identity_mismatch_refused(self):
        for field, bad in (("world_id", "R-impostor"),
                           ("code_ref", "evil/code.py")):
            with tempfile.TemporaryDirectory() as tmp, self.subTest(field=field):
                state_dir, ledger = self._suspended(tmp)
                ckpt_path = state_dir / WORKER_ID / "checkpoint.json"
                ckpt = json.loads(ckpt_path.read_text(encoding="utf-8"))
                ckpt[field] = bad
                ckpt_path.write_text(json.dumps(ckpt, indent=2, sort_keys=True),
                                     encoding="utf-8")
                host2 = Host.reopen(state_dir, ledger,
                                    records=[worker_record(state_dir)], reason="R3")
                with self.assertRaisesRegex(ContractViolation,
                                            "checkpoint identity mismatch"):
                    host2.reattach(WORKER_ID, "host", reason="R3")
                last = host2.ledger_entries()[-1]
                self.assertEqual(last["kind"], "deny")
                self.assertIn("identity mismatch", last["payload"]["reason"])

    def test_R3b_reopen_supply_record_mismatch_refused(self):
        with tempfile.TemporaryDirectory() as tmp:
            state_dir, ledger = self._suspended(tmp)
            bad = worker_record(state_dir)
            bad.code_ref = "evil/code.py"
            with self.assertRaisesRegex(ContractViolation, "does not match ledger"):
                Host.reopen(state_dir, ledger, records=[bad], reason="R3b")
            ghost = WorldRecord(world_id="ghost", lineage=[], code_ref="t",
                                instance_state_dir=str(state_dir / "ghost"),
                                custodians={})
            with self.assertRaisesRegex(ContractViolation, "never created"):
                Host.reopen(state_dir, ledger, records=[ghost], reason="R3b")
            # Denials recorded (each failed reopen appended one deny).
            probe = Host.reopen(state_dir, ledger, reason="R3b probe")
            denies = [e for e in probe.ledger_entries()
                      if e["kind"] == "deny"
                      and e["payload"].get("action") == "reopen"]
            self.assertEqual(len(denies), 2)


class TestSettleOnTerminal(unittest.TestCase):
    def _funded_pair(self, tmp: str) -> Host:
        host = make_host(tmp)
        parent = WorldRecord(world_id="parent", lineage=[], code_ref="t",
                             instance_state_dir=str(Path(host.state_dir) / "parent"),
                             custodians={},
                             authorities=["grant.delegate", "world.create"])
        host.create_world(parent, "host",
                          grant_limits={"max_cost_usd": 4.0, "max_time_s": 200.0,
                                        "max_invocations": 40})
        host.transition("parent", "active", "host", reason="test")
        child = WorldRecord(world_id="child", lineage=[], code_ref="t",
                            instance_state_dir=str(Path(host.state_dir) / "child"),
                            custodians={})
        host.create_world(child, "parent")
        host.transition("child", "active", "parent", reason="test")
        host.grant("parent", "child",
                   {"max_cost_usd": 1.0, "max_time_s": 60.0, "max_invocations": 10},
                   authority=[], grant_id="g-parent-child")
        host.consume("child", cost_usd=0.25, invocations=3, evidence_ref="work")
        return host

    def test_R4_settle_leaves_zero_stranded_holdings(self):
        with tempfile.TemporaryDirectory() as tmp:
            host = self._funded_pair(tmp)
            parent_before = dict(host.holdings["parent"])
            host.transition("child", "dissolved", "parent", reason="R4 done")
            settles = [e for e in host.ledger_entries()
                       if e["kind"] == "grant_settle"]
            self.assertEqual(len(settles), 1)
            self.assertEqual(settles[0]["payload"]["world_id"], "child")
            self.assertEqual(settles[0]["payload"]["grants"], ["g-parent-child"])
            self.assertTrue(all(v == 0 for v in host.holdings["child"].values()))
            # Remainder (0.75 / 60 / 7) flowed back to the grantor.
            self.assertAlmostEqual(
                host.holdings["parent"]["max_cost_usd"]
                - parent_before["max_cost_usd"], 0.75)
            host.transition("child", "retired", "host", reason="R4 archived")
            settles = [e for e in host.ledger_entries()
                       if e["kind"] == "grant_settle"]
            self.assertEqual(len(settles), 2)  # every terminal move settles
            report = host.verify_conservation()
            self.assertTrue(report["ok"])
            self.assertIn("child", report["settled_terminals"])
            self.assertTrue(all(abs(v) < 1e-9
                                for v in report["balances"]["child"].values()))

    def test_R4m_multi_grantor_settle_distributes(self):
        with tempfile.TemporaryDirectory() as tmp:
            host = self._funded_pair(tmp)
            host.grant("host", "child",
                       {"max_cost_usd": 2.0, "max_time_s": 10.0,
                        "max_invocations": 4},
                       authority=[], grant_id="g-host-child")
            host_before = dict(host.holdings["host"])
            parent_before = dict(host.holdings["parent"])
            host.transition("child", "dissolved", "host", reason="R4m done")
            settles = [e for e in host.ledger_entries()
                       if e["kind"] == "grant_settle"
                       and e["payload"]["world_id"] == "child"]
            self.assertEqual(len(settles), 1)
            self.assertEqual(sorted(settles[0]["payload"]["grants"]),
                             ["g-host-child", "g-parent-child"])
            self.assertTrue(all(v == 0 for v in host.holdings["child"].values()))
            # Both grantors got funds back (child held 2.75 cost across grants).
            self.assertGreater(host.holdings["host"]["max_cost_usd"],
                               host_before["max_cost_usd"])
            self.assertGreater(host.holdings["parent"]["max_cost_usd"],
                               parent_before["max_cost_usd"])
            self.assertTrue(host.verify_conservation()["ok"])

    def test_R4n_unsettled_terminal_ledger_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            ledger = Path(tmp) / "ledger.jsonl"
            rows = [
                {"seq": 1, "at": "2026-10-04T00:00:00+00:00", "kind": "host_init",
                 "contract_version": "0", "actor": "host",
                 "payload": {"root_holdings": dict(ROOT_HOLDINGS)}},
                {"seq": 2, "at": "2026-10-04T00:00:01+00:00", "kind": "create",
                 "contract_version": "0", "actor": "host",
                 "payload": {"world_id": "w1", "creator": "host",
                             "code_ref": "t",
                             "instance_state_dir": str(Path(tmp) / "state" / "w1"),
                             "custodians": {}, "authorities": [],
                             "capabilities": [], "representations": [],
                             "lineage": []}},
                {"seq": 3, "at": "2026-10-04T00:00:02+00:00", "kind": "lifecycle",
                 "contract_version": "0", "actor": "host",
                 "payload": {"world_id": "w1", "from": "active",
                             "to": "dissolved", "reason": "hand-written"}},
            ]
            ledger.write_text("".join(json.dumps(r, sort_keys=True) + "\n"
                                      for r in rows), encoding="utf-8")
            host = Host.reopen(Path(tmp) / "state", ledger, reason="R4n probe")
            with self.assertRaisesRegex(ContractViolation, "unsettled terminal"):
                host.verify_conservation()


class TestReopenDescriptors(unittest.TestCase):
    def test_R5_ledger_only_worlds_fail_closed_for_non_host(self):
        with tempfile.TemporaryDirectory() as tmp:
            host = make_host(tmp)
            setup(host, StubSearchEngine())
            state_dir, ledger = Path(host.state_dir), Path(host.ledger_path)
            del host
            host2 = Host.reopen(state_dir, ledger, reason="R5 (no records)")
            caps = host2.worlds[WORKER_ID].capabilities
            self.assertTrue(all(c.required_authority == WITHHELD_AUTHORITY
                                for c in caps))
            with self.assertRaisesRegex(ContractViolation, "recovery.withheld"):
                host2.invoke(WORKER_ID, WORKER_ID, "search.propose", "1.0",
                             "args-r5", lambda: "never")
            last = host2.ledger_entries()[-1]
            self.assertEqual(last["kind"], "deny")
            # Host inspection path stays open (host bypasses authority checks).
            entry = host2.invoke("host", WORKER_ID, "search.propose", "1.0",
                                 "args-r5-host", lambda: "inspected")
            self.assertEqual(entry["payload"]["result_ref"], "inspected")


if __name__ == "__main__":
    unittest.main()
