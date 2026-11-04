# Copyright 2026 Anshul48
# SPDX-License-Identifier: Apache-2.0
"""anima memory: setup | status | ingest | record | recall | prompt | verify"""
from __future__ import annotations

import argparse
import json
import os
import shutil
import subprocess
import sys
from pathlib import Path

REQ = ["numpy==2.5.4", "blake3==1.0.11", "onnxruntime==1.31.1", "tokenizers==0.23.3"]
DEPS = ("numpy", "blake3", "onnxruntime", "tokenizers")
REPO_ROOT = Path(__file__).resolve().parents[2]  # directory that contains the `anima` package


def _home() -> Path:
    from .encoder import anima_home
    return anima_home()


def _venv_python() -> Path:
    return _home() / "memory-venv" / "bin" / "python"


def _have_deps() -> bool:
    try:
        for d in DEPS:
            __import__(d)
        return True
    except ImportError:
        return False


def _ensure_deps(argv):
    """Memory needs numpy/onnxruntime/tokenizers/blake3. If this interpreter lacks them but
    `anima memory setup` built a venv, re-run inside it; otherwise say what to do."""
    if _have_deps() or os.environ.get("ANIMA_MEMORY_REEXEC"):
        return
    vp = _venv_python()
    if vp.is_file():
        env = dict(os.environ, ANIMA_MEMORY_REEXEC="1",
                   PYTHONPATH=os.pathsep.join(filter(None, [str(REPO_ROOT), os.environ.get("PYTHONPATH", "")])))
        os.execve(str(vp), [str(vp), "-m", "anima.memory", *argv], env)
    print("anima memory: needs numpy, blake3, onnxruntime, tokenizers. Run:  python3 -m anima.memory setup",
          file=sys.stderr)
    sys.exit(2)


def _enc_arg(args):
    from .encoder import get_encoder
    return get_encoder(args.encoder)


# --------------------------------------------------------------------------- commands
def cmd_setup(args):
    home = _home()
    home.mkdir(parents=True, exist_ok=True)
    print(f"ANIMA_HOME = {home}")
    vp = _venv_python()
    if not args.check and not _have_deps() and not vp.is_file():
        venv = home / "memory-venv"
        if shutil.which("uv"):
            subprocess.check_call(["uv", "venv", str(venv), "--python", sys.executable])
            subprocess.check_call(["uv", "pip", "install", "--python", str(vp), *REQ])
        else:
            subprocess.check_call([sys.executable, "-m", "venv", str(venv)])
            subprocess.check_call([str(vp), "-m", "pip", "install", "--quiet", *REQ])
    from .stores import TRACE_REPO, find_trace_src
    src = find_trace_src()
    if src is None and not args.check:
        dest = home / "trace"
        if not dest.exists():
            subprocess.check_call(["git", "clone", "--depth", "1", TRACE_REPO, str(dest)])
        src = find_trace_src()
    from .encoder import download_model, model_ready
    if not args.check and not args.no_model and not model_ready():
        download_model()
    print(f"python deps      : {'ok in this interpreter' if _have_deps() else ('ok in ' + str(vp) if vp.is_file() else 'MISSING')}")
    print(f"TRACE source     : {src if src else 'MISSING (git clone ' + TRACE_REPO + ')'}")
    print(f"embedding model  : {'ok' if model_ready() else 'MISSING (about 90 MB; needs network once)'}")
    ok = (_have_deps() or vp.is_file()) and src is not None and (model_ready() or args.no_model)
    print("setup:", "READY" if ok else "NOT READY")
    return 0 if ok else 1


def _open(args, create):
    from .stores import open_store
    return open_store(args.store, _enc_arg(args), backend=args.backend, create=create)


def _apply_require(args):
    """--require trace/minilm: the run must use exactly that engine and encoder, or it stops (exit 3).
    Without it a missing TRACE source or model would quietly fall back to the labelled simple retriever."""
    spec = getattr(args, "require", None)
    if not spec:
        return
    want_b, _, want_e = spec.partition("/")
    for have, want, what in ((args.backend, want_b, "backend"), (args.encoder, want_e, "encoder")):
        if have not in ("auto", want):
            print(f"anima memory: --require {spec} conflicts with --{what} {have}", file=sys.stderr)
            raise SystemExit(3)
    args.backend, args.encoder = want_b, want_e


def _check_required(args, backend_kind, encoder_name):
    spec = getattr(args, "require", None)
    if spec:
        want_b, _, want_e = spec.partition("/")
        if backend_kind != want_b or not str(encoder_name or "").startswith(want_e):
            print(f"anima memory: --require {spec}, but this memory is {backend_kind}/{encoder_name}. Stopping.", file=sys.stderr)
            raise SystemExit(3)


