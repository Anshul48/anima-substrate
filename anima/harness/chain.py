"""The decision chain: one JSON line per decision, each carrying the SHA-256 of
the line before it. Same line format as the recorded nine-job run
(docs/evidence/flagship-run3/decisions.jsonl), so the repository's own
check_chain.py reads our files too.
"""
from __future__ import annotations

import hashlib
import json
import os
import time
import uuid
from pathlib import Path


def _ts() -> str:
    t = time.time()
    return time.strftime("%Y-%m-%dT%H:%M:%S", time.gmtime(t)) + ".%03dZ" % int((t % 1) * 1000)


class Chain:
    def __init__(self, path, actor="anima", mode="REAL"):
        self.path, self.actor, self.mode = Path(path), actor, mode
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.prev = "GENESIS"
        self.count = 0
        if self.path.exists() and self.path.stat().st_size:
            lines = [ln for ln in self.path.read_bytes().split(b"\n") if ln]
            self.prev = hashlib.sha256(lines[-1]).hexdigest()
            self.count = len(lines)

    def append(self, kind: str, task: str = "", actor: str | None = None, supersedes=(), **data) -> dict:
        data.setdefault("mode", self.mode)
        ev = {"actor": actor or self.actor, "data": data, "id": uuid.uuid4().hex, "kind": kind,
              "prev": self.prev, "supersedes": list(supersedes), "task": task, "ts": _ts()}
        line = json.dumps(ev, sort_keys=True, separators=(",", ":")).encode()
        with open(self.path, "ab") as f:
            f.write(line + b"\n")
            f.flush()
            os.fsync(f.fileno())
        self.prev = hashlib.sha256(line).hexdigest()
        self.count += 1
        return ev

    def write_head(self) -> dict:
        raw = self.path.read_bytes()
        head = {"bytes": len(raw), "events": self.count, "mode": self.mode, "sha256": hashlib.sha256(raw).hexdigest()}
        self.path.with_name(self.path.name + ".head.json").write_text(json.dumps(head, sort_keys=True) + "\n")
        return head


def verify(path) -> tuple[bool, str, int, str]:
    """(ok, why, record count, file sha256). Same rule as docs/evidence/flagship-run3/check_chain.py."""
    raw = Path(path).read_bytes()
    lines = [ln for ln in raw.split(b"\n") if ln]
    prev = "GENESIS"
    for n, line in enumerate(lines, start=1):
        try:
            ev = json.loads(line)
        except ValueError:
            return False, f"line {n} is not valid JSON", len(lines), hashlib.sha256(raw).hexdigest()
        if ev.get("prev") != prev:
            return False, f"line {n} does not match the line before it", len(lines), hashlib.sha256(raw).hexdigest()
        prev = hashlib.sha256(line).hexdigest()
    head = Path(path).with_name(Path(path).name + ".head.json")
    why = "every link matches"
    digest = hashlib.sha256(raw).hexdigest()
    if head.exists():
        try:
            want = json.loads(head.read_text())["sha256"]
            if want != digest:
                return False, "links match but the file fingerprint differs from the saved head (lines appended or removed after the run)", len(lines), digest
            why += "; matches the fingerprint saved at the end of the run"
        except (ValueError, KeyError):
            pass
    return True, why, len(lines), digest
