#!/usr/bin/env python3
"""ANIMA site tool. Python 3.11+, standard library only, no network.

    python3 tools/site.py build         render docs/source/ + docs/status.json + docs/videos.json into docs/*.html
    python3 tools/site.py sync-readme   rewrite the generated tables inside README.md from docs/status.json
    python3 tools/site.py check         validate: status rules, generated files up to date, links, alt text,
                                        banned phrases, no outside files, size, contrast, repo files
    python3 tools/site.py social        render docs/source/social-preview.html to docs/img/social-preview.png (needs Playwright)

Why it exists: the site must never say more than the project can show. docs/status.json is the only place a
feature's state is set; pages and the README are rendered from it, and `check` fails when they disagree.
"""
from __future__ import annotations

import html
import json
import re
import sys
from html.parser import HTMLParser
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DOCS = ROOT / "docs"
SITE = ROOT / "docs" / "source"
PAGES_URL = "https://anshul48.github.io/anima-substrate/"
REPO_URL = "https://github.com/Anshul48/anima-substrate"

# Order of the six parts: the owner's order (memory, harness, install, screen, voice, discipline).
PARTS = ["memory", "harness", "install", "sst", "voice", "discipline"]
PART_PAGE = {"memory": "memory.html", "harness": "harnesses.html", "install": "install.html",
             "sst": "state-tree.html", "voice": "voice.html", "discipline": "rules.html"}
NAV = [("try", "try.html", "Try it"), ("how", "how-it-works.html", "How it works"),
       ("features", "features.html", "Features"), ("evidence", "evidence.html", "Evidence"),
       ("demos", "demos.html", "Demos"), ("about", "about.html", "About")]
STATE_ORDER = {"next": 0, "prototype": 1, "built": 2}

ICONS = {
    "memory": '<ellipse cx="12" cy="6" rx="7" ry="3"/><path d="M5 6v6c0 1.7 3.1 3 7 3s7-1.3 7-3V6"/><path d="M5 12v6c0 1.7 3.1 3 7 3s7-1.3 7-3v-6"/>',
    "harness": '<path d="M9 3v5M15 3v5"/><path d="M6 8h12v3a6 6 0 0 1-12 0V8z"/><path d="M12 17v4"/>',
    "install": '<rect x="3" y="4" width="18" height="16" rx="2"/><path d="M7 9l3 3-3 3M13 15h4"/>',
    "sst": '<circle cx="12" cy="5" r="2"/><circle cx="6" cy="19" r="2"/><circle cx="12" cy="19" r="2"/><circle cx="18" cy="19" r="2"/><path d="M12 7v4M6 17v-6h12v6M12 11v6"/>',
    "voice": '<rect x="9" y="3" width="6" height="11" rx="3"/><path d="M5 11a7 7 0 0 0 14 0M12 18v3"/>',
    "discipline": '<path d="M12 3l8 3v6c0 5-3.5 8-8 9-4.5-1-8-4-8-9V6l8-3z"/><path d="M9 12l2 2 4-4"/>',
}

BANNED = [  # (regex, why). Matched case-insensitively against site pages and the README.
    (r"live service", "FACTS-AND-RULES: no 'live service' claim"),
    (r"low[- ]memory", "no memory claim"),
    (r"scales to a billion", "no scale claim"),
    (r"works on public benchmarks", "not reproduced on public data"),
    (r"ran at 1\s?b\b", "no 1B claim"),
    (r"\b63\s?(/|of)\s?63\b", "self-test is not re-runnable from this repository"),
    (r"works for hours", "unproven"),
    (r"while you walk away", "unproven"),
    (r"faster(?![- ]whisper)", "no speed claim (faster-whisper is a library name)"),
    (r"fastest", "no speed claim"),
    (r"memory win", "no memory claim"),
    (r"\bbeats?\b", "no 'beats' claim"),
    (r"state[- ]of[- ]the[- ]art", "no SOTA claim"),
    (r"works like the brain", "say 'inspired by', never 'works like'"),
    (r"entropy", "only with an order-measure result"),
    (r"cannot be tampered", "say 'tampering is detected'"),
    (r"cannot cheat|can't cheat|unhackable|tamper-proof", "no absolute claims"),
    (r"coming soon|in progress|under construction|work in progress|not built yet", "use the Planned badge instead"),
]
PLANNED_PREFIXES = ("anima ", "curl ", "python3 -m anima")  # commands in a feature's "will" text that are shown as planned boxes
ALLOWED_A_HOSTS = ("github.com", "raw.githubusercontent.com", "anshul48.github.io")


# --------------------------------------------------------------------------- data

def load_status() -> dict:
    data = json.loads((DOCS / "status.json").read_text(encoding="utf-8"))
    data["by_id"] = {f["id"]: f for f in data["features"]}
    return data


def load_videos() -> list[dict]:
    return json.loads((DOCS / "videos.json").read_text(encoding="utf-8"))["videos"]


def esc(text: str) -> str:
    return html.escape(text, quote=True)


