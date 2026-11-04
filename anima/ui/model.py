# Copyright 2026 Anshul48
# SPDX-License-Identifier: Apache-2.0
"""Read ANIMA's decision record and job folders; build the state space tree.

Stdlib only.  Two data sources, both read from disk every time (nothing is
cached beyond a file-signature check):

* a decision record: a JSONL file where every line is one decision and carries
  ``prev`` = SHA-256 of the full text of the line before it (first line:
  ``GENESIS``).  This is the same chain the repository's
  ``docs/evidence/flagship-run3/check_chain.py`` checks.  Events seen here are
  tamper-evident: the reader reports the first line whose link does not match.
* job folders: ``<jobs>/<id>/job.json`` + ``events.jsonl`` (the layout written
  by the ``hand-run`` supervisor).  These logs are NOT hash-chained; the tree
  marks them ``chained: false`` so nothing unchained is shown as sealed.

The tree is:   owner -> workstream -> task -> attempt
where an *attempt* is one try of a task by one harness (a rung of the ladder).
An escalation (gate FAIL -> next helper) is the edge between two attempts.
"""
from __future__ import annotations

import hashlib
import json
import re
import time
from datetime import datetime, timezone
from pathlib import Path

DECISIVE = ("decision.made", "task.done", "task.blocked")
ESC_SUFFIX = re.compile(r"-e(\d+)$")

# status names the UI knows (kept small on purpose)
QUEUED, RUNNING, VERIFIED, REJECTED = "queued", "running", "verified", "rejected"


# ---------------------------------------------------------------- time helpers
def parse_ts(value):
    """ISO-8601 (``...Z`` or offset) -> epoch seconds, or None."""
    if not isinstance(value, str):
        return None
    try:
        text = value.strip()
        if text.endswith("Z"):
            text = text[:-1] + "+00:00"
        dt = datetime.fromisoformat(text)
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return dt.timestamp()
    except ValueError:
        return None


def fmt_clock(epoch):
    if epoch is None:
        return "-"
    return datetime.fromtimestamp(epoch, timezone.utc).strftime("%H:%M:%S")


# ---------------------------------------------------------------- the chain
def harness_of(pool):
    """Display name of the harness behind a pool name (the pool name is kept too)."""
    p = (pool or "").lower()
    if "muse" in p:
        return "Muse Code"
    if "claude" in p:
        return "Claude Code"
    if "codex" in p:
        return "Codex"
    return pool or "unknown"


def read_chain(path):
    """Read a decision record.  Returns (events, verdict).

    ``events`` items: n (1-based line number), ts, epoch, kind, actor, task,
    data, id, prev, seal (SHA-256 of this line = what the next line must carry
    as ``prev``), link_ok (this line's ``prev`` matches the line before it).
    ``verdict``: ok, records, broken_at, why, sha256, head_match.
    """
    path = Path(path)
    raw = path.read_bytes()
    lines = [ln for ln in raw.split(b"\n") if ln]
    events, prev = [], "GENESIS"
    broken_at, why = None, None
    for n, line in enumerate(lines, start=1):
        seal = hashlib.sha256(line).hexdigest()
        try:
            ev = json.loads(line)
            if not isinstance(ev, dict):
                raise ValueError("not an object")
        except ValueError:
            ev = {"kind": "unreadable", "task": "", "data": {"line": n}}
            link_ok = False
            if broken_at is None:
                broken_at, why = n, "line is not valid JSON"
        else:
            link_ok = ev.get("prev") == prev
            if not link_ok and broken_at is None:
                broken_at, why = n, "does not match the line before it"
        events.append({
            "n": n,
            "ts": ev.get("ts"),
            "epoch": parse_ts(ev.get("ts")),
            "kind": ev.get("kind", ""),
            "actor": ev.get("actor", ""),
            "task": ev.get("task") or "",
            "data": ev.get("data") if isinstance(ev.get("data"), dict) else {},
            "id": ev.get("id"),
            "prev": ev.get("prev"),
            "supersedes": ev.get("supersedes") or [],
            "seal": seal,
            "link_ok": link_ok,
            "chained": True,
        })
        prev = seal
    digest = hashlib.sha256(raw).hexdigest()
    head_match = None
    head = path.with_name(path.name + ".head.json")
    if head.exists():
        try:
            head_match = json.loads(head.read_text())["sha256"] == digest
        except (ValueError, KeyError, OSError):
            head_match = None
    verdict = {
        "ok": broken_at is None and len(lines) > 0,
        "records": len(lines),
        "broken_at": broken_at,
        "why": why,
        "sha256": digest,
        "head_match": head_match,
        "path": str(path),
    }
    return events, verdict


