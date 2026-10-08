"""L1 harness (stdlib-only). Drives frozen r1 ONLY via release.py CLI.

Subcommands (run in order): extract -> transfer -> baseline -> secondary -> verdict
  extract   both arms on TRAIN tasks, fit recipe.json (mechanical, prereg §4)
  transfer  recipe arm on HELD-OUT tasks (recipe consumed read-only)
  baseline  fixed split-pair arm on HELD-OUT tasks
  secondary fit routing rule on setup observations, predict 8 descriptors
  verdict   mechanical P1/P2/P3 + calibration guard + secondary check

Every CLI call is logged (command + rc + stdout/stderr tails) under logs/.
First-run results stand; no retries.
"""
from __future__ import annotations

import hashlib
import json
import subprocess
import sys
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
R1 = (HERE / ".." / ".." / "successor-002").resolve()
RELEASE = str(R1 / "release.py")
TASKS = HERE / "tasks"
RUNS = HERE / "runs"
LOGS = HERE / "logs"

TRAIN = [f"L1-TR-0{i}" for i in range(1, 7)]
TEST = [f"L1-TE-{i:02d}" for i in range(1, 13)]
PARTITION = ("sched.requirements=SC-L2,sched.composite=SC-L2,"
             "sched.slots=SC-S2")
ENV = {"PYTHONDONTWRITEBYTECODE": "1"}

CAL_S1 = {"lane": "central", "central": 655, "direct": 0}
CAL_S2 = {"lane": "local", "central": 310, "direct": 500}


