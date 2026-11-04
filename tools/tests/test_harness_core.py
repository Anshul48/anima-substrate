# Copyright 2026 Anshul48
# SPDX-License-Identifier: Apache-2.0
"""Harness adapter tests (unittest, stdlib-only). No real coding agent is called:
fake hands (small python scripts) stand in, so these run anywhere.

    PYTHONPATH=. python3 -m unittest tests.test_harness_core -v
"""
from __future__ import annotations

import hashlib
import importlib.util
import json
import os
import shutil
import sys
import tempfile
import textwrap
import time
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from anima.harness import adapters, chain, miniyaml, rules  # noqa: E402
from anima.harness.ladder import GATE, load_task, run_task  # noqa: E402
from anima.harness.profile import Profile, build_default  # noqa: E402

FAKE = textwrap.dedent('''
    import pathlib, sys
    mode, ws, prompt = sys.argv[1], pathlib.Path(sys.argv[2]), pathlib.Path(sys.argv[3]).read_text()
    f = ws / "src" / "statslite" / "window.py"
    FIXED = (
        "def moving_average(values, window):\\n"
        "    if window <= 0:\\n        raise ValueError('window')\\n"
        "    return [sum(values[i:i+window]) / window for i in range(len(values) - window + 1)]\\n")
    fix = mode == "fix" or (mode == "fix-on-retry" and "Previous attempt" in prompt)
    if fix:
        f.write_text(FIXED)
    if mode == "edit-tests":
        f.write_text(FIXED)
        t = ws / "tests" / "test_basic.py"
        t.write_text(t.read_text() + "\\n# tampered\\n")
    print("done: " + mode)
''')

CONTRACT_A = """
version: 1
harness: muse
memory: {kind: trace, store: .anima/trace, write: [decisions, failures]}   # comment
enforce: {mode: warn, via: wrapper}
roles:
  worker:
    model: {name: muse-spark-1.3, effort: max}
    may: [read_workspace, write_workspace, run_tests]
    budget: {timeout_s: 3000, attempts: 3}
watches:
  - {name: stall,  every: 60s, check: no_output_for 1200s, action: restart_worker, mode: shadow}
  - {name: budget, every: 5m,  check: spent_pct > 90,      action: warn_manager}
ladder:                      # first match wins
  - {on: gate_fail, do: retry_with_failure_line, times: 1}
  - {on: gate_fail, do: run_with, harness: claude}
  - {on: still_failing, do: ask, role: architect}
"""


class MiniYaml(unittest.TestCase):
    def test_contract_example_parses_and_roundtrips(self):
        d = miniyaml.loads(CONTRACT_A)
        self.assertEqual(d["roles"]["worker"]["model"]["effort"], "max")
        self.assertEqual(d["watches"][1]["check"], "spent_pct > 90")
        self.assertEqual(d["ladder"][0]["times"], 1)
        self.assertEqual(miniyaml.loads(miniyaml.dumps(d)), d)

    def test_rejects_what_it_cannot_read(self):
        for bad in ("a: &x 1\n", "a:\n\tb: 1\n", "a: {b: [1,\n", "a: 1\na: 2\n", "- a: 1\n  b: 2\n"):
            with self.assertRaises(miniyaml.YamlError, msg=bad):
                miniyaml.loads(bad)

    def test_scalars(self):
        d = miniyaml.loads("a: true\nb: ~\nc: 3\nd: '1.5'\ne: \"x: y\"\nf: /usr/bin/x y\n")
        self.assertEqual(d, {"a": True, "b": None, "c": 3, "d": "1.5", "e": "x: y", "f": "/usr/bin/x y"})
        self.assertEqual(miniyaml.loads(miniyaml.dumps({"s": "true", "n": "12", "p": "a b"})), {"s": "true", "n": "12", "p": "a b"})

    def test_json_is_accepted(self):
        self.assertEqual(miniyaml.loads('{"version": 1}'), {"version": 1})