def canon_task(ev):
    d = ev["data"]
    if d.get("original_task"):
        return d["original_task"]
    t = ev["task"]
    if t:
        return ESC_SUFFIX.sub("", t)
    return d.get("from_card") or ""


def rung_of(ev):
    r = ev["data"].get("rung")
    if isinstance(r, int):
        return r
    m = ESC_SUFFIX.search(ev["task"] or "")
    return int(m.group(1)) if m else 0


def _short(text, n=70):
    text = " ".join(str(text).split())
    return text if len(text) <= n else text[: n - 1] + "…"


def describe(ev):
    """One plain-English line for a record (never invents content)."""
    k, d = ev["kind"], ev["data"]
    if k == "heartbeat":
        return d.get("status") or "heartbeat"
    if k == "task.created":
        if d.get("from_card"):
            return f"retry created from {d['from_card']} ({d.get('from_pool')} -> {d.get('to_pool')})"
        return f"created for {d.get('pool', '?')}, rung {d.get('rung', 0)}"
    if k == "task.started":
        return f"started on {d.get('pool', '?')}"
    if k == "task.done":
        v = (d.get("outcome") or {}).get("verified")
        return "verified by the hidden checker" if v else "marked done, not verified"
    if k == "task.blocked":
        parts = [p.strip() for p in d.get("reason", "").split(";")]
        rule = parts[0] or "gate"
        why = parts[-1] if len(parts) > 1 else ""
        return f"gate rejected ({rule}): " + _short(why, 80)
    if k == "decision.made":
        return f"{d.get('decision', 'decision')} to {d.get('to_pool', '?')} ({d.get('reason', '')})"
    if k == "artifact.added":
        a = d.get("attempt")
        if a:
            rule = f", rule {a['failed_rule']}" if a.get("failed_rule") else ""
            return f"attempt recorded: gate {a.get('gate_verdict')} in {a.get('wall_seconds', 0):.0f} s{rule}"
        return f"evidence added: {d.get('name', '?')} ({d.get('evidence_bytes', '?')} B)"
    return k or "record"


def _cost_of(data):
    """Dollar / token cost if (and only if) the record carries it."""
    c = data.get("cost")
    if isinstance(c, dict):
        return c.get("usd"), c.get("tokens")
    usd = data.get("cost_usd", data.get("usd"))
    tok = data.get("tokens")
    ok = lambda v: v if isinstance(v, (int, float)) and not isinstance(v, bool) else None
    return ok(usd), ok(tok)


class _Attempt:
    def __init__(self, rung):
        self.rung, self.pool, self.state = rung, None, None
        self.started, self.wall, self.gate, self.rule = None, None, None, None
        self.digest, self.job_id, self.via = None, None, None
        self.said_done, self.usd, self.tokens = None, None, None
        self.events = []
        self.finished_epoch = None


def _last_for(evs):
    if not evs:
        return None
    decisive = [e for e in evs if e["kind"] in DECISIVE]
    e = (decisive or evs)[-1]
    return {
        "n": e["n"], "ts": e["ts"], "kind": e["kind"], "actor": e["actor"],
        "text": describe(e), "seal": e["seal"][:12], "link_ok": e["link_ok"],
        "chained": e.get("chained", True),
    }


def _empty_pending(commands, names):
    out = []
    for c in commands:
        t = c.get("target") or {}
        if t.get("task") in names or t.get("node") in names:
            out.append({"id": c.get("id"), "verb": c.get("verb"), "args": c.get("args"),
                        "issued_by": c.get("issued_by"), "issued_at": c.get("issued_at"),
                        "file": c.get("_file")})
    return out