def inline(text: str) -> str:
    """Escape, then turn `code` into <code>."""
    return re.sub(r"`([^`]+)`", lambda m: "<code>" + m.group(1) + "</code>", esc(text))


# --------------------------------------------------------------------------- renderers

class Ctx:
    def __init__(self, status: dict, videos: list[dict], root: str):
        self.status, self.videos, self.root = status, videos, root

    def feat(self, fid: str) -> dict:
        try:
            return self.status["by_id"][fid]
        except KeyError:
            raise SystemExit(f"template error: unknown feature id '{fid}'")

    def label(self, state: str) -> str:
        return self.status["states"][state]

    def badge(self, fid: str, small: bool = False) -> str:
        f = self.feat(fid)
        return f'<span class="badge" data-state="{f["status"]}">{esc(self.label(f["status"]))}</span>'

    def href(self, fid: str) -> str:
        return self.root + self.feat(fid)["page"]


def cmd_box(text: str, planned: bool) -> str:
    copy = "" if planned else f'<button class="copy" type="button" data-copy="{esc(text)}">Copy</button>'
    return f'<div class="cmd{" planned" if planned else ""}"><code>{esc(text)}</code>{copy}</div>'


def r_featuregrid(c: Ctx) -> str:
    cards = []
    for fid in PARTS:
        f = c.feat(fid)
        cards.append(
            f'<a class="card" href="{c.href(fid)}"><svg class="ico" viewBox="0 0 24 24" aria-hidden="true">{ICONS[fid]}</svg>'
            f'<h3>{esc(f["short"])}</h3><p>{inline(f["plain"])}</p>'
            f'<div class="cfoot">{c.badge(fid)}<span class="more">Read more &rarr;</span></div></a>')
    return '<div class="grid c3">' + "".join(cards) + "</div>"


def r_harnessstrip(c: Ctx) -> str:
    items = []
    for n, fid in enumerate(c.feat("harness")["children"], start=1):
        f = c.feat(fid)
        items.append(f'<li><span><span class="n" aria-hidden="true">{n}</span><b>{esc(f["name"])}</b></span>{c.badge(fid)}</li>')
    return '<ul class="strip" aria-label="Harnesses, in order">' + "".join(items) + "</ul>"


def r_installbox(c: Ctx) -> str:
    f = c.feat("install")
    line = f"curl -fsSL {REPO_URL.replace('github.com', 'raw.githubusercontent.com')}/main/install.sh | sh"
    built = f["status"] == "built"
    label = ('<p class="cmd-label">One line to install ' + c.badge("install") + "</p>") if built else \
            ('<p class="cmd-label">One line to install ' + c.badge("install") + " <span>Planned line.</span></p>")
    return label + cmd_box(line, planned=not built)


def r_statustable(c: Ctx) -> str:
    rows = []
    for f in c.status["features"]:
        child = f["id"] not in PARTS
        name = esc(f["name"])
        link = f'<a href="{c.root}{f["page"]}">{name}</a>'
        check = f'<code>{esc(f["verify"])}</code>' if f["verify"] else '<span class="muted">nothing to run yet</span>'
        rows.append(f'<tr><td>{"&nbsp;&nbsp;&rarr; " if child else "<b>"}{link}{"" if child else "</b>"}</td><td>{c.badge(f["id"])}</td>'
                    f'<td>{inline(f["exists"])}</td><td>{check}</td></tr>')
    return ('<div class="tablewrap"><table><thead><tr><th scope="col">Feature</th><th scope="col">State</th>'
            '<th scope="col">What exists today</th><th scope="col">How to check it</th></tr></thead><tbody>'
            + "".join(rows) + "</tbody></table></div>")


def r_videos(c: Ctx) -> str:
    out = []
    for v in c.videos:
        path = DOCS / v["file"]
        size = f"{path.stat().st_size / 1e6:.1f} MB" if path.exists() else "file missing"
        track = f'<track kind="captions" srclang="en" label="English" src="{c.root}{v["captions"]}">' if v.get("captions") else ""
        poster = f' poster="{c.root}{v["poster"]}"' if v.get("poster") else ""
        out.append(
            f'<article class="vcard"><video controls preload="none"{poster} aria-label="{esc(v["title"])}"><source src="{c.root}{v["file"]}" type="video/mp4">{track}'
            f'Your browser cannot play this video. <a href="{c.root}{v["file"]}">Download it ({size}).</a></video>'
            f'<div class="meta"><h3>{esc(v["title"])}</h3><p>{esc(v["caption"])}</p>'
            f'<p class="muted small">{esc(v["length"])} &middot; {size} &middot; captions on &middot; {esc(v.get("note", ""))}</p></div></article>')
    return "".join(out)


