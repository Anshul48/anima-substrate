# Copyright 2026 Anshul48
# SPDX-License-Identifier: Apache-2.0
"""Turn ANIMA's records of finished jobs into memory passages (stdlib only).

Three inputs are understood:

  decisions.jsonl   the hash-chained decision log of a harness run (one JSON event
                    per line, each carrying the SHA-256 of the line before it). One
                    passage per attempt: the task, who tried, what the hidden checker
                    said, the first failing line.
  job.json          an `anima-job-v1` record (see docs/MEMORY.md): task text, what was
                    changed, the checker result per attempt, what failed first. This is
                    what `anima memory record` writes.
  attempts dir      a folder of `<task>/attempt.json + hand.json` as written by the
                    flagship harness (adds the agent's own one-line summary).
  run folder        what `anima run` writes: attempts/<rung>-<harness>/{attempt.json,
                    hand.json,changes.patch} next to decisions.jsonl. One passage per
                    attempt, with a line-count summary of the diff (never the code).

Every passage carries a SOURCE POINTER that can be re-checked later: a file, a line
(for logs), a record id and the SHA-256 of that line or file. `verify_pointer` re-reads
the file and says OK, CHANGED or MISSING.
"""
from __future__ import annotations

import hashlib
import json
import re
from dataclasses import dataclass, field, asdict
from pathlib import Path

SCHEMA = "anima-job-v1"
MAX_WORDS = 175  # TRACE chunks at 200 whitespace tokens; keep one passage = one atom
_EXTRA = re.compile(r"-e\d+$")


def _redact_text(text):
    from anima.harness.redact import redact_text
    return redact_text(text)[0]


def _redact_obj(obj):
    from anima.harness.redact import redact_obj
    return redact_obj(obj)[0]


@dataclass
class Passage:
    base_id: str                 # stable id, e.g. "decision:flagship-run3:click-short-help-abbrev:a0"
    kind: str                    # "attempt" | "job-attempt"
    task: str
    library: str
    text: str                    # what TRACE indexes and what the next agent reads
    source: dict                 # {"file","line"?, "record_id"?, "sha256", "what"}
    meta: dict = field(default_factory=dict)  # verdict, rule, pool, rung, ...

    def __post_init__(self):
        # key-shaped strings never reach the memory (redacted BEFORE the content-addressed id is computed)
        self.text = _redact_text(self.text)
        self.meta = _redact_obj(self.meta)

    @property
    def sha(self) -> str:
        return hashlib.sha256(self.text.encode("utf-8")).hexdigest()

    @property
    def doc_id(self) -> str:
        # content-addressed: a changed record becomes a new document, never a silent overwrite
        return f"{self.base_id}@{self.sha[:8]}"

    def to_json(self) -> dict:
        d = asdict(self)
        d["doc_id"] = self.doc_id
        d["sha256"] = self.sha
        return d


def sha256_bytes(b: bytes) -> str:
    return hashlib.sha256(b).hexdigest()


def library_of(task: str) -> str:
    return _EXTRA.sub("", task).split("-")[0]


def words(task: str) -> str:
    return _EXTRA.sub("", task).replace("-", " ")


def clip(text: str, n: int) -> str:
    w = " ".join(str(text).split())
    if w.startswith("E "):  # pytest's "E       " failure-line marker
        w = w[2:].lstrip()
    parts = w.split(" ")
    return w if len(parts) <= n else " ".join(parts[:n]) + " ..."


def combined_sha(main: Path, parts) -> str:
    """SHA-256 over the main file and the named sibling files it was written together with, so a changed summary
    or patch is caught by the source check, not only a changed attempt.json. No parts: plain file hash."""
    if not parts:
        return sha256_bytes(Path(main).read_bytes())
    h = hashlib.sha256()
    h.update(Path(main).read_bytes())
    for name in parts:
        h.update(b"\0" + name.encode() + b"\0")
        h.update((Path(main).parent / name).read_bytes())
    return h.hexdigest()


