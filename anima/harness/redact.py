"""Redact obvious secrets before anything is written to a log, a decision record, a diff or the memory.

Scope (honest): this catches KEY-SHAPED strings (well-known token prefixes, private-key blocks, bearer
tokens, JWTs, and `NAME_KEY=value` style assignments with a long mixed value). It is a net for accidents,
not a data-loss-prevention system: a secret in an unusual shape passes through. The file system permissions
of the run folders (owner only) are the second layer; containment of the agent itself is a separate matter
(see docs/INTEGRATED-DEMO.md, "What is NOT built").

Redaction happens BEFORE the decision chain hashes a record, so the chain never contains the secret.
"""
from __future__ import annotations

import re
from pathlib import Path

_PRIVATE_KEY = re.compile(r"-----BEGIN [A-Z ]*PRIVATE KEY-----.*?(?:-----END [A-Z ]*PRIVATE KEY-----|\Z)", re.S)
_PREFIXED = [
    ("anthropic-key", re.compile(r"\bsk-ant-[A-Za-z0-9_\-]{16,}")),
    ("api-key", re.compile(r"\bsk-[A-Za-z0-9_\-]{20,}")),
    ("github-token", re.compile(r"\b(?:ghp|gho|ghu|ghs|ghr)_[A-Za-z0-9]{30,}\b")),
    ("github-token", re.compile(r"\bgithub_pat_[A-Za-z0-9_]{30,}")),
    ("aws-key-id", re.compile(r"\b(?:AKIA|ASIA)[0-9A-Z]{16}\b")),
    ("google-key", re.compile(r"\bAIza[0-9A-Za-z_\-]{35}\b")),
    ("slack-token", re.compile(r"\bxox[abprs]-[A-Za-z0-9\-]{10,}")),
    ("hf-token", re.compile(r"\bhf_[A-Za-z0-9]{30,}\b")),
    ("jwt", re.compile(r"\beyJ[A-Za-z0-9_\-]{10,}\.[A-Za-z0-9_\-]{10,}\.[A-Za-z0-9_\-]{10,}")),
    ("bearer", re.compile(r"(?i)\bBearer\s+[A-Za-z0-9._~+/=\-]{20,}")),
]
# NAME=value where NAME looks like a credential name; value must look like a secret (long, mixed)
_ASSIGN = re.compile(
    r"""(?ix)\b([A-Z0-9_.\-]*(?:KEY|TOKEN|SECRET|PASSWORD|PASSWD|CREDENTIAL)[A-Z0-9_.\-]*)(\s*[=:]\s*)(['"]?)([^\s'",;]{12,})(\3)""")


def _looks_secret(value: str) -> bool:
    has_alpha = any(c.isalpha() for c in value)
    has_digit = any(c.isdigit() for c in value)
    return (has_alpha and has_digit) or len(value) >= 24


def redact_text(text: str) -> tuple[str, int]:
    """Returns (text with key-shaped strings replaced by [REDACTED:kind], number of replacements)."""
    if not text:
        return text, 0
    n = 0

    def sub_private(_m):
        nonlocal n
        n += 1
        return "[REDACTED:private-key]"

    text = _PRIVATE_KEY.sub(sub_private, text)
    for kind, rx in _PREFIXED:
        def sub(_m, kind=kind):
            nonlocal n
            n += 1
            return f"[REDACTED:{kind}]"
        text = rx.sub(sub, text)

    def sub_assign(m):
        nonlocal n
        if m.group(4).startswith("[REDACTED") or not _looks_secret(m.group(4)):
            return m.group(0)
        n += 1
        return f"{m.group(1)}{m.group(2)}{m.group(3)}[REDACTED:credential-value]{m.group(5)}"

    text = _ASSIGN.sub(sub_assign, text)
    return text, n


def redact_obj(obj):
    """Redact every string inside a JSON-like structure. Returns (new object, number of replacements)."""
    total = 0

    def walk(o):
        nonlocal total
        if isinstance(o, str):
            s, k = redact_text(o)
            total += k
            return s
        if isinstance(o, dict):
            return {k: walk(v) for k, v in o.items()}
        if isinstance(o, (list, tuple)):
            return [walk(v) for v in o]
        return o

    return walk(obj), total


def redact_file(path, max_bytes: int = 20_000_000) -> int:
    """Redact a text file in place (owner-only permissions). Returns the number of replacements; 0 if the
    file is missing, binary or larger than max_bytes."""
    p = Path(path)
    try:
        if not p.is_file() or p.stat().st_size > max_bytes:
            return 0
        raw = p.read_bytes()
        if b"\x00" in raw[:4096]:
            return 0
        new, n = redact_text(raw.decode("utf-8", "replace"))
        if n:
            p.write_text(new, "utf-8")
        p.chmod(0o600)
        return n
    except OSError:
        return 0
