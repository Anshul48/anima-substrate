# Copyright 2026 Anshul48
# SPDX-License-Identifier: Apache-2.0
"""Test tool: feed a REAL decision record into a state dir one record at a time,
so that live mode (`anima ui --state DIR`) has something to follow.

    python3 -m anima.ui.replay_feed --to /tmp/live-state --speed 25
    python3 -m anima.ui --state /tmp/live-state          # in another terminal

The records are the real ones (default: the nine-job run).  Their timestamps
are shifted so the first record is "now" (otherwise a live screen would count
"running for 17 hours"), and the hash chain is recomputed, because changing a
timestamp changes the line.  So this is a time-shifted, re-sealed COPY used to
test the live screen; it is not evidence of a new run and must never be
presented as one.  The pace between records is the recorded pace / --speed.
"""
import argparse
import hashlib
import json
import time
from datetime import datetime, timezone
from pathlib import Path

from . import model, source

EPOCH_KEYS = ("started_at", "finished_at")


def shift(obj, delta):
    if isinstance(obj, dict):
        return {k: (v + delta if k in EPOCH_KEYS and isinstance(v, (int, float)) else shift(v, delta))
                for k, v in obj.items()}
    if isinstance(obj, list):
        return [shift(x, delta) for x in obj]
    return obj


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("--from", dest="src", default=str(source.DEMO_CHAIN))
    ap.add_argument("--to", required=True, help="state dir (created); decisions.jsonl is written here")
    ap.add_argument("--speed", type=float, default=25.0)
    a = ap.parse_args(argv)
    events, _ = model.read_chain(a.src)
    raws = [json.loads(ln) for ln in Path(a.src).read_bytes().split(b"\n") if ln]
    dest = Path(a.to)
    dest.mkdir(parents=True, exist_ok=True)
    out = dest / "decisions.jsonl"
    out.write_bytes(b"")
    t0_rec, t0_now = events[0]["epoch"], time.time()
    prev_seal, prev_epoch = "GENESIS", None
    for ev, raw in zip(events, raws):
        if prev_epoch is not None:
            time.sleep(max(0.0, (ev["epoch"] - prev_epoch) / a.speed))
        prev_epoch = ev["epoch"]
        new_epoch = time.time()
        raw = shift(raw, new_epoch - ev["epoch"])
        raw["ts"] = datetime.fromtimestamp(new_epoch, timezone.utc).strftime("%Y-%m-%dT%H:%M:%S.") + \
            f"{int(new_epoch * 1000) % 1000:03d}Z"
        raw["prev"] = prev_seal
        line = json.dumps(raw, sort_keys=True, separators=(",", ":")).encode()
        with open(out, "ab") as f:
            f.write(line + b"\n")
        prev_seal = hashlib.sha256(line).hexdigest()
        print(f"wrote record {ev['n']}/{len(raws)} {ev['kind']}", flush=True)


if __name__ == "__main__":
    main()