class Rules(unittest.TestCase):
    def test_blocks(self):
        for cmd, rule in (("cat ~/.ssh/id_ed25519", "SECRETS-READ"), ("cat /home/u/.config/muse/auth.json", "SECRETS-READ"),
                          ("env", "SECRETS-ENV-DUMP"), ("sudo apt install x", "SUDO-NEVER"), ("git push origin main", "GIT-PUSH"),
                          ("git -C repo push --force", "GIT-PUSH"), ("rm -rf ~", "RM-ROOT-HOME"), ("gh pr create", "GH-PUBLISH")):
            v = rules.check_command(cmd)
            self.assertFalse(v.allowed, cmd)
            self.assertEqual(v.rule, rule, cmd)

    def test_allows(self):
        for cmd in ("python3 -m unittest", "git status", "git diff HEAD", "ls src", "cat src/app.py", "env FOO=1 python3 x.py",
                    "rm -rf build", "echo pushing forward"):
            self.assertTrue(rules.check_command(cmd).allowed, cmd)

    def test_hook(self):
        code, msg = rules.hook_decision(json.dumps({"tool_name": "Bash", "tool_input": {"command": "cat ~/.ssh/nope"}}))
        self.assertEqual(code, 2)
        self.assertIn("SECRETS-READ", msg)
        self.assertEqual(rules.hook_decision(json.dumps({"tool_name": "Bash", "tool_input": {"command": "ls"}}))[0], 0)
        self.assertEqual(rules.hook_decision("not json")[0], 0)


class Chain(unittest.TestCase):
    def test_chain_and_tamper_and_repo_checker(self):
        with tempfile.TemporaryDirectory() as tmp:
            p = Path(tmp) / "decisions.jsonl"
            c = chain.Chain(p)
            c.append("heartbeat", "", status="x")
            c.append("task.created", "t1", pool="a")
            c.append("task.done", "t1", ok=True)
            c.write_head()
            ok, why, n, _ = chain.verify(p)
            self.assertTrue(ok, why)
            self.assertEqual(n, 3)
            # the repository's own checker (written for the recorded run) reads our file too
            spec = importlib.util.spec_from_file_location("cc", ROOT / "docs/evidence/flagship-run3/check_chain.py")
            if (ROOT / "docs/evidence/flagship-run3/check_chain.py").exists():
                cc = importlib.util.module_from_spec(spec)
                spec.loader.exec_module(cc)
                self.assertTrue(cc.check(p)[0])
            lines = p.read_bytes().split(b"\n")
            lines[1] = lines[1].replace(b"task.created", b"task.createX")
            p.write_bytes(b"\n".join(lines))
            self.assertFalse(chain.verify(p)[0])

    def test_resume_appends_to_existing_chain(self):
        with tempfile.TemporaryDirectory() as tmp:
            p = Path(tmp) / "d.jsonl"
            chain.Chain(p).append("heartbeat", "")
            chain.Chain(p).append("heartbeat", "")
            self.assertEqual(chain.verify(p)[2], 2)
            self.assertTrue(chain.verify(p)[0])


class AdapterShapes(unittest.TestCase):
    def build(self, kind, role, **cfg):
        ad = adapters.make_adapter(kind, {"kind": kind, "bin": kind, **cfg})
        return ad.build(role, "/w", "/w/p.txt", "/w/out.txt", "j")

    def test_muse(self):
        w = self.build("muse", "worker", model="muse-spark-1.3", effort="max").argv
        self.assertEqual(w[1:3], ["exec", "--json"])
        self.assertIn("--prompt-file", w)
        self.assertIn("--approval-mode", w)
        self.assertNotIn("--yolo", w)
        a = self.build("muse", "architect").argv
        self.assertIn("--disable-write", a)
        self.assertIn("--disable-shell", a)
        self.assertIn("--yolo", self.build("muse", "worker", yolo=True).argv)

    def test_claude(self):
        w = self.build("claude", "worker", model="claude-sonnet-5-5")
        self.assertIn("acceptEdits", w.argv)
        self.assertEqual(w.stdin_file, "/w/p.txt")
        a = self.build("claude", "architect").argv
        self.assertEqual(a[a.index("--permission-mode") + 1], "plan")
        self.assertEqual(a[a.index("--tools") + 1], "Read,Glob,Grep")
        h = self.build("claude", "worker", hook_cmd="x check --hook").argv
        self.assertIn("PreToolUse", h[h.index("--settings") + 1])

    def test_codex(self):
        w = self.build("codex", "worker").argv
        self.assertEqual(w[w.index("-s") + 1], "workspace-write")
        self.assertEqual(w[-1], "-")
        a = self.build("codex", "architect").argv
        self.assertEqual(a[a.index("-s") + 1], "read-only")

    def test_prompt_never_in_argv_and_env_scrubbed(self):
        os.environ["FOO_API_KEY"] = "sk-not-real"
        os.environ["SOME_TOKEN"] = "x"
        try:
            inv = self.build("claude", "worker")
            self.assertNotIn("FOO_API_KEY", inv.env)
            self.assertNotIn("SOME_TOKEN", inv.env)
            self.assertIn("PATH", inv.env)
            with self.assertRaises(adapters.HarnessError):
                adapters.scrubbed_env("claude", ["MY_API_KEY"])
        finally:
            del os.environ["FOO_API_KEY"], os.environ["SOME_TOKEN"]

    def test_custom_template_validation(self):
        with self.assertRaises(adapters.HarnessError):
            adapters.make_adapter("c", {"kind": "custom", "argv": ["x", "{nope}"]})
        with self.assertRaises(adapters.HarnessError):
            adapters.make_adapter("c", {"kind": "custom", "argv": ["x", "--api-key", "k"]})
        ad = adapters.make_adapter("c", {"kind": "custom", "argv": ["x", "{workspace}", "{prompt_file}"]})
        self.assertEqual(ad.build("worker", "/w", "/p", "/o").argv, ["x", "/w", "/p"])