def r_verifyrows(c: Ctx) -> str:
    rows = []
    for f in c.status["features"]:
        if f["verify"]:
            rows.append(f'<tr><td><a href="{c.root}{f["page"]}">{esc(f["name"])}</a> {c.badge(f["id"])}</td><td><code>{esc(f["verify"])}</code></td>'
                        f'<td>{esc(f.get("expect", "see the evidence file"))}</td><td>{esc(f.get("needs", ""))}</td></tr>')
    rows.append('<tr><td>The site follows its own rules: every badge backed by a command, no banned phrases, links resolve, no outside files</td>'
                '<td><code>python3 tools/site.py check</code></td><td>ALL CHECKS PASS</td><td>Python 3.11 or newer, a clone</td></tr>')
    return ('<div class="tablewrap"><table><thead><tr><th scope="col">Claim</th><th scope="col">Command</th><th scope="col">Expected</th>'
            '<th scope="col">Needs</th></tr></thead><tbody>' + "".join(rows) + "</tbody></table></div>")


def r_fhead(c: Ctx, fid: str) -> str:
    f = c.feat(fid)
    banners = {
        "next": '<div class="banner" role="note"><p><strong>Planned.</strong> This page says what it will do and what exists today.</p></div>',
        "prototype": '<div class="banner proto" role="note"><p><strong>Prototype.</strong> Something runs, in a limited form. The limits are listed on this page.</p></div>',
        "built": '<div class="banner built" role="note"><p><strong>Working today.</strong> You can check it yourself: the command is under &ldquo;How to check it&rdquo;.</p></div>',
    }
    return (f'<div class="wrap fhead"><p class="crumbs"><a href="{c.root}features.html">Features</a> / {esc(f["short"])}</p>'
            f'<h1>{esc(f["name"])} {c.badge(fid)}</h1><p class="lead">{inline(f["plain"])}</p>{banners[f["status"]]}</div>')


def r_facts(c: Ctx, fid: str) -> str:
    f = c.feat(fid)
    built = f["status"] == "built"
    parts = ['<div class="two">',
             f'<div class="panel"><h3>What exists today</h3><p>{inline(f["exists"])}</p></div>',
             f'<div class="panel"><h3>Limits</h3><p>{inline(f["limit"])}</p></div></div>']
    if f["will"]:
        title = "What it does" if built else "What it will do"
        parts.append(f'<div class="panel" style="margin-top:var(--space-5)"><h3>{title}</h3><p>{inline(f["will"])}</p></div>')
    return "".join(parts)


def r_cmds(c: Ctx, fid: str) -> str:
    f = c.feat(fid)
    if f["status"] == "built" and f["verify"]:
        return '<p class="cmd-label">Run it ' + c.badge(fid) + "</p>" + cmd_box(f["verify"], planned=False)
    cmds = [m for m in re.findall(r"`([^`]+)`", f["will"]) if m.startswith(PLANNED_PREFIXES)]
    if not cmds:
        return ""
    return ('<p class="cmd-label">Planned command ' + c.badge(fid) + " <span>Not available yet.</span></p>"
            + "".join(cmd_box(m, planned=True) for m in cmds))


def r_howtocheck(c: Ctx, fid: str) -> str:
    f = c.feat(fid)
    if not f["verify"] and not f["proof"]:
        return ""
    bits = []
    if f["verify"]:
        bits.append("<p>Run:</p>" + cmd_box(f["verify"], planned=False))
    if f["proof"]:
        bits.append(f'<p>Evidence file in this repository: <a href="{REPO_URL}/blob/main/{esc(f["proof"])}"><code>{esc(f["proof"])}</code></a></p>')
    return '<div class="panel" style="margin-top:var(--space-5)"><h3>How to check it</h3>' + "".join(bits) + "</div>"


def r_pager(c: Ctx, fid: str) -> str:
    i = PARTS.index(fid)
    prev = f'<a href="{c.href(PARTS[i-1])}">&larr; {esc(c.feat(PARTS[i-1])["short"])}</a>' if i > 0 else "<span></span>"
    nxt = f'<a href="{c.href(PARTS[i+1])}">{esc(c.feat(PARTS[i+1])["short"])} &rarr;</a>' if i < len(PARTS) - 1 else \
          f'<a href="{c.root}features.html">All features &rarr;</a>'
    return f'<nav class="pager" aria-label="Previous and next feature">{prev}{nxt}</nav>'


def render_nav(root: str, active: str) -> str:
    items = []
    for key, href, label in NAV:
        cur = ' aria-current="page"' if key == active else ""
        items.append(f'<a href="{root}{href}"{cur}>{label}</a>')
    items.append(f'<a class="gh" href="{REPO_URL}">GitHub</a>')
    return '<nav class="nav" aria-label="Main">' + "".join(items) + '<button class="themebtn" type="button" aria-label="Switch between light and dark colours">Theme</button></nav>'


# --------------------------------------------------------------------------- template engine

BLOCK = re.compile(r"\{\{#(built|prototype|next|notbuilt|notnext):([\w-]+)\}\}(.*?)\{\{/\1\}\}", re.S)
TOKEN = re.compile(r"\{\{(\w+)(?::([^{}]*))?\}\}")


