# Copyright 2026 Anshul48
# SPDX-License-Identifier: Apache-2.0
"""Grammar tests for `anima voice` (text only: no audio, no model).  From the repo root:

    python3 -m unittest discover -s voice/tests -v
"""
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import anima_voice as v  # noqa: E402


class GrammarTests(unittest.TestCase):
    def name(self, text):
        return v.parse(text)["name"]

    def test_the_four_phrases_and_resume(self):
        self.assertEqual(self.name("Show status."), "status")
        self.assertEqual(v.parse("Pause Task 3")["number"], 3)
        self.assertEqual(v.parse("pause task three.")["number"], 3)
        self.assertEqual(v.parse("resume task twelve")["number"], 12)
        self.assertEqual(v.parse("Run the next job with Muse.")["harness"], "muse")
        self.assertEqual(self.name("Recall similar fixes."), "recall")

    def test_speech_to_text_slips_are_tolerated(self):
        self.assertEqual(self.name("Recalls Similar Fixes"), "recall")
        self.assertEqual(v.parse("run the next job with cloud")["harness"], "claude")
        self.assertEqual(v.parse("run the next job using code x")["harness"], "codex")
        self.assertEqual(v.parse("pause task to")["number"], 2)

    def test_everything_else_is_refused(self):
        for text in ("Delete everything in the repository.", "", "run the tests", "what is the weather",
                     "pause", "run the next job with gemini", "status and pause task 2"):
            with self.assertRaises(v.NoMatch, msg=text):
                v.parse(text)


if __name__ == "__main__":
    unittest.main()