def build_chain_workstream(events, name, *, now=None, commands=()):
    """Workstream node (dict) for one decision record, plus a flat task list."""
    groups = {}
    order = []
    ws_events = []
    for ev in events:
        t = canon_task(ev)
        if not t:
            ws_events.append(ev)
            continue
        if t not in groups:
            groups[t] = {}
            order.append(t)
        atts = groups[t]
        r = rung_of(ev)
        a = atts.setdefault(r, _Attempt(r))
        a.events.append(ev)
        k, d = ev["kind"], ev["data"]
        if d.get("pool") and not a.pool:
            a.pool = d["pool"]
        if d.get("to_pool") and k == "decision.made":
            a.pool = a.pool or d["to_pool"]
            a.via = ev
        if k == "task.created" and a.state is None:
            a.state = QUEUED
        elif k == "task.started":
            a.state = RUNNING
            a.started = d.get("started_at") or ev["epoch"]
            a.job_id = d.get("job_id")
        elif k == "task.done" and (d.get("outcome") or {}).get("verified"):
            a.state, a.finished_epoch = VERIFIED, ev["epoch"]
        elif k == "task.blocked":
            a.state, a.finished_epoch = REJECTED, ev["epoch"]
            a.digest = d.get("reason")
        elif k == "artifact.added" and isinstance(d.get("attempt"), dict):
            at = d["attempt"]
            a.pool = at.get("pool") or a.pool
            a.wall, a.gate = at.get("wall_seconds"), at.get("gate_verdict")
            a.rule, a.job_id = at.get("failed_rule"), at.get("hand") or a.job_id
            a.digest = at.get("digest") or a.digest
            a.said_done = at.get("said_done")
            a.finished_epoch = at.get("finished_at") or a.finished_epoch
            if a.gate == "PASS":
                a.state = VERIFIED
            elif a.gate == "FAIL":
                a.state = REJECTED
        usd, tok = _cost_of(d)
        if usd is not None:
            a.usd = (a.usd or 0) + usd
        if tok is not None:
            a.tokens = (a.tokens or 0) + tok

    tasks = []
    for num, t in enumerate(order, start=1):
        atts = [groups[t][r] for r in sorted(groups[t])]
        att_nodes = []
        for a in atts:
            running = a.state == RUNNING
            wall = a.wall
            if wall is None and running and a.started and now:
                wall = max(0.0, now - a.started)
            pend = _empty_pending(commands, {f"att:{t}:{a.rung}"})
            node = {
                "id": f"att:{t}:{a.rung}", "type": "attempt",
                "label": f"rung {a.rung}", "status": a.state or QUEUED,
                "harness": harness_of(a.pool), "pool": a.pool, "rung": a.rung,
                "job_id": a.job_id, "gate": a.gate, "rule": a.rule,
                "digest": a.digest if a.state == REJECTED else None,
                "said_done": a.said_done,
                "started_epoch": a.started, "running": running,
                "cost": {"wall_s": wall, "usd": a.usd, "tokens": a.tokens},
                "via": (None if not a.via else describe(a.via)),
                "last": _last_for(a.events), "events": [e["n"] for e in a.events],
                "pending": pend, "chained": True, "children": [],
            }
            att_nodes.append(node)
        statuses = [n["status"] for n in att_nodes]
        if VERIFIED in statuses:
            status = VERIFIED
        else:
            status = statuses[-1] if statuses else QUEUED
        tevs = [e for a in atts for e in a.events]
        tevs.sort(key=lambda e: e["n"])
        last_att = att_nodes[-1]
        pend = _empty_pending(commands, {t, f"task:{t}"})
        overlay = None
        for p in pend:
            if p["verb"] in ("pause", "cancel") and status not in (VERIFIED,):
                overlay = f"{p['verb']} requested"
        wall_total = sum((n["cost"]["wall_s"] or 0) for n in att_nodes)
        usd_vals = [n["cost"]["usd"] for n in att_nodes if n["cost"]["usd"] is not None]
        tasks.append({
            "id": f"task:{t}", "type": "task", "num": num, "label": t,
            "status": status, "overlay": overlay,
            "harness": last_att["harness"], "pool": last_att["pool"],
            "rung": last_att["rung"],
            "started_epoch": min([n["started_epoch"] for n in att_nodes if n["started_epoch"]] or [None]) if any(n["started_epoch"] for n in att_nodes) else None,
            "running": any(n["running"] for n in att_nodes),
            "cost": {"wall_s": wall_total, "usd": sum(usd_vals) if usd_vals else None, "tokens": None},
            "last": _last_for(tevs), "events": [e["n"] for e in tevs],
            "pending": pend, "chained": True, "children": att_nodes,
            "escalated": len(att_nodes) > 1,
        })
    ws_status = _roll_status([t["status"] for t in tasks])
    wall = sum(t["cost"]["wall_s"] or 0 for t in tasks)
    node = {
        "id": f"ws:{name}", "type": "workstream", "label": name,
        "status": ws_status, "harness": None,
        "running": any(t["running"] for t in tasks),
        "cost": {"wall_s": wall, "usd": None, "tokens": None},
        "last": _last_for(events), "events": [e["n"] for e in events],
        "pending": [], "chained": True, "children": tasks,
        "mode": next((e["data"].get("mode") for e in events if e["data"].get("mode")), None),
    }
    return node


