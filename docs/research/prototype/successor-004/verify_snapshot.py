"""Successor-004 snapshot verifier (stdlib-only).

Run BEFORE every SST import (and after every SST consumption): compares
the live vendor/sst-snapshot/ bytes against vendor/SNAPSHOT-MANIFEST.json
and raises SSTBoundary naming every mismatched file on ANY drift
(changed bytes, missing file, extra file, count change, hash change).
There is no warn-and-proceed posture: drift is a loud refusal.

Run from the repo root:
    PYTHONDONTWRITEBYTECODE=1 python3 prototype/successor-004/verify_snapshot.py
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

from make_snapshot_manifest import (CONSTRUCTION, collect_files,  # noqa: E402
                                    file_manifest, snapshot_hash)

DEFAULT_SNAPSHOT = HERE / "vendor" / "sst-snapshot"
DEFAULT_MANIFEST = HERE / "vendor" / "SNAPSHOT-MANIFEST.json"


class SSTBoundary(Exception):
    """Exact consumption boundary: what failed, where, with what evidence."""


def load_manifest(manifest_path: Path = DEFAULT_MANIFEST) -> dict:
    try:
        doc = json.loads(manifest_path.read_text(encoding="utf-8"))
    except OSError as exc:
        raise SSTBoundary(f"SST boundary: cannot read snapshot manifest "
                          f"{manifest_path}: {exc}")
    except ValueError as exc:
        raise SSTBoundary(f"SST boundary: snapshot manifest is not valid "
                          f"JSON ({manifest_path}): {exc}")
    if doc.get("construction") != CONSTRUCTION:
        raise SSTBoundary(
            f"SST boundary: manifest construction "
            f"{doc.get('construction')!r} != {CONSTRUCTION!r} "
            f"({manifest_path}); refusing to guess the hash algorithm")
    if not isinstance(doc.get("files"), list):
        raise SSTBoundary(f"SST boundary: manifest has no file list "
                          f"({manifest_path})")
    return doc


def verify(snapshot_dir: Path = DEFAULT_SNAPSHOT,
           manifest_path: Path = DEFAULT_MANIFEST) -> dict:
    """Verify live snapshot bytes against the manifest. Returns evidence.

    Raises SSTBoundary naming every offending file on any drift.
    """
    snapshot_dir = Path(snapshot_dir)
    manifest_path = Path(manifest_path)
    if not (snapshot_dir / "sst").is_dir():
        raise SSTBoundary(f"SST boundary: snapshot tree missing: "
                          f"{snapshot_dir / 'sst'}")
    doc = load_manifest(manifest_path)
    pinned = {e["relpath"]: e["sha256"] for e in doc["files"]}
    live = {e["relpath"]: e["sha256"] for e in file_manifest(snapshot_dir)}
    missing = sorted(set(pinned) - set(live))
    extra = sorted(set(live) - set(pinned))
    changed = sorted(r for r in set(pinned) & set(live)
                     if pinned[r] != live[r])
    problems = []
    if missing:
        problems.append(f"missing files ({len(missing)}): "
                        + ", ".join(missing))
    if extra:
        problems.append(f"extra files ({len(extra)}): "
                        + ", ".join(extra))
    if changed:
        problems.append(f"changed bytes ({len(changed)}): "
                        + ", ".join(changed))
    if doc.get("file_count") != len(live):
        problems.append(f"file count drift: manifest "
                        f"{doc.get('file_count')} vs live {len(live)}")
    live_hash = snapshot_hash(file_manifest(snapshot_dir))
    if live_hash != doc.get("snapshot_hash"):
        problems.append(f"snapshot_hash drift: manifest "
                        f"{doc.get('snapshot_hash')} vs live {live_hash}")
    if problems:
        raise SSTBoundary(
            "SST boundary: vendor snapshot drift — REFUSING SST import.\n"
            + "\n".join(f"  - {p}" for p in problems)
            + f"\nsnapshot: {snapshot_dir}\nmanifest: {manifest_path}")
    return {"snapshot": str(snapshot_dir), "manifest": str(manifest_path),
            "construction": CONSTRUCTION, "file_count": len(live),
            "snapshot_hash": live_hash, "verdict": "MATCH"}


def main(argv: list[str]) -> int:
    snapshot = Path(argv[1]) if len(argv) > 1 else DEFAULT_SNAPSHOT
    manifest = Path(argv[2]) if len(argv) > 2 else DEFAULT_MANIFEST
    try:
        rep = verify(snapshot, manifest)
    except SSTBoundary as exc:
        print(f"{exc}", file=sys.stderr)
        return 1
    print(f"snapshot MATCH: files={rep['file_count']} "
          f"hash={rep['snapshot_hash']}")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