class Parsers(unittest.TestCase):
    def write(self, rows):
        d = Path(tempfile.mkdtemp())
        p = d / "stdout.log"
        p.write_text("\n".join(json.dumps(r) for r in rows) + "\n")
        return d, str(p)

    def test_muse_events(self):
        d, p = self.write([
            {"payload_type": "run.output.delta", "stream": {"id": "s1"}, "payload": {"text": "Fixed "}},
            {"payload_type": "run.output.delta", "payload": {"text": "it."}},
            {"payload_type": "run.usage", "payload": {"calls": 3}},
        ])
        r = adapters.make_adapter("muse", {"kind": "muse"}).parse("worker", p, str(d / "o.txt"), 0)
        self.assertTrue(r.ok)
        self.assertEqual(r.summary, "Fixed it.")
        self.assertEqual(r.usage, {"calls": 3})

    def test_claude_events(self):
        d, p = self.write([{"type": "system", "model": "m1"},
                           {"type": "result", "result": "all done", "is_error": False, "total_cost_usd": 0.05, "num_turns": 4, "session_id": "z"}])
        r = adapters.make_adapter("claude", {"kind": "claude"}).parse("worker", p, str(d / "o.txt"), 0)
        self.assertTrue(r.ok)
        self.assertEqual((r.cost_usd, r.turns, r.model_seen), (0.05, 4, "m1"))
        d, p = self.write([{"type": "result", "result": "boom", "is_error": True}])
        self.assertFalse(adapters.make_adapter("claude", {"kind": "claude"}).parse("worker", p, str(d / "o.txt"), 1).ok)

    def test_codex_events(self):
        d, p = self.write([{"type": "thread.started", "thread_id": "t9"},
                           {"type": "item.completed", "item": {"type": "agent_message", "text": "finished"}}])
        r = adapters.make_adapter("codex", {"kind": "codex"}).parse("worker", p, str(d / "o.txt"), 0)
        self.assertTrue(r.ok)
        self.assertEqual((r.summary, r.session_id), ("finished", "t9"))


