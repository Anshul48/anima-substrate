# Copyright 2026 Anshul48
# SPDX-License-Identifier: Apache-2.0
"""Tests for the SST screen's data layer, commands and server.  Run from the repo root:

    python3 -m unittest discover -s anima/ui/tests -t . -v
"""
import hashlib
import http.client
import json
import os
import tempfile
import threading
import unittest
from http.server import ThreadingHTTPServer
from pathlib import Path

from anima.ui import commands, model, server, source, textmode

CHAIN = source.DEMO_CHAIN


class ChainTests(unittest.TestCase):
    def test_real_record_chain_ok(self):
        events, v = model.read_chain(CHAIN)
        self.assertTrue(v["ok"])
        self.assertEqual(v["records"], 69)
        self.assertTrue(v["head_match"])
        self.assertTrue(all(e["link_ok"] for e in events))

    def test_tamper_is_reported_at_the_right_line(self):
        lines = CHAIN.read_bytes().split(b"\n")
        victim = bytearray(lines[5])
        i = victim.index(b'"kind":"') + 8
        victim[i] = ord("X")
        lines[5] = bytes(victim)
        with tempfile.TemporaryDirectory() as d:
            p = Path(d) / "decisions.jsonl"
            p.write_bytes(b"\n".join(lines))
            events, v = model.read_chain(p)
        self.assertFalse(v["ok"])
        self.assertEqual(v["broken_at"], 7)  # same line check_chain.py reports
        self.assertFalse(events[6]["link_ok"])


class TreeTests(unittest.TestCase):
    def setUp(self):
        self.src = source.Source.from_args(demo=True)

    def test_final_tree_matches_recorded_aggregates(self):
        t = self.src.snapshot()["tree"]
        c = t["counts"]
        self.assertEqual((c["tasks"], c["verified"], c["running"], c["escalated"]), (9, 9, 0, 2))
        by = {x["label"]: x for x in t["children"][0]["children"]}
        esc = by["click-short-help-abbrev"]
        self.assertEqual([a["harness"] for a in esc["children"]], ["Muse Code", "Claude Code"])
        self.assertEqual([a["gate"] for a in esc["children"]], ["FAIL", "PASS"])
        self.assertAlmostEqual(esc["children"][0]["cost"]["wall_s"], 478.038421, places=3)

    def test_prefix_replay_and_running_cost(self):
        snap = self.src.snapshot(14)
        c = snap["tree"]["counts"]
        self.assertEqual(c["running"], 6)
        running = [a for t in snap["tree"]["children"][0]["children"] for a in t["children"] if a["running"]]
        self.assertTrue(running and all(a["cost"]["wall_s"] is not None for a in running))

    def test_no_cost_is_invented(self):
        t = self.src.snapshot()["tree"]
        self.assertIsNone(t["children"][0]["children"][0]["cost"]["usd"])
        self.assertIsNone(t["children"][0]["children"][0]["cost"]["tokens"])

    def test_text_mode_is_narrow_and_plain(self):
        txt = textmode.render(self.src.snapshot(), self.src.describe())
        self.assertIn("chain OK, 69 records", txt)
        self.assertTrue(all(len(l) <= 60 for l in txt.splitlines()), max(map(len, txt.splitlines())))
        self.assertTrue(txt.isascii())


class JobFolderTests(unittest.TestCase):
    def test_job_folder_is_read_and_marked_unchained(self):
        with tempfile.TemporaryDirectory() as d:
            j = Path(d) / "job-a"
            j.mkdir()
            (j / "job.json").write_text(json.dumps({
                "id": "job-a", "state": "running", "accounts": ["muse"], "cancel_requested": False,
                "attempts": [{"n": 1, "account": "muse", "state": "running", "t0": 1.0}]}))
            (j / "events.jsonl").write_text('{"ts": "2026-11-03T00:00:00Z", "event": "submitted", "detail": "x"}\n')
            s = source.Source(jobs=d, commands=Path(d) / "c", names=[])
            t = s.snapshot()["tree"]
            task = t["children"][0]["children"][0]
            self.assertEqual((task["status"], task["harness"], task["chained"]), ("running", "Muse Code", False))
            self.assertFalse(task["last"]["chained"])


