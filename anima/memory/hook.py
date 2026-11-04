# Copyright 2026 Anshul48
# SPDX-License-Identifier: Apache-2.0
"""The hook `anima run --memory trace` calls to put recalled fixes in front of the worker's prompt.

    from anima.memory.hook import augment_prompt
    prompt, report = augment_prompt(prompt, task_text=issue_text, store_dir=".anima/trace")

Fail-open: if memory is empty or broken the prompt is returned unchanged and `report` says why.
Memory must never stop a job.
"""
from __future__ import annotations

from .recall import DEFAULT_K, DEFAULT_MIN_SCORE, DEFAULT_STORE, format_block, recall


def augment_prompt(prompt, task_text=None, store_dir=DEFAULT_STORE, k=DEFAULT_K, min_score=DEFAULT_MIN_SCORE,
                   exclude_tasks=(), **kw):
    try:
        res = recall(task_text if task_text is not None else prompt, store_dir=store_dir, k=k,
                     min_score=min_score, exclude_tasks=exclude_tasks, **kw)
    except Exception as exc:  # noqa: BLE001
        return prompt, {"injected": 0, "error": f"{type(exc).__name__}: {exc}"}
    block = format_block(res)
    report = {"injected": len(res["hits"]), "backend": res.get("backend"), "seconds": res.get("seconds"),
              "hits": [{k_: h[k_] for k_ in ("rank", "score", "task", "doc_id", "pointer", "source_check")}
                       for h in res["hits"]], "block_chars": len(block)}
    if not block:
        return prompt, report
    return block + "\n---\n\n" + prompt, report


def record_run(run_dir, task_ref=None, store_dir=DEFAULT_STORE, encoder="auto", backend="auto"):
    """After `anima run`: put the finished run's attempts into memory so the next job can recall them.
    Returns a small report; never raises (memory must not turn a finished job into a crash)."""
    try:
        from pathlib import Path

        from .encoder import get_encoder
        from .passages import load_path
        from .stores import open_store, read_config
        cfg = read_config(store_dir)
        root = Path(cfg["project_root"]) if cfg else Path.cwd()
        passages = load_path(run_dir, root=root, task=task_ref)
        st = open_store(store_dir, get_encoder(encoder), backend=backend, create=True)
        try:
            rep = st.ingest(passages)
            return {"recorded": len(passages), "store_count": st.count(), "ingest": rep, "backend": st.label()}
        finally:
            st.close()
    except Exception as exc:  # noqa: BLE001
        return {"recorded": 0, "error": f"{type(exc).__name__}: {exc}"}
