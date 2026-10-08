"""L2 step-0 throwaway probe generator (stdlib-only, deterministic).

Builds 8 pre-committed L2P-* lane tasks (see STEP0-PROBES.md) from the
published example grids (T4/T5 shapes as shown in the H2 consumer
examples; T6 = T5 + slot S5{M0,t3} + task F{window:[S5]} + [E,F],
the L1-proven 6-shape) using ONLY solvability-preserving transforms
(task-label permutation + machine swap, fixed seeds).

Grid bytes below are authored probe-construction inputs in this work
dir; the host consumes the emitted task JSONs via release.py CLI only.

Usage: python3 gen_probes_step0.py --out probes
"""
from __future__ import annotations

import argparse
import hashlib
import json
import random
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent

# T4: 4-task / 4-slot grid (S2 example shape).
T4 = {
    "slots": {"S0": {"machine": "M0", "time": "t0"},
              "S1": {"machine": "M1", "time": "t0"},
              "S2": {"machine": "M0", "time": "t1"},
              "S3": {"machine": "M1", "time": "t1"}},
    "tasks": {"A": {"window": ["S0", "S2"]}, "B": {"window": ["S1", "S3"]},
              "C": {"window": ["S0", "S1"]}, "D": {"window": ["S2", "S3"]}},
    "precedence": [["A", "B"], ["C", "D"]],
    "prefs": {"A": "M0", "B": "M1", "C": "M1", "D": "M0"},
}

# T5: 5-task / 5-slot grid (S4-followup example shape).
T5 = {
    "slots": {"S0": {"machine": "M0", "time": "t0"},
              "S1": {"machine": "M1", "time": "t0"},
              "S2": {"machine": "M0", "time": "t1"},
              "S3": {"machine": "M1", "time": "t1"},
              "S4": {"machine": "M1", "time": "t2"}},
    "tasks": {"A": {"window": ["S0", "S2"]}, "B": {"window": ["S1", "S3"]},
              "C": {"window": ["S0", "S1"]}, "D": {"window": ["S2", "S3"]},
              "E": {"window": ["S4"]}},
    "precedence": [["A", "B"], ["C", "D"]],
    "prefs": {"A": "M0", "B": "M1", "C": "M1", "D": "M0", "E": "M1"},
}


def base6() -> dict:
    b = {"slots": dict(T5["slots"]), "tasks": dict(T5["tasks"]),
         "precedence": [list(p) for p in T5["precedence"]],
         "prefs": dict(T5["prefs"])}
    b["slots"]["S5"] = {"machine": "M0", "time": "t3"}
    b["tasks"]["F"] = {"window": ["S5"]}
    b["precedence"].append(["E", "F"])
    b["prefs"]["F"] = "M0"
    return b


BASES = {4: T4, 5: T5, 6: None}  # 6 built by base6()

# Pre-committed probe specs: (probe_id, size, seed, req_L, req_S, pref_L, pref_S)
# Labels are pre-permutation; shapes fixed by STEP0-PROBES.md.
PROBES = [
    ("L2P-01", 4, 901, ["A", "B"], ["C", "D"],
     ["A", "B"], ["C", "D"]),
    ("L2P-02", 4, 902, ["A", "B", "C", "D"], [],
     ["A", "B", "C", "D"], []),
    ("L2P-03", 4, 903, ["A", "B"], ["C", "D"],
     ["A", "B", "C", "D"], []),
    ("L2P-04", 5, 904, ["A", "B", "C"], ["D", "E"],
     ["A", "B", "C"], ["D", "E"]),
    ("L2P-05", 5, 905, ["A", "B"], ["C", "D", "E"],
     ["A", "B", "C", "D", "E"], []),
    ("L2P-06", 5, 906, ["A", "B", "C", "D", "E"], [],
     ["A", "B"], ["C", "D", "E"]),
    ("L2P-07", 6, 907, ["A", "B", "C"], ["D", "E", "F"],
     ["A", "B", "C"], ["D", "E", "F"]),
    ("L2P-08", 6, 908, ["A", "B", "C", "D", "E", "F"], [],
     [], ["A", "B", "C", "D", "E", "F"]),
]


def build_probe(base: dict, probe_id: str, seed: int,
                req_l, req_s, pref_l, pref_s) -> dict:
    rng = random.Random(seed)
    labels = sorted(base["tasks"])
    perm = rng.sample(labels, len(labels))
    m = dict(zip(labels, perm))
    swap = rng.random() < 0.5
    sw = (lambda x: {"M0": "M1", "M1": "M0"}[x]) if swap else (lambda x: x)
    return {
        "task_id": probe_id,
        "slots": {s: {"machine": sw(v["machine"]), "time": v["time"]}
                  for s, v in sorted(base["slots"].items())},
        "tasks": {m[k]: {"window": list(v["window"])}
                  for k, v in sorted(base["tasks"].items())},
        "precedence": [[m[a], m[b]] for a, b in base["precedence"]],
        "prefs": {m[k]: sw(v) for k, v in sorted(base["prefs"].items())},
        "holdings": {
            "SC-L": {"req_tasks": sorted(m[t] for t in req_l),
                     "prefs": sorted(m[t] for t in pref_l)},
            "SC-S": {"req_tasks": sorted(m[t] for t in req_s),
                     "prefs": sorted(m[t] for t in pref_s)}},
        "adapter": "list2slot/v1",
        "l2p_seed": seed,
    }


def main(argv: list[str]) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default="probes")
    args = ap.parse_args(argv)
    out = (HERE / args.out)
    out.mkdir(parents=True, exist_ok=True)
    for pid, size, seed, req_l, req_s, pref_l, pref_s in PROBES:
        base = base6() if size == 6 else BASES[size]
        t = build_probe(base, pid, seed, req_l, req_s, pref_l, pref_s)
        p = out / f"{pid}.json"
        p.write_text(json.dumps(t, indent=2, sort_keys=True) + "\n",
                     encoding="utf-8")
        h = hashlib.sha256(p.read_bytes()).hexdigest()[:16]
        print(f"{pid} size={size} seed={seed} sha={h}")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
