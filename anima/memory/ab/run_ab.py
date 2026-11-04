# Copyright 2026 Anshul48
# SPDX-License-Identifier: Apache-2.0
"""Drive the memory A/B through `anima run` and report it (stdlib only).

  A1, A2   the worker with NO memory (run twice: A1 vs A2 is the run-to-run noise of the worker itself)
  B        `--memory trace --memory-exclude-self --memory-no-record`: the same worker, with similar past
           jobs from the memory put in front of the prompt. A task never recalls its own earlier jobs.

One attempt per task (`--harness NAME`, no ladder, no retry), so "first-time pass" means what it says.

  python3 -m anima.memory.ab.run_ab run    --arm A1 --tasks DIR --out OUT --python PY --profile anima.yaml [--jobs 3] [--only ID]
  python3 -m anima.memory.ab.run_ab report --out OUT [--md FILE]

Tokens come from the `run.usage` event the Muse CLI emits (stored in hand.json by anima run);
nothing is estimated. The Muse weekly allowance is read with `muse usage` before and after a batch.
"""
from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
import time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

ARMS = ("A1", "A2", "B")


def allowance():
    try:
        r = subprocess.run(["muse", "usage"], capture_output=True, text=True, timeout=60)
        return " | ".join(ln.strip() for ln in r.stdout.splitlines() if ln.startswith(("Window", "Weekly")))
    except (OSError, subprocess.SubprocessError):
        return "muse usage unavailable"


def usage_numbers(u):
    """(input, output, cached) summed over models in a run.usage payload; None if absent."""
    if not isinstance(u, dict):
        return None
    ms = u.get("models") or []
    if not ms:
        return None
    return tuple(sum(int(m.get(k) or 0) for m in ms) for k in ("input_tokens", "output_tokens", "cached_tokens"))


def summarize(run_root: Path, arm: str, task: str, exit_code: int, seconds: float):
    res = {"arm": arm, "task": task, "exit": exit_code, "seconds": round(seconds, 1), "verdict": "NOT RUN"}
    runs = sorted(p for p in run_root.glob("*") if p.is_dir())
    if not runs:
        return res
    rd = runs[-1]
    res["run_dir"] = str(rd)
    aj = next(iter(sorted((rd / "attempts").glob("*/attempt.json"))), None)
    if aj:
        a = json.loads(aj.read_text())
        h = json.loads((aj.parent / "hand.json").read_text()) if (aj.parent / "hand.json").is_file() else {}
        tok = usage_numbers(h.get("usage"))
        res.update(verdict=a.get("verdict"), failed_rule=a.get("failed_rule"), digest=(a.get("digest") or "")[:200],
                   said_done=a.get("said_done"), wall_seconds=a.get("wall_seconds"), failure_class=a.get("failure_class"),
                   input_tokens=tok[0] if tok else None, output_tokens=tok[1] if tok else None,
                   cached_tokens=tok[2] if tok else None, summary=(h.get("summary") or "")[-300:])
    ch = rd / "decisions.jsonl"
    if ch.is_file():
        for ln in ch.read_text().splitlines():
            ev = json.loads(ln)
            if ev.get("kind") == "decision.made" and (ev.get("data") or {}).get("decision") == "memory-recall":
                d = ev["data"]
                res.update(memory_injected=d.get("injected"), memory_hits=[(h["task"], h["score"]) for h in d.get("hits", [])],
                           memory_error=d.get("error"), memory_block_chars=d.get("block_chars"))
    return res


def one(args, arm, task_dir: Path):
    task = task_dir.name
    root = Path(args.out) / arm / task
    done = root / "result.json"
    if done.is_file():
        return json.loads(done.read_text())
    root.mkdir(parents=True, exist_ok=True)
    cmd = [args.python, "-m", "anima.harness", "--profile", args.profile, "run", "--task", str(task_dir),
           "--harness", args.harness, "--runs-dir", str(root.resolve())]
    if arm == "B":
        cmd += ["--memory", "trace", "--memory-store", str(Path(args.store).resolve()), "--memory-exclude-self", "--memory-no-record"]
    t0 = time.time()
    r = subprocess.run(cmd, capture_output=True, text=True, timeout=args.timeout)
    (root / "anima-run.log").write_text(r.stdout + "\n--- stderr ---\n" + r.stderr)
    res = summarize(root, arm, task, r.returncode, time.time() - t0)
    done.write_text(json.dumps(res, indent=1) + "\n")
    print(f"[{arm}] {task:32s} {res['verdict']:8s} tokens in/out/cached {res.get('input_tokens')}/{res.get('output_tokens')}/{res.get('cached_tokens')}  {res['seconds']:.0f}s"
          + (f"  memory hits {len(res.get('memory_hits') or [])}" if arm == "B" else ""), flush=True)
    return res


def cmd_run(args):
    tasks = sorted(p for p in Path(args.tasks).iterdir() if (p / "task.json").is_file() and (not args.only or p.name in args.only))
    before = allowance()
    print(f"arm {args.arm}: {len(tasks)} tasks, {args.jobs} at a time. Muse allowance before: {before}", flush=True)
    with ThreadPoolExecutor(args.jobs) as ex:
        list(ex.map(lambda t: one(args, args.arm, t), tasks))
    after = allowance()
    line = f"{time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime())} arm {args.arm} tasks {[t.name for t in tasks]}\n  before: {before}\n  after:  {after}\n"
    with open(Path(args.out) / "allowance.log", "a") as f:
        f.write(line)
    print(line, flush=True)
    return 0


