# Copyright 2026 Anshul48
# SPDX-License-Identifier: Apache-2.0
"""Local web server for the SST screen.  Binds 127.0.0.1 only.  Stdlib only.

Read endpoints are GET; the one write endpoint (POST /api/command) only ever
writes a command file (see commands.py).  It checks the Host header (DNS
rebinding), the Origin header, and a per-process token handed out by
/api/meta, so a web page on another origin cannot write commands.
"""
from __future__ import annotations

import json
import os
import secrets
import sys
import webbrowser
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, urlparse

from . import commands as cmdmod
from . import source as srcmod

UI_DIR = Path(os.environ.get("ANIMA_UI_DIR") or srcmod.REPO_ROOT / "ui").resolve()
STATIC = {
    "/": ("index.html", "text/html; charset=utf-8"),
    "/index.html": ("index.html", "text/html; charset=utf-8"),
    "/app.js": ("app.js", "text/javascript; charset=utf-8"),
    "/app.css": ("app.css", "text/css; charset=utf-8"),
    "/favicon.svg": ("favicon.svg", "image/svg+xml"),
}
MAX_BODY = 8 * 1024


def make_handler(src, token, port):
    allowed_hosts = {f"127.0.0.1:{port}", f"localhost:{port}"}

    class Handler(BaseHTTPRequestHandler):
        server_version = "anima-ui"

        def log_message(self, fmt, *args):  # quiet: one line per request on stderr
            if os.environ.get("ANIMA_UI_LOG"):
                sys.stderr.write("ui: " + fmt % args + "\n")

        # ---- helpers
        def _send(self, code, body, ctype="application/json; charset=utf-8"):
            if isinstance(body, (dict, list)):
                body = json.dumps(body).encode()
            elif isinstance(body, str):
                body = body.encode()
            self.send_response(code)
            self.send_header("Content-Type", ctype)
            self.send_header("Content-Length", str(len(body)))
            self.send_header("Cache-Control", "no-store")
            self.send_header("X-Content-Type-Options", "nosniff")
            self.send_header("Content-Security-Policy",
                             "default-src 'self'; style-src 'self' 'unsafe-inline'; img-src 'self' data:")
            self.end_headers()
            self.wfile.write(body)

        def _host_ok(self):
            return self.headers.get("Host", "") in allowed_hosts

        def _upto(self, q):
            v = q.get("upto", [None])[0]
            return int(v) if v is not None and v.isdigit() else None

        # ---- GET
        def do_GET(self):
            if not self._host_ok():
                return self._send(HTTPStatus.FORBIDDEN, {"error": "bad host"})
            u = urlparse(self.path)
            q = parse_qs(u.query)
            try:
                if u.path in STATIC:
                    name, ctype = STATIC[u.path]
                    f = UI_DIR / name
                    if not f.is_file():
                        return self._send(HTTPStatus.NOT_FOUND, {"error": f"{name} missing"})
                    return self._send(HTTPStatus.OK, f.read_bytes(), ctype)
                if u.path == "/api/meta":
                    d = src.describe()
                    d["token"] = token
                    d["hand_run"] = bool(cmdmod.hand_run_path())
                    d["verbs"] = cmdmod.VERBS
                    d["harnesses"] = cmdmod.HARNESSES
                    d["priorities"] = cmdmod.PRIORITIES
                    d["total"] = len(src.timeline()) if src.demo else None
                    return self._send(HTTPStatus.OK, d)
                if u.path == "/api/timeline":
                    return self._send(HTTPStatus.OK, src.timeline())
                if u.path == "/api/tree":
                    snap = src.snapshot(self._upto(q))
                    return self._send(HTTPStatus.OK, {
                        "tree": snap["tree"], "now": snap["now"], "n": snap["n"], "total": snap["total"],
                        "pending": [{k: v for k, v in c.items()} for c in snap["pending"]]})
                if u.path == "/api/events":
                    node = q.get("node", [""])[0]
                    snap = src.snapshot(self._upto(q))
                    evs = src.events_for(snap, node)
                    if evs is None:
                        return self._send(HTTPStatus.NOT_FOUND, {"error": "no such node"})
                    return self._send(HTTPStatus.OK, {"node": node, "events": evs})
            except Exception as e:  # report, never crash the server
                return self._send(HTTPStatus.INTERNAL_SERVER_ERROR, {"error": f"{type(e).__name__}: {e}"})
            return self._send(HTTPStatus.NOT_FOUND, {"error": "not found"})

        # ---- POST /api/command
        def do_POST(self):
            if not self._host_ok():
                return self._send(HTTPStatus.FORBIDDEN, {"error": "bad host"})
            origin = self.headers.get("Origin")
            if origin and origin not in {f"http://127.0.0.1:{port}", f"http://localhost:{port}"}:
                return self._send(HTTPStatus.FORBIDDEN, {"error": "bad origin"})
            if urlparse(self.path).path != "/api/command":
                return self._send(HTTPStatus.NOT_FOUND, {"error": "not found"})
            if not secrets.compare_digest(self.headers.get("X-Anima-Token", ""), token):
                return self._send(HTTPStatus.FORBIDDEN, {"error": "bad token"})
            try:
                n = int(self.headers.get("Content-Length", "0"))
                if n <= 0 or n > MAX_BODY:
                    return self._send(HTTPStatus.BAD_REQUEST, {"error": "body size"})
                body = json.loads(self.rfile.read(n))
                cmd = cmdmod.build_command(body.get("verb"), body.get("target"), body.get("args"),
                                           body.get("reason", ""), "ui")
            except (ValueError, cmdmod.CommandError) as e:
                return self._send(HTTPStatus.BAD_REQUEST, {"error": str(e)})
            out = {"command": cmd, "cli": cmdmod.cli_line(cmd, src.state if src.state else None),
                   "commands_dir": str(src.commands), "demo": src.demo}
            if body.get("dry_run"):
                out["written"] = None
                return self._send(HTTPStatus.OK, out)
            try:
                out["written"] = str(cmdmod.write_command(src.commands, cmd))
            except OSError as e:
                return self._send(HTTPStatus.INTERNAL_SERVER_ERROR, {"error": f"cannot write: {e}"})
            if body.get("forward") and cmd["verb"] == "cancel":
                if src.demo:
                    out["forwarded"] = {"ran": False, "message": "replay mode: nothing real to cancel"}
                else:
                    ran, msg = cmdmod.forward_cancel(cmd, src.jobs)
                    out["forwarded"] = {"ran": ran, "message": msg}
            return self._send(HTTPStatus.OK, out)

    return Handler


def serve(src, host="127.0.0.1", port=8765, open_browser=False):
    assert host == "127.0.0.1", "the SST screen is local-only"
    token = secrets.token_urlsafe(18)
    srv = ThreadingHTTPServer((host, port), make_handler(src, token, port))
    d = src.describe()
    url = f"http://127.0.0.1:{port}/"
    print(f"ANIMA SST screen: {url}  ({d['mode']}; chains={d['chains']}; jobs={d['jobs']})", flush=True)
    print(f"command files go to: {d['commands']}", flush=True)
    if open_browser:
        webbrowser.open(url)
    try:
        srv.serve_forever()
    except KeyboardInterrupt:
        print("\nbye")
    finally:
        srv.server_close()
    return 0