def cmd_ingest(args):
    from .passages import load_path
    from .safety import locked
    from .stores import read_config
    _apply_require(args)
    store = Path(args.store)
    root = Path(read_config(store)["project_root"]) if read_config(store) else Path.cwd()
    passages, say = [], (lambda *a: print(*a, file=sys.stderr)) if args.json else print
    for p in args.paths:
        got = load_path(p, root=root, verify_chain=not args.no_verify_chain, task=args.task)
        say(f"read {len(got):3d} passages from {p}")
        passages += got
    with locked(store, exclusive=True):  # one writer at a time
        st = _open(args, create=True)
        try:
            _check_required(args, st.backend, st.enc.name)
            rep = st.ingest(passages)
            if args.json:
                print(json.dumps({"recorded": len(passages), "store_count": st.count(), "ingest": rep, "backend": st.label()}))
            else:
                say(f"backend: {st.label()}")
                say("ingest:", json.dumps(rep))
                say(f"store {store}: {st.count()} atoms searchable")
        finally:
            st.close()
    return 0


def cmd_record(args):
    from .passages import SCHEMA, load_path
    from .stores import read_config
    from .safety import locked, safe_dest, safe_id
    _apply_require(args)
    j = json.loads(Path(args.job).read_text())
    if j.get("schema") != SCHEMA:
        print(f"anima memory record: {args.job} is not {SCHEMA}", file=sys.stderr)
        return 2
    store = Path(args.store)
    try:  # the id becomes a file name: no '/', no '..', no symlink in the way
        dest = safe_dest(store / "jobs", safe_id(j.get("job_id") or j["task"], "job id") + ".json")
    except ValueError as exc:
        print(f"anima memory record: refused: {exc}", file=sys.stderr)
        return 2
    with locked(store, exclusive=True):
        shutil.copyfile(args.job, dest)
        root = Path(read_config(store)["project_root"]) if read_config(store) else Path.cwd()
        st = _open(args, create=True)
        try:
            _check_required(args, st.backend, st.enc.name)
            rep = st.ingest(load_path(dest, root=root))
            print("record:", json.dumps(rep), f"-> {dest}")
        finally:
            st.close()
    return 0


def cmd_recall(args):
    from .recall import recall
    _apply_require(args)
    res = recall(args.task, store_dir=args.store, k=args.k, min_score=args.min_score, exclude_tasks=args.exclude_task,
                 encoder=args.encoder, backend=args.backend, verify=not args.no_verify)
    if res.get("backend"):
        _check_required(args, res["backend_kind"], res["encoder"])
    if args.json:
        print(json.dumps(res, indent=1))
        return 0
    print(f"backend: {res['backend']}")
    if res.get("note"):
        print(res["note"])
    print(f"query  : {res['query'][:200]}")
    print(f"recall : {len(res['hits'])} hit(s) in {res['seconds']} s (min similarity {args.min_score})")
    for d in res.get("excluded_unverified", []):
        print(f"left out (source check {d['status']}): task {d['task']} - {d['detail']}")
    for h in res["hits"]:
        print(f"\n[{h['rank']}] similarity {h['score']:.3f}  task {h['task']}  "
              f"({h['meta'].get('verdict')}{', rule ' + h['meta']['failed_rule'] if h['meta'].get('failed_rule') else ''})")
        print(f"    {h['text']}")
        print(f"    source: {h['pointer']}")
        print(f"    source check: {h['source_check']} ({h['source_detail']})"
              + (f"   TRACE integrity: {h['trace_integrity']}" if h.get("trace_integrity") else ""))
    return 0


def cmd_prompt(args):
    from .hook import augment_prompt
    prompt = Path(args.prompt_file).read_text() if args.prompt_file else sys.stdin.read()
    task = Path(args.task_file).read_text() if args.task_file else None
    _apply_require(args)
    new, rep = augment_prompt(prompt, task_text=task, store_dir=args.store, k=args.k, min_score=args.min_score,
                              exclude_tasks=args.exclude_task, encoder=args.encoder, backend=args.backend, isolate=False)
    if getattr(args, "require", None) and rep.get("backend_kind"):
        _check_required(args, rep["backend_kind"], rep.get("encoder"))
    print(json.dumps(rep), file=sys.stderr)
    sys.stdout.write(new)
    return 0


