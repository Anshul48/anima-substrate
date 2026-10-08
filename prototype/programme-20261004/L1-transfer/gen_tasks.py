"""L1 task-family generator (stdlib-only, deterministic).

Builds scheduling-grid follow-up tasks inside the successor-002 host
envelope from r1's own proven grids, using ONLY solvability-preserving
transforms (task-label permutation applied consistently to
tasks/precedence/prefs; machine swap applied consistently to
slots/prefs). Isomorphic grids, distinct bytes/assignments.

Bases (read-only from the frozen r1 accept pack + a proven extension):
  T4: accept/S2.json grid (4 tasks / 4 slots)
  T5: accept/S4-followup.json grid (5 tasks / 5 slots)
  T6: T5 grid + slot S5{M0,t3} + task F{window:[S5]} + precedence [E,F]
      (this exact 6-grid shape ran VALID 6/6 in pre-prereg probe pb-reuse)

Usage:
  python3 gen_tasks.py --out tasks
Prints task_id, size, seed, sha256 per file.
"""
from __future__ import annotations

import argparse
import hashlib
import itertools
import json
import random
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
R1 = HERE / ".." / ".." / "successor-002"
R1 = R1.resolve()

TRAIN = [("L1-TR-01", 4, 101), ("L1-TR-02", 4, 102),
         ("L1-TR-03", 5, 103), ("L1-TR-04", 5, 104),
         ("L1-TR-05", 6, 105), ("L1-TR-06", 6, 106)]
TEST = [("L1-TE-%02d" % i, size, 200 + i)
        for i, size in enumerate([4, 4, 4, 4, 5, 5, 5, 5, 6, 6, 6, 6], start=1)]

# Secondary (routing-prediction) descriptors: (grid task, rounds, split).
SECONDARY = [("L1-TE-01", 1, False), ("L1-TE-02", 1, True),
              ("L1-TE-05", 2, False), ("L1-TE-06", 2, True),
              ("L1-TE-09", 3, False), ("L1-TE-10", 3, True),
              ("L1-TE-03", 4, False), ("L1-TE-04", 4, True)]


def load_base4() -> dict:
    b = json.loads((R1 / "accept" / "S2.json").read_text(encoding="utf-8"))
    return {"slots": b["slots"], "tasks": b["tasks"],
            "precedence": b["precedence"], "prefs": b["prefs"]}


def load_base5() -> dict:
    b = json.loads((R1 / "accept" / "S4-followup.json").read_text(
        encoding="utf-8"))
    return {"slots": b["slots"], "tasks": b["tasks"],
            "precedence": b["precedence"], "prefs": b["prefs"]}


def load_base6() -> dict:
    b = load_base5()
    slots = dict(b["slots"])
    slots["S5"] = {"machine": "M0", "time": "t3"}
    tasks = dict(b["tasks"])
    tasks["F"] = {"window": ["S5"]}
    prec = [list(p) for p in b["precedence"]] + [["E", "F"]]
    prefs = dict(b["prefs"])
    prefs["F"] = "M0"
    return {"slots": slots, "tasks": tasks,
            "precedence": prec, "prefs": prefs}


BASES = {4: load_base4, 5: load_base5, 6: load_base6}


def transform(base: dict, seed: int, task_id: str) -> dict:
    rng = random.Random(seed)
    labels = sorted(base["tasks"])
    perm = rng.sample(labels, len(labels))
    m = dict(zip(labels, perm))
    swap = rng.random() < 0.5
    sw = (lambda x: {"M0": "M1", "M1": "M0"}[x]) if swap else (lambda x: x)
    return {
        "task_id": task_id,
        "slots": {s: {"machine": sw(v["machine"]), "time": v["time"]}
                  for s, v in sorted(base["slots"].items())},
        "tasks": {m[k]: {"window": list(v["window"])}
                  for k, v in sorted(base["tasks"].items())},
        "precedence": [[m[a], m[b]] for a, b in base["precedence"]],
        "prefs": {m[k]: sw(v) for k, v in sorted(base["prefs"].items())},
        "adapter": "list2slot/v1",
        "l1_seed": seed,
    }


def main(argv: list[str]) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default="tasks")
    args = ap.parse_args(argv)
    out = (HERE / args.out)
    out.mkdir(parents=True, exist_ok=True)
    made = {}
    for task_id, size, seed in itertools.chain(TRAIN, TEST):
        t = transform(BASES[size](), seed, task_id)
        p = out / f"{task_id}.json"
        p.write_text(json.dumps(t, indent=2, sort_keys=True) + "\n",
                     encoding="utf-8")
        made[task_id] = t
        h = hashlib.sha256(p.read_bytes()).hexdigest()[:16]
        print(f"{task_id} size={size} seed={seed} sha={h}")
    sec = out / "secondary-descriptors.json"
    descs = []
    for grid_id, rounds, split in SECONDARY:
        g = dict(made[grid_id])
        g["expected_rounds"] = rounds
        g["split_state"] = split
        g["holdings"] = {"SC-L": {"req_tasks": sorted(g["tasks"])[:2],
                                  "prefs": sorted(g["tasks"])[:2]},
                         "SC-S": {"req_tasks": sorted(g["tasks"])[2:],
                                  "prefs": sorted(g["tasks"])[2:]}}
        d = {"desc_id": f"{grid_id}-r{rounds}-s{int(split)}",
             "grid": grid_id, "expected_rounds": rounds,
             "split_state": split, "task": g}
        descs.append(d)
    sec.write_text(json.dumps(descs, indent=2, sort_keys=True) + "\n",
                   encoding="utf-8")
    print(f"secondary descriptors: {len(descs)} -> {sec.name}")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
