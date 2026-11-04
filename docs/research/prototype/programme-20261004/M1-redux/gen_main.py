"""M1-redux main-family generator (stdlib-only, deterministic).

Train/test lane tasks with DISJOINT descriptors (IDs, grids/seeds,
holdings splits) but shared fine-shape coverage (test shapes ⊆ train
shapes — stratum coverage, not descriptor overlap).

Bases: frozen H2 accept S2 grid (T4), S4-followup grid (T5), T6
extension (L1-precedent). Transforms: solvability-preserving
label-permutation + machine-swap only (seeded) or identity.

- TRAIN (M1R-TR-01..18): plain grids, canonical index splits.
- TEST (M1R-TE-01..18): even cell index -> permuted grid (seed 900+idx);
  odd cell index -> plain grid with COMPLEMENTARY index splits
  (halves/1vREST/split3 from the other end; ALL_*/REQL_PREFS have no
  complement and keep canonical splits).
All IDs are 9 chars (task_id length enters fragment bytes).

Usage:
  PYTHONDONTWRITEBYTECODE=1 python3 gen_main.py --out main/tasks
Prints task_id, split, size, shape, seed, sha per file.
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

SHAPES = ["ALL_L", "ALL_S", "HALVES", "REQL_PREFS", "SPLIT3", "ONEVREST"]
SIZES = [4, 5, 6]


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


def split_spec(shape: str, size: int, complement: bool):
    """Return (L_req_idx, L_pref_idx) into sorted labels (train canonical
    unless complement=True, which mirrors from the other end)."""
    n = size
    half = n // 2
    if shape == "ALL_L":
        return (list(range(n)), list(range(n)))
    if shape == "ALL_S":
        return ([], [])
    if shape == "REQL_PREFS":
        return (list(range(n)), [])
    if shape == "HALVES":
        idx = list(range(n - half, n)) if complement else list(range(half))
        # size 5: halves are 2v3 either way
        if size == 5 and complement:
            idx = [3, 4]
        if size == 5 and not complement:
            idx = [0, 1]
        return (idx, list(idx))
    if shape == "SPLIT3":
        if size == 4:
            req = [2, 3] if complement else [0, 1]
        elif size == 5:
            req = [2, 3, 4] if complement else [0, 1, 2]
        else:
            req = [3, 4, 5] if complement else [0, 1, 2]
        return (req, list(range(n)))
    if shape == "ONEVREST":
        idx = [n - 1] if complement else [0]
        return (idx, list(idx))
    raise ValueError(shape)


def holdings(labels: list[str], spec) -> dict:
    li, pi = spec
    l_req = [labels[i] for i in li]
    l_pref = [labels[i] for i in pi]
    return {"SC-L": {"req_tasks": l_req, "prefs": l_pref},
            "SC-S": {"req_tasks": [t for t in labels if t not in l_req],
                     "prefs": [t for t in labels if t not in l_pref]}}


def main(argv: list[str]) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default="main/tasks")
    args = ap.parse_args(argv)
    out = HERE / args.out
    out.mkdir(parents=True, exist_ok=True)
    cells = [(size, shape) for size in SIZES for shape in SHAPES]
    assert len(cells) == 18
    for idx, (size, shape) in enumerate(cells):
        # TRAIN: plain grid, canonical splits
        g = transform(BASES[size](), None)
        labels = sorted(g["tasks"])
        t = {"task_id": f"M1R-TR-{idx+1:02d}", "slots": g["slots"],
             "tasks": g["tasks"], "precedence": g["precedence"],
             "prefs": g["prefs"],
             "holdings": holdings(labels, split_spec(shape, size, False)),
             "adapter": "list2slot/v1"}
        p = out / f"{t['task_id']}.json"
        p.write_text(json.dumps(t, indent=2, sort_keys=True) + "\n",
                     encoding="utf-8")
        h = hashlib.sha256(p.read_bytes()).hexdigest()[:16]
        lr = t["holdings"]["SC-L"]
        print(f"{t['task_id']} train size={size} shape={shape} seed=None "
              f"L=({len(lr['req_tasks'])},{len(lr['prefs'])}) sha={h}")
    for idx, (size, shape) in enumerate(cells):
        # TEST: even idx permuted (seed 900+idx, canonical splits);
        # odd idx plain with complementary splits.
        permuted = (idx % 2 == 0)
        seed = 900 + idx if permuted else None
        g = transform(BASES[size](), seed)
        labels = sorted(g["tasks"])
        spec = split_spec(shape, size, complement=not permuted)
        t = {"task_id": f"M1R-TE-{idx+1:02d}", "slots": g["slots"],
             "tasks": g["tasks"], "precedence": g["precedence"],
             "prefs": g["prefs"],
             "holdings": holdings(labels, spec),
             "adapter": "list2slot/v1"}
        p = out / f"{t['task_id']}.json"
        p.write_text(json.dumps(t, indent=2, sort_keys=True) + "\n",
                     encoding="utf-8")
        h = hashlib.sha256(p.read_bytes()).hexdigest()[:16]
        lr = t["holdings"]["SC-L"]
        print(f"{t['task_id']} test size={size} shape={shape} seed={seed} "
              f"L=({len(lr['req_tasks'])},{len(lr['prefs'])}) sha={h}")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