class CommandTests(unittest.TestCase):
    def test_build_validates(self):
        with self.assertRaises(commands.CommandError):
            commands.build_command("explode", "x")
        with self.assertRaises(commands.CommandError):
            commands.build_command("pause", None)
        with self.assertRaises(commands.CommandError):
            commands.build_command("pause", "bad name; rm -rf /")
        with self.assertRaises(commands.CommandError):
            commands.build_command("redirect", "t", {"harness": "gemini"})
        c = commands.build_command("reprioritise", "t1", {"priority": "high"}, "why", "ui")
        self.assertEqual((c["verb"], c["target"]["task"], c["args"]), ("reprioritise", "t1", {"priority": "high"}))

    def test_write_is_atomic_file_and_listed(self):
        with tempfile.TemporaryDirectory() as d:
            c = commands.build_command("pause", "t1", reason="r")
            p = commands.write_command(d, c)
            self.assertEqual(json.loads(p.read_text())["id"], c["id"])
            self.assertEqual([x["id"] for x in commands.list_commands(d)], [c["id"]])
            self.assertFalse(list(Path(d).glob("*.tmp")))

    def test_pending_pause_shows_on_the_node(self):
        with tempfile.TemporaryDirectory() as d:
            s = source.Source.from_args(demo=True, commands=d)
            commands.write_command(d, commands.build_command("pause", "task:click-pager-params"))
            t = s.snapshot(48)["tree"]  # click-pager-params still running at record 48
            by = {x["label"]: x for x in t["children"][0]["children"]}
            self.assertEqual(by["click-pager-params"]["overlay"], "pause requested")

    def test_cancel_forward_refuses_other_verbs_and_missing_jobs(self):
        c = commands.build_command("pause", "t")
        self.assertFalse(commands.forward_cancel(c, "/nonexistent")[0])
        c = commands.build_command("cancel", "nojob")
        self.assertFalse(commands.forward_cancel(c, "/nonexistent")[0])


class ServerTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.src = source.Source.from_args(demo=True, commands=self.tmp.name)
        self.token = "tok"
        h = server.make_handler(self.src, self.token, 0)
        self.httpd = ThreadingHTTPServer(("127.0.0.1", 0), h)
        self.port = self.httpd.server_address[1]
        # the handler was built with port 0 for the Host allow-list; rebuild with the real one
        self.httpd.RequestHandlerClass = server.make_handler(self.src, self.token, self.port, commands_enabled=True)
        threading.Thread(target=self.httpd.serve_forever, daemon=True).start()

    def tearDown(self):
        self.httpd.shutdown()
        self.httpd.server_close()
        self.tmp.cleanup()

    def call(self, method, path, body=None, headers=None):
        c = http.client.HTTPConnection("127.0.0.1", self.port, timeout=10)
        c.request(method, path, body=body, headers=headers or {})
        r = c.getresponse()
        data = r.read()
        return r.status, data

    def test_static_and_api(self):
        st, body = self.call("GET", "/")
        self.assertEqual(st, 200)
        self.assertIn(b"state tree", body)
        st, body = self.call("GET", "/api/tree?upto=14")
        self.assertEqual(json.loads(body)["tree"]["counts"]["running"], 6)
        st, body = self.call("GET", "/api/events?node=task:cachetools-unbound-keyword&upto=69")
        evs = json.loads(body)["events"]
        self.assertEqual(len(evs), 13)
        self.assertEqual(evs[0]["kind"], "task.created")
        self.assertEqual([e["n"] for e in evs], sorted(e["n"] for e in evs))

    def test_traversal_and_unknown_paths(self):
        self.assertEqual(self.call("GET", "/../../etc/passwd")[0], 404)
        self.assertEqual(self.call("GET", "/api/nope")[0], 404)

    def test_host_header_must_be_local(self):
        self.assertEqual(self.call("GET", "/api/meta", headers={"Host": "evil.example"})[0], 403)

    def test_command_needs_token_and_good_origin(self):
        body = json.dumps({"verb": "pause", "target": "task:click-pager-params"})
        hdr = {"Content-Type": "application/json", "Host": f"127.0.0.1:{self.port}"}
        self.assertEqual(self.call("POST", "/api/command", body, hdr)[0], 403)  # no token
        bad = dict(hdr, **{"X-Anima-Token": self.token, "Origin": "http://evil.example"})
        self.assertEqual(self.call("POST", "/api/command", body, bad)[0], 403)
        ok = dict(hdr, **{"X-Anima-Token": self.token})
        st, out = self.call("POST", "/api/command", body, ok)
        self.assertEqual(st, 200)
        self.assertTrue(Path(json.loads(out)["written"]).is_file())
        st, out = self.call("POST", "/api/command", json.dumps({"verb": "explode"}), ok)
        self.assertEqual(st, 400)

    def test_commands_disabled_by_default(self):
        """Nothing reads command files yet, so the server refuses to write one unless started with commands_enabled."""
        h = server.make_handler(self.src, self.token, self.port)  # default: disabled
        self.httpd.RequestHandlerClass = h
        hdr = {"Content-Type": "application/json", "Host": f"127.0.0.1:{self.port}", "X-Anima-Token": self.token}
        st, out = self.call("POST", "/api/command", json.dumps({"verb": "pause", "target": "task:x"}), hdr)
        self.assertEqual(st, 409)
        self.assertEqual(list(Path(self.tmp.name).glob("*.json")), [])
        st, out = self.call("GET", "/api/meta", headers={"Host": f"127.0.0.1:{self.port}"})
        self.assertFalse(json.loads(out)["commands_enabled"])

    def test_dry_run_writes_nothing(self):
        hdr = {"Content-Type": "application/json", "Host": f"127.0.0.1:{self.port}", "X-Anima-Token": self.token}
        st, out = self.call("POST", "/api/command", json.dumps(
            {"verb": "pause", "target": "task:x", "dry_run": True}), hdr)
        self.assertEqual(st, 200)
        self.assertEqual(list(Path(self.tmp.name).glob("*.json")), [])