def cmd_status(args):
    from .stores import find_trace_src, read_config
    cfg = read_config(args.store)
    if not cfg:
        print(f"no memory at {args.store}")
        return 1
    side = Path(args.store) / "passages.jsonl"
    n = sum(1 for ln in side.read_text().splitlines() if ln.strip()) if side.is_file() else 0
    print(json.dumps({**cfg, "passages": n, "trace_src": str(find_trace_src())}, indent=1))
    return 0


def cmd_verify(args):
    from .passages import verify_passage
    from .stores import Sidecar, read_config
    cfg = read_config(args.store)
    root = Path(cfg["project_root"]) if cfg else Path.cwd()
    side, bad = Sidecar(Path(args.store)), 0
    for r in side.rows.values():
        status, detail, _ = verify_passage(r, root)  # pointer AND the stored text, re-derived from the source
        bad += status != "OK"
        if status != "OK" or args.verbose:
            print(f"{status:8s} {r['doc_id']}  {detail}")
    print(f"verified {len(side.rows)} passages (source pointer and text): {len(side.rows) - bad} OK, {bad} not OK")
    return 1 if bad else 0


def build_parser():
    ap = argparse.ArgumentParser(prog="anima memory", description="ANIMA memory on TRACE: ingest finished jobs, recall similar past fixes.")
    sub = ap.add_subparsers(dest="cmd", required=True)

    def common(p, store=True):
        if store:
            p.add_argument("--store", default=None, help="memory folder (default: $ANIMA_MEMORY_STORE, else <ANIMA_HOME>/memory/trace)")
        p.add_argument("--encoder", choices=["auto", "minilm", "hash"], default="auto")
        p.add_argument("--backend", choices=["auto", "trace", "simple"], default="auto")
        p.add_argument("--require", choices=["trace/minilm"], help="stop (exit 3) unless the memory is the real TRACE engine with the MiniLM encoder; no silent fallback")

    p = sub.add_parser("setup", help="build the memory venv, clone TRACE, fetch the model (needs network once)")
    p.add_argument("--check", action="store_true", help="only report")
    p.add_argument("--no-model", action="store_true")
    p.set_defaults(fn=cmd_setup)
    

    p = sub.add_parser("ingest", help="turn decision logs / job records / attempt folders into passages in the TRACE index")
    p.add_argument("paths", nargs="+")
    p.add_argument("--no-verify-chain", action="store_true", help="ingest a decision log even if its hash chain does not verify")
    p.add_argument("--task", help="for `anima run` folders: a task.json, a task folder, or a folder of task folders (the run folder does not store the task text)")
    p.add_argument("--json", action="store_true", help="print one JSON report line on stdout (progress goes to stderr)")
    common(p)
    p.set_defaults(fn=cmd_ingest)

    p = sub.add_parser("record", help="add one finished-job record (anima-job-v1 JSON) to the memory")
    p.add_argument("job")
    common(p)
    p.set_defaults(fn=cmd_record)

    p = sub.add_parser("recall", help='top similar past jobs for a task text, with source pointers')
    p.add_argument("task")
    p.add_argument("-k", type=int, default=3)
    p.add_argument("--min-score", type=float, default=0.30)
    p.add_argument("--json", action="store_true")
    p.add_argument("--no-verify", action="store_true", help="skip re-reading the source files")
    p.add_argument("--exclude-task", action="append", default=[], help="never return this task's own records (repeatable)")
    common(p)
    p.set_defaults(fn=cmd_recall)

    p = sub.add_parser("prompt", help="print a worker prompt with the recalled fixes prepended (what `anima run --memory trace` does)")
    p.add_argument("--prompt-file", help="the worker prompt (default: stdin)")
    p.add_argument("--task-file", help="text to search with (default: the prompt itself)")
    p.add_argument("--exclude-task", action="append", default=[], help="never return this task's own records (repeatable)")
    p.add_argument("-k", type=int, default=3)
    p.add_argument("--min-score", type=float, default=0.30)
    common(p)
    p.set_defaults(fn=cmd_prompt)

    p = sub.add_parser("status")
    common(p, store=False)
    p.add_argument("--store", default=None)
    p.set_defaults(fn=cmd_status)

    p = sub.add_parser("verify", help="re-check every stored passage against its source (pointer and text)")
    p.add_argument("--store", default=None)
    p.add_argument("-v", "--verbose", action="store_true")
    p.set_defaults(fn=cmd_verify)
    return ap


def main(argv=None):
    argv = list(sys.argv[1:] if argv is None else argv)
    args = build_parser().parse_args(argv)
    if hasattr(args, "store") and not args.store:
        from .stores import default_store
        args.store = str(default_store())
    if args.cmd not in ("setup", "verify"):
        _ensure_deps(argv)
    return args.fn(args)