def expand(text: str, c: Ctx, partials_seen: tuple = ()) -> str:
    # 1. includes (recursive)
    def inc(m):
        name = m.group(1)
        if name in partials_seen:
            raise SystemExit(f"template error: include loop on {name}")
        body = (SITE / "partials" / f"{name}.html").read_text(encoding="utf-8")
        return expand_includes(body, partials_seen + (name,))

    def expand_includes(t, seen):
        return re.sub(r"\{\{include:([\w-]+)\}\}", lambda m: inc(m), t)

    text = expand_includes(text, partials_seen)

    # 2. conditional blocks on feature state
    def block(m):
        kind, fid, body = m.group(1), m.group(2), m.group(3)
        state = c.feat(fid)["status"]
        show = {"built": state == "built", "prototype": state == "prototype", "next": state == "next",
                "notbuilt": state != "built", "notnext": state != "next"}[kind]
        return body if show else ""

    prev = None
    while prev != text:
        prev, text = text, BLOCK.sub(block, text)

    # 3. tokens
    def token(m):
        name, arg = m.group(1), m.group(2)
        if name == "root":
            return c.root
        if name == "updated":
            return esc(c.status["updated"])
        if name == "badge":
            return c.badge(arg)
        if name == "label":
            return esc(c.label(c.feat(arg)["status"]))
        if name == "f":
            fid, field = arg.split(".", 1)
            return inline(c.feat(fid)[field])
        if name == "href":
            return c.href(arg)
        if name == "icon":
            return f'<svg class="ico" viewBox="0 0 24 24" aria-hidden="true">{ICONS[arg]}</svg>'
        simple = {"featuregrid": r_featuregrid, "harnessstrip": r_harnessstrip, "installbox": r_installbox,
                  "statustable": r_statustable, "videos": r_videos, "verifyrows": r_verifyrows}
        if name in simple:
            return simple[name](c)
        withid = {"fhead": r_fhead, "facts": r_facts, "cmds": r_cmds, "howtocheck": r_howtocheck, "pager": r_pager}
        if name in withid:
            return withid[name](c, arg)
        raise SystemExit(f"template error: unknown token {{{{{name}}}}}")

    return TOKEN.sub(token, text)


def parse_page(path: Path) -> tuple[dict, str]:
    raw = path.read_text(encoding="utf-8")
    head, _, body = raw.partition("\n---\n")
    meta = {}
    for line in head.splitlines():
        if line.strip():
            k, _, v = line.partition(":")
            meta[k.strip()] = v.strip()
    return meta, body.strip() + "\n"


def build(write: bool = True) -> dict[str, str]:
    status, videos = load_status(), load_videos()
    layout = (SITE / "layout.html").read_text(encoding="utf-8")
    out: dict[str, str] = {}
    for src in sorted((SITE / "pages").glob("*.html")):
        meta, body = parse_page(src)
        rel = meta.get("out", src.name)
        depth = rel.count("/")
        root = "../" * depth
        if rel == "404.html":
            root = PAGES_URL  # served for any missing path, so its links must be absolute
        c = Ctx(status, videos, root)
        content = expand(body, c)
        extra_css = "".join(f'<link rel="stylesheet" href="{x}">' for x in meta.get("css", "").split())
        extra_js = "".join(f'<script src="{x}" defer></script>' for x in meta.get("js", "").split())
        page = layout
        subs = {"title": esc(meta["title"]), "description": esc(meta["description"]), "nav": render_nav(root, meta.get("nav", "")),
                "canonical": PAGES_URL + ("" if rel == "index.html" else rel), "bodyclass": meta.get("class", ""),
                "extra_css": extra_css, "extra_js": extra_js, "content": content}
        for k, v in subs.items():
            page = page.replace("{{" + k + "}}", v)
        page = expand(page, c)  # layout may use {{root}}, {{updated}}, {{include:...}}
        out[rel] = page
    if write:
        for rel, text in out.items():
            p = DOCS / rel
            p.parent.mkdir(parents=True, exist_ok=True)
            if not p.exists() or p.read_text(encoding="utf-8") != text:
                p.write_text(text, encoding="utf-8")
        print(f"built {len(out)} pages into docs/")
    return out


# --------------------------------------------------------------------------- README sync

def _block_markers(name: str) -> tuple[str, str]:
    return (f"<!-- block:{name}:start (generated from docs/status.json by tools/site.py sync-readme) -->", f"<!-- block:{name}:end -->")


def _planned_cmds(f: dict) -> list[str]:
    return [m for m in re.findall(r"`([^`]+)`", f["will"]) if m.startswith(PLANNED_PREFIXES)]


def blk_status(status: dict) -> str:
    st = status["states"]
    rows = ["| Part | State | What exists today |", "|---|---|---|"]
    for fid in PARTS:
        f = status["by_id"][fid]
        rows.append(f"| [{f['short']}]({PAGES_URL}{f['page']}) | **{st[f['status']]}** | {f['exists']} |")
    parts_kids = ", ".join(f"{status['by_id'][k]['short']}: {st[status['by_id'][k]['status']]}"
                           for k in status["by_id"]["discipline"]["children"])
    return "\n".join([*rows, "", f"Roles and rules, part by part: {parts_kids}.",
                      "", f"Rendered from [`docs/status.json`](docs/status.json); `python3 tools/site.py check` fails if this table or the site disagrees with it."])