class Ladder(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp(prefix="anima-test-"))
        self.hand = self.tmp / "fake_hand.py"
        self.hand.write_text(FAKE)

    def tearDown(self):
        shutil.rmtree(self.tmp, ignore_errors=True)

    def profile(self, modes):
        hs = {}
        for name, mode in modes.items():
            hs[name] = {"kind": "custom", "argv": [sys.executable, str(self.hand), mode, "{workspace}", "{prompt_file}"],
                        "architect_argv": [sys.executable, "-c", "print('1. fix window.py')"], "timeout_s": 60}
        first = next(iter(modes))
        steps = [{"on": "gate_fail", "do": "run_with", "harness": n} for n in list(modes)[1:]]
        steps.append({"on": "still_failing", "do": "ask", "role": "architect"})
        return Profile({"version": 1, "harness": first, "harnesses": hs, "enforce": {"mode": "warn", "via": "wrapper"},
                        "rules": ["secrets"], "ladder": steps})

    def events(self, outcome):
        return [json.loads(x) for x in outcome.chain_path.read_text().splitlines()]

    def test_gate_accepts_a_real_fix(self):
        o = run_task(self.profile({"a": "fix"}), load_task("tiny-bug"), self.tmp / "runs", harness="a", say=lambda *_: None)
        self.assertEqual(o.verdict, "PASS")
        self.assertTrue(chain.verify(o.chain_path)[0])
        self.assertEqual(self.events(o)[0]["data"]["mode"], "CUSTOM")  # a fake hand is never labelled REAL

    def test_gate_rejects_noop(self):
        o = run_task(self.profile({"a": "noop"}), load_task("tiny-bug"), self.tmp / "runs", harness="a", say=lambda *_: None)
        self.assertEqual(o.verdict, "FAIL")
        self.assertEqual(o.final.failed_rule, "target-tests")

    def test_gate_rejects_test_tampering(self):
        o = run_task(self.profile({"a": "edit-tests"}), load_task("tiny-bug"), self.tmp / "runs", harness="a", say=lambda *_: None)
        self.assertEqual(o.verdict, "FAIL")
        self.assertEqual(o.final.failed_rule, "tests-untouched")

    def test_escalation_passes_failure_line_and_records_decision(self):
        o = run_task(self.profile({"a": "noop", "b": "fix-on-retry"}), load_task("tiny-bug"), self.tmp / "runs", say=lambda *_: None)
        self.assertEqual(o.verdict, "PASS")
        self.assertEqual([a.harness for a in o.attempts], ["a", "b"])
        prompt = (Path(o.attempts[1].dir) / "prompt.txt").read_text()
        self.assertIn("Previous attempt (a) failed gate: target-tests", prompt)
        kinds = [e["kind"] for e in self.events(o)]
        self.assertIn("task.blocked", kinds)
        esc = [e for e in self.events(o) if e["kind"] == "decision.made"][0]["data"]
        self.assertEqual((esc["decision"], esc["from_pool"], esc["to_pool"]), ("escalate", "a", "b"))
        self.assertTrue(chain.verify(o.chain_path)[0])

    def test_exhausted_ladder_asks_architect(self):
        o = run_task(self.profile({"a": "noop", "b": "noop"}), load_task("tiny-bug"), self.tmp / "runs", say=lambda *_: None)
        self.assertEqual(o.verdict, "FAIL")
        last = self.events(o)[-1]["data"]
        self.assertEqual((last["decision"], last["role"]), ("ask", "architect"))

    def test_plan_first_gives_architect_plan_to_worker_and_proves_read_only(self):
        o = run_task(self.profile({"a": "fix"}), load_task("tiny-bug"), self.tmp / "runs", harness="a", plan_first=True, say=lambda *_: None)
        self.assertEqual(o.verdict, "PASS")
        self.assertIn("1. fix window.py", (Path(o.attempts[0].dir) / "prompt.txt").read_text())
        art = [e for e in self.events(o) if e["kind"] == "artifact.added" and e["data"].get("name") == "plan.md"][0]
        self.assertTrue(art["data"]["read_only_respected"])

    def test_hand_that_cannot_start_is_not_run(self):
        prof = Profile({"version": 1, "harness": "x", "harnesses": {"x": {"kind": "custom", "argv": ["/nonexistent/tool", "{workspace}"]}}})
        o = run_task(prof, load_task("tiny-bug"), self.tmp / "runs", harness="x", say=lambda *_: None)
        self.assertEqual(o.verdict, "NOT RUN")
        self.assertEqual(o.final.failure_class, "not_found")

    def test_two_runs_in_the_same_second_get_separate_folders(self):
        prof = self.profile({"a": "noop"})
        a = run_task(prof, load_task("tiny-bug"), self.tmp / "runs", harness="a", say=lambda *_: None)
        b = run_task(prof, load_task("tiny-bug"), self.tmp / "runs", harness="a", say=lambda *_: None)
        self.assertNotEqual(a.run_dir, b.run_dir)
        self.assertTrue(chain.verify(a.chain_path)[0] and chain.verify(b.chain_path)[0])

    def test_login_problem_is_reported_in_the_cli_s_own_words(self):
        prof = Profile({"version": 1, "harness": "x", "harnesses": {"x": {"kind": "custom", "argv": [
            sys.executable, "-c",
            "import sys; sys.stderr.write('ERROR codex_login: refresh token was already used. Please log out and sign in again.\\n'); sys.exit(1)"]}}})
        o = run_task(prof, load_task("tiny-bug"), self.tmp / "runs", harness="x", say=lambda *_: None)
        self.assertEqual(o.verdict, "NOT RUN")
        self.assertEqual(o.final.failure_class, "auth_quota")
        self.assertIn("log out and sign in again", o.final.note)

    def test_gate_file_is_the_recorded_one(self):
        self.assertEqual(hashlib.sha256(GATE.read_bytes()).hexdigest(),
                         "0ac9c39c7e93f907c68e9aa2387521b2c1e34ef73e17c842e0ec8bb311e6b424")