def load_all(out: Path):
    rows = {}
    for arm in ARMS:
        for f in sorted((out / arm).glob("*/result.json")) if (out / arm).is_dir() else []:
            r = json.loads(f.read_text())
            rows.setdefault(r["task"], {})[arm] = r
    return rows


def cmd_report(args):
    rows = load_all(Path(args.out))
    tasks = sorted(rows)
    lines = []
    w = lines.append
    w("| task | A1 | A2 | B | memory hits in B (task, similarity) |")
    w("|---|---|---|---|---|")
    for t in tasks:
        cells = []
        for arm in ARMS:
            r = rows[t].get(arm)
            cells.append("-" if not r else f"{r['verdict']} ({(r.get('input_tokens') or 0) + (r.get('output_tokens') or 0):,} tok, {r['seconds']:.0f}s)")
        hits = rows[t].get("B", {}).get("memory_hits") or []
        w(f"| {t} | {cells[0]} | {cells[1]} | {cells[2]} | " + ("; ".join(f"{a} {b:.2f}" for a, b in hits) or "none") + " |")
    w("")
    w("| arm | tasks run | first-time PASS | FAIL | NOT RUN | input tokens | output tokens | cached tokens | input+output per task (median) |")
    w("|---|---|---|---|---|---|---|---|---|")
    for arm in ARMS:
        rs = [rows[t][arm] for t in tasks if arm in rows[t]]
        if not rs:
            continue
        def tot(k):
            return sum(r.get(k) or 0 for r in rs)
        per = sorted((r.get("input_tokens") or 0) + (r.get("output_tokens") or 0) for r in rs)
        med = per[len(per) // 2] if per else 0
        w(f"| {arm} | {len(rs)} | {sum(r['verdict'] == 'PASS' for r in rs)} | {sum(r['verdict'] == 'FAIL' for r in rs)} | "
          f"{sum(r['verdict'] == 'NOT RUN' for r in rs)} | {tot('input_tokens'):,} | {tot('output_tokens'):,} | {tot('cached_tokens'):,} | {med:,} |")
    both = [t for t in tasks if "A1" in rows[t] and "A2" in rows[t] and "B" in rows[t]]
    if both:
        w("")
        a1 = sum(rows[t]["A1"]["verdict"] == "PASS" for t in both)
        a2 = sum(rows[t]["A2"]["verdict"] == "PASS" for t in both)
        b = sum(rows[t]["B"]["verdict"] == "PASS" for t in both)
        w(f"On the {len(both)} tasks that have all three arms: first-time PASS A1 {a1}, A2 {a2}, B {b}.")
        flips = [t for t in both if rows[t]["A1"]["verdict"] != rows[t]["A2"]["verdict"]]
        w(f"A1 and A2 (same setup, no memory) disagree on {len(flips)} task(s): {', '.join(flips) or 'none'}.")
        diff = [t for t in both if rows[t]["B"]["verdict"] != rows[t]["A1"]["verdict"] or rows[t]["B"]["verdict"] != rows[t]["A2"]["verdict"]]
        w(f"B differs from A1 or A2 on {len(diff)} task(s): {', '.join(diff) or 'none'}.")
    if args.store and (Path(args.store) / "passages.jsonl").is_file():
        mem_tasks = {json.loads(ln)["task"] for ln in (Path(args.store) / "passages.jsonl").read_text().splitlines() if ln.strip()}
        lib = lambda t: t.split("-")[0]  # noqa: E731
        rows_b = [(t, rows[t]["B"]) for t in tasks if "B" in rows[t]]
        have = [(t, r) for t, r in rows_b if any(lib(m) == lib(t) and m != t for m in mem_tasks)]
        got = [t for t, r in have if any(lib(h[0]) == lib(t) for h in (r.get("memory_hits") or []))]
        top1 = [t for t, r in have if r.get("memory_hits") and lib(r["memory_hits"][0][0]) == lib(t)]
        none_ = [t for t, r in rows_b if not (r.get("memory_hits") or [])]
        w("")
        w(f"Retrieval check (arm B, memory holds {len(mem_tasks)} tasks): {len(have)} of {len(rows_b)} tasks have a past job from the same library "
          f"in memory; recall returned a same-library job for {len(got)} of them and ranked one first for {len(top1)}. "
          f"Recall returned nothing for {len(none_)} task(s){': ' + ', '.join(none_) if none_ else ''}.")
    text = "\n".join(lines)
    print(text)
    if args.md:
        Path(args.md).write_text(text + "\n")
    return 0


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    sub = ap.add_subparsers(dest="cmd", required=True)
    p = sub.add_parser("run")
    p.add_argument("--arm", choices=ARMS, required=True)
    p.add_argument("--tasks", required=True)
    p.add_argument("--out", required=True)
    p.add_argument("--python", default=sys.executable)
    p.add_argument("--profile", default="anima.yaml")
    p.add_argument("--harness", default="muse")
    p.add_argument("--store", default=".anima/trace", help="the memory used by arm B")
    p.add_argument("--jobs", type=int, default=3)
    p.add_argument("--only", action="append")
    p.add_argument("--timeout", type=int, default=2400)
    p.set_defaults(fn=cmd_run)
    p = sub.add_parser("report")
    p.add_argument("--out", required=True)
    p.add_argument("--md")
    p.add_argument("--store", help="the memory arm B used (for the retrieval check)")
    p.set_defaults(fn=cmd_report)
    a = ap.parse_args(argv)
    return a.fn(a)


if __name__ == "__main__":
    sys.exit(main())