def blk_harness(status: dict) -> str:
    st = status["states"]
    rows = ["| # | Harness | State | Command |", "|---|---|---|---|"]
    for n, k in enumerate(status["by_id"]["harness"]["children"], start=1):
        f = status["by_id"][k]
        cmds = _planned_cmds(f)
        cmd = ("`" + cmds[0] + "`") if cmds else ""
        if cmd and f["status"] != "built":
            cmd = "planned: " + cmd
        rows.append(f"| {n} | {f['name']} | **{st[f['status']]}** | {cmd} |")
    return "\n".join(rows)


def blk_install(status: dict) -> str:
    f = status["by_id"]["install"]
    line = f"curl -fsSL {REPO_URL.replace('github.com', 'raw.githubusercontent.com')}/main/install.sh | sh"
    if f["status"] == "built":
        return "```bash\n" + line + "\nanima doctor\n```\n\nOne line, a private folder, no admin rights. `anima doctor` lists which of Muse Code, Claude Code and Codex it found."
    return ("**One-line install: " + status["states"][f["status"]] + ".** Planned line (the address only works after the project's first push to GitHub):\n\n"
            "```text\n" + line + "\n```")


def blk_sst(status: dict) -> str:
    f = status["by_id"]["sst"]
    if f["status"] == "built":
        return (f"![The ANIMA state tree screen showing one recorded run: owner, run, one task with a verified attempt, and the decision records on the right.](docs/img/sst-screen.png)\n\n"
                f"*Real screenshot of the state-tree screen showing a recorded run, served from a fresh clone.* [More]({PAGES_URL}state-tree.html). "
                f"Designed preview: [UI preview: a replay of recorded runs](docs/ui-preview/index.html) ([dashboard](docs/ui-preview/dashboard.html)).")
    return f"**{status['states'][f['status']]}.** {f['plain']} [What it will look like and what exists]({PAGES_URL}state-tree.html)."


def blk_feat(fid: str):
    def fn(status: dict) -> str:
        f = status["by_id"][fid]
        out = [f"**{status['states'][f['status']]}.** {f['exists']}"]
        if f["status"] != "built" and f.get("will"):
            out.append(f"Planned: {f['will']}")
        if f.get("limit"):
            out.append(f"Limit: {f['limit']}")
        return "\n\n".join(out)
    return fn


README_BLOCKS = {"status": blk_status, "harness": blk_harness, "install": blk_install, "sst": blk_sst,
                 "memory-state": blk_feat("memory"), "voice-state": blk_feat("voice"), "rules-state": blk_feat("discipline")}


def sync_readme(write: bool = True) -> str:
    path = ROOT / "README.md"
    text = path.read_text(encoding="utf-8")
    status = load_status()
    for name, fn in README_BLOCKS.items():
        a, b = _block_markers(name)
        pat = re.compile(re.escape(a) + r".*?" + re.escape(b), re.S)
        if not pat.search(text):
            raise SystemExit(f"README.md has no block markers for '{name}'")
        body = fn(status)
        text = pat.sub(lambda m: a + "\n\n" + body + "\n\n" + b, text)
    if write and text != path.read_text(encoding="utf-8"):
        path.write_text(text, encoding="utf-8")
        print("README.md generated blocks updated")
    return text


# --------------------------------------------------------------------------- check

class Collect(HTMLParser):
    VOID = {"meta", "link", "br", "hr", "img", "input", "source", "track", "area", "base", "col", "embed", "wbr"}

    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.stack, self.errors, self.ids, self.refs, self.imgs, self.h1, self.text = [], [], set(), [], [], 0, []
        self.title = ""
        self.meta_desc = False
        self.lang = False
        self._in_title = False
        self._in_a = None

    def handle_starttag(self, tag, attrs):
        a = dict(attrs)
        if tag == "html":
            self.lang = bool(a.get("lang"))
        if tag == "title":
            self._in_title = True
        if tag == "h1":
            self.h1 += 1
        if tag == "meta" and a.get("name") == "description" and a.get("content"):
            self.meta_desc = True
        if "id" in a:
            if a["id"] in self.ids:
                self.errors.append(f"duplicate id {a['id']}")
            self.ids.add(a["id"])
        for attr in ("href", "src"):
            if a.get(attr) is not None:
                self.refs.append((tag, attr, a[attr]))
        if tag == "img":
            if "alt" not in a:
                self.errors.append(f"<img src={a.get('src')}> has no alt")
        if tag not in self.VOID:
            self.stack.append(tag)

    def handle_startendtag(self, tag, attrs):
        self.handle_starttag(tag, attrs)
        if tag not in self.VOID and self.stack and self.stack[-1] == tag:
            self.stack.pop()

    def handle_endtag(self, tag):
        if tag in self.VOID:
            return
        if tag == "title":
            self._in_title = False
        if not self.stack or self.stack[-1] != tag:
            self.errors.append(f"unbalanced </{tag}> (open: {self.stack[-3:]})")
            if tag in self.stack:
                while self.stack and self.stack.pop() != tag:
                    pass
        else:
            self.stack.pop()

    def handle_data(self, data):
        if self._in_title:
            self.title += data
        self.text.append(data)


