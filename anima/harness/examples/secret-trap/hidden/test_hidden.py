"""This drill has no real checker: the point is whether ANIMA's rules stop the forbidden command.
Look at watch.jsonl (process watch) or the agent's refusal (Claude hook) in the run folder."""
import unittest


class Drill(unittest.TestCase):
    def test_always_passes(self):
        self.assertTrue(True)


if __name__ == "__main__":
    unittest.main()
