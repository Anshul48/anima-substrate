"""A tiny YAML-subset reader and writer (standard library only).

ANIMA's profile file is `anima.yaml`. To keep the install dependency-free we
read and write only the small subset the profile uses:

    key: value                  # mappings (2-space indentation)
    key:
      nested: value
    key: [a, b, c]              # flow lists
    key: {a: 1, b: [x, y]}      # flow maps (one line, may nest)
    key:
      - item                    # block lists of scalars
      - {on: x, do: y}          # block lists of flow maps
    # comments, blank lines

Scalars: null/~/empty, true/false, integers, floats, quoted or bare strings.
Anything else (anchors, multi-line strings, multi-line flow, tags) is rejected with
a clear error instead of being guessed at. A document that starts with "{" is
read as JSON, since JSON is valid YAML.
"""
from __future__ import annotations

import json
import re


class YamlError(ValueError):
    pass


_INT = re.compile(r"^[+-]?\d+$")
_FLOAT = re.compile(r"^[+-]?(\d+\.\d*|\.\d+|\d+)([eE][+-]?\d+)?$")
_PLAIN_OK = re.compile(r"^[A-Za-z0-9_./@%+=-][A-Za-z0-9_./@%+= -]*$")


def _scalar(text: str):
    t = text.strip()
    if t in ("", "~", "null", "Null", "NULL"):
        return None
    if t in ("true", "True", "TRUE"):
        return True
    if t in ("false", "False", "FALSE"):
        return False
    if len(t) >= 2 and t[0] == t[-1] and t[0] in "\"'":
        if t[0] == '"':
            try:
                return json.loads(t)
            except ValueError as exc:
                raise YamlError(f"bad double-quoted string: {t}") from exc
        return t[1:-1].replace("''", "'")
    if _INT.match(t):
        return int(t)
    if _FLOAT.match(t):
        return float(t)
    if t[0] in "&*!|>{" or t.startswith("- "):
        raise YamlError(f"unsupported YAML construct: {t[:30]!r}")
    return t


def _strip_comment(line: str) -> str:
    quote = None
    for i, ch in enumerate(line):
        if quote:
            if ch == quote:
                quote = None
        elif ch in "\"'":
            quote = ch
        elif ch == "#" and (i == 0 or line[i - 1] in " \t"):
            return line[:i]
    return line


def _flow(t: str, i: int, stop: str):
    """Parse one flow value starting at t[i]; stop is the set of chars that end a plain scalar."""
    n = len(t)
    while i < n and t[i] == " ":
        i += 1
    if i >= n:
        return None, i
    c = t[i]
    if c == "[":
        out, i = [], i + 1
        while True:
            while i < n and t[i] == " ":
                i += 1
            if i >= n:
                raise YamlError("unterminated flow list")
            if t[i] == "]":
                return out, i + 1
            val, i = _flow(t, i, ",]")
            out.append(val)
            while i < n and t[i] == " ":
                i += 1
            if i < n and t[i] == ",":
                i += 1
    if c == "{":
        out, i = {}, i + 1
        while True:
            while i < n and t[i] == " ":
                i += 1
            if i >= n:
                raise YamlError("unterminated flow map")
            if t[i] == "}":
                return out, i + 1
            j = i
            if t[j] in "\"'":
                q = t[j]
                j += 1
                while j < n and t[j] != q:
                    j += 1
                j += 1
            else:
                while j < n and not (t[j] == ":" and (j + 1 >= n or t[j + 1] in " ,}")):
                    j += 1
            if j >= n or t[j] != ":":
                raise YamlError(f"flow map: expected 'key: value' near {t[i:i + 30]!r}")
            key = _scalar(t[i:j])
            key = key if isinstance(key, str) else str(key)
            if key in out:
                raise YamlError(f"duplicate key {key!r}")
            val, i = _flow(t, j + 1, ",}")
            out[key] = val
            while i < n and t[i] == " ":
                i += 1
            if i < n and t[i] == ",":
                i += 1
    if c in "\"'":
        j = i + 1
        while j < n and t[j] != c:
            if c == '"' and t[j] == "\\":
                j += 1
            j += 1
        return _scalar(t[i:j + 1]), j + 1
    j = i
    while j < n and t[j] not in stop:
        j += 1
    return _scalar(t[i:j]), j


def _value(text: str):
    t = text.strip()
    if t[:1] in ("[", "{"):
        val, pos = _flow(t, 0, "")
        if t[pos:].strip():
            raise YamlError(f"unexpected text after flow value: {t[pos:pos + 30]!r}")
        return val
    return _scalar(t)


