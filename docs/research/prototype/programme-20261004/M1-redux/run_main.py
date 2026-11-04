"""M1-redux main runner (stdlib-only).

Executes the frozen family: 18 train + 18 test tasks x both lanes +
one S1/S2 guard per phase, via the release.py CLI (black-box
subprocesses only). One task per state dir.

Usage:
  PYTHONDONTWRITEBYTECODE=1 python3 run_main.py
Writes main/train-results.json, main/test-results.json (+ guards inside).
"""
from __future__ import annotations

import json
import re
import subprocess
import sys
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE / ".." / ".." / ".."
ROOT = ROOT.resolve()
H2 = HERE / ".." / "H2-lane"
H2 = H2.resolve()
RELEASE = H2 / "release.py"
TASKS = HERE / "main" / "tasks"
RUNS = HERE / "main" / "runs"

LINE_RE = re.compile(
    r"^(?P<tid>\S+): lane=(?P<lane>\S+) valid=(?P<valid>\S+) "
    r"quality=(?P<q>\d+)/(?P<pt>\d+) "
    r"central=(?P<central>\d+) direct=(?P<direct>\d+)")


def cli(args: list[str]) -> subprocess.CompletedProcess:
    env = {"PYTHONDONTWRITEBYTECODE": "1", "PATH": "/usr/bin:/bin"}
    return subprocess.run(
        [sys.executable, str(RELEASE)] + args, capture_output=True,
        text=True, env=env, cwd=str(ROOT), timeout=300)


def ledger_stats(run_dir: Path) -> tuple[int, int]:
    entries, invokes = 0, 0
    for line in (run_dir / "ledger.jsonl").read_text(
            encoding="utf-8").splitlines():
        line = line.strip()
        if not line:
            continue
        entries += 1
        if json.loads(line).get("kind") == "invoke":
            invokes += 1
    return entries, invokes


def solution_valid(run_dir: Path, tid: str) -> bool | None:
    p = run_dir / "artifacts" / f"solution-{tid}.json"
    if not p.exists():
        return None
    return bool(json.loads(p.read_text(encoding="utf-8"))["valid"])


def one_run(name: str, task_json: str | None = None,
            tasks: str | None = None,
            lane_override: str | None = None) -> dict:
    run_dir = RUNS / name
    if run_dir.exists():
        raise RuntimeError(f"run dir exists (refusing overwrite): {run_dir}")
    t0 = time.time()
    r = cli(["init", "--state-dir", str(run_dir)])
    if r.returncode != 0:
        raise RuntimeError(f"init failed for {name}: {r.stderr.strip()}")
    args = ["run", "--state-dir", str(run_dir)]
    if task_json:
        args += ["--task-json", task_json]
    if tasks:
        args += ["--tasks", tasks]
    if lane_override:
        args += ["--lane-override", lane_override]
    r = cli(args)
    wall = time.time() - t0
    rec: dict = {"name": name, "rc": r.returncode, "wall_s": round(wall, 2),
                 "stderr": r.stderr.strip()[:300]}
    if r.returncode != 0:
        rec["stdout"] = r.stdout.strip()[:300]
        return rec
    per_task = []
    for line in r.stdout.splitlines():
        m = LINE_RE.match(line.strip())
        if not m:
            continue
        tid = m.group("tid")
        per_task.append({
            "task_id": tid, "lane": m.group("lane"),
            "valid_cli": m.group("valid") == "True",
            "quality": int(m.group("q")),
            "prefs_total": int(m.group("pt")),
            "central_bytes": int(m.group("central")),
            "direct_bytes": int(m.group("direct")),
            "valid_artifact": solution_valid(run_dir, tid),
        })
    rec["tasks"] = per_task
    entries, invokes = ledger_stats(run_dir)
    rec["ledger_entries"] = entries
    rec["invokes"] = invokes
    return rec


def sweep(prefix: str, ids: list[str]) -> list[dict]:
    out = []
    for pid in ids:
        for lane in ("central", "local"):
            name = f"{prefix}-{pid}-{lane}"
            rec = one_run(name, task_json=str(TASKS / f"{pid}.json"),
                          lane_override=lane)
            out.append(rec)
            for t in rec.get("tasks", []):
                print(f"{name}: lane={t['lane']} valid={t['valid_cli']}/"
                      f"{t['valid_artifact']} central={t['central_bytes']} "
                      f"direct={t['direct_bytes']} entries="
                      f"{rec['ledger_entries']} invokes={rec['invokes']} "
                      f"wall={rec['wall_s']}s", flush=True)
            if rec["rc"] != 0:
                print(f"{name}: FAILED rc={rec['rc']} {rec['stderr']}",
                      flush=True)
    return out


def main() -> int:
    RUNS.mkdir(parents=True, exist_ok=True)
    train_ids = [f"M1R-TR-{i:02d}" for i in range(1, 19)]
    test_ids = [f"M1R-TE-{i:02d}" for i in range(1, 19)]
    train = sweep("tr", train_ids)
    train.append(one_run("guard-train-S1S2", tasks="S1,S2"))
    (HERE / "main" / "train-results.json").write_text(
        json.dumps(train, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    test = sweep("te", test_ids)
    test.append(one_run("guard-test-S1S2", tasks="S1,S2"))
    (HERE / "main" / "test-results.json").write_text(
        json.dumps(test, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    fails = sum(1 for r in train + test if r["rc"] != 0)
    print(f"runs={len(train) + len(test)} failed={fails}")
    return 1 if fails else 0


if __name__ == "__main__":
    sys.exit(main())