def _rel(path: Path, root: Path | None) -> str:
    p = Path(path).resolve()
    if root is not None:
        try:
            return str(p.relative_to(Path(root).resolve()))
        except ValueError:
            pass
    return str(p)


def _outcome_sentence(verdict: str, rule, first_failure) -> str:
    if verdict == "PASS":
        return "The hidden checker said PASS."
    s = f"The hidden checker said {verdict}"
    if rule:
        s += f", rule {rule}"
    s += "."
    if first_failure:
        s += f" First failing line: {clip(first_failure, 40)}."
    return s


# --------------------------------------------------------------------------- decisions.jsonl
def check_chain(raw: bytes):
    """Same rule as docs/evidence/flagship-run3/check_chain.py: prev = sha256 of the previous line."""
    lines = [ln for ln in raw.split(b"\n") if ln]
    prev = "GENESIS"
    for n, ln in enumerate(lines, 1):
        try:
            ev = json.loads(ln)
        except ValueError:
            return False, f"line {n} is not valid JSON", len(lines)
        if ev.get("prev") != prev:
            return False, f"line {n} does not match the line before it", len(lines)
        prev = hashlib.sha256(ln).hexdigest()
    return True, "every link matches", len(lines)


def parse_decisions(path, root=None, verify_chain=True):
    path = Path(path)
    raw = path.read_bytes()
    if verify_chain:
        ok, why, n = check_chain(raw)
        if not ok:
            raise ValueError(f"{path}: CHAIN BROKEN ({why}); refusing to ingest a log that does not verify")
    lines = [ln for ln in raw.split(b"\n") if ln]
    run = path.parent.name
    rel = _rel(path, root)
    attempts = {}   # original task -> list of (lineno, line, attempt dict)
    decisions = {}  # original task -> escalate decision (lineno, data)
    for no, ln in enumerate(lines, 1):
        ev = json.loads(ln)
        d = ev.get("data") or {}
        if ev.get("kind") == "artifact.added" and isinstance(d.get("attempt"), dict):
            a = d["attempt"]
            orig = _EXTRA.sub("", a.get("task") or ev.get("task") or "")
            attempts.setdefault(orig, []).append((no, ln, ev, a))
        elif ev.get("kind") == "decision.made" and d.get("decision") == "escalate":
            decisions[_EXTRA.sub("", ev.get("task", ""))] = (no, d)
    out = []
    for orig, items in attempts.items():
        items.sort(key=lambda t: (t[3].get("rung", 0), t[0]))
        prior_fail = None
        for idx, (no, ln, ev, a) in enumerate(items):
            verdict = a.get("gate_verdict", "UNKNOWN")
            rule, digest = a.get("failed_rule"), (a.get("digest") or "").strip()
            text = (f"Job {orig} (library {library_of(orig)}; task words: {words(orig)}). "
                    f"Attempt {idx + 1} by {a.get('pool', 'unknown')}"
                    f"{' (said done)' if a.get('said_done') else ''}. "
                    f"{_outcome_sentence(verdict, rule, digest)}")
            if verdict == "PASS" and prior_fail:
                text += (f" It passed after the earlier attempt failed on: {clip(prior_fail, 40)}.")
            if verdict != "PASS" and orig in decisions:
                text += f" The ladder then escalated to {decisions[orig][1].get('to_pool', 'the next helper')}."
            if a.get("wall_seconds") is not None:
                text += f" Wall time {float(a['wall_seconds']):.0f} s."
            if verdict != "PASS" and digest:
                prior_fail = digest
            out.append(Passage(
                base_id=f"decision:{run}:{orig}:a{idx}", kind="attempt", task=orig, library=library_of(orig),
                text=text,
                source={"file": rel, "line": no, "record_id": ev.get("id"), "sha256": sha256_bytes(ln),
                        "what": "artifact.added attempt record in a hash-chained decision log"},
                meta={"verdict": verdict, "failed_rule": rule, "pool": a.get("pool"), "rung": a.get("rung"),
                      "first_failure": digest or None, "run": run, "origin": "decisions.jsonl"}))
    return out


