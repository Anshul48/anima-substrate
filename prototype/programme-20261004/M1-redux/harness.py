"""M1-redux harness: features + fit + predict + baselines + verdict (stdlib-only).

Fit on train items, evaluate ONCE on held-out test items. The verdict
imports the frozen predicates.py (never reimplements it).

Usage (SINGLE evaluation run, after ALL executions):
  PYTHONDONTWRITEBYTECODE=1 python3 harness.py
Writes main/verdict.json + prints the primary + secondary report.
"""
from __future__ import annotations

import glob
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import predicates  # noqa: E402  (frozen prereg predicates)

TASKS = HERE / "main" / "tasks"


def features(task: dict, lane: str) -> dict:
    """All features computable from the task JSON WITHOUT execution.
    Derivation mirrors the DOCUMENTED H2.2 rule (own implementation)."""
    hold = task["holdings"]
    L, S = hold["SC-L"], hold["SC-S"]
    nL_req, nS_req = len(L["req_tasks"]), len(S["req_tasks"])
    nL_pref, nS_pref = len(L["prefs"]), len(S["prefs"])
    rounds = sum([bool(L["req_tasks"]), bool(S["req_tasks"]),
                  bool(L["prefs"]), bool(S["prefs"])])
    split = bool(L["req_tasks"] or L["prefs"]) \
        and bool(S["req_tasks"] or S["prefs"])
    return {
        "n_tasks": len(task["tasks"]), "n_slots": len(task["slots"]),
        "n_prec": len(task["precedence"]),
        "nL_req": nL_req, "nS_req": nS_req,
        "nL_pref": nL_pref, "nS_pref": nS_pref,
        "derived_rounds": rounds, "derived_split": split,
        "rule_lane": "local" if (rounds >= 2 and split) else "central",
        "lane": lane,
    }


def group_key(f: dict) -> tuple:
    return (f["n_tasks"], f["nL_req"], f["nS_req"], f["nL_pref"],
            f["nS_pref"], f["lane"])


def rule_key(f: dict) -> tuple:
    return (f["rule_lane"], f["lane"])


def load_items(results_path: Path) -> list[dict]:
    """Flatten one-task-per-dir results into (task_id, lane, bytes, ...)."""
    items = []
    for r in json.loads(results_path.read_text(encoding="utf-8")):
        if r["name"].startswith("guard-"):
            continue
        if r["rc"] != 0 or not r.get("tasks"):
            items.append({"run": r["name"], "missing": True})
            continue
        t = r["tasks"][0]
        items.append({
            "run": r["name"], "task_id": t["task_id"], "lane": t["lane"],
            "central_bytes": t["central_bytes"],
            "direct_bytes": t["direct_bytes"],
            "valid": bool(t["valid_cli"]) and bool(t["valid_artifact"]),
            "ledger_entries": r["ledger_entries"], "invokes": r["invokes"],
            "wall_s": r["wall_s"],
        })
    return items


def guards_ok(results_path: Path, guard_name: str) -> bool:
    for r in json.loads(results_path.read_text(encoding="utf-8")):
        if r["name"] != guard_name:
            continue
        if r["rc"] != 0:
            return False
        got = {t["task_id"]: (t["central_bytes"], t["direct_bytes"])
               for t in r.get("tasks", [])}
        return got.get("S1") == (655, 0) and got.get("S2") == (310, 500)
    return False


def mae(pairs: list[tuple[float, float]]) -> float:
    return sum(abs(p - a) for p, a in pairs) / len(pairs)


