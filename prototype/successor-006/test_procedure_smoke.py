"""Successor-006 procedure-participant smoke (carried code, NOT re-verified).

procedure.py is carried byte-identical from successor-005 (see
PROVENANCE.md); the full 57-test procedure suite is NOT carried
(out of scope for the R11/J1 brief). These 2 smoke tests prove the
carried participant still advertises + executes through the
successor-006 consumer surface.

Run from the repo root:
    PYTHONDONTWRITEBYTECODE=1 python3 prototype/successor-006/test_procedure_smoke.py

All run dirs live under successor-006/.test-tmp/.
"""
from __future__ import annotations

import hashlib
import json
import os
import shutil
import sys
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

import api  # noqa: E402
from minihost import ContractViolation  # noqa: E402


def _bundle(path: Path) -> None:
    code = ("from pathlib import Path; "
            "Path('out.txt').write_text('smoke-ok\\n')")
    (path / "MANIFEST.json").write_text(json.dumps(
        {"files": {},
         "steps": [{"step": "greet",
                    "argv": [sys.executable, "-c", code],
                    "declared_outputs": ["out.txt"],
                    "timeout_s": 60}],
         "python": "system"},
        indent=2, sort_keys=True), encoding="utf-8")


class TestProcedureSmoke(unittest.TestCase):
    def setUp(self):
        self.root = HERE / ".test-tmp" / self._testMethodName
        if self.root.exists():
            shutil.rmtree(self.root)
        self.root.mkdir(parents=True, exist_ok=True)

    def tearDown(self):
        if os.environ.get("SUBSTRATE_KEEP_TMP"):
            return
        shutil.rmtree(self.root, ignore_errors=True)

    def test_carried_bytes(self):
        mine = (HERE / "procedure.py").read_bytes()
        frozen = (HERE.parent / "successor-005" / "procedure.py") \
            .read_bytes()
        self.assertEqual(hashlib.sha256(mine).hexdigest(),
                         hashlib.sha256(frozen).hexdigest())

    def test_advertise_and_run(self):
        bundle = self.root / "bundle-hello"
        bundle.mkdir()
        _bundle(bundle)
        state = self.root / "proc"
        rep = api.create_proc_world(state, "PW", bundle, "smoke")
        self.assertEqual(rep["steps"], ["greet"])
        out = api.run_procedure(state, "PW", "bundle-hello", "smoke-key")
        self.assertEqual(out["re_executed_steps"], [])
        result = json.loads(
            (state / "artifacts" / "proc-smoke-key" / "greet"
             / "RESULT.json").read_text(encoding="utf-8"))
        self.assertEqual(result["step"], "greet")
        # Re-driving skips the finished step (same C1 matcher family).
        out2 = api.run_procedure(state, "PW", "bundle-hello", "smoke-key")
        self.assertEqual(out2["executed"], [])

    def test_table_miss_denied(self):
        bundle = self.root / "bundle-hello"
        bundle.mkdir()
        _bundle(bundle)
        state = self.root / "proc"
        api.create_proc_world(state, "PW", bundle, "smoke")
        with self.assertRaises(ContractViolation):
            api.run_procedure(state, "PW", "no-such-proc", "k2")


if __name__ == "__main__":
    unittest.main(verbosity=2)
