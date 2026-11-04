"""L2 step-0 driver (stdlib-only). Host contact ONLY via release.py CLI
subprocess calls. State + logs under this step0 dir (L1 precedent);
the frozen H2 tree is never written.

Per probe x lane: init -> run --task-json --lane-override -> parse
stdout metrics + OUR ledger.jsonl (entries/invokes) -> settle.
Guard batch: S1+S2 by-name rule-lane run vs EXPECTED pins.

Usage: PYTHONDONTWRITEBYTECODE=1 python3 run_step0.py
"""
from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
WORK = HERE.parent
ROOT = WORK.parents[2]  # substrate repo root
H2 = ROOT / "prototype" / "programme-20261004" / "H2-lane"
RELEASE = H2 / "release.py"
PY = sys.executable

PROBES = [f"L2P-{i:02d}" for i in range(1, 9)]
LANES = ["central", "local"]

EXPECTED = {
    "S1": {"lane": "central", "central": 655, "direct": 0},
    "S2": {"lane": "local", "central": 310, "direct": 500},
}


def sh(args: list[str], log) -> str:
    log.write(f"$ {' '.join(args)}\n")
    r = subprocess.run(args, capture_output=True, text=True,
                       cwd=str(ROOT))
    log.write(r.stdout)
    if r.stderr:
        log.write("STDERR:\n" + r.stderr)
    log.write(f"[exit={r.returncode}]\n\n")
    if r.returncode != 0:
        raise RuntimeError(f"command failed rc={r.returncode}: {args}\n"
                           f"{r.stdout}\n{r.stderr}")
    return r.stdout


def parse_run_line(out: str, task_id: str) -> dict:
    for line in out.splitlines():
        if line.startswith(task_id + ":"):
            parts = line.split()
            kv = {}
            for p in parts[1:]:
                if "=" in p:
                    k, v = p.split("=", 1)
                    kv[k] = v
            return {"lane": kv["lane"],
                    "valid": kv["valid"] == "True",
                    "quality": kv["quality"],
                    "central_bytes": int(kv["central"]),
                    "direct_bytes": int(kv["direct"])}
    raise RuntimeError(f"no run line for {task_id} in:\n{out}")


def ledger_counts(state_dir: Path) -> dict:
    entries = 0
    invokes = 0
    for line in (state_dir / "ledger.jsonl").read_text(
            encoding="utf-8").splitlines():
        line = line.strip()
        if not line:
            continue
        entries += 1
        if json.loads(line).get("kind") == "invoke":
            invokes += 1
    return {"ledger_entries": entries, "invokes": invokes}


def main() -> int:
    runs = HERE / "runs"
    logs = HERE / "logs"
    probes = HERE / "probes"
    results: dict = {"probes": {}, "guard": {}, "explain": {}}
    with open(logs / "step0.log", "w", encoding="utf-8") as log:
        # 0. authoritative derived routing inputs (prediction-only CLI).
        for pid in PROBES:
            out = sh([PY, str(RELEASE), "explain-route", "--task-json",
                      str(probes / f"{pid}.json"), "--json"], log)
            results["explain"][pid] = json.loads(out)
        # 1. probe x lane runs.
        for pid in PROBES:
            results["probes"][pid] = {}
            for lane in LANES:
                sd = runs / f"{pid}-{lane}"
                sh([PY, str(RELEASE), "init", "--state-dir", str(sd)], log)
                out = sh([PY, str(RELEASE), "run", "--state-dir", str(sd),
                          "--task-json", str(probes / f"{pid}.json"),
                          "--lane-override", lane], log)
                m = parse_run_line(out, pid)
                m.update(ledger_counts(sd))
                sh([PY, str(RELEASE), "ops", "settle", "--state-dir",
                    str(sd), "--worlds", "SC-L,SC-S", "--reason",
                    f"L2 step-0 {pid} {lane}"], log)
                results["probes"][pid][lane] = m
                print(f"{pid} {lane}: valid={m['valid']} "
                      f"central={m['central_bytes']} "
                      f"direct={m['direct_bytes']} "
                      f"entries={m['ledger_entries']} "
                      f"invokes={m['invokes']}", flush=True)
        # 2. guard batch: S1+S2 by name (rule lanes) vs EXPECTED.
        gd = runs / "guard-S1S2"
        sh([PY, str(RELEASE), "init", "--state-dir", str(gd)], log)
        out = sh([PY, str(RELEASE), "run", "--state-dir", str(gd),
                  "--tasks", "S1,S2"], log)
        for tid in ("S1", "S2"):
            m = parse_run_line(out, tid)
            m.update(ledger_counts(gd))
            results["guard"][tid] = m
            exp = EXPECTED[tid]
            ok = (m["lane"] == exp["lane"]
                  and m["central_bytes"] == exp["central"]
                  and m["direct_bytes"] == exp["direct"]
                  and m["valid"])
            print(f"guard {tid}: lane={m['lane']} central="
                  f"{m['central_bytes']} direct={m['direct_bytes']} "
                  f"EXPECT={'MATCH' if ok else 'DEVIATION'}", flush=True)
            if not ok:
                raise SystemExit(f"GUARD DEVIATION on {tid}: {m} vs {exp} "
                                 f"-- phase VOID")
        sh([PY, str(RELEASE), "ops", "settle", "--state-dir", str(gd),
            "--worlds", "SC-L,SC-S", "--reason", "L2 step-0 guard"], log)
    (HERE / "STEP0-RESULTS.json").write_text(
        json.dumps(results, indent=2, sort_keys=True) + "\n",
        encoding="utf-8")
    print("wrote STEP0-RESULTS.json")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
