"""S5-A12 lane-owned op-matrix kill legs (independent params).

Leg A (fission, deterministic): crash at EVERY fission append
boundary N=1..growth+1 (growth re-derived, never trusted), then
`ops recover` (+partitioned re-run exactly where the classified
refusal fires; clean re-run after a pre-op kill) and convergence
assertions per boundary.

Leg B (settle, real SIGKILL): lane-owned delays (0.03/0.11/0.37/0.8 s
— distinct from the builder's 0.05/0.2/0.5), then recover + converge.

All run dirs under this lane's scratch. s005 is imported/CLI-driven
read-only. stdlib-only. Exit 0 iff every round converges.
"""
from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
import time
from pathlib import Path

LANE = Path(__file__).resolve().parent
SCRATCH = LANE / "scratch" / "lane-opmatrix"
S005 = (Path(__file__).resolve().parents[3] / "prototype"
        / "successor-005")
sys.path.insert(0, str(S005))

CRASH_RC = 42
PARTITION_CLI = ("sched.composite=SC-L2,sched.requirements=SC-L2,"
                 "sched.slots=SC-S2")


def child_env(**extra) -> dict:
    env = dict(os.environ)
    env["PYTHONDONTWRITEBYTECODE"] = "1"
    for var in ("SUBSTRATE_CRASH_AFTER_APPENDS", "SUBSTRATE_CRASH_AT",
                "SUBSTRATE_CRASH_MID_APPEND",
                "SUBSTRATE_CRASH_MID_SIDE_WRITE"):
        env.pop(var, None)
    env.update(extra)
    return env


def cli(*args: str, env: dict | None = None) -> subprocess.CompletedProcess:
    return subprocess.run(
        [sys.executable, str(S005 / "release.py"), *args],
        cwd=str(S005), env=env or child_env(),
        stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)


def inspect_json(root: Path) -> dict:
    proc = cli("inspect", "--state-dir", str(root), "--json")
    assert proc.returncode == 0, proc.stderr
    return json.loads(proc.stdout)


def ledger_lines(root: Path) -> list[dict]:
    out = []
    with open(root / "ledger.jsonl", encoding="utf-8") as fh:
        for line in fh:
            line = line.strip()
            if line:
                out.append(json.loads(line))
    return out


def kinds_of(root: Path) -> dict[str, int]:
    kinds: dict[str, int] = {}
    for e in ledger_lines(root):
        kinds[e["kind"]] = kinds.get(e["kind"], 0) + 1
    return kinds


def cli_run(name: str) -> Path:
    root = SCRATCH / name
    if root.exists():
        shutil.rmtree(root)
    proc = cli("init", "--state-dir", str(root))
    assert proc.returncode == 0, proc.stderr
    proc = cli("run", "--state-dir", str(root), "--tasks", "S1,S2")
    assert proc.returncode == 0, proc.stderr
    return root


def fresh_copy(template: Path, name: str) -> Path:
    dest = SCRATCH / name
    if dest.exists():
        shutil.rmtree(dest)
    shutil.copytree(template, dest)
    return dest


def fission_args(root: Path) -> list[str]:
    return ["ops", "fission", "--state-dir", str(root),
            "--composite", "SC-FUSED", "--left", "SC-L2",
            "--right", "SC-S2", "--partition", PARTITION_CLI,
            "--reason", "lane"]


def leg_a_fission_every_boundary() -> None:
    template = cli_run("lane-fission-template")
    proc = cli("ops", "fuse", "--state-dir", str(template),
               "--a", "SC-L", "--b", "SC-S", "--fused", "SC-FUSED",
               "--reason", "template fusion")
    assert proc.returncode == 0, proc.stderr
    probe = fresh_copy(template, "lane-growth-probe")
    before = len(ledger_lines(probe))
    proc = cli(*fission_args(probe))
    assert proc.returncode == 0, proc.stderr
    growth = len(ledger_lines(probe)) - before
    print(f"lane legA: fission growth re-derived = {growth}", flush=True)
    assert growth > 0
    for n in range(1, growth + 2):
        root = fresh_copy(template, f"lane-fission-n{n}")
        proc = cli(*fission_args(root),
                   env=child_env(SUBSTRATE_CRASH_AFTER_APPENDS=str(n)))
        if n > growth:
            assert proc.returncode == 0, proc.stderr
        else:
            assert proc.returncode == CRASH_RC, (n, proc.returncode)
        bare = cli("ops", "recover", "--state-dir", str(root),
                   "--reason", "rec")
        if bare.returncode != 0:
            proc2 = cli("ops", "recover", "--state-dir", str(root),
                        "--reason", "rec", "--fission", "SC-FUSED",
                        "--left", "SC-L2", "--right", "SC-S2",
                        "--partition", PARTITION_CLI)
            assert proc2.returncode == 0, proc2.stderr
        state = inspect_json(root)
        if state["worlds"]["SC-FUSED"]["lifecycle"] == "active" \
                and kinds_of(root).get("fission", 0) == 0:
            assert n == 1, f"no-trace rerun only valid pre-op (n={n})"
            proc3 = cli(*fission_args(root))
            assert proc3.returncode == 0, proc3.stderr
            state = inspect_json(root)
        assert state["worlds"]["SC-FUSED"]["lifecycle"] == "dissolved", n
        assert kinds_of(root).get("fission", 0) == 1, n
        assert state["conservation"]["ok"], n
        print(f"lane legA fission N={n}: "
              f"rc={0 if n > growth else CRASH_RC} -> converged",
              flush=True)
    print(f"lane legA: {growth + 1} boundaries converged", flush=True)


def leg_b_settle_sigkill() -> None:
    template = cli_run("lane-settle-template")
    delays = (0.03, 0.11, 0.37, 0.8)  # lane-owned, != builder 0.05/0.2/0.5
    for i, delay in enumerate(delays):
        root = fresh_copy(template, f"lane-settle-{i}")
        child = subprocess.Popen(
            [sys.executable, str(S005 / "release.py"), "ops", "settle",
             "--state-dir", str(root), "--worlds", "SC-L,SC-S",
             "--reason", "lane-kill"],
            cwd=str(S005), env=child_env(),
            stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        time.sleep(delay)
        try:
            child.kill()
            killed = True
        except ProcessLookupError:
            killed = False
        child.communicate(timeout=60)
        if child.returncode == 0:
            landing = "completed-before-kill"
        else:
            assert killed and child.returncode < 0, child.returncode
            landing = "killed"
        proc = cli("ops", "recover", "--state-dir", str(root),
                   "--worlds", "SC-L,SC-S", "--reason", "rec")
        assert proc.returncode == 0, proc.stderr
        state = inspect_json(root)
        assert state["conservation"]["ok"], delay
        assert state["worlds"]["SC-L"]["lifecycle"] == "dissolved", delay
        assert state["worlds"]["SC-S"]["lifecycle"] == "dissolved", delay
        print(f"lane legB settle delay={delay}: {landing} -> converged",
              flush=True)
    print("lane legB: 4/4 settle SIGKILL rounds converged", flush=True)


def main() -> int:
    SCRATCH.mkdir(parents=True, exist_ok=True)
    t0 = time.monotonic()
    leg_a_fission_every_boundary()
    leg_b_settle_sigkill()
    print(f"lane opmatrix: ALL CONVERGED wall={time.monotonic()-t0:.1f}s")
    return 0


if __name__ == "__main__":
    sys.exit(main())