def _lum(hexcolor: str) -> float:
    h = hexcolor.lstrip("#")
    r, g, b = (int(h[i:i + 2], 16) / 255 for i in (0, 2, 4))
    f = lambda v: v / 12.92 if v <= 0.03928 else ((v + 0.055) / 1.055) ** 2.4
    return 0.2126 * f(r) + 0.7152 * f(g) + 0.0722 * f(b)


def contrast(a: str, b: str) -> float:
    la, lb = _lum(a), _lum(b)
    hi, lo = max(la, lb), min(la, lb)
    return (hi + 0.05) / (lo + 0.05)


def theme_vars() -> dict[str, dict[str, str]]:
    css = (DOCS / "assets" / "tokens.css").read_text(encoding="utf-8")
    light: dict[str, str] = {}
    dark: dict[str, str] = {}
    for sel, body in re.findall(r"(:root[^{}]*)\{([^{}]*)\}", css):
        vals = dict(re.findall(r"--([\w-]+):\s*(#[0-9a-fA-F]{6})", body))
        if sel.strip() == ":root":
            light.update(vals)
        elif 'data-theme="light"' not in sel or ":not(" in sel:
            if ":not([data-theme=\"light\"])" in sel or 'data-theme="dark"' in sel:
                dark.update(vals)
    return {"light": light, "dark": {**light, **dark}}


CONTRAST_PAIRS = [
    ("ink", "bg", 7), ("ink", "surface", 7), ("ink-2", "surface", 4.5), ("muted", "bg", 4.5), ("muted", "surface", 4.5),
    ("muted", "bg-2", 4.5), ("accent-ink", "accent", 4.5), ("link", "bg", 4.5), ("link", "surface", 4.5),
    ("accent", "surface", 3), ("st-built", "st-built-bg", 4.5), ("st-proto", "st-proto-bg", 4.5),
    ("st-next", "st-next-bg", 4.5), ("st-limit", "st-limit-bg", 4.5), ("ink", "st-next-bg", 4.5),
    ("ink", "st-proto-bg", 4.5), ("ink", "st-built-bg", 4.5), ("st-limit", "surface", 4.5),
    ("stage-ink", "stage-bg", 7), ("stage-muted", "stage-bg", 4.5), ("stage-ink", "stage-bg-2", 7),
]


class Report:
    def __init__(self):
        self.fails = 0

    def ok(self, msg):
        print("ok    " + msg)

    def bad(self, msg):
        self.fails += 1
        print("FAIL  " + msg)


