# Copyright 2026 Anshul48
# SPDX-License-Identifier: Apache-2.0
"""Where the tree's data comes from: decision record(s), job folders, command files.

Everything is re-read from disk on every snapshot (the files are small and the
caller decides how often to poll), so a live run shows up without a restart.
"""
from __future__ import annotations

import hashlib
import os
import re
import tempfile
import time
from pathlib import Path

from . import commands as cmdmod
from . import model

REPO_ROOT = Path(__file__).resolve().parents[2]
DEMO_CHAIN = REPO_ROOT / "docs" / "evidence" / "flagship-run3" / "decisions.jsonl"
_RUN_ID = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_.\-]{0,120}$")


def anima_home():
    """The one state root, shared with `anima run` and `anima memory`: $ANIMA_HOME, else ~/.anima."""
    return Path(os.environ.get("ANIMA_HOME") or (Path.home() / ".anima"))


def runs_dir():
    return anima_home() / "runs"


def resolve_run(run="latest"):
    """The decision record of one real `anima run` under <state root>/runs: a run folder name, or 'latest'.
    The name is validated (no path parts) so it cannot point outside the runs folder."""
    root = runs_dir()
    if run in (None, "", "latest"):
        found = sorted(root.glob("*/decisions.jsonl"), key=lambda q: q.stat().st_mtime) if root.is_dir() else []
        if not found:
            raise SystemExit(f"anima: no runs yet in {root}. Run `anima run --task tiny-bug` first, or use --demo for the recorded run.")
        return found[-1]
    if not _RUN_ID.match(run) or ".." in run:
        raise SystemExit(f"anima: bad run name {run!r} (a folder name under {root}, or 'latest')")
    chain = root / run / "decisions.jsonl"
    if not chain.is_file() or chain.is_symlink() or not chain.resolve().is_relative_to(root.resolve()):
        raise SystemExit(f"anima: no run {run!r} with a decisions.jsonl in {root}")
    return chain


class Source:
    def __init__(self, chains=(), jobs=None, commands=None, demo=False, state=None,
                 names=None, job_limit=30, job_prefix=None):
        self.demo = demo
        self.chains = [Path(c) for c in chains]
        self.names = list(names or [])
        self.jobs = Path(jobs) if jobs else None
        self.job_limit, self.job_prefix = job_limit, job_prefix
        self.state = Path(state) if state else None
        if commands:
            self.commands = Path(commands)
        elif demo:
            # replay must never write into the evidence folder
            self.commands = Path(tempfile.gettempdir()) / "anima-ui-demo-commands"
        elif self.state:
            self.commands = self.state / "commands"
        else:
            self.commands = anima_home() / "commands"

    # ------------------------------------------------------------ construction
    @classmethod
    def from_args(cls, demo=False, state=None, chains=(), jobs=None, commands=None,
                  job_limit=30, job_prefix=None):
        chains = list(chains or [])
        if demo and not chains:
            chains = [DEMO_CHAIN]
        if state:
            st = Path(state)
            if not chains:   # may not exist yet: a live run creates it
                chains = [st / "decisions.jsonl"]
            if not jobs and (st / "jobs").is_dir():
                jobs = st / "jobs"
        names = [chain_name(c) for c in chains]
        return cls(chains=chains, jobs=jobs, commands=commands, demo=demo, state=state,
                   names=names, job_limit=job_limit, job_prefix=job_prefix)

    # ------------------------------------------------------------- snapshotting
    def describe(self):
        return {
            "mode": "demo" if self.demo else "live",
            "chains": [str(c) for c in self.chains],
            "jobs": str(self.jobs) if self.jobs else None,
            "commands": str(self.commands),
            "names": self.names,
        }

    def snapshot(self, upto=None):
        """Build the tree.  ``upto`` = show only the first N records of the first
        chain (replay).  Returns a dict: tree, now, n, total, events, job_events."""
        commands = cmdmod.list_commands(self.commands)
        wss, all_events, verdict_full = [], [], None
        now, n_shown, total = None, 0, 0
        for i, path in enumerate(self.chains):
            try:
                events, verdict = model.read_chain(path)
            except FileNotFoundError:   # live: the run has not written its record yet
                events, verdict = [], {"ok": False, "records": 0, "broken_at": None, "why": "waiting for the record file",
                                       "sha256": hashlib.sha256(b"").hexdigest(), "head_match": None,
                                       "path": str(path), "waiting": True}
            total += len(events)
            if i == 0:
                verdict_full = verdict
                if upto is not None:
                    events = events[: max(0, int(upto))]
            n_shown += len(events)
            if events:
                last_epoch = max((e["epoch"] for e in events if e["epoch"]), default=None)
                if last_epoch and (now is None or last_epoch > now):
                    now = last_epoch
            if self.demo:
                ref = now
            else:
                ref = time.time()
            wss.append(model.build_chain_workstream(events, self.names[i], now=ref, commands=commands))
            all_events.append(events)
        job_events = {}
        if self.jobs:
            jobs = model.read_jobs(self.jobs, limit=self.job_limit, prefix=self.job_prefix)
            for j in jobs:
                job_events[f"job:{j['id']}"] = j["_events"]
            wss.append(model.build_jobs_workstream(jobs, chain_name(self.jobs), now=time.time(), commands=commands))
        if not self.demo:
            now = time.time()
        chain = None
        if verdict_full:
            pre = all_events[0] if all_events else []
            prefix_ok = all(e["link_ok"] for e in pre)
            chain = dict(verdict_full)
            chain["shown"] = len(pre)
            chain["shown_ok"] = prefix_ok and len(pre) > 0
        tree = model.build_tree(wss, now=now, chain=chain)
        return {
            "tree": tree, "now": now, "n": n_shown, "total": total,
            "events": all_events[0] if all_events else [], "all_events": all_events,
            "job_events": job_events, "pending": commands,
        }

    def events_for(self, snap, node_id):
        """Full records (dicts for the UI) behind a node, oldest first."""
        node = model.find_node(snap["tree"], node_id)
        if node is None:
            return None
        if node_id in snap["job_events"] or node_id.startswith("job:"):
            evs = snap["job_events"].get(node_id, [])
        elif node_id.startswith("jatt:"):
            jid = node_id.split(":")[1]
            evs = snap["job_events"].get(f"job:{jid}", [])
        else:
            by_n = {e["n"]: e for e in snap["events"]}
            evs = [by_n[n] for n in node.get("events", []) if n in by_n]
        return [{
            "n": e["n"], "ts": e["ts"], "kind": e["kind"], "actor": e["actor"], "task": e["task"],
            "text": model.describe(e) if e.get("chained", True) else e["kind"] + ": " + str(e["data"].get("detail", "")),
            "data": e["data"], "id": e.get("id"), "prev": e.get("prev"), "seal": e["seal"],
            "link_ok": e["link_ok"], "chained": e.get("chained", True),
        } for e in evs]

    def timeline(self):
        """Light list of every record of the first chain (for the replay scrubber)."""
        if not self.chains:
            return []
        try:
            events, _ = model.read_chain(self.chains[0])
        except FileNotFoundError:
            return []
        return [{"n": e["n"], "epoch": e["epoch"], "ts": e["ts"], "kind": e["kind"], "task": e["task"],
                 "text": model.describe(e)} for e in events]


def chain_name(path):
    p = Path(path)
    return p.parent.name if p.name == "decisions.jsonl" else p.stem if p.suffix else p.name