def _roll_status(statuses):
    if not statuses:
        return QUEUED
    if any(s == RUNNING for s in statuses):
        return RUNNING
    if all(s == VERIFIED for s in statuses):
        return VERIFIED
    if any(s == REJECTED for s in statuses):
        return REJECTED
    if any(s in ("failed", "cancelled") for s in statuses):
        return "failed"
    if any(s == QUEUED for s in statuses):
        return QUEUED
    return statuses[0]


# ---------------------------------------------------------------- job folders
JOB_STATUS = {"running": RUNNING, "queued": QUEUED, "waiting_net": "waiting", "backoff": "waiting",
              "done": "finished", "failed": "failed", "cancelled": "cancelled"}


def read_job(job_dir):
    job_dir = Path(job_dir)
    try:
        job = json.loads((job_dir / "job.json").read_text())
    except (OSError, ValueError):
        return None
    evs = []
    try:
        for i, line in enumerate((job_dir / "events.jsonl").read_text().splitlines(), start=1):
            try:
                e = json.loads(line)
            except ValueError:
                continue
            evs.append({"n": i, "ts": e.get("ts"), "epoch": parse_ts(e.get("ts")),
                        "kind": e.get("event", ""), "actor": "job-supervisor", "task": job.get("id", ""),
                        "data": {"detail": e.get("detail", "")}, "seal": "", "link_ok": None,
                        "chained": False, "id": None, "prev": None, "supersedes": []})
    except OSError:
        pass
    job["_events"] = evs
    job["_mtime"] = (job_dir / "job.json").stat().st_mtime
    return job


def read_jobs(jobs_dir, limit=30, prefix=None):
    """Most recently changed job folders first (bounded: never scans unboundedly)."""
    jobs_dir = Path(jobs_dir)
    try:
        names = [p for p in jobs_dir.iterdir() if p.is_dir() and (not prefix or p.name.startswith(prefix))]
    except OSError:
        return []
    stamped = []
    for p in names:
        try:
            stamped.append(((p / "job.json").stat().st_mtime, p))
        except OSError:
            continue
    stamped.sort(reverse=True)
    out = []
    for _, p in stamped[:limit]:
        j = read_job(p)
        if j:
            out.append(j)
    return out


