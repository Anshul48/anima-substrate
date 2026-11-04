# Copyright 2026 Anshul48
# SPDX-License-Identifier: Apache-2.0
"""Two memory back ends behind one small interface.

TraceStore   the real thing at small scale: TRACE's frozen engine (the 207-file stack-fork
             candidate in github.com/Anshul48/trace, freeze-src/cand), driven the way
             that repo's own pilot and demo drive it: TLStore + OrganizationService
             (ingest, organise, publish a generation) and the published view's
             `search` (guided search merged with the not-yet-organised tail). The
             engine's own integrity flag is returned with every hit.

SimpleStore  FALLBACK, labelled plainly "TRACE-format memory, simple retriever": the same
             passage records and source pointers, but retrieval is a plain cosine scan
             over the stored vectors. Used only when the frozen TRACE source is not
             available (reason is stored and printed).

Both keep `passages.jsonl` (the passage text, metadata and source pointer) next to the
index, so a recalled hit can always be traced to its source record.
"""
from __future__ import annotations

import hashlib
import json
import os
import shutil
import sys
import time
from pathlib import Path

from .encoder import anima_home

EXPECTED_FREEZE_SHA = "38c66bef71fbc8768a2887024fecf1bf58ff90f3feaf3a922d4c8b51a43a0d54"
EXPECTED_FREEZE_FILES = 207
TRACE_REPO = "https://github.com/Anshul48/trace"
CONFIG = "anima-memory.json"


# --------------------------------------------------------------------------- locating TRACE
def find_trace_src() -> Path | None:
    """The frozen candidate dir (…/freeze-src/cand), from $ANIMA_TRACE_SRC or $ANIMA_HOME/trace."""
    cands = []
    env = os.environ.get("ANIMA_TRACE_SRC")
    if env:
        cands += [Path(env), Path(env) / "freeze-src" / "cand"]
    cands += [anima_home() / "trace" / "freeze-src" / "cand"]
    for c in cands:
        if (c / "tools" / "product_pilot.py").is_file() and (c / "SOURCEFREEZE.json").is_file():
            return c.resolve()
    return None


def verify_freeze(src: Path):
    """Re-hash every frozen file against SOURCEFREEZE.json (what the TRACE demo-app does at start-up)."""
    mraw = (src / "SOURCEFREEZE.json").read_bytes()
    msha = hashlib.sha256(mraw).hexdigest()
    if msha != EXPECTED_FREEZE_SHA:
        raise RuntimeError(f"TRACE source freeze identity {msha[:12]} != expected {EXPECTED_FREEZE_SHA[:12]}")
    files = json.loads(mraw)["files"]
    if len(files) != EXPECTED_FREEZE_FILES:
        raise RuntimeError(f"TRACE freeze lists {len(files)} files, expected {EXPECTED_FREEZE_FILES}")
    bad = [rel for rel, want in files.items()
           if not (src / rel).is_file() or hashlib.sha256((src / rel).read_bytes()).hexdigest() != want]
    if bad:
        raise RuntimeError(f"TRACE freeze check failed for {len(bad)} files, e.g. {bad[:3]}")
    return msha, len(files)


_loaded = {}


def load_trace(src: Path):
    """Verify, then put the frozen modules on sys.path (once per process). Returns a namespace dict."""
    if _loaded:
        return _loaded
    sha, n = verify_freeze(src)
    for p in (src / "tools", src / "fork" / "tl-sys", src / "fork" / "tl-candidate-batch" / "candidate", src):
        if str(p) not in sys.path:
            sys.path.insert(0, str(p))
    # Importing the pilot harness installs tools/preserve_deletes.py, which REPLACES os.remove, os.unlink and
    # shutil.rmtree for the whole process (deletes become renames). Fine for an evidence run, wrong inside an
    # agent harness, so keep the originals and put them back right after the import.
    saved = (os.remove, os.unlink, shutil.rmtree)
    try:
        import product_pilot as pp  # frozen tools/product_pilot.py (its constants and caps rule)
    finally:
        os.remove, os.unlink, shutil.rmtree = saved
    from drain_instrument import run_drain_loop
    from tlsys.local_repair import RepairConfig
    from tlsys.org_service import OrganizationService
    from tlsys.repair_hook import TLStoreRepairHook
    from tlsys.store_if import TLStore
    _loaded.update(pp=pp, run_drain_loop=run_drain_loop, RepairConfig=RepairConfig,
                   OrganizationService=OrganizationService, TLStoreRepairHook=TLStoreRepairHook,
                   TLStore=TLStore, freeze_sha=sha, freeze_files=n, src=str(src))
    return _loaded


