#!/usr/bin/env python3
"""Check the recorded decision chain of the nine-job run (python 3, no install).

Every line in decisions.jsonl is one recorded decision. Each line carries a
"prev" field: the SHA-256 of the full text of the line before it (the first
line says GENESIS). Change any earlier line and the next line no longer
matches, so the change shows up.

    python3 check_chain.py                # check the recorded chain
    python3 check_chain.py --tamper       # change one byte in a COPY, check again
    python3 check_chain.py path/to/decisions.jsonl

This reader was written for this README. It only reads the record; it does not
re-run any job and does not re-run the hidden checker.
"""
import hashlib
import json
import sys
import tempfile
from pathlib import Path

HERE = Path(__file__).resolve().parent


def check(path):
    raw = Path(path).read_bytes()
    lines = [line for line in raw.split(b"\n") if line]
    previous = "GENESIS"
    for number, line in enumerate(lines, start=1):
        try:
            event = json.loads(line)
        except ValueError:
            return False, f"line {number} is not valid JSON", len(lines), raw
        if event.get("prev") != previous:
            return False, f"line {number} does not match the line before it", len(lines), raw
        previous = hashlib.sha256(line).hexdigest()
    return True, "every link matches", len(lines), raw


def report(path, label):
    ok, why, count, raw = check(path)
    digest = hashlib.sha256(raw).hexdigest()
    print(f"{label}: {'CHAIN OK' if ok else 'CHAIN BROKEN'} - {count} records, {why}")
    print(f"  file fingerprint (SHA-256): {digest}")
    return ok, digest


def main(argv):
    tamper = "--tamper" in argv
    args = [a for a in argv if not a.startswith("--")]
    path = Path(args[0]) if args else HERE / "decisions.jsonl"
    ok, digest = report(path, "recorded run")
    head = path.parent / "decisions.jsonl.head.json"
    if head.exists():
        expected = json.loads(head.read_text())["sha256"]
        print("  matches the fingerprint saved at the end of the run:", "yes" if digest == expected else "NO")
    if not tamper:
        return 0 if ok else 1
    lines = Path(path).read_bytes().split(b"\n")
    victim = bytearray(lines[5])
    index = victim.index(b'"kind":"') + len(b'"kind":"')
    victim[index] = ord("X")
    lines[5] = bytes(victim)
    with tempfile.TemporaryDirectory() as folder:
        copy = Path(folder) / "decisions.jsonl"
        copy.write_bytes(b"\n".join(lines))
        print("\nchanged one character on line 6 of a temporary copy (the original is untouched)")
        copy_ok, _ = report(copy, "edited copy")
    # exit 0 means: the real record is intact AND the edit was noticed
    return 0 if (ok and not copy_ok) else 1


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
