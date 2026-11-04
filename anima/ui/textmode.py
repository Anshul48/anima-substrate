# Copyright 2026 Anshul48
# SPDX-License-Identifier: Apache-2.0
"""Plain-text rendering of the state space tree (narrow, no colour, no emoji).

Meant for a phone chat (paste inside a code block) and for a terminal.
"""
from __future__ import annotations

from . import model

TAG = {
    "queued": "[..]", "running": "[RUN]", "verified": "[OK]", "rejected": "[NO]",
    "failed": "[ERR]", "cancelled": "[X]", "finished": "[END]", "waiting": "[WAIT]",
}


def tag(node):
    t = TAG.get(node["status"], "[" + node["status"][:4].upper() + "]")
    return t


def secs(v):
    if v is None:
        return "-"
    return f"{v:,.0f} s"


def render(snap, source_desc, *, width=46, verbose=False):
    tree = snap["tree"]
    out = []
    c = tree["counts"]
    out.append("ANIMA state tree" + ("  [REPLAY, not live]" if source_desc["mode"] == "demo" else "  [LIVE]"))
    ch = tree.get("chain")
    if ch and ch.get("waiting"):
        out.append("waiting for the decision record to appear")
    elif ch:
        if snap["n"] < snap["total"]:
            out.append(f"record: first {snap['n']} of {snap['total']} lines linked: {'yes' if ch['shown_ok'] else 'NO'}")
        else:
            out.append(("chain OK" if ch["ok"] else f"CHAIN BROKEN at line {ch['broken_at']}")
                       + f", {ch['records']} records")
        out.append("fingerprint " + ch["sha256"][:16])
    out.append(f"{c['tasks']} tasks: {c['verified']} verified, {c['running']} running,"
               f" {c['escalated']} escalated")
    out.append(f"agent wall time, summed: {secs(tree['cost']['wall_s'])}")
    out.append("tokens and dollars: not in this record")
    out.append("")
    out.append("owner")
    for wi, ws in enumerate(tree["children"]):
        last_ws = wi == len(tree["children"]) - 1
        mode = f" ({ws['mode']})" if ws.get("mode") else ""
        out.append(("`- " if last_ws else "|- ") + f"{ws['label']}{mode}")
        pad = "   " if last_ws else "|  "
        for t in ws["children"]:
            ov = f" ({t['overlay']})" if t.get("overlay") else ""
            out.append(f"{pad}{t['num']:>2} {tag(t):<5} {t['label'][:width - 12]}{ov}")
            for a in t["children"]:
                gate = a.get("gate") or a["status"]
                extra = ""
                if a.get("rule"):
                    extra = f" {a['rule']}"
                out.append(f"{pad}      {a['label'].replace('rung ', 'r').replace('attempt ', 'a')} {a['harness']:<11} {gate:<8} {secs(a['cost']['wall_s']):>7}{extra}")
            if verbose and t.get("last"):
                l = t["last"]
                seal = f" seal {l['seal']}" if l.get("chained") else " (job log, unchained)"
                out.append(f"{pad}      last #{l['n']} {l['text']}{seal}")
    if snap.get("pending"):
        out.append("")
        out.append(f"{len(snap['pending'])} command file(s) waiting for anima:")
        for p in snap["pending"][-5:]:
            tgt = (p.get("target") or {}).get("task", "-")
            out.append(f"  {p['verb']} {tgt} ({p.get('issued_by')})")
    return "\n".join(out)