class RunSourceTests(unittest.TestCase):
    """The UI reads the real run chain under the one state root ($ANIMA_HOME/runs)."""

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self._old = os.environ.get("ANIMA_HOME")
        os.environ["ANIMA_HOME"] = self.tmp.name

    def tearDown(self):
        if self._old is None:
            os.environ.pop("ANIMA_HOME", None)
        else:
            os.environ["ANIMA_HOME"] = self._old
        self.tmp.cleanup()

    def test_no_runs_is_a_clear_error(self):
        with self.assertRaises(SystemExit) as cm:
            source.resolve_run("latest")
        self.assertIn("no runs yet", str(cm.exception))

    def test_latest_and_named_run(self):
        for name in ("20261104T000001Z-a", "20261104T000002Z-b"):
            d = Path(self.tmp.name) / "runs" / name
            d.mkdir(parents=True)
            (d / "decisions.jsonl").write_text("")
            os.utime(d / "decisions.jsonl", (1000 + len(name) + int(name[-6:-4] == "02"), 1000 + int(name.endswith("b")) * 50))
        self.assertTrue(str(source.resolve_run("latest")).endswith("-b/decisions.jsonl"))
        self.assertTrue(str(source.resolve_run("20261104T000001Z-a")).endswith("-a/decisions.jsonl"))

    def test_run_names_cannot_escape(self):
        for bad in ("../x", "a/b", "..", "/etc", "x..y"):
            with self.assertRaises(SystemExit):
                source.resolve_run(bad)

    def test_symlinked_run_is_refused(self):
        outside = Path(self.tmp.name) / "outside.jsonl"
        outside.write_text("")
        d = Path(self.tmp.name) / "runs" / "evil"
        d.mkdir(parents=True)
        (d / "decisions.jsonl").symlink_to(outside)
        with self.assertRaises(SystemExit):
            source.resolve_run("evil")

    def test_default_commands_dir_is_under_the_state_root(self):
        s = source.Source.from_args(chains=[str(Path(self.tmp.name) / "x.jsonl")])
        self.assertEqual(s.commands, Path(self.tmp.name) / "commands")


if __name__ == "__main__":
    unittest.main()
