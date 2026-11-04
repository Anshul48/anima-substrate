# Copyright 2026 Anshul48
# SPDX-License-Identifier: Apache-2.0
"""Needs numpy/blake3 (and, for the TRACE test, the frozen TRACE source + the MiniLM files:
run `python3 -m anima.memory setup` once). Skipped when they are absent."""

from pathlib import Path
import shutil
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

try:
    import numpy  # noqa: F401

    HAVE_NP = True
except ImportError:
    HAVE_NP = False

from anima.memory import encoder as E  # noqa: E402
from anima.memory import passages as P  # noqa: E402
from anima.memory.recall import recall  # noqa: E402

LOG = ROOT / "docs" / "evidence" / "flagship-run3" / "decisions.jsonl"
JOB = ROOT / "anima" / "memory" / "examples" / "job-click-short-help-abbrev.json"
Q_CLICK = "short help text is cut at the wrong dot after an abbreviation like vs."


def _trace_ready():
    if not HAVE_NP:
        return False
    try:
        import blake3  # noqa: F401,E401
        import onnxruntime  # noqa: F401
        import tokenizers  # noqa: F401

        from anima.memory.stores import find_trace_src
    except ImportError:
        return False
    return E.model_ready() and find_trace_src() is not None


@unittest.skipUnless(HAVE_NP, "numpy missing")
class Tmp(unittest.TestCase):
    def tmp(self):
        # TemporaryDirectory's cleanup trips on TRACE's artifacts folder; plain rmtree is fine.
        d = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, d, True)
        return d


class SimpleBackend(Tmp):
    """The fallback ('TRACE-format memory, simple retriever') with the offline hash encoder."""

    def test_ingest_recall_idempotent(self):
        from anima.memory.stores import open_store

        if True:
            d = self.tmp()
            st = open_store(d, E.HashEncoder(), backend="simple")
            ps = P.parse_decisions(LOG, root=ROOT) + P.parse_job(JOB, root=ROOT)
            self.assertEqual(st.ingest(ps)["added"], 13)
            self.assertEqual(st.ingest(ps)["added"], 0)
            res = recall(
                Q_CLICK,
                store_dir=d,
                k=2,
                min_score=0.0,
                encoder="hash",
                store=st,
                verify=False,
            )
            self.assertEqual(res["hits"][0]["task"], "click-short-help-abbrev")
            self.assertIn("simple retriever", res["backend"])
            st.close()


@unittest.skipUnless(
    _trace_ready(),
    "TRACE source / model / deps not set up (python3 -m anima.memory setup)",
)
class TraceBackend(Tmp):
    def test_ingest_recall_reopen(self):
        from anima.memory.stores import open_store

        if True:
            d = self.tmp()
            enc = E.get_encoder("minilm")
            st = open_store(d, enc, backend="trace")
            ps = P.parse_decisions(LOG, root=ROOT) + P.parse_job(JOB, root=ROOT)
            self.assertEqual(st.ingest(ps)["added"], 13)
            self.assertEqual(st.count(), 13)
            st.close()
            res = recall(
                Q_CLICK,
                store_dir=d,
                k=3,
                min_score=0.0,
                encoder="minilm",
                backend="trace",
                verify=False,
            )
            self.assertIn("TRACE frozen engine 38c66bef", res["backend"])
            self.assertEqual(res["hits"][0]["task"], "click-short-help-abbrev")
            self.assertTrue(
                all(h["trace_integrity"] == "intact-verified" for h in res["hits"])
            )
            import os
            import shutil

            self.assertEqual(
                shutil.rmtree.__module__, "shutil"
            )  # the pilot's delete-preserving patch must not leak
            self.assertEqual(os.remove.__name__, "remove")
            res2 = recall(
                "cached methods cannot be pickled",
                store_dir=d,
                k=1,
                min_score=0.0,
                encoder="minilm",
                backend="trace",
                verify=False,
            )
            self.assertEqual(res2["hits"][0]["task"], "cachetools-cachedmethod-pickle")


if __name__ == "__main__":
    unittest.main()
