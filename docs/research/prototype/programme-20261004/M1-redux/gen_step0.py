"""M1-redux step-0 probe generator (stdlib-only, deterministic).

Builds throwaway lane-task probes (IDs M1R-T0-*, never reused as
train/test) from the FROZEN H2 accept grids (read-only JSON inputs,
same precedent as L1 gen_tasks.py reading the frozen accept pack):
  T4: accept/S2.json grid (4 tasks / 4 slots)
  T5: accept/S4-followup.json grid (5 tasks / 5 slots)
  T6: T5 grid + slot S5{M0,t3} + task F{window:[S5]} + precedence [E,F]
      (L1 precedent shape, proven VALID 6/6 as a follow-up)

Transforms are solvability-preserving ONLY (task-label permutation +
machine swap, seeded). Holdings partitions are pre-registered below to
span derived_rounds x split x side shapes.

Usage:
  PYTHONDONTWRITEBYTECODE=1 python3 gen_step0.py --out t0-throwaway/tasks
Prints task_id, size, shape, sha256 per file.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import random
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
H2 = HERE / ".." / "H2-lane"
H2 = H2.resolve()

# (probe_id, size, seed_or_None, holdings_spec, adapter)
# holdings_spec: (L_req, L_pref) as index lists into sorted task labels
#   (S sides get the complement). "ALL_L"/"ALL_S" shortcuts.
# All probe IDs are 9 chars (task_id length enters fragment bytes).
PROBES = [
    # 4-task base (S2 grid, n_prec=2)
    ("M1R-T0-01", 4, None, "ALL_L", "list2slot/v1"),   # (4,4) r2 splitF
    ("M1R-T0-02", 4, None, "ALL_S", "list2slot/v1"),   # (0,0) r2 splitF
    ("M1R-T0-03", 4, None, ([0, 1], [0, 1]), "list2slot/v1"),  # halves (2,2)
    ("M1R-T0-04", 4, None, ([0, 1, 2, 3], []), "list2slot/v1"),  # (4,0)
    ("M1R-T0-05", 4, None, ([0, 1], [0, 1, 2, 3]), "list2slot/v1"),  # (2,4)
    ("M1R-T0-06", 4, None, ([0], [0]), "list2slot/v1"),  # 1v3 (1,1)
    ("M1R-T0-07", 4, 701, ([0, 1], [0, 1]), "list2slot/v1"),  # perm halves
    ("M1R-T0-08", 4, None, ([0, 1], [0, 1]), "list2slot/v2"),  # v2 dup of 03
    # 5-task base (S4 grid, n_prec=2)
    ("M1R-T0-09", 5, None, "ALL_L", "list2slot/v1"),   # (5,5)
    ("M1R-T0-10", 5, None, ([0, 1], [0, 1]), "list2slot/v1"),  # 2v3 halves
    ("M1R-T0-11", 5, None, ([0, 1, 2, 3, 4], []), "list2slot/v1"),  # (5,0)
    ("M1R-T0-12", 5, None, ([0, 1, 2], [0, 1, 2, 3, 4]), "list2slot/v1"),  # (3,5)
    # 6-task base (T6, n_prec=3)
    ("M1R-T0-13", 6, None, "ALL_L", "list2slot/v1"),   # (6,6)
    ("M1R-T0-14", 6, None, ([0, 1, 2], [0, 1, 2]), "list2slot/v1"),  # 3v3
    ("M1R-T0-15", 6, None, ([0], [0]), "list2slot/v1"),  # 1v5 (1,1)
]


def load_base4() -> dict:
    b = json.loads((H2 / "accept" / "S2.json").read_text(encoding="utf-8"))
    return {"slots": b["slots"], "tasks": b["tasks"],
            "precedence": b["precedence"], "prefs": b["prefs"]}


def load_base5() -> dict:
    b = json.loads((H2 / "accept" / "S4-followup.json").read_text(
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


def transform(base: dict, seed: int | None) -> dict:
    """Solvability-preserving transform (L1 precedent). None = identity."""
    if seed is None:
        return {"slots": dict(base["slots"]),
                "tasks": {k: {"window": list(v["window"])}
                          for k, v in base["tasks"].items()},
                "precedence": [list(p) for p in base["precedence"]],
                "prefs": dict(base["prefs"])}
    rng = random.Random(seed)
    labels = sorted(base["tasks"])
    perm = rng.sample(labels, len(labels))
    m = dict(zip(labels, perm))
    swap = rng.random() < 0.5
    sw = (lambda x: {"M0": "M1", "M1": "M0"}[x]) if swap else (lambda x: x)
    return {
        "slots": {s: {"machine": sw(v["machine"]), "time": v["time"]}
                  for s, v in sorted(base["slots"].items())},
        "tasks": {m[k]: {"window": list(v["window"])}
                  for k, v in sorted(base["tasks"].items())},
        "precedence": [[m[a], m[b]] for a, b in base["precedence"]],
        "prefs": {m[k]: sw(v) for k, v in sorted(base["prefs"].items())},
    }


def holdings(labels: list[str], spec) -> dict:
    if spec == "ALL_L":
        return {"SC-L": {"req_tasks": list(labels), "prefs": list(labels)},
                "SC-S": {"req_tasks": [], "prefs": []}}
    if spec == "ALL_S":
        return {"SC-L": {"req_tasks": [], "prefs": []},
                "SC-S": {"req_tasks": list(labels), "prefs": list(labels)}}
    li, pi = spec
    l_req = [labels[i] for i in li]
    l_pref = [labels[i] for i in pi]
    s_req = [t for t in labels if t not in l_req]
    s_pref = [t for t in labels if t not in l_pref]
    return {"SC-L": {"req_tasks": l_req, "prefs": l_pref},
            "SC-S": {"req_tasks": s_req, "prefs": s_pref}}


def main(argv: list[str]) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default="t0-throwaway/tasks")
    args = ap.parse_args(argv)
    out = HERE / args.out
    out.mkdir(parents=True, exist_ok=True)
    for pid, size, seed, spec, adapter in PROBES:
        assert len(pid) == 9, pid
        g = transform(BASES[size](), seed)
        labels = sorted(g["tasks"])
        t = {"task_id": pid, "slots": g["slots"], "tasks": g["tasks"],
             "precedence": g["precedence"], "prefs": g["prefs"],
             "holdings": holdings(labels, spec), "adapter": adapter}
        p = out / f"{pid}.json"
        p.write_text(json.dumps(t, indent=2, sort_keys=True) + "\n",
                     encoding="utf-8")
        h = hashlib.sha256(p.read_bytes()).hexdigest()
        lr = t["holdings"]["SC-L"]
        print(f"{pid} size={size} seed={seed} "
              f"L=({len(lr['req_tasks'])},{len(lr['prefs'])}) "
              f"adapter={adapter[-2:]} sha256={h[:16]}")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
