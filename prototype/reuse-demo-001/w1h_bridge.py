"""Explicit path import of the w1-harden recovery capability.

Mechanism: importlib.spec_from_file_location() on the literal path
  <repo>/prototype/w1-harden/recovery_lib.py
(no package import, no sys.path guessing, no copy). Because
recovery_lib.py uses relative-with-fallback imports
(`from .HOST import Host` -> fallback `from HOST import Host`), the
w1-harden directory is temporarily prepended to sys.path during the
load so the fallback resolves, then removed. The loaded module is
cached (singleton).

Transitive-load note: executing recovery_lib.py necessarily executes
its own module-level imports (w1-harden HOST.py, contract.py,
world_explore.py). That is recovery_lib's dependency closure, not this
demo's host: minihost.py contains no w1-harden import and never touches
the Host class -- MiniHost plays the entire host role. The demo reuses
from the loaded module: resume_to_verdict, phase_formulate,
phase_propose, phase_score, phase_verdict, successful_invokes,
WORKER_ID, WORKER_CODE_REF (read-only use; w1-harden is never written).
"""
from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

W1H_DIR = Path(__file__).resolve().parent.parent / "w1-harden"
RECOVERY_LIB_PATH = W1H_DIR / "recovery_lib.py"

_cached = None


def load_recovery_lib():
    """Load w1-harden/recovery_lib.py from its explicit file path."""
    global _cached
    if _cached is not None:
        return _cached
    if not RECOVERY_LIB_PATH.exists():
        raise FileNotFoundError(f"missing reuse target: {RECOVERY_LIB_PATH}")
    if str(W1H_DIR) not in sys.path:
        sys.path.insert(0, str(W1H_DIR))
        added = True
    else:
        added = False
    try:
        spec = importlib.util.spec_from_file_location(
            "w1h_recovery_lib", RECOVERY_LIB_PATH)
        module = importlib.util.module_from_spec(spec)
        sys.modules["w1h_recovery_lib"] = module
        spec.loader.exec_module(module)
    finally:
        if added:
            sys.path.remove(str(W1H_DIR))
    _cached = module
    return _cached
