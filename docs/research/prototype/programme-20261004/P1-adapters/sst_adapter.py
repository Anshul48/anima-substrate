"""P1 SST adapter: pinned snapshot reader + envelope validator (stdlib-only).

Consumes ONLY a vendored copy (see VENDORING.md) made by the documented
copy procedure. Never references a live producer tree at runtime.
Never imports producer code: read + hash + parse only.

Two gates:
  1. verify_snapshot_copy(copy_dir): the copy's bytes must reproduce the
     pinned substrate-snapshot-v1 identity (file set + per-file sha256 +
     snapshot_hash). ANY drift -> PinMismatch naming the files.
  2. validate_envelope(obj): a run_search/SearchResult-shaped mapping must
     carry EXACTLY the 8 pinned keys with the pinned value shapes.
     Missing/extra keys or wrong shapes -> EnvelopeViolation.

Both gates are exact-match; there is no warn-and-proceed.
"""
from __future__ import annotations

import hashlib
import sys
from pathlib import Path
from typing import Any

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

from pins import DEFAULT_PINS, PinMismatch, load_pins, require_equal  # noqa: E402

__all__ = [
    "PinMismatch",
    "EnvelopeViolation",
    "collect_files",
    "file_entries",
    "snapshot_hash",
    "verify_snapshot_copy",
    "validate_envelope",
]

CONSTRUCTION = "substrate-snapshot-v1"

# Pinned value shapes for the 8-key envelope (observed 2026-10-04 from
# SST SearchResult + live-qual envelopes; NOT owner-declared stable).
# champion: dict or None; budget_consumed: dict; lists stay lists.
ENVELOPE_SPEC: dict[str, tuple[type, ...]] = {
    "tree_id": (str,),
    "termination_reason": (str,),
    "champion": (dict, type(None)),
    "alternatives": (list,),
    "budget_consumed": (dict,),
    "provider_errors": (list,),
    "gateway_bindings": (list,),
    "event_log_ref": (str,),
}


class EnvelopeViolation(Exception):
    """Envelope bytes do not match the pinned run_search/SearchResult shape."""


# ------------------------------------------------- snapshot verification

def collect_files(copy_dir: Path) -> list[str]:
    """Relpaths of every regular file under sst/ (POSIX form, sorted).

    __pycache__ excluded (never vendored). Symlinks refused.
    """
    root = Path(copy_dir) / "sst"
    if not root.is_dir():
        raise PinMismatch(f"snapshot copy has no sst/ tree: {root}")
    rels: list[str] = []
    for path in sorted(root.rglob("*")):
        if "__pycache__" in path.parts:
            continue
        if path.is_symlink():
            raise PinMismatch(f"snapshot copy contains symlink: {path}")
        if path.is_file():
            rels.append(path.relative_to(copy_dir).as_posix())
    return sorted(rels)


def file_entries(copy_dir: Path) -> list[dict[str, str]]:
    entries = []
    for rel in collect_files(copy_dir):
        data = (Path(copy_dir) / rel).read_bytes()
        entries.append(
            {"relpath": rel, "sha256": hashlib.sha256(data).hexdigest()}
        )
    return entries


def snapshot_hash(entries: list[dict[str, str]]) -> str:
    payload = b"".join(
        e["relpath"].encode("utf-8") + b"\n"
        + e["sha256"].encode("utf-8") + b"\n"
        for e in entries
    )
    return hashlib.sha256(payload).hexdigest()


def verify_snapshot_copy(
    copy_dir: Path | str,
    pins_path: Path = DEFAULT_PINS,
) -> dict[str, Any]:
    """Verify a vendored SST copy against PINS.json. Returns evidence.

    Raises PinMismatch naming every offending file on any drift.
    """
    copy_dir = Path(copy_dir)
    pins = load_pins(pins_path)["sst"]
    if pins.get("snapshot_construction") != CONSTRUCTION:
        raise PinMismatch(
            f"pin construction {pins.get('snapshot_construction')!r} != "
            f"{CONSTRUCTION!r}; refusing to guess the hash algorithm"
        )
    live = {e["relpath"]: e["sha256"] for e in file_entries(copy_dir)}
    if pins.get("file_count") != len(live):
        raise PinMismatch(
            f"file count drift: pinned {pins.get('file_count')} vs "
            f"observed {len(live)} in {copy_dir}"
        )
    live_hash = snapshot_hash(file_entries(copy_dir))
    require_equal("sst snapshot_hash", live_hash, pins["snapshot_hash"])
    for rel, want in pins.get("critical_files", {}).items():
        got = live.get(rel)
        if got is None:
            raise PinMismatch(f"critical file missing from copy: {rel}")
        require_equal(f"sst critical file {rel}", got, want)
    return {
        "copy_dir": str(copy_dir),
        "construction": CONSTRUCTION,
        "file_count": len(live),
        "snapshot_hash": live_hash,
        "tree_commit": pins["tree_commit"],
        "verdict": "MATCH",
    }


# ------------------------------------------------- envelope validation

def validate_envelope(obj: Any) -> dict[str, Any]:
    """Validate a parsed run_search/SearchResult-shaped mapping.

    Input must already be parsed (dict); this function never touches
    producer code or the network. Returns a small evidence dict.
    """
    if not isinstance(obj, dict):
        raise EnvelopeViolation(
            f"envelope must be a mapping, got {type(obj).__name__}"
        )
    missing = sorted(set(ENVELOPE_SPEC) - set(obj))
    extra = sorted(set(obj) - set(ENVELOPE_SPEC))
    if missing or extra:
        raise EnvelopeViolation(
            "envelope key mismatch "
            f"(missing={missing or 'none'}, extra={extra or 'none'}); "
            f"pinned keys={sorted(ENVELOPE_SPEC)}"
        )
    bad: list[str] = []
    for key, types in ENVELOPE_SPEC.items():
        if not isinstance(obj[key], types):
            bad.append(
                f"{key}: {type(obj[key]).__name__} not in "
                f"{[t.__name__ for t in types]}"
            )
    if bad:
        raise EnvelopeViolation("envelope shape mismatch: " + "; ".join(bad))
    return {
        "keys": sorted(obj),
        "termination_reason": obj["termination_reason"],
        "has_champion": obj["champion"] is not None,
        "n_alternatives": len(obj["alternatives"]),
        "n_provider_errors": len(obj["provider_errors"]),
        "verdict": "VALID",
    }