# --------------------------------------------------------------------------- anima-job-v1
def parse_job(path, root=None):
    """One job.json -> one passage per attempt."""
    path = Path(path)
    raw = path.read_bytes()
    j = json.loads(raw)
    if j.get("schema") != SCHEMA:
        raise ValueError(f"{path}: schema is {j.get('schema')!r}, expected {SCHEMA!r}")
    task = j["task"]
    lib = j.get("library") or library_of(task)
    rel, fsha = _rel(path, root), sha256_bytes(raw)
    out, prior_fail = [], None
    atts = j.get("attempts") or []
    for i, a in enumerate(atts):
        verdict = a.get("verdict", "UNKNOWN")
        n_issue = 70
        while True:  # one passage = one TRACE atom (<= 200 whitespace tokens): shrink the issue text, never the outcome
            issue = clip(j.get("issue_text", ""), n_issue)
            text = f"Task {task} (library {lib}): {issue} " if issue else f"Task {task} (library {lib}; task words: {words(task)}). "
            text += f"Attempt {a.get('n', i + 1)}{' by ' + a['pool'] if a.get('pool') else ''}."
            if a.get("summary"):
                text += f" The agent's summary: {clip(a['summary'], 45)}"
                if not text.endswith("."):
                    text += "."
            if a.get("diff_summary"):
                text += f" Change: {clip(a['diff_summary'], 40)}."
            text += " " + _outcome_sentence(verdict, a.get("failed_rule"), a.get("first_failure"))
            if verdict == "PASS" and prior_fail:
                text += f" It passed after the earlier attempt failed on: {clip(prior_fail, 40)}."
            if len(text.split()) <= MAX_WORDS or n_issue <= 15:
                break
            n_issue -= 10
        if verdict != "PASS" and a.get("first_failure"):
            prior_fail = a["first_failure"]
        out.append(Passage(
            base_id=f"job:{j.get('job_id') or task}:a{i}", kind="job-attempt", task=task, library=lib,
            text=" ".join(text.split()),
            source={"file": rel, "record_id": j.get("job_id") or task, "sha256": fsha,
                    "what": f"{SCHEMA} job record (whole file)"},
            meta={"verdict": verdict, "failed_rule": a.get("failed_rule"), "pool": a.get("pool"),
                  "first_failure": a.get("first_failure"), "origin": SCHEMA, "attempt": a.get("n", i + 1)}))
    return out


# --------------------------------------------------------------------------- `anima run` run folders
def diff_summary(patch_text: str, max_files: int = 4) -> str:
    """'src/a.py (+3 -1), src/b.py (+10 -0)' from a unified diff. Counts lines only; never quotes code."""
    files, cur = [], None
    for ln in patch_text.splitlines():
        if ln.startswith("diff --git "):
            cur = [ln.split(" b/", 1)[-1].strip(), 0, 0]
            files.append(cur)
        elif cur and ln.startswith("+") and not ln.startswith("+++"):
            cur[1] += 1
        elif cur and ln.startswith("-") and not ln.startswith("---"):
            cur[2] += 1
    if not files:
        return "no file changes"
    s = ", ".join(f"{f} (+{a} -{b})" for f, a, b in files[:max_files])
    return s + (f", and {len(files) - max_files} more files" if len(files) > max_files else "")


def find_task_card(task_ref, task_id: str):
    """task_ref: a task.json, a task folder, or a folder of task folders. Returns the parsed card or None."""
    if not task_ref:
        return None
    p = Path(task_ref)
    for c in ([p] if p.is_file() else [p / "task.json", p / task_id / "task.json"]):
        if c.is_file():
            try:
                card = json.loads(c.read_text())
            except ValueError:
                continue
            if card.get("id") == task_id:
                return card
    return None


def is_run_dir(p: Path) -> bool:
    a = p / "attempts"
    return a.is_dir() and any((s / "attempt.json").is_file() for s in a.iterdir() if s.is_dir())