def sha16(p: Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()[:16]


def run_cli(args: list[str], log: list) -> dict:
    t0 = time.monotonic()
    cmd = [sys.executable, RELEASE] + args
    r = subprocess.run(cmd, capture_output=True, text=True,
                       env={**dict(__import__("os").environ), **ENV})
    dt = time.monotonic() - t0
    rec = {"cmd": " ".join(["release.py"] + args), "rc": r.returncode,
           "secs": round(dt, 2), "stdout": r.stdout, "stderr": r.stderr}
    log.append(rec)
    return rec


def parse_run_stdout(out: str) -> dict:
    # "S1: lane=central valid=True quality=4/4 central=655 direct=0"
    obs = {}
    for line in out.splitlines():
        parts = line.split()
        if len(parts) >= 2 and parts[0].endswith(":") and "lane=" in line:
            name = parts[0][:-1]
            kv = dict(p.split("=", 1) for p in parts[1:] if "=" in p)
            obs[name] = {"lane": kv.get("lane"),
                         "central": int(kv.get("central", -1)),
                         "direct": int(kv.get("direct", -1)),
                         "valid": kv.get("valid") == "True",
                         "quality": kv.get("quality")}
    return obs


def ledger_stats(state: Path) -> dict:
    lp = state / "ledger.jsonl"
    lines = lp.read_text(encoding="utf-8").splitlines()
    kinds: dict[str, int] = {}
    for ln in lines:
        try:
            k = json.loads(ln).get("kind", "?")
        except json.JSONDecodeError:
            k = "?"
        kinds[k] = kinds.get(k, 0) + 1
    return {"ledger_entries": len(lines),
            "invokes": kinds.get("invoke", 0),
            "ledger_bytes": lp.stat().st_size,
            "ledger_sha16": sha16(lp), "kinds": kinds}


def solution_stats(state: Path, task_id: str) -> dict:
    sp = state / "artifacts" / f"solution-{task_id}.json"
    if not sp.exists():
        return {"valid": False, "quality": None, "prefs_total": None,
                "artifact": None}
    b = json.loads(sp.read_text(encoding="utf-8"))
    return {"valid": bool(b.get("valid")), "quality": b.get("quality"),
            "prefs_total": b.get("prefs_total"),
            "artifact_sha16": sha16(sp)}


def run_arm(task_id: str, arm: str, phase: str) -> dict:
    """One task x arm on a fresh state dir. No retries; failures recorded."""
    assert arm in ("reuse", "split")
    state = RUNS / phase / f"{task_id}-{arm}"
    log: list[dict] = []
    rec: dict = {"task_id": task_id, "arm": arm, "phase": phase,
                 "state_dir": str(state.relative_to(HERE)),
                 "failed_step": None}
    t0 = time.monotonic()
    followup = str(TASKS / f"{task_id}.json")
    ok = True
    r = run_cli(["init", "--state-dir", str(state)], log)
    ok = ok and r["rc"] == 0
    if ok:
        r = run_cli(["run", "--state-dir", str(state), "--tasks", "S1,S2"],
                    log)
        ok = ok and r["rc"] == 0
        rec["setup_obs"] = parse_run_stdout(r["stdout"])
    if ok:
        r = run_cli(["ops", "fuse", "--state-dir", str(state), "--a", "SC-L",
                     "--b", "SC-S", "--fused", "SC-FUSED",
                     "--reason", f"L1 {phase} {task_id} {arm}"], log)
        ok = ok and r["rc"] == 0
    if ok and arm == "reuse":
        r = run_cli(["ops", "reuse", "--state-dir", str(state),
                     "--composite", "SC-FUSED", "--followup", followup], log)
        if r["rc"] != 0:
            rec["failed_step"] = "reuse"
            ok = False
    if ok and arm == "split":
        r = run_cli(["ops", "fission", "--state-dir", str(state),
                     "--composite", "SC-FUSED", "--left", "SC-L2",
                     "--right", "SC-S2", "--partition", PARTITION,
                     "--reason", f"L1 {phase} {task_id} {arm}"], log)
        ok = ok and r["rc"] == 0
        if ok:
            r = run_cli(["ops", "split-pair", "--state-dir", str(state),
                         "--left", "SC-L2", "--right", "SC-S2",
                         "--followup", followup], log)
            if r["rc"] != 0:
                rec["failed_step"] = "split-pair"
                ok = False
    if ok:
        # Settle only ACTIVE worlds (r1 refuses dissolved->dissolved edges).
        # World list discovered read-only via inspect (consumer interface).
        r = run_cli(["inspect", "--state-dir", str(state), "--json"], log)
        if r["rc"] != 0:
            rec["failed_step"] = "inspect"
            ok = False
        else:
            act = [w for w, d in
                   json.loads(r["stdout"])["worlds"].items()
                   if d["lifecycle"] == "active"]
            rec["settled_worlds"] = act
            r = run_cli(["ops", "settle", "--state-dir", str(state),
                         "--worlds", ",".join(act),
                         "--reason", f"L1 {phase} finish {task_id}"], log)
            if r["rc"] != 0:
                rec["failed_step"] = "settle"
                ok = False
    rec["wall_secs"] = round(time.monotonic() - t0, 2)
    rec.update(ledger_stats(state))
    rec.update(solution_stats(state, task_id))
    rec["ok"] = ok
    (LOGS / phase).mkdir(parents=True, exist_ok=True)
    (LOGS / phase / f"{task_id}-{arm}.json").write_text(
        json.dumps(log, indent=2, sort_keys=True), encoding="utf-8")
    return rec


def task_features(task_id: str) -> dict:
    t = json.loads((TASKS / f"{task_id}.json").read_text(encoding="utf-8"))
    n = len(t["tasks"])
    shape = {4: "fresh-4", 5: "extension-5", 6: "extension-6"}[n]
    return {"n_tasks": n, "n_slots": len(t["slots"]), "shape": shape}


def fit_recipe(rows: list[dict]) -> dict:
    by_task = {r["task_id"]: r for r in rows if r["arm"] == "reuse"}
    by_task_s = {r["task_id"]: r for r in rows if r["arm"] == "split"}
    groups: dict[str, list[str]] = {}
    for tid in by_task:
        g = task_features(tid)["shape"]
        groups.setdefault(g, []).append(tid)
    gcost = {"reuse": sum(r["ledger_entries"] for r in rows
                          if r["arm"] == "reuse"),
             "split": sum(r["ledger_entries"] for r in rows
                          if r["arm"] == "split")}
    global_cheaper = ("reuse" if gcost["reuse"] <= gcost["split"]
                      else "split")
    decisions = {}
    for g, tids in sorted(groups.items()):
        votes = []
        for tid in tids:
            a, b = by_task[tid], by_task_s[tid]
            if a["valid"] and not b["valid"]:
                votes.append("reuse")
            elif b["valid"] and not a["valid"]:
                votes.append("split")
            elif not a["valid"] and not b["valid"]:
                continue  # abstain; reported
            else:
                votes.append("reuse" if a["ledger_entries"]
                             <= b["ledger_entries"] else "split")
        if not votes:
            decisions[g] = global_cheaper
        elif votes.count("reuse") == votes.count("split"):
            decisions[g] = global_cheaper
        else:
            decisions[g] = ("reuse" if votes.count("reuse") >
                            votes.count("split") else "split")
    return {"groups": decisions, "default": global_cheaper,
            "group_costs": gcost, "fit_votes": {
                g: [1 if by_task[t]["ledger_entries"] <=
                    by_task_s[t]["ledger_entries"] else 0 for t in tids]
                for g, tids in groups.items()}}


def check_calibration(rows: list[dict]) -> list[str]:
    problems = []
    for r in rows:
        obs = r.get("setup_obs", {})
        for name, exp in (("S1", CAL_S1), ("S2", CAL_S2)):
            o = obs.get(name, {})
            if (o.get("lane") != exp["lane"]
                    or o.get("central") != exp["central"]
                    or o.get("direct") != exp["direct"]
                    or o.get("valid") is not True):
                problems.append(f"{r['task_id']}-{r['arm']}: {name} "
                                f"observed {o}, expected {exp}")
    return problems


def cmd_extract() -> int:
    rows = []
    for tid in TRAIN:
        for arm in ("reuse", "split"):
            print(f"[extract] {tid} {arm}", flush=True)
            rows.append(run_arm(tid, arm, "extract"))
    (RUNS / "extraction-log.json").write_text(
        json.dumps(rows, indent=2, sort_keys=True), encoding="utf-8")
    recipe = fit_recipe(rows)
    rp = HERE / "recipe.json"
    rp.write_text(json.dumps(recipe, indent=2, sort_keys=True) + "\n",
                  encoding="utf-8")
    rp.chmod(0o444)  # frozen: transfer consumes read-only
    print("recipe:", json.dumps(recipe, sort_keys=True))
    print("recipe sha:", hashlib.sha256(rp.read_bytes()).hexdigest())
    probs = check_calibration(rows)
    print("calibration problems:", probs if probs else "none")
    return 0


def cmd_transfer() -> int:
    rp = HERE / "recipe.json"
    print("recipe sha at transfer start:",
          hashlib.sha256(rp.read_bytes()).hexdigest(), flush=True)
    recipe = json.loads(rp.read_text(encoding="utf-8"))
    rows = []
    for tid in TEST:
        arm = recipe["groups"].get(task_features(tid)["shape"],
                                   recipe["default"])
        print(f"[transfer] {tid} -> {arm}", flush=True)
        r = run_arm(tid, arm, "transfer")
        r["recipe_arm"] = arm
        rows.append(r)
    (RUNS / "transfer-log.json").write_text(
        json.dumps(rows, indent=2, sort_keys=True), encoding="utf-8")
    probs = check_calibration(rows)
    print("calibration problems:", probs if probs else "none")
    return 0


def cmd_baseline() -> int:
    rows = []
    for tid in TEST:
        print(f"[baseline] {tid} -> split", flush=True)
        rows.append(run_arm(tid, "split", "baseline"))
    (RUNS / "baseline-log.json").write_text(
        json.dumps(rows, indent=2, sort_keys=True), encoding="utf-8")
    probs = check_calibration(rows)
    print("calibration problems:", probs if probs else "none")
    return 0


def cmd_secondary() -> int:
    ext = json.loads((RUNS / "extraction-log.json").read_text(
        encoding="utf-8"))
    s1 = json.loads((R1 / "accept" / "S1.json").read_text(encoding="utf-8"))
    s2 = json.loads((R1 / "accept" / "S2.json").read_text(encoding="utf-8"))
    obs = []
    seen = set()
    for r in ext:
        for name, feat in (("S1", s1), ("S2", s2)):
            lane = r.get("setup_obs", {}).get(name, {}).get("lane")
            key = (feat["expected_rounds"], feat["split_state"], lane)
            if key not in seen:
                seen.add(key)
                obs.append({"rounds": feat["expected_rounds"],
                            "split": feat["split_state"], "lane": lane})
    cands = [("always-central", 0, lambda ro, sp: "central"),
             ("always-local", 0, lambda ro, sp: "local"),
             ("local-iff-split", 1, lambda ro, sp: "local" if sp
              else "central")]
    for k in range(1, 6):
        cands.append((f"local-iff-rounds>={k}", 1,
                      lambda ro, sp, k=k: "local" if ro >= k else "central"))
        cands.append((f"local-iff-rounds>={k}-and-split", 2,
                      lambda ro, sp, k=k: "local" if (ro >= k and sp)
                      else "central"))
    consistent = [c for c in cands
                  if all(c[2](o["rounds"], o["split"]) == o["lane"]
                         for o in obs)]
    consistent.sort(key=lambda c: (c[1], c[0]))
    rule = consistent[0]
    descs = json.loads((TASKS / "secondary-descriptors.json").read_text(
        encoding="utf-8"))
    (RUNS / "secondary").mkdir(exist_ok=True)
    results = []
    for d in descs:
        p = RUNS / "secondary" / f"{d['desc_id']}.json"
        p.write_text(json.dumps(d["task"], indent=2, sort_keys=True),
                     encoding="utf-8")
        r = subprocess.run([sys.executable, RELEASE, "explain-route",
                            "--task-json", str(p), "--json"],
                           capture_output=True, text=True,
                           env={**dict(__import__("os").environ), **ENV})
        truth = json.loads(r.stdout).get("lane")
        pred = rule[2](d["expected_rounds"], d["split_state"])
        results.append({"desc_id": d["desc_id"], "pred": pred,
                        "truth": truth, "hit": pred == truth,
                        "base_pred": "central",
                        "base_hit": truth == "central"})
    acc = sum(r["hit"] for r in results) / len(results)
    bacc = sum(r["base_hit"] for r in results) / len(results)
    out = {"observations": obs, "rule": rule[0], "accuracy": acc,
           "baseline_accuracy": bacc, "results": results}
    (RUNS / "secondary-log.json").write_text(
        json.dumps(out, indent=2, sort_keys=True), encoding="utf-8")
    print(f"rule={rule[0]} accuracy={acc:.3f} baseline={bacc:.3f}")
    return 0


def cmd_verdict() -> int:
    ext = json.loads((RUNS / "extraction-log.json").read_text(
        encoding="utf-8"))
    tr = json.loads((RUNS / "transfer-log.json").read_text(encoding="utf-8"))
    bl = json.loads((RUNS / "baseline-log.json").read_text(encoding="utf-8"))
    sec = json.loads((RUNS / "secondary-log.json").read_text(
        encoding="utf-8"))
    cal = check_calibration(ext + tr + bl)
    # P1: recipe choices differ from BOTH fixed paths on >=2 test tasks
    choices = [r["recipe_arm"] for r in tr]
    p1 = (sum(c != "reuse" for c in choices) >= 2
          and sum(c != "split" for c in choices) >= 2)
    # P2: equal VALID rates
    p2 = (sum(r["valid"] for r in tr) == sum(r["valid"] for r in bl)
          == len(TEST))
    # P3: strict net gain in entries AND invokes
    acq_e = sum(r["ledger_entries"] for r in ext)
    acq_i = sum(r["invokes"] for r in ext)
    tr_e = sum(r["ledger_entries"] for r in tr)
    tr_i = sum(r["invokes"] for r in tr)
    bl_e = sum(r["ledger_entries"] for r in bl)
    bl_i = sum(r["invokes"] for r in bl)
    p3 = (acq_e + tr_e < bl_e) and (acq_i + tr_i < bl_i)
    verdict = {
        "calibration_guard": "VOID" if cal else "OK",
        "calibration_problems": cal,
        "P1_conditional": {"pass": p1, "choices": choices},
        "P2_parity": {"pass": p2,
                      "recipe_valid": sum(r["valid"] for r in tr),
                      "baseline_valid": sum(r["valid"] for r in bl),
                      "n": len(TEST)},
        "P3_net_gain": {"pass": p3, "acquisition_entries": acq_e,
                        "acquisition_invokes": acq_i,
                        "recipe_entries": tr_e, "recipe_invokes": tr_i,
                        "baseline_entries": bl_e,
                        "baseline_invokes": bl_i},
        "secondary": {"pass": sec["accuracy"] > sec["baseline_accuracy"],
                      **{k: sec[k] for k in ("rule", "accuracy",
                                             "baseline_accuracy")}},
        "OVERALL": "PASS" if (p1 and p2 and p3 and not cal) else "NEGATIVE",
    }
    (RUNS / "verdict.json").write_text(
        json.dumps(verdict, indent=2, sort_keys=True), encoding="utf-8")
    print(json.dumps(verdict, indent=2, sort_keys=True))
    return 0 if not cal else 2


CMDS = {"extract": cmd_extract, "transfer": cmd_transfer,
        "baseline": cmd_baseline, "secondary": cmd_secondary,
        "verdict": cmd_verdict}


def main(argv: list[str]) -> int:
    if len(argv) != 2 or argv[1] not in CMDS:
        print(f"usage: harness.py [{'|'.join(CMDS)}]", file=sys.stderr)
        return 1
    RUNS.mkdir(exist_ok=True)
    LOGS.mkdir(exist_ok=True)
    return CMDS[argv[1]]()


if __name__ == "__main__":
    sys.exit(main(sys.argv))
