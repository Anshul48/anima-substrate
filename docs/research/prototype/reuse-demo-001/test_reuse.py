"""Unittest suite for reuse-demo-001 (stdlib-only, offline, $0).

Proves MiniHost (a NEW host, zero w1-harden imports) can consume the
w1-harden recovery capability: the tests drive the REUSED
recovery_lib.resume_to_verdict (+ phase_*/successful_invokes helpers)
through MiniHost, plus cover settle/refusal paths natively.
"""
import json
import os
import signal
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from minihost import (ContractViolation, MiniCapability, MiniHost,
                      MiniRepresentation, MiniWorld, MiniWorldRecord)
from reuse_demo import (GRANT_LIMITS, artifact_shas, invoke_counts,
                        setup_worker)
from w1h_bridge import load_recovery_lib


class ReuseCase(unittest.TestCase):
    def setUp(self):
        self.rl = load_recovery_lib()
        self.tmp = Path(tempfile.mkdtemp(prefix="reuse-test-"))
        self.addCleanup(lambda: None)  # state kept for inspection on failure

    def fresh(self, name="main"):
        root = self.tmp / name
        host = MiniHost(root / "state", root / "ledger.jsonl")
        world = setup_worker(host, self.rl)
        return root, host, world

    # -- (a) kill-mid-run ------------------------------------------------
    def test_1_drop_kill_resumes_with_zero_reexecuted_invokes(self):
        root, host, world = self.fresh()
        form_ref = self.rl.phase_formulate(world)
        self.rl.phase_propose(host, world, form_ref)
        before_shas = artifact_shas(world)
        before_inv = invoke_counts(host)
        del host, world
        host2 = MiniHost.reopen(
            root / "state", root / "ledger.jsonl",
            records=[MiniWorldRecord(
                world_id=self.rl.WORKER_ID, lineage=[],
                code_ref=self.rl.WORKER_CODE_REF,
                instance_state_dir=str(root / "state" / self.rl.WORKER_ID),
                capabilities=[MiniCapability("search.propose", "1.0"),
                              MiniCapability("search.score", "1.0")],
                representations=[MiniRepresentation("minihost-run", "v0")],
                authorities=["search.sst"])])
        world2 = MiniWorld(root / "state" / self.rl.WORKER_ID)
        report = self.rl.resume_to_verdict(host2, world2)
        self.assertEqual(report["re_executed_invokes"], 0)
        self.assertIn("propose", report["skipped"])
        self.assertEqual(invoke_counts(host2)["search.propose"],
                         before_inv["search.propose"])
        after = artifact_shas(world2)
        for name, digest in before_shas.items():
            self.assertEqual(after[name], digest, f"{name} changed across kill")
        self.assertTrue(Path(report["verdict_ref"]).exists())

    @unittest.skipUnless(hasattr(signal, "SIGKILL"), "needs POSIX SIGKILL")
    def test_2_sigkill_subprocess_resumes_with_zero_reexecuted_invokes(self):
        root = self.tmp / "sigkill"
        demo = str(Path(__file__).resolve().parent / "reuse_demo.py")
        proc = subprocess.run(
            [sys.executable, demo, "--child-partial", str(root)],
            capture_output=True, text=True)
        self.assertEqual(proc.returncode, -signal.SIGKILL,
                         f"rc={proc.returncode} err={proc.stderr[-300:]}")
        wdir = root / "state" / self.rl.WORKER_ID
        pre = {f.name: MiniHost.sha256_file(str(f))
               for sub in ("formulations", "candidates")
               for f in sorted((wdir / sub).glob("*.json"))}
        self.assertTrue(pre, "SIGKILLed child left no artifacts")
        host = MiniHost.reopen(
            root / "state", root / "ledger.jsonl",
            records=[MiniWorldRecord(
                world_id=self.rl.WORKER_ID, lineage=[],
                code_ref=self.rl.WORKER_CODE_REF,
                instance_state_dir=str(wdir),
                capabilities=[MiniCapability("search.propose", "1.0"),
                              MiniCapability("search.score", "1.0")],
                representations=[MiniRepresentation("minihost-run", "v0")],
                authorities=["search.sst"])])
        report = self.rl.resume_to_verdict(host, MiniWorld(wdir))
        self.assertEqual(report["re_executed_invokes"], 0)
        self.assertIn("propose", report["skipped"])
        post = artifact_shas(MiniWorld(wdir))
        for name, digest in pre.items():
            self.assertEqual(post[name], digest)

    def test_3_second_resume_skips_everything(self):
        root, host, world = self.fresh()
        first = self.rl.resume_to_verdict(host, world)
        self.assertTrue(Path(first["verdict_ref"]).exists())
        n_inv = len([e for e in host.ledger_entries()
                     if e.get("kind") == "invoke"])
        second = self.rl.resume_to_verdict(host, world)
        self.assertEqual(second["executed"], [])
        self.assertEqual(second["re_executed_invokes"], 0)
        self.assertEqual(len([e for e in host.ledger_entries()
                              if e.get("kind") == "invoke"]), n_inv)

    def test_4_failed_invoke_is_not_reused_as_success(self):
        root, host, world = self.fresh()
        args = host.store_args(self.rl.WORKER_ID, "r-bad", {"x": 1})

        def boom():
            raise RuntimeError("kaboom")

        with self.assertRaises(RuntimeError):
            host.invoke(self.rl.WORKER_ID, self.rl.WORKER_ID,
                        "search.score", "1.0", args, boom)
        entries = host.ledger_entries()
        # Reused matcher: error entries are excluded from resume proof.
        self.assertEqual(self.rl.successful_invokes(entries, "search.score"), [])
        self.assertIn("error", entries[-1]["payload"])

    # -- (b) settle ------------------------------------------------------
    def test_5_terminal_settle_leaves_zero_stranded_holdings(self):
        root, host, world = self.fresh()
        self.rl.resume_to_verdict(host, world)
        host.transition(self.rl.WORKER_ID, "dissolved", "host", reason="t5")
        held = host.holdings[self.rl.WORKER_ID]
        self.assertTrue(all(v == 0 for v in held.values()), held)
        rep = host.verify_conservation()
        self.assertTrue(rep["ok"])
        self.assertIn(self.rl.WORKER_ID, rep["settled_terminals"])
        # Ledger order is settle-then-move: grant_settle precedes lifecycle.
        kinds = [(e["kind"], e["payload"].get("world_id"))
                 for e in host.ledger_entries()]
        settle_i = kinds.index(("grant_settle", self.rl.WORKER_ID))
        life_i = next(i for i, (k, w) in enumerate(kinds)
                      if k == "lifecycle" and w == self.rl.WORKER_ID
                      and host.ledger_entries()[i]["payload"]["to"] == "dissolved")
        self.assertLess(settle_i, life_i)

    def test_6_handwritten_unsettled_terminal_ledger_rejected(self):
        bad = self.tmp / "bad.jsonl"
        rows = [
            {"seq": 1, "at": "t", "kind": "host_init",
             "contract_version": "0", "actor": "host",
             "payload": {"root_holdings": {"max_cost_usd": 1.0,
                                           "max_time_s": 10.0,
                                           "max_invocations": 5}}},
            {"seq": 2, "at": "t", "kind": "create",
             "contract_version": "0", "actor": "host",
             "payload": {"world_id": "w", "creator": "host", "code_ref": "x",
                         "instance_state_dir": str(self.tmp / "bs" / "w"),
                         "custodians": {}, "authorities": [],
                         "capabilities": [], "representations": [],
                         "lineage": []}},
            {"seq": 3, "at": "t", "kind": "lifecycle",
             "contract_version": "0", "actor": "host",
             "payload": {"world_id": "w", "from": "active",
                         "to": "dissolved", "reason": "no settle"}},
        ]
        bad.write_text("".join(json.dumps(r, sort_keys=True) + "\n" for r in rows),
                       encoding="utf-8")
        host = MiniHost.reopen(self.tmp / "bs", bad, reason="t6")
        with self.assertRaisesRegex(ContractViolation, "unsettled terminal"):
            host.verify_conservation()

    # -- (c) refusals ----------------------------------------------------
    def test_7_reattach_missing_checkpoint_refused_with_deny(self):
        root, host, world = self.fresh()
        host.suspend(self.rl.WORKER_ID, "host", "t7", pending_effects=["score"])
        (Path(world.state_dir) / "checkpoint.json").unlink()
        with self.assertRaisesRegex(ContractViolation, "missing checkpoint"):
            host.reattach(self.rl.WORKER_ID, "host", "t7")
        denies = [e for e in host.ledger_entries()
                  if e.get("kind") == "deny"
                  and e["payload"].get("action") == "reattach"]
        self.assertTrue(any("missing checkpoint" in d["payload"]["reason"]
                            for d in denies))

    def test_8_reattach_identity_mismatch_refused_with_deny(self):
        root, host, world = self.fresh()
        host.suspend(self.rl.WORKER_ID, "host", "t8", pending_effects=[])
        ckpt = Path(world.state_dir) / "checkpoint.json"
        doc = json.loads(ckpt.read_text(encoding="utf-8"))
        doc["code_ref"] = "evil/fork"
        ckpt.write_text(json.dumps(doc, indent=2, sort_keys=True), encoding="utf-8")
        with self.assertRaisesRegex(ContractViolation, "identity mismatch"):
            host.reattach(self.rl.WORKER_ID, "host", "t8")
        denies = [e for e in host.ledger_entries()
                  if e.get("kind") == "deny"
                  and e["payload"].get("action") == "reattach"]
        self.assertTrue(any("identity mismatch" in d["payload"]["reason"]
                            for d in denies))

    def test_9_reused_resume_refuses_unknown_worker_with_deny(self):
        root = self.tmp / "empty"
        host = MiniHost(root / "state", root / "ledger.jsonl")
        world = MiniWorld(root / "state" / "ghost")
        with self.assertRaisesRegex(Exception, "unknown worker"):
            self.rl.resume_to_verdict(host, world)
        denies = [e for e in host.ledger_entries()
                  if e.get("kind") == "deny"]
        self.assertTrue(any(d["payload"].get("action") == "resume"
                            for d in denies))

    # -- structural: the new host is genuinely separate ------------------
    def test_10_minihost_has_no_w1harden_imports(self):
        src = (Path(__file__).resolve().parent / "minihost.py").read_text(
            encoding="utf-8")
        imports = [ln for ln in src.splitlines()
                   if ln.startswith("import ") or ln.startswith("from ")]
        blob = "\n".join(imports)
        for banned in ("w1-harden", "w1h", "recovery_lib", "HOST"):
            self.assertNotIn(banned, blob, f"import line mentions {banned}")
        stdlib = {"__future__", "hashlib", "json", "os", "dataclasses",
                  "datetime", "pathlib"}
        for ln in imports:
            mod = ln.replace("from ", "").replace("import ", "").split()[0]
            self.assertIn(mod.split(".")[0], stdlib, f"non-stdlib import: {ln}")


if __name__ == "__main__":
    unittest.main(verbosity=2)