def build_jobs_workstream(jobs, name, *, now=None, commands=()):
    now = now or time.time()
    tasks = []
    for num, j in enumerate(jobs, start=1):
        jid = j.get("id", "?")
        status = JOB_STATUS.get(j.get("state"), j.get("state") or "unknown")
        if j.get("cancel_requested") and status in (RUNNING, QUEUED, "waiting"):
            status_overlay = "cancel requested"
        else:
            status_overlay = None
        att_nodes = []
        for a in j.get("attempts", []):
            st = JOB_STATUS.get(a.get("state"), a.get("state") or "unknown")
            secs = a.get("seconds")
            running = a.get("state") == "running"
            if secs is None and running and a.get("t0"):
                secs = max(0.0, now - a["t0"])
            att_nodes.append({
                "id": f"jatt:{jid}:{a.get('n')}", "type": "attempt", "label": f"attempt {a.get('n')}",
                "status": st, "harness": harness_of(a.get("account")), "pool": a.get("account"),
                "rung": a.get("n"), "job_id": jid, "gate": None, "rule": None,
                "digest": a.get("detail"), "said_done": None,
                "started_epoch": a.get("t0"), "running": running,
                "cost": {"wall_s": secs, "usd": None, "tokens": None},
                "via": a.get("classification"), "last": None, "events": [], "pending": [],
                "chained": False, "children": [],
            })
        evs = j.get("_events", [])
        last = evs[-1] if evs else None
        wall = sum((n["cost"]["wall_s"] or 0) for n in att_nodes)
        pend = _empty_pending(commands, {jid, f"job:{jid}"})
        overlay = status_overlay
        for p in pend:
            if p["verb"] in ("pause", "cancel"):
                overlay = f"{p['verb']} requested"
        accounts = [a for a in (j.get("accounts") or [])]
        lastatt = att_nodes[-1] if att_nodes else None
        tasks.append({
            "id": f"job:{jid}", "type": "task", "num": num, "label": jid, "status": status,
            "overlay": overlay,
            "harness": (lastatt["harness"] if lastatt else harness_of(accounts[0] if accounts else None)),
            "pool": (lastatt["pool"] if lastatt else None), "rung": None,
            "started_epoch": (lastatt or {}).get("started_epoch"),
            "running": any(n["running"] for n in att_nodes),
            "cost": {"wall_s": wall, "usd": None, "tokens": None},
            "last": None if not last else {
                "n": last["n"], "ts": last["ts"], "kind": last["kind"], "actor": "job log",
                "text": f"{last['kind']}: {_short(last['data'].get('detail', ''), 60)}",
                "seal": "", "link_ok": None, "chained": False},
            "events": [e["n"] for e in evs], "pending": pend, "chained": False,
            "children": att_nodes, "escalated": len(att_nodes) > 1,
            "model": j.get("model"), "job_state": j.get("state"),
        })
    return {
        "id": f"ws:{name}", "type": "workstream", "label": name,
        "status": _roll_status([t["status"] for t in tasks if t["status"] != "finished"] or ["finished"]),
        "harness": None, "running": any(t["running"] for t in tasks),
        "cost": {"wall_s": sum(t["cost"]["wall_s"] or 0 for t in tasks), "usd": None, "tokens": None},
        "last": None, "events": [], "pending": [], "chained": False, "children": tasks,
        "mode": "not hash-chained",
    }


# ---------------------------------------------------------------- whole tree
def count_nodes(tree):
    c = {"tasks": 0, "verified": 0, "running": 0, "rejected": 0, "escalated": 0, "queued": 0, "other": 0}
    for ws in tree["children"]:
        for t in ws["children"]:
            c["tasks"] += 1
            s = t["status"]
            if s in c:
                c[s] += 1
            else:
                c["other"] += 1
            if t.get("escalated"):
                c["escalated"] += 1
    return c


def build_tree(workstreams, *, now=None, chain=None):
    """Owner root over the given workstream nodes."""
    root = {
        "id": "owner", "type": "owner", "label": "owner",
        "status": _roll_status([w["status"] for w in workstreams]),
        "harness": None, "running": any(w["running"] for w in workstreams),
        "cost": {"wall_s": sum(w["cost"]["wall_s"] or 0 for w in workstreams), "usd": None, "tokens": None},
        "last": None, "events": [], "pending": [], "chained": bool(chain),
        "children": workstreams,
    }
    root["counts"] = count_nodes(root)
    if chain:
        root["chain"] = chain
    return root


def find_node(tree, node_id):
    if tree["id"] == node_id:
        return tree
    for c in tree.get("children", []):
        r = find_node(c, node_id)
        if r:
            return r
    return None


def task_by_number(tree, n):
    for ws in tree["children"]:
        for t in ws["children"]:
            if t.get("num") == n:
                return t
    return None
