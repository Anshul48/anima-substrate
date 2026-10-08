"""P1 adapter pin handling (stdlib-only, shared).

Deliberate-pin mechanics: pins live in PINS.json. Adapters load them,
verify vendored COPIES against them, and raise PinMismatch on ANY
deviation. There is no HEAD-following path: upgrading a pin means a
human edits PINS.json (with date + reason recorded in SURVEY.md) and
re-runs selftest.py.
"""
from __future__ import annotations

import json
from pathlib import Path

HERE = Path(__file__).resolve().parent
DEFAULT_PINS = HERE / "PINS.json"


class PinMismatch(Exception):
    """Pinned identity does not match observed bytes. Refuse loudly."""


def load_pins(pins_path: Path = DEFAULT_PINS) -> dict:
    try:
        doc = json.loads(Path(pins_path).read_text(encoding="utf-8"))
    except OSError as exc:
        raise PinMismatch(f"pin file unreadable ({pins_path}): {exc}")
    except ValueError as exc:
        raise PinMismatch(f"pin file is not valid JSON ({pins_path}): {exc}")
    if not isinstance(doc, dict) or "sst" not in doc or "stc" not in doc:
        raise PinMismatch(f"pin file missing sst/stc sections ({pins_path})")
    return doc


def require_equal(what: str, observed: str, pinned: str) -> None:
    if observed != pinned:
        raise PinMismatch(
            f"pin mismatch on {what}: observed {observed!r} != "
            f"pinned {pinned!r} — refusing (edit PINS.json deliberately "
            f"to advance, never auto-follow)"
        )
