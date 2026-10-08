"""W1-hardened pilot package (SUBSTRATE track, recovery focus).

Adapted copies of prototype/w1/ with: grant auto-settle on terminal
transitions, conservation replay honoring grant_settle + unsettled-terminal
refusal, Windows-safe paths, CWD-independent imports, failure-injection
tests (F1-F5), and checkpoint/recovery exercises (reopen + reattach).

NOTE on imports: this directory is named `w1-harden` (dash), so it is NOT
importable as a dotted package. Library modules therefore use
relative-with-fallback imports (try `from .x`, except ImportError fall back
to top-level `from x`), and every entry point (demo_T, tests, exercises)
bootstraps sys.path with its own directory. The suite runs green from BOTH
the package dir and the repo root; see RUN-REPORT.md X1 for commands.
"""

__version__ = "1.0.0-harden"
