"""Successor-003 snapshot manifest generator (stdlib-only).

Builds vendor/SNAPSHOT-MANIFEST.json for the vendored SST snapshot
per vendor/HASH-CONSTRUCTION.md (construction substrate-snapshot-v1).
Deterministic: same snapshot bytes -> byte-identical manifest bytes.

Run from the repo root:
    PYTHONDONTWRITEBYTECODE=1 python3 prototype/successor-003/make_snapshot_manifest.py
"""
from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
DEFAULT_SNAPSHOT = HERE / "vendor" / "sst-snapshot"
DEFAULT_MANIFEST = HERE / "vendor" / "SNAPSHOT-MANIFEST.json"

CONSTRUCTION = "substrate-snapshot-v1"
EXPECTED_FILE_COUNT = 54
LABEL = ("SUBSTRATE-QUALIFIED SNAPSHOT — NO SST-OWNER RELEASE ACCEPTANCE "
         "(see vendor/PROVENANCE.md)")


def collect_files(snapshot_dir: Path) -> list[str]:
    """Sorted snapshot-root-relative posix relpaths of every file under sst/.

    ALL regular files are pinned (importable or not); __pycache__ is
    excluded (none vendored)."""
    pkg = snapshot_dir / "sst"
    if not pkg.is_dir():
        raise ValueError(f"snapshot has no sst/ package dir: {pkg}")
    rels = []
    for p in pkg.rglob("*"):
        if "__pycache__" in p.parts:
            continue
        if p.is_dir():
            continue
        if p.is_symlink() or not p.is_file():
            raise ValueError(f"snapshot member is not a regular file: {p}")
        rels.append(p.relative_to(snapshot_dir).as_posix())
    return sorted(rels)


def file_manifest(snapshot_dir: Path) -> list[dict[str, str]]:
    out = []
    for rel in collect_files(snapshot_dir):
        digest = hashlib.sha256(
            (snapshot_dir / rel).read_bytes()).hexdigest()
        out.append({"relpath": rel, "sha256": digest})
    return out


def payload_bytes(manifest: list[dict[str, str]]) -> bytes:
    """Exact HASH-CONSTRUCTION.md payload: relpath LF hexdigest LF per file."""
    return b"".join(
        entry["relpath"].encode("utf-8") + b"\n"
        + entry["sha256"].encode("ascii") + b"\n"
        for entry in manifest)


def snapshot_hash(manifest: list[dict[str, str]]) -> str:
    return hashlib.sha256(payload_bytes(manifest)).hexdigest()


def build_manifest(snapshot_dir: Path) -> dict:
    manifest = file_manifest(snapshot_dir)
    return {
        "construction": CONSTRUCTION,
        "file_count": len(manifest),
        "files": manifest,
        "label": LABEL,
        "snapshot_hash": snapshot_hash(manifest),
    }


def write_manifest(snapshot_dir: Path = DEFAULT_SNAPSHOT,
                   out_path: Path = DEFAULT_MANIFEST) -> dict:
    doc = build_manifest(snapshot_dir)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(doc, indent=2, sort_keys=True) + "\n",
                        encoding="utf-8")
    return doc


def main(argv: list[str]) -> int:
    snapshot = Path(argv[1]) if len(argv) > 1 else DEFAULT_SNAPSHOT
    out = Path(argv[2]) if len(argv) > 2 else DEFAULT_MANIFEST
    doc = write_manifest(snapshot, out)
    print(f"files={doc['file_count']} "
          f"snapshot_hash={doc['snapshot_hash']}")
    print(f"wrote {out}")
    if doc["file_count"] != EXPECTED_FILE_COUNT:
        print(f"WARNING: expected {EXPECTED_FILE_COUNT} files, "
              f"found {doc['file_count']}", file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