def main() -> int:
    task_cache: dict[str, dict] = {}

    def task_of(tid: str) -> dict:
        if tid not in task_cache:
            task_cache[tid] = json.loads(
                (TASKS / f"{tid}.json").read_text(encoding="utf-8"))
        return task_cache[tid]

    train = load_items(HERE / "main" / "train-results.json")
    test = load_items(HERE / "main" / "test-results.json")
    train = [i for i in train if not i.get("missing")]
    test_present = [i for i in test if not i.get("missing")]
    n_test_items = len(test_present)
    n_valid_test = sum(1 for i in test_present if i["valid"])

    # Fit on train only.
    groups: dict[tuple, list[float]] = {}
    lane_vals: dict[str, list[float]] = {}
    rule_vals: dict[tuple, list[float]] = {}
    all_vals: list[float] = []
    for i in train:
        f = features(task_of(i["task_id"]), i["lane"])
        groups.setdefault(group_key(f), []).append(i["central_bytes"])
        lane_vals.setdefault(f["lane"], []).append(i["central_bytes"])
        rule_vals.setdefault(rule_key(f), []).append(i["central_bytes"])
        all_vals.append(i["central_bytes"])
    group_mean = {k: sum(v) / len(v) for k, v in groups.items()}
    lane_mean = {k: sum(v) / len(v) for k, v in lane_vals.items()}
    rule_mean = {k: sum(v) / len(v) for k, v in rule_vals.items()}
    const = sum(all_vals) / len(all_vals)

    # Predict test (single pass, no tuning).
    fallback_uses = 0
    mp, cp, rp = [], [], []
    rows = []
    for i in test_present:
        f = features(task_of(i["task_id"]), i["lane"])
        key = group_key(f)
        if key in group_mean:
            pred = group_mean[key]
        else:
            pred = lane_mean[f["lane"]]
            fallback_uses += 1
        mp.append((pred, i["central_bytes"]))
        cp.append((const, i["central_bytes"]))
        rp.append((rule_mean[rule_key(f)], i["central_bytes"]))
        rows.append({"task_id": i["task_id"], "lane": i["lane"],
                     "actual": i["central_bytes"], "pred_model": pred,
                     "pred_const": const,
                     "pred_rule": rule_mean[rule_key(f)],
                     "n_tasks": f["n_tasks"],
                     "fallback": key not in group_mean})
    mae_model, mae_const, mae_rule = mae(mp), mae(cp), mae(rp)

    g_ok = guards_ok(HERE / "main" / "train-results.json",
                     "guard-train-S1S2") and guards_ok(
                         HERE / "main" / "test-results.json",
                         "guard-test-S1S2")
    tr_ids = {p.stem for p in TASKS.glob("M1R-TR-*.json")}
    te_ids = {p.stem for p in TASKS.glob("M1R-TE-*.json")}
    t0_ids = {p.stem for p in
              (HERE / "t0-throwaway" / "tasks").glob("M1R-T0-*.json")}
    disjoint = (not (tr_ids & te_ids) and not (tr_ids & t0_ids)
                and not (te_ids & t0_ids)
                and len(tr_ids) == 18 and len(te_ids) == 18)

    v = predicates.verdict(mae_model, mae_const, mae_rule, n_test_items,
                           n_valid_test, fallback_uses, g_ok, disjoint)
    out = {"mae_model": mae_model, "mae_const": mae_const,
           "mae_rule": mae_rule, "n_test_items": n_test_items,
           "n_valid_test": n_valid_test, "fallback_uses": fallback_uses,
           "guards_ok": g_ok, "ids_disjoint": disjoint,
           "n_train_items": len(train), "n_groups_fit": len(group_mean),
           "predicates": dict(v), "rows": rows}
    (HERE / "main" / "verdict.json").write_text(
        json.dumps(out, indent=2, sort_keys=True) + "\n", encoding="utf-8")

    print(f"model MAE={mae_model:.2f} const MAE={mae_const:.2f} "
          f"rule MAE={mae_rule:.2f}")
    print(f"P1={v['P1']} P2={v['P2']} valid={v['valid']} OVERALL={v['OVERALL']}")
    print(f"items={n_test_items} valid={n_valid_test} "
          f"fallback={fallback_uses} guards={g_ok} disjoint={disjoint}")
    # Secondaries (advisory, no thresholds).
    for size in (4, 5, 6):
        sub = [(r["pred_model"], r["actual"]) for r in rows
               if r["n_tasks"] == size]
        print(f"  size-{size} model MAE={mae(sub):.2f} n={len(sub)}")
    for tag, sel in (("permuted", lambda tid: int(tid[-2:]) % 2 == 1),
                     ("plain", lambda tid: int(tid[-2:]) % 2 == 0)):
        sub = [(r["pred_model"], r["actual"]) for r in rows
               if sel(r["task_id"])]
        print(f"  test-{tag} model MAE={mae(sub):.2f} n={len(sub)}")
    print(f"  max|err| model={max(abs(p-a) for p, a in mp):.1f} "
          f"const={max(abs(p-a) for p, a in cp):.1f} "
          f"rule={max(abs(p-a) for p, a in rp):.1f}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