def parse_run_dir(run_dir, root=None, task=None, verify_chain=True):
    """A folder written by `anima run`: attempts/<rung>-<harness>/{attempt.json,hand.json,changes.patch}
    next to a hash-chained decisions.jsonl. One passage per attempt. The task text is not stored in the
    run folder, so pass `task` (a task.json, a task folder, or a folder of task folders)."""
    run_dir = Path(run_dir)
    chain = run_dir / "decisions.jsonl"
    if verify_chain and chain.is_file():
        ok, why, _ = check_chain(chain.read_bytes())
        if not ok:
            raise ValueError(f"{chain}: CHAIN BROKEN ({why}); refusing to ingest a run whose log does not verify")
    items = []
    for sub in sorted((run_dir / "attempts").iterdir()):
        aj = sub / "attempt.json"
        if aj.is_file():
            araw = aj.read_bytes()
            hj, pj = sub / "hand.json", sub / "changes.patch"
            parts = [x.name for x in (hj, pj) if x.is_file()]
            items.append((json.loads(araw), json.loads(hj.read_text()) if hj.is_file() else {},
                          pj.read_text(errors="replace") if pj.is_file() else None, aj, combined_sha(aj, parts), parts))
    items.sort(key=lambda t: t[0].get("rung", 0))
    out, prior_fail = [], None
    for i, (a, h, patch, aj, fsha, parts) in enumerate(items):
        tid = a.get("task") or run_dir.name
        lib, verdict = library_of(tid), a.get("verdict", "UNKNOWN")
        card = find_task_card(task, tid)
        n_issue = 70
        while True:
            issue = clip((card or {}).get("issue_text", ""), n_issue)
            text = f"Task {tid} (library {lib}): {issue} " if issue else f"Task {tid} (library {lib}; task words: {words(tid)}). "
            text += f"Attempt {i + 1} by {a.get('harness', 'unknown')}."
            if h.get("summary"):
                text += f" The agent's summary: {clip(h['summary'], 40)}"
                if not text.endswith("."):
                    text += "."
            if patch is not None:
                text += f" Change: {clip(diff_summary(patch), 40)}."
            text += " " + _outcome_sentence(verdict, a.get("failed_rule"), (a.get("digest") or "").strip())
            if verdict == "PASS" and prior_fail:
                text += f" It passed after the earlier attempt failed on: {clip(prior_fail, 40)}."
            if len(text.split()) <= MAX_WORDS or n_issue <= 15:
                break
            n_issue -= 10
        if verdict != "PASS" and (a.get("digest") or "").strip():
            prior_fail = a["digest"]
        out.append(Passage(
            base_id=f"run:{run_dir.name}:{tid}:a{i}", kind="run-attempt", task=tid, library=lib,
            text=" ".join(text.split()),
            source={"file": _rel(aj, root), "record_id": a.get("job_id") or aj.parent.name, "sha256": fsha,
                    "parts": parts, "what": "anima run attempt.json + " + " + ".join(parts) + " (every file the text was written from)"},
            meta={"verdict": verdict, "failed_rule": a.get("failed_rule"), "pool": a.get("harness"),
                  "rung": a.get("rung"), "first_failure": (a.get("digest") or "").strip() or None,
                  "origin": "anima-run", "run": run_dir.name, "attempt": i + 1, "has_task_text": bool(card)}))
    return out