class Watch(unittest.TestCase):
    def run_watch(self, script, mode, stall_s=None, stall_mode="shadow"):
        d = Path(tempfile.mkdtemp())
        ad = adapters.make_adapter("c", {"kind": "custom", "argv": ["sh", "-c", script]})
        res = ad.run("worker", str(d), str(d / "p"), str(d / "r"),
                     timeout_s=20, watch={"packs": ["push-public", "secrets"], "mode": mode, "stall_s": stall_s, "stall_mode": stall_mode})
        return res, d / "r" / "watch.jsonl"

    def test_enforce_kills_on_forbidden_command(self):
        t0 = time.time()
        res, log = self.run_watch("sh -c 'git push nowhere >/dev/null 2>&1; sleep 15'; true", "enforce")
        self.assertLess(time.time() - t0, 10)
        self.assertFalse(res.ok)
        self.assertEqual(res.failure_class, "watch_blocked")
        self.assertIn("GIT-PUSH", log.read_text())

    def test_enforce_sees_and_kills_a_child_in_its_own_session(self):
        # Muse starts each shell command in a new session (probe in RUN-LOG); the session-only scan missed it.
        if not shutil.which("setsid"):
            self.skipTest("setsid not available")
        t0 = time.time()
        res, log = self.run_watch("setsid sh -c 'git push nowhere >/dev/null 2>&1; sleep 15' & wait", "enforce")
        self.assertLess(time.time() - t0, 10)
        self.assertEqual(res.failure_class, "watch_blocked")
        self.assertIn("GIT-PUSH", log.read_text())

    def test_warn_logs_but_does_not_kill(self):
        res, log = self.run_watch("sh -c 'git push nowhere >/dev/null 2>&1; sleep 1'; true", "warn")
        self.assertTrue(res.ok or res.returncode == 0)
        self.assertEqual(json.loads(log.read_text().splitlines()[0])["action"], "would_kill")

    def test_stall_enforce_kills_and_shadow_only_logs(self):
        res, log = self.run_watch("sleep 15", "warn", stall_s=1, stall_mode="enforce")
        self.assertEqual(res.failure_class, "watch_blocked")
        self.assertIn('"kind": "stall"', log.read_text())
        res, log = self.run_watch("sleep 3", "warn", stall_s=1, stall_mode="shadow")
        self.assertTrue(res.watch["stalled"])
        self.assertFalse(res.watch["killed"])


class Profiles(unittest.TestCase):
    def test_default_profile_order_muse_first(self):
        d = build_default({"codex": "/c", "muse": "/m", "claude": "/cl"})
        self.assertEqual(d["harness"], "muse")
        self.assertEqual([s.get("harness") for s in d["ladder"] if s["do"] == "run_with"], ["claude", "codex"])
        self.assertEqual(build_default({"codex": "/c"})["harness"], "codex")
        self.assertIsNone(build_default({})["harness"])

    def test_roles_and_ladder(self):
        p = Profile(miniyaml.loads(CONTRACT_A))
        self.assertEqual(p.adapter_mode("worker"), "worker")
        self.assertEqual(p.adapter_mode("architect"), "architect")
        plan = p.attempt_plan("muse")
        self.assertEqual([s.get("how") or "ask" for s in plan], ["first", "retry", "run_with", "ask"])
        self.assertEqual(p.watch_cfg("worker")["stall_s"], 1200)
        self.assertIn("watches.budget", p.not_enforced())