# --------------------------------------------------------------------------- sidecar
class Sidecar:
    """passages.jsonl: one JSON object per passage (text, meta, source pointer)."""

    def __init__(self, store_dir: Path):
        self.path = Path(store_dir) / "passages.jsonl"
        self.rows = {}
        if self.path.is_file():
            for ln in self.path.read_text().splitlines():
                if ln.strip():
                    r = json.loads(ln)
                    self.rows[r["doc_id"]] = r

    def new(self, passages):
        return [p for p in passages if p.doc_id not in self.rows]

    def add(self, passages):
        with open(self.path, "a") as f:
            for p in passages:
                r = p.to_json()
                r["ingested_at"] = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
                self.rows[p.doc_id] = r
                f.write(json.dumps(r, sort_keys=True) + "\n")
                f.flush()


def read_config(store_dir: Path):
    p = Path(store_dir) / CONFIG
    return json.loads(p.read_text()) if p.is_file() else None


def write_config(store_dir: Path, cfg: dict):
    tmp = Path(store_dir) / (CONFIG + ".tmp")
    tmp.write_text(json.dumps(cfg, indent=1, sort_keys=True))
    os.replace(tmp, Path(store_dir) / CONFIG)


# --------------------------------------------------------------------------- TRACE
class TraceStore:
    backend = "trace"

    def __init__(self, store_dir, encoder, src: Path, create: bool):
        self.dir, self.enc = Path(store_dir), encoder
        self.t = load_trace(src)
        self.side = Sidecar(self.dir)
        self.root = self.dir / "trace-store"
        n = max(len(self.side.rows), 1)
        pp = self.t["pp"]
        caps = pp.qualification_caps(planned_atoms=n, planned_docs=n)
        self.tl = self.t["TLStore"](str(self.root), create=create and not self.root.exists(),
                                    lease_owner="anima-memory", local_repair=True,
                                    repair_config=self.t["RepairConfig"](edge_threshold=pp.EDGE, leaf_threshold=pp.LEAF),
                                    caps=caps)
        self.svc = self.t["OrganizationService"](self.tl, config=pp.service_config(), keyed_state=True,
                                                 repair=self.t["TLStoreRepairHook"](self.tl))

    def _embed(self, texts):
        return [v.tolist() for v in self.enc.embed(texts)]

    def label(self):
        return (f"TRACE frozen engine {self.t['freeze_sha'][:8]} ({self.t['freeze_files']} files re-hashed OK), "
                f"encoder {self.enc.name}")

    def ingest(self, passages):
        fresh = self.side.new(passages)
        if not fresh:
            return {"added": 0, "skipped": len(passages)}
        docs = [(p.doc_id, p.text) for p in fresh]
        t0 = time.perf_counter()
        ack = self.svc.ingest_visible(docs, self._embed)
        walls = {}
        self.t["run_drain_loop"](self.svc, self.tl, "anima-memory-drain", walls,
                                 lambda: self.svc.last_future.result(), budget_seconds=60)
        self.side.add(fresh)
        return {"added": len(fresh), "skipped": len(passages) - len(fresh),
                "seconds": round(time.perf_counter() - t0, 2),
                "generation": str(getattr(ack.get("generation"), "generation_id", ""))[:40]}

    def count(self):
        with self.svc.publisher.acquire() as view:
            return view.facade.atom_count

    def search(self, query, k=3):
        import numpy as np
        q = np.asarray(self.enc.embed([query])[0], dtype=np.float64)
        with self.svc.publisher.acquire() as view:
            rows, rep = view.facade.search(query, q, k=max(k * 3, k))
            gen = rep.get("generation")
        hits, seen = [], set()
        for r in rows:
            if r["doc_id"] in seen:
                continue
            seen.add(r["doc_id"])
            hits.append({"doc_id": r["doc_id"], "score": float(r["score"]), "trace_text": r.get("text"),
                         "trace_integrity": r.get("integrity"), "trace_aid": r["aid"], "trace_span": r.get("span"),
                         "trace_path": r.get("path"), "generation": gen})
            if len(hits) == k:
                break
        return hits

    def close(self):
        try:
            self.svc.close()
        finally:
            self.tl.close()