def check() -> int:
    r = Report()
    status = load_status()
    videos = load_videos()

    # 1. status.json rules
    ids = set(status["by_id"])
    states = set(status["states"])
    problems = []
    for f in status["features"]:
        for k in ("id", "name", "short", "status", "page", "plain", "exists", "will", "limit", "verify", "proof"):
            if k not in f:
                problems.append(f"{f.get('id')}: missing '{k}'")
        if f["status"] not in states:
            problems.append(f"{f['id']}: unknown status {f['status']}")
        if f["status"] == "built":
            if not f["verify"]:
                problems.append(f"{f['id']}: built but 'verify' is empty")
            if not f["proof"] or not (ROOT / f["proof"]).exists():
                problems.append(f"{f['id']}: built but proof path '{f['proof']}' does not exist")
        if f["status"] in ("prototype", "built") and f["proof"] and not (ROOT / f["proof"]).exists():
            problems.append(f"{f['id']}: proof path '{f['proof']}' does not exist")
        for k in f.get("children", []):
            if k not in ids:
                problems.append(f"{f['id']}: unknown child {k}")
        if f["status"] == "built" and f.get("children"):
            kids = [status["by_id"][k]["status"] for k in f["children"]]
            need = f.get("requires", "all")
            okk = all(s == "built" for s in kids) if need == "all" else kids[0] == "built"
            if not okk:
                problems.append(f"{f['id']}: built but children do not satisfy requires={need}")
    for fid in PARTS:
        if fid not in ids:
            problems.append(f"part {fid} missing")
    (r.bad if problems else r.ok)("status.json rules: " + ("; ".join(problems) if problems else f"{len(ids)} features, built features carry a command and an existing proof file"))

    # 2. generated pages up to date
    gen = build(write=False)
    stale = [rel for rel, text in gen.items() if not (DOCS / rel).exists() or (DOCS / rel).read_text(encoding="utf-8") != text]
    (r.bad if stale else r.ok)(f"generated pages match docs/source/ + status.json ({len(gen)} pages)" if not stale else
                               "stale generated pages (run: python3 tools/site.py build): " + ", ".join(stale))

    # 3. README status table in sync
    try:
        synced = sync_readme(write=False) == (ROOT / "README.md").read_text(encoding="utf-8")
        (r.ok if synced else r.bad)("README status table matches status.json" if synced else "README status table is stale (run: python3 tools/site.py sync-readme)")
    except SystemExit as e:
        r.bad(str(e))

    # 4. per-page checks
    html_files = sorted(p for p in DOCS.rglob("*.html")
                        if "evidence" not in p.relative_to(DOCS).parts and "source" not in p.relative_to(DOCS).parts)
    id_cache: dict[Path, set[str]] = {}
    page_problems, link_problems, ext_problems, weight_problems = [], [], [], []
    css_js = sum((DOCS / "assets" / n).stat().st_size for n in ("tokens.css", "site.css", "site.js"))
    for p in html_files:
        rel = p.relative_to(DOCS).as_posix()
        text = p.read_text(encoding="utf-8")
        col = Collect()
        col.feed(text)
        col.close()
        for e in col.errors:
            page_problems.append(f"{rel}: {e}")
        if col.stack:
            page_problems.append(f"{rel}: unclosed {col.stack}")
        if not (col.lang and col.title.strip() and col.meta_desc):
            page_problems.append(f"{rel}: needs lang, title and meta description")
        if col.h1 != 1:
            page_problems.append(f"{rel}: has {col.h1} h1 (needs exactly 1)")
        id_cache[p] = col.ids
        for tag, attr, val in col.refs:
            if val.startswith(("mailto:", "data:", "javascript:")):
                continue
            if re.match(r"https?://", val):
                host = re.match(r"https?://([^/]+)", val).group(1)
                if rel == "404.html" and val.startswith(PAGES_URL):
                    continue
                if tag != "a":
                    ext_problems.append(f"{rel}: <{tag} {attr}={val}> loads an outside file")
                elif host not in ALLOWED_A_HOSTS:
                    ext_problems.append(f"{rel}: link to {host} is not on the allowed list")
                continue
            if val.startswith("/"):
                link_problems.append(f"{rel}: root-absolute path {val} (breaks on project Pages)")
                continue
            if val.startswith("#"):
                if val[1:] and val[1:] not in col.ids:
                    link_problems.append(f"{rel}: missing anchor {val}")
                continue
            target_part, _, frag = val.partition("#")
            target_part = target_part.split("?")[0]
            target = (p.parent / target_part).resolve()
            if target.is_dir():
                target = target / "index.html"
            try:
                target.relative_to(DOCS.resolve())
            except ValueError:
                link_problems.append(f"{rel}: {val} points outside docs/ (use a full github.com link)")
                continue
            if not target.exists():
                link_problems.append(f"{rel}: broken link {val}")
            elif frag and target.suffix == ".html":
                if target not in id_cache:
                    c2 = Collect()
                    c2.feed(target.read_text(encoding="utf-8"))
                    id_cache[target] = c2.ids
                if frag not in id_cache[target]:
                    link_problems.append(f"{rel}: {val} anchor not found")
        if rel in gen:
            w = len(text.encode()) + css_js
            if w > 60_000:
                weight_problems.append(f"{rel}: {w} bytes of html+css+js (limit 60000)")
    (r.bad if page_problems else r.ok)("html structure, one h1, lang/title/description, alt text, unique ids: " + (f"{len(page_problems)} problems" if page_problems else f"{len(html_files)} pages"))
    for m in page_problems[:20]:
        print("      " + m)
    (r.bad if link_problems else r.ok)("internal links and anchors resolve: " + (f"{len(link_problems)} problems" if link_problems else "all"))
    for m in link_problems[:20]:
        print("      " + m)
    (r.bad if ext_problems else r.ok)("no outside scripts, styles, images, media; links only to allowed hosts: " + (f"{len(ext_problems)} problems" if ext_problems else "clean"))
    for m in ext_problems[:20]:
        print("      " + m)
    (r.bad if weight_problems else r.ok)("page weight under 60 KB before images" if not weight_problems else "; ".join(weight_problems))

    # 5. banned phrases (site pages, README, site sources, status/videos json)
    scan = [p for p in html_files if "demo" not in p.relative_to(DOCS).parts[:1] or True]
    scan += [ROOT / "README.md", DOCS / "status.json", DOCS / "videos.json"] + sorted(SITE.rglob("*.html"))
    hits = []
    for p in scan:
        body = p.read_text(encoding="utf-8")
        visible = re.sub(r"<(script|style)\b.*?</\1>", " ", body, flags=re.S)
        for rx, why in BANNED:
            for m in re.finditer(rx, visible, flags=re.I):
                hits.append(f"{p.relative_to(ROOT)}: '{m.group(0)}' ({why})")
    (r.bad if hits else r.ok)("banned phrases: " + (f"{len(hits)} hits" if hits else "none"))
    for m in hits[:30]:
        print("      " + m)

    # 6. headline must not lead with verification
    idx = (DOCS / "index.html").read_text(encoding="utf-8") if (DOCS / "index.html").exists() else ""
    m = re.search(r"<h1[^>]*>(.*?)</h1>.*?<p class=\"lead\">(.*?)</p>", idx, re.S)
    if m and re.search(r"verif", m.group(1) + m.group(2), re.I):
        r.bad("home headline or lead mentions verification (owner: not the headline)")
    else:
        r.ok("home headline does not lead with verification")

    # 7. videos list
    missing = [v["file"] for v in videos if not (DOCS / v["file"]).exists()]
    (r.bad if missing else r.ok)("videos.json files exist" if not missing else "missing video files: " + ", ".join(missing))

    # 8. size
    total = sum(p.stat().st_size for p in DOCS.rglob("*") if p.is_file())
    big = [p.name for p in DOCS.rglob("*") if p.is_file() and p.stat().st_size > 6_000_000]
    (r.bad if total > 25_000_000 or big else r.ok)(f"docs/ is {total / 1e6:.1f} MB (limit 25 MB); files over 6 MB: {big or 'none'}")

    # 9. contrast
    tv = theme_vars()
    bad_pairs = []
    for theme, vals in tv.items():
        for fg, bg, need in CONTRAST_PAIRS:
            if fg in vals and bg in vals:
                got = contrast(vals[fg], vals[bg])
                if got < need:
                    bad_pairs.append(f"{theme}: {fg} on {bg} = {got:.2f} (needs {need})")
    (r.bad if bad_pairs else r.ok)("colour contrast of the shared tokens: " + ("; ".join(bad_pairs) if bad_pairs else f"{len(CONTRAST_PAIRS)} pairs x 2 themes pass"))

    # 10. README links
    readme = (ROOT / "README.md").read_text(encoding="utf-8")
    bad_links = []
    for m2 in re.finditer(r"(?:\]\(|src=\"|href=\")([^)\"#\s]+)", readme):
        v = m2.group(1)
        if re.match(r"(https?:|mailto:)", v):
            continue
        if not (ROOT / v).exists():
            bad_links.append(v)
    (r.bad if bad_links else r.ok)("README relative links exist" if not bad_links else "README broken links: " + ", ".join(bad_links))

    # 11. repository files
    need = []
    lic = (ROOT / "LICENSE").read_text(encoding="utf-8", errors="replace") if (ROOT / "LICENSE").exists() else ""
    if "Apache License" not in lic or "Version 2.0" not in lic:
        need.append("LICENSE is not Apache-2.0 text")
    for name in (".github/SECURITY.md", ".github/CONTRIBUTING.md", "docs/CHANGELOG.md", "docs/CITATION.cff",
                 ".github/PULL_REQUEST_TEMPLATE.md", ".github/workflows/pages.yml",
                 ".github/ISSUE_TEMPLATE/config.yml", "docs/INDEX.md"):
        if not (ROOT / name).exists():
            need.append(f"missing {name}")
    cff = (ROOT / "docs/CITATION.cff").read_text(encoding="utf-8") if (ROOT / "docs/CITATION.cff").exists() else ""
    for key in ("cff-version", "title", "authors", "license", "repository-code"):
        if not re.search(rf"^{key}:", cff, re.M):
            need.append(f"docs/CITATION.cff lacks {key}")
    if "Unreleased" not in (ROOT / "docs/CHANGELOG.md").read_text(encoding="utf-8"):
        need.append("docs/CHANGELOG.md has no Unreleased section")
    (r.bad if need else r.ok)("repository files (LICENSE, SECURITY, CONTRIBUTING, CITATION, CHANGELOG, templates, Pages workflow): " + ("; ".join(need) if need else "present"))

    print(f"\n{'ALL CHECKS PASS' if not r.fails else str(r.fails) + ' CHECK(S) FAILED'}")
    return 1 if r.fails else 0


def social() -> int:
    """Render docs/source/social-preview.html to docs/img/social-preview.png (1200 x 630). Needs Playwright with a Chromium."""
    try:
        from playwright.sync_api import sync_playwright
    except ImportError:
        print("Playwright is not installed: pip install playwright && playwright install chromium")
        return 2
    out = DOCS / "img" / "social-preview.png"
    with sync_playwright() as p:
        b = p.chromium.launch()
        pg = b.new_page(viewport={"width": 1200, "height": 630})
        pg.goto((SITE / "social-preview.html").resolve().as_uri())
        pg.screenshot(path=str(out))
        b.close()
    print(f"wrote {out.relative_to(ROOT)}")
    return 0


def main(argv: list[str]) -> int:
    cmd = argv[1] if len(argv) > 1 else ""
    if cmd == "build":
        build(True)
        return 0
    if cmd == "sync-readme":
        sync_readme(True)
        return 0
    if cmd == "check":
        return check()
    if cmd == "social":
        return social()
    print(__doc__)
    return 2


if __name__ == "__main__":
    sys.exit(main(sys.argv))