# --------------------------------------------------------------------------- flagship attempts dir
def parse_attempts_dir(path, root=None):
    """<dir>/<task>/{attempt.json,hand.json}: the flagship harness' evidence layout."""
    path = Path(path)
    jobs = {}
    for sub in sorted(p for p in path.iterdir() if p.is_dir()):
        aj = sub / "attempt.json"
        if not aj.is_file():
            continue
        araw = aj.read_bytes()
        a = json.loads(araw)
        hj = sub / "hand.json"
        h = json.loads(hj.read_text()) if hj.is_file() else {}
        orig = _EXTRA.sub("", a.get("task") or sub.name)
        jobs.setdefault(orig, []).append((a, h, aj, sha256_bytes(araw)))
    out = []
    for orig, items in jobs.items():
        items.sort(key=lambda t: t[0].get("rung", 0))
        prior_fail = None
        for i, (a, h, aj, fsha) in enumerate(items):
            verdict = a.get("gate_verdict", "UNKNOWN")
            digest = (a.get("digest") or "").strip()
            text = (f"Job {orig} (library {library_of(orig)}; task words: {words(orig)}). "
                    f"Attempt {i + 1} by {a.get('pool', 'unknown')}.")
            if h.get("summary"):
                text += f" The agent's summary: {clip(h['summary'], 45)}"
                if not text.endswith("."):
                    text += "."
            text += " " + _outcome_sentence(verdict, a.get("failed_rule"), digest)
            if verdict == "PASS" and prior_fail:
                text += f" It passed after the earlier attempt failed on: {clip(prior_fail, 40)}."
            if verdict != "PASS" and digest:
                prior_fail = digest
            out.append(Passage(
                base_id=f"attempts:{path.name}:{orig}:a{i}", kind="attempt", task=orig, library=library_of(orig),
                text=" ".join(text.split()),
                source={"file": _rel(aj, root), "record_id": a.get("hand") or aj.parent.name, "sha256": fsha,
                        "what": "flagship attempt.json (whole file)"},
                meta={"verdict": verdict, "failed_rule": a.get("failed_rule"), "pool": a.get("pool"),
                      "rung": a.get("rung"), "first_failure": digest or None, "origin": "attempts-dir"}))
    return out


def load_path(path, root=None, verify_chain=True, task=None):
    """Dispatch on what `path` is. Returns a list of Passage. `task` = where to find task.json text for `anima run` folders."""
    p = Path(path)
    if p.is_dir():
        if is_run_dir(p):
            return parse_run_dir(p, root, task, verify_chain)
        out = []
        runs = [d for d in sorted(p.iterdir()) if d.is_dir() and is_run_dir(d)]
        for d in runs:
            out += parse_run_dir(d, root, task, verify_chain)
        if runs:
            return out
        if any((s / "attempt.json").is_file() for s in p.iterdir() if s.is_dir()):
            out += parse_attempts_dir(p, root)
        for f in sorted(p.rglob("job.json")):
            out += parse_job(f, root)
        for f in sorted(p.rglob("decisions.jsonl")):
            out += parse_decisions(f, root, verify_chain)
        return out
    if p.name.endswith(".jsonl"):
        return parse_decisions(p, root, verify_chain)
    if p.suffix == ".json":
        return parse_job(p, root)
    raise ValueError(f"don't know how to ingest {p}")


# --------------------------------------------------------------------------- pointers
def pointer_str(src: dict) -> str:
    s = src["file"]
    if src.get("line"):
        s += f" line {src['line']}"
    if src.get("record_id"):
        s += f" id {src['record_id'][:12]}"
    return f"{s} sha256 {src['sha256'][:12]}"


def verify_pointer(src: dict, root=None) -> tuple[str, str]:
    """Re-read the source and compare the SHA-256. Returns (status, detail): OK | CHANGED | MISSING."""
    f = Path(src["file"])
    if not f.is_absolute() and root is not None:
        f = Path(root) / f
    if not f.is_file():
        return "MISSING", f"file not found: {f}"
    raw = f.read_bytes()
    if src.get("line"):
        lines = [ln for ln in raw.split(b"\n") if ln]
        n = int(src["line"])
        if n > len(lines):
            return "CHANGED", f"{f.name} has only {len(lines)} lines"
        got = sha256_bytes(lines[n - 1])
        if src.get("record_id"):
            try:
                if json.loads(lines[n - 1]).get("id") != src["record_id"]:
                    return "CHANGED", f"line {n} has a different record id"
            except ValueError:
                return "CHANGED", f"line {n} is not JSON"
    elif src.get("parts"):
        try:
            got = combined_sha(f, src["parts"])
        except OSError as exc:
            return "MISSING", f"a file the text was written from is gone: {exc}"
    else:
        got = sha256_bytes(raw)
    if got != src["sha256"]:
        return "CHANGED", f"sha256 {got[:12]} != recorded {src['sha256'][:12]}"
    return "OK", f"{f.name}{' line ' + str(src['line']) if src.get('line') else ''} matches"