# --------------------------------------------------------------------------- simple fallback
class SimpleStore:
    backend = "simple"

    def __init__(self, store_dir, encoder, reason: str, create: bool):
        import numpy as np
        self.np, self.dir, self.enc, self.reason = np, Path(store_dir), encoder, reason
        self.side = Sidecar(self.dir)
        self.vpath = self.dir / "vectors.npy"
        self.ids = [r for r in self.side.rows]
        self.vecs = np.load(self.vpath) if self.vpath.is_file() else np.zeros((0, 384), dtype=np.float32)

    def label(self):
        return f"TRACE-format memory, simple retriever (plain cosine scan; TRACE engine not used: {self.reason}), encoder {self.enc.name}"

    def ingest(self, passages):
        fresh = self.side.new(passages)
        if fresh:
            v = self.np.array(self.enc.embed([p.text for p in fresh]), dtype=self.np.float32)
            self.vecs = self.np.vstack([self.vecs, v])
            self.ids += [p.doc_id for p in fresh]
            self.np.save(self.vpath, self.vecs)
            self.side.add(fresh)
        return {"added": len(fresh), "skipped": len(passages) - len(fresh)}

    def count(self):
        return len(self.ids)

    def search(self, query, k=3):
        np = self.np
        if not len(self.ids):
            return []
        q = np.asarray(self.enc.embed([query])[0], dtype=np.float32)
        m = self.vecs / np.clip(np.linalg.norm(self.vecs, axis=1, keepdims=True), 1e-12, None)
        s = m @ (q / max(float(np.linalg.norm(q)), 1e-12))
        order = np.argsort(-s, kind="stable")[:k]
        return [{"doc_id": self.ids[i], "score": float(s[i]), "trace_text": None, "trace_integrity": None}
                for i in order]

    def close(self):
        pass


def open_store(store_dir, encoder, backend="auto", create=True):
    """Open (or create) the memory at store_dir. backend: auto | trace | simple."""
    store_dir = Path(store_dir)
    store_dir.mkdir(parents=True, exist_ok=True)
    cfg = read_config(store_dir)
    if cfg:
        backend = cfg["backend"] if backend == "auto" else backend
        if backend != cfg["backend"]:
            raise RuntimeError(f"{store_dir} was created with backend {cfg['backend']!r}, not {backend!r}")
        if cfg["encoder"] != encoder.name:
            raise RuntimeError(f"{store_dir} holds {cfg['encoder']} vectors; refusing to mix with {encoder.name}")
    reason = None
    if backend in ("auto", "trace"):
        src = find_trace_src()
        if src is None:
            reason = (f"frozen TRACE source not found (set ANIMA_TRACE_SRC or run `anima memory setup`, "
                      f"which clones {TRACE_REPO} into {anima_home() / 'trace'})")
        else:
            try:
                st = TraceStore(store_dir, encoder, src, create)
                if not cfg:
                    write_config(store_dir, {"schema": "anima-memory-v1", "backend": "trace", "encoder": encoder.name,
                                             "encoder_describe": encoder.describe, "trace_freeze_sha256": st.t["freeze_sha"],
                                             "project_root": str(Path.cwd()),
                                             "created": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())})
                return st
            except Exception as exc:  # noqa: BLE001  (say why, then degrade out loud)
                if backend == "trace":
                    raise
                reason = f"TRACE engine failed to start: {type(exc).__name__}: {str(exc)[:160]}"
        if backend == "trace":
            raise RuntimeError(reason)
        if cfg and cfg["backend"] == "trace":
            raise RuntimeError(f"{store_dir} is a TRACE store but TRACE cannot start: {reason}")
        print(f"anima memory: using the simple retriever. Reason: {reason}", file=sys.stderr)
    st = SimpleStore(store_dir, encoder, reason or "requested", create)
    if not cfg:
        write_config(store_dir, {"schema": "anima-memory-v1", "backend": "simple", "encoder": encoder.name,
                                 "encoder_describe": encoder.describe, "simple_reason": st.reason,
                                 "project_root": str(Path.cwd()),
                                 "created": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())})
    return st