class Cli(unittest.TestCase):
    def setUp(self):
        from unittest import mock
        self.tmp = Path(tempfile.mkdtemp(prefix="anima-cli-"))
        self.bin = self.tmp / "bin"
        self.bin.mkdir()
        self.env = mock.patch.dict(os.environ, {"HOME": str(self.tmp), "ANIMA_HOME": str(self.tmp / "ah"), "PATH": str(self.bin),
                                                 "ANIMA_PROFILE": ""}, clear=False)
        self.env.start()
        os.environ.pop("ANIMA_PROFILE", None)
        self.cwd = os.getcwd()
        os.chdir(self.tmp)

    def tearDown(self):
        os.chdir(self.cwd)
        self.env.stop()
        shutil.rmtree(self.tmp, ignore_errors=True)

    def fake_cli(self, name):
        f = self.bin / name
        f.write_text("#!/bin/sh\necho %s 9.9\n" % name)
        f.chmod(0o755)

    def main(self, *argv):
        from io import StringIO
        from contextlib import redirect_stdout, redirect_stderr
        from anima.harness import cli
        buf = StringIO()
        with redirect_stdout(buf), redirect_stderr(buf):
            code = cli.main(list(argv))
        return code, buf.getvalue()

    def test_doctor_label_never_calls_a_login_problem_a_failure(self):
        from anima.harness.cli import doctor_label
        rec = lambda *st: {"when": "T", "live": {f"r{i}": {"status": x} for i, x in enumerate(st)}}
        self.assertEqual(doctor_label(False, {}), "READY (not live-tested)")
        self.assertEqual(doctor_label(True, {}), "NOT RUN")
        self.assertEqual(doctor_label(False, rec("PASS", "PASS")), "PASS (live, T)")
        self.assertEqual(doctor_label(False, rec("NOT RUN", "NOT RUN")), "NOT RUN (live, T)")
        self.assertEqual(doctor_label(False, rec("PASS", "NOT RUN")), "NOT RUN (live, T)")
        self.assertEqual(doctor_label(False, rec("PASS", "FAIL")), "FAIL (live, T)")

    def test_add_custom_rejects_a_non_list_argv_cleanly(self):
        code, text = self.main("harness", "add", "custom", "--name", "bad", "--argv", "true")
        self.assertNotEqual(code, 0)
        self.assertIn("must be a JSON list of strings", text)
        self.assertNotIn("Traceback", text)

    def test_check_exit_codes(self):
        self.assertEqual(self.main("check", "--cmd", "git push origin main")[0], 3)
        self.assertEqual(self.main("check", "--cmd", "ls src")[0], 0)

    def test_init_finds_the_three_clis_muse_first_and_is_idempotent(self):
        for n in ("codex", "claude", "muse"):
            self.fake_cli(n)
        code, text = self.main("init")
        self.assertEqual(code, 0)
        self.assertLess(text.index("muse"), text.index("claude"))
        prof = Profile(miniyaml.loads((self.tmp / "ah" / "anima.yaml").read_text()))
        self.assertEqual(prof.main, "muse")
        self.assertEqual(prof.names(), ["muse", "claude", "codex"])
        before = (self.tmp / "ah" / "anima.yaml").read_text()
        code, text = self.main("init")
        self.assertIn("kept as it is", text)
        self.assertEqual((self.tmp / "ah" / "anima.yaml").read_text(), before)

    def test_init_with_nothing_installed_and_doctor_says_not_run(self):
        code, text = self.main("init")
        self.assertEqual(code, 0)
        self.assertIn("no harness found", text)
        code, text = self.main("doctor")
        self.assertEqual(code, 0)
        self.assertIn("NOT RUN", text)
        self.assertNotIn("PASS (live", text)

    def test_add_custom_and_list_and_dry_run(self):
        code, text = self.main("harness", "add", "custom", "--name", "mine", "--argv",
                               json.dumps([sys.executable, "-c", "print(1)", "{prompt_file}"]), "--stdin", "prompt_file")
        self.assertEqual(code, 0, text)
        code, text = self.main("harness", "list", "--fast")
        self.assertIn("mine", text)
        code, text = self.main("run", "--harness", "mine", "--task", "tiny-bug", "--dry-run")
        self.assertEqual(code, 2)
        self.assertIn("DRY RUN", text)
        self.assertEqual(self.main("harness", "add", "muse")[0], 2)  # not installed here -> clear error, nothing written

    def test_unknown_group_is_reported(self):
        self.assertEqual(self.main("nosuchgroup")[0], 64)


if __name__ == "__main__":
    unittest.main()
