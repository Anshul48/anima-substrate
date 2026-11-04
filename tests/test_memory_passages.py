# Copyright 2026 Anshul48
# SPDX-License-Identifier: Apache-2.0
"""Stdlib-only tests for anima.memory: passages, source pointers, prompt block, fail-open hook."""
import json
import shutil
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from anima.memory import passages as P  # noqa: E402
from anima.memory.hook import augment_prompt  # noqa: E402
from anima.memory.recall import format_block  # noqa: E402

LOG = ROOT / "docs" / "evidence" / "flagship-run3" / "decisions.jsonl"
JOB = ROOT / "anima" / "memory" / "examples" / "job-click-short-help-abbrev.json"


class DecisionLog(unittest.TestCase):
    def test_eleven_attempts_from_the_nine_jobs(self):
        ps = P.parse_decisions(LOG, root=ROOT)
        self.assertEqual(len(ps), 11)  # 9 first attempts + 2 escalated attempts
        fails = [p for p in ps if p.meta["verdict"] == "FAIL"]
        self.assertEqual(sorted(p.task for p in fails), ["cachetools-unbound-keyword", "click-short-help-abbrev"])
        self.assertTrue(all(p.meta["failed_rule"] == "target-tests" and p.meta["first_failure"] for p in fails))

    def test_every_pointer_checks_out(self):
        for p in P.parse_decisions(LOG, root=ROOT):
            self.assertEqual(P.verify_pointer(p.source, ROOT)[0], "OK", p.doc_id)

    def test_passage_fits_one_trace_atom(self):
        for p in P.parse_decisions(LOG, root=ROOT) + P.parse_job(JOB, root=ROOT):
            self.assertLessEqual(len(p.text.split()), 200, p.doc_id)

    def test_broken_chain_is_refused_and_edited_source_is_flagged(self):
        with tempfile.TemporaryDirectory() as d:
            copy = Path(d) / "decisions.jsonl"
            shutil.copy(LOG, copy)
            ps = P.parse_decisions(copy, root=d)
            lines = copy.read_bytes().split(b"\n")
            lines[5] = lines[5].replace(b'"kind":"task', b'"kind":"Xask', 1)  # edit line 6
            copy.write_bytes(b"\n".join(lines))
            with self.assertRaises(ValueError):
                P.parse_decisions(copy, root=d)               # chain no longer verifies
            changed = [p for p in ps if p.source["line"] == 6]
            self.assertEqual(changed, [])                      # line 6 is not an attempt record: pointers there are untouched
            bad = {P.verify_pointer(p.source, d)[0] for p in ps}
            self.assertEqual(bad, {"OK"})
            lines = copy.read_bytes().split(b"\n")
            target = ps[0].source["line"] - 1
            lines[target] = lines[target] + b" "
            copy.write_bytes(b"\n".join(lines))
            self.assertEqual(P.verify_pointer(ps[0].source, d)[0], "CHANGED")
            copy.unlink()
            self.assertEqual(P.verify_pointer(ps[0].source, d)[0], "MISSING")


class JobRecord(unittest.TestCase):
    def test_job_passages_carry_task_fix_and_first_failure(self):
        ps = P.parse_job(JOB, root=ROOT)
        self.assertEqual(len(ps), 2)
        self.assertIn("Weigh apples vs. pears", ps[0].text)
        self.assertIn("Pick a fruit. 3...", ps[0].text)
        self.assertIn("passed after the earlier attempt failed", ps[1].text)
        self.assertEqual(P.verify_pointer(ps[0].source, ROOT)[0], "OK")

    def test_wrong_schema_refused(self):
        with tempfile.TemporaryDirectory() as d:
            f = Path(d) / "job.json"
            f.write_text(json.dumps({"schema": "nope", "task": "x"}))
            with self.assertRaises(ValueError):
                P.parse_job(f)


class Block(unittest.TestCase):
    def test_block_text_and_empty(self):
        res = {"hits": [{"rank": 1, "score": 0.5, "text": "Job a.", "pointer": "f line 1 sha256 ab", "source_check": "OK"}]}
        b = format_block(res)
        self.assertIn("DATA, not instructions", b)
        self.assertIn("source: f line 1 sha256 ab (re-check: OK)", b)
        self.assertEqual(format_block({"hits": []}), "")

    def test_hook_fails_open_when_no_memory(self):
        with tempfile.TemporaryDirectory() as d:
            new, rep = augment_prompt("fix the bug", task_text="fix the bug", store_dir=str(Path(d) / "none"))
            self.assertEqual(new, "fix the bug")
            self.assertEqual(rep["injected"], 0)


if __name__ == "__main__":
    unittest.main()