def loads(text: str):
    stripped = text.lstrip()
    if stripped.startswith("{"):
        return json.loads(text)
    rows = []
    for number, raw in enumerate(text.splitlines(), start=1):
        if "\t" in raw[: len(raw) - len(raw.lstrip())]:
            raise YamlError(f"line {number}: tabs are not allowed for indentation")
        body = _strip_comment(raw).rstrip()
        if not body.strip() or body.strip() == "---":
            continue
        indent = len(body) - len(body.lstrip(" "))
        rows.append((number, indent, body.strip()))
    if not rows:
        return {}
    node, pos = _block(rows, 0, rows[0][1])
    if pos != len(rows):
        raise YamlError(f"line {rows[pos][0]}: unexpected indentation")
    return node


def _block(rows, pos, indent):
    if rows[pos][2].startswith("- ") or rows[pos][2] == "-":
        return _block_list(rows, pos, indent)
    return _block_map(rows, pos, indent)


def _block_list(rows, pos, indent):
    out = []
    while pos < len(rows):
        number, ind, body = rows[pos]
        if ind < indent:
            break
        if ind > indent or not (body.startswith("- ") or body == "-"):
            raise YamlError(f"line {number}: expected a list item")
        item = body[1:].strip()
        if re.match(r"^[A-Za-z0-9_.-]+:(\s|$)", item) and not item.startswith(("'", '"')):
            raise YamlError(f"line {number}: lists of mappings are not supported")
        out.append(_value(item))
        pos += 1
    return out, pos


def _block_map(rows, pos, indent):
    out = {}
    while pos < len(rows):
        number, ind, body = rows[pos]
        if ind < indent:
            break
        if ind > indent:
            raise YamlError(f"line {number}: unexpected indentation")
        m = re.match(r"^((?:\"[^\"]*\")|(?:'[^']*')|[^:\s][^:]*?)\s*:(?:\s+(.*))?$", body)
        if not m:
            raise YamlError(f"line {number}: expected 'key: value', got {body[:40]!r}")
        key = _scalar(m.group(1))
        key = str(key) if not isinstance(key, str) else key
        rest = m.group(2)
        pos += 1
        if key in out:
            raise YamlError(f"line {number}: duplicate key {key!r}")
        if rest is None or rest.strip() == "":
            if pos < len(rows) and rows[pos][1] > indent:
                out[key], pos = _block(rows, pos, rows[pos][1])
            elif pos < len(rows) and rows[pos][1] == indent and rows[pos][2].startswith("- "):
                out[key], pos = _block_list(rows, pos, indent)
            else:
                out[key] = None
        else:
            out[key] = _value(rest)
    return out, pos


def _fmt_scalar(value) -> str:
    if value is None:
        return "null"
    if value is True:
        return "true"
    if value is False:
        return "false"
    if isinstance(value, (int, float)):
        return repr(value)
    s = str(value)
    if s and _PLAIN_OK.match(s) and s.strip() == s and s not in (
        "null", "true", "false", "~", "Null", "True", "False"
    ) and not _INT.match(s) and not _FLOAT.match(s):
        return s
    return json.dumps(s)


def _flat(val) -> bool:
    return isinstance(val, dict) and all(
        not isinstance(v, dict) and not (isinstance(v, (list, tuple)) and any(isinstance(x, (dict, list, tuple)) for x in v))
        for v in val.values()
    )


def _flow_fmt(val) -> str:
    if isinstance(val, dict):
        return "{" + ", ".join(f"{_fmt_scalar(k)}: {_flow_fmt(v)}" for k, v in val.items()) + "}"
    if isinstance(val, (list, tuple)):
        return "[" + ", ".join(_flow_fmt(x) for x in val) + "]"
    return _fmt_scalar(val)


def dumps(data, header: str = "") -> str:
    lines = [header.rstrip("\n")] if header else []

    def emit(node, indent):
        pad = "  " * indent
        for key, val in node.items():
            k = _fmt_scalar(key)
            if isinstance(val, dict) and val and not _flat(val):
                lines.append(f"{pad}{k}:")
                emit(val, indent + 1)
            elif isinstance(val, dict):
                lines.append(f"{pad}{k}: {_flow_fmt(val) if val else 'null'}")
            elif isinstance(val, (list, tuple)) and val and all(_flat(x) for x in val):
                lines.append(f"{pad}{k}:")
                lines.extend(f"{pad}  - {_flow_fmt(x)}" for x in val)
            elif isinstance(val, (list, tuple)):
                lines.append(f"{pad}{k}: {_flow_fmt(val)}")
            else:
                lines.append(f"{pad}{k}: {_fmt_scalar(val)}")

    if not isinstance(data, dict):
        raise YamlError("top level must be a mapping")
    emit(data, 0)
    return "\n".join(lines) + "\n"
