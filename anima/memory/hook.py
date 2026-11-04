# Copyright 2026 Anshul48
# SPDX-License-Identifier: Apache-2.0
"""The hook `anima run --memory trace` calls to put recalled fixes in front of the worker's prompt.

    from anima.memory.hook import augment_prompt
    prompt, report = augment_prompt(prompt, task_text=issue_text)

By default the memory work runs in a CHILD PROCESS (`python -m anima.memory ...`, which re-launches itself
inside the memory venv). The host program never imports TRACE, numpy or onnxruntime, and the temporary
process-wide patching that TRACE's pilot harness does to os.remove / os.unlink / shutil.rmtree stays in the child.
Pass isolate=False only from inside that child (the CLI does) or in tests.

Fail-open: if memory is empty or broken the prompt is returned unchanged, `report` says why, and the failure is
appended to <store>/failures.jsonl. Memory never stops a job.
"""
from __future__ import annotations

import json
import os
import subprocess
import sys
import tempfile
from pathlib import Path

from .recall import DEFAULT_K, DEFAULT_MIN_SCORE, DEFAULT_STORE, format_block, recall
from .safety import locked, record_failure
from .stores import default_store

REPO_ROOT = Path(__file__).resolve().parents[2]  # the folder that contains the `anima` package
CHILD_TIMEOUT = 180


def _child(args, timeout=CHILD_TIMEOUT):
    """Run `python -m anima.memory <args>` in its own process. Returns (returncode, stdout, stderr)."""
    env = dict(os.environ, PYTHONPATH=os.pathsep.join(filter(None, [str(REPO_ROOT), os.environ.get("PYTHONPATH", "")])))
    r = subprocess.run([sys.executable, "-m", "anima.memory", *map(str, args)], capture_output=True, text=True,
                       timeout=timeout, env=env)
    return r.returncode, r.stdout, r.stderr


def _last_json(text):
    for ln in reversed((text or "").strip().splitlines()):
        if ln.startswith("{"):
            try:
                return json.loads(ln)
            except ValueError:
                continue
    return None


def augment_prompt(prompt, task_text=None, store_dir=DEFAULT_STORE, k=DEFAULT_K, min_score=DEFAULT_MIN_SCORE,
                   exclude_tasks=(), isolate=True, encoder="auto", backend="auto", **kw):
    store = Path(store_dir or default_store())
    try:
        if isolate:
            with tempfile.TemporaryDirectory(prefix="anima-mem-") as td:
                pf, tf = Path(td, "prompt.txt"), Path(td, "task.txt")
                pf.write_text(prompt)
                tf.write_text(task_text if task_text is not None else prompt)
                argv = ["prompt", "--prompt-file", pf, "--task-file", tf, "--store", store, "-k", k,
                        "--min-score", min_score, "--encoder", encoder, "--backend", backend]
                for t in exclude_tasks:
                    argv += ["--exclude-task", t]
                rc, out, err = _child(argv)
            rep = _last_json(err)
            if rc != 0 or rep is None:
                raise RuntimeError(f"memory process exited {rc}: {(err or '').strip()[-200:]}")
            if rep.get("error") and not rep.get("failure_recorded"):  # the child failed open and told us why
                rep["failure_recorded"] = bool(record_failure(store, "recall", rep["error"]))
            return (out if rep.get("injected") else prompt), rep
        res = recall(task_text if task_text is not None else prompt, store_dir=store, k=k, min_score=min_score,
                     exclude_tasks=exclude_tasks, encoder=encoder, backend=backend, **kw)
    except Exception as exc:  # noqa: BLE001
        err = f"{type(exc).__name__}: {exc}"
        return prompt, {"injected": 0, "error": err, "failure_recorded": bool(record_failure(store, "recall", err))}
    block = format_block(res)
    shown = [h for h in res["hits"]][: block.count("\n    source:")]
    report = {"injected": len(shown), "backend": res.get("backend"), "backend_kind": res.get("backend_kind"),
              "encoder": res.get("encoder"), "seconds": res.get("seconds"),
              "hits": [{k_: h[k_] for k_ in ("rank", "score", "task", "doc_id", "pointer", "source_check")} for h in shown],
              "excluded_unverified": res.get("excluded_unverified", []), "block_chars": len(block)}
    if not block:
        return prompt, report
    return block + "\n---\n\n" + prompt, report


def record_run(run_dir, task_ref=None, store_dir=DEFAULT_STORE, encoder="auto", backend="auto", isolate=True):
    """After `anima run`: put the finished run's attempts into memory so the next job can recall them.
    Returns a small report; never raises (memory must not turn a finished job into a crash). Failures are
    appended to <store>/failures.jsonl and returned as {"recorded": 0, "error": ...}."""
    store = Path(store_dir or default_store())
    try:
        if isolate:
            argv = ["ingest", run_dir, "--store", store, "--encoder", encoder, "--backend", backend, "--json"]
            if task_ref:
                argv += ["--task", task_ref]
            rc, out, err = _child(argv, timeout=300)
            rep = _last_json(out)
            if rc != 0 or rep is None:
                raise RuntimeError(f"memory process exited {rc}: {(err or out or '').strip()[-200:]}")
            return rep
        from .encoder import get_encoder
        from .passages import load_path
        from .stores import open_store, read_config
        cfg = read_config(store)
        root = Path(cfg["project_root"]) if cfg else Path.cwd()
        passages = load_path(run_dir, root=root, task=task_ref)
        with locked(store, exclusive=True):
            st = open_store(store, get_encoder(encoder), backend=backend, create=True)
            try:
                rep = st.ingest(passages)
                return {"recorded": len(passages), "store_count": st.count(), "ingest": rep, "backend": st.label()}
            finally:
                st.close()
    except Exception as exc:  # noqa: BLE001
        err = f"{type(exc).__name__}: {exc}"
        return {"recorded": 0, "error": err, "failure_recorded": bool(record_failure(store, "record", err))}
