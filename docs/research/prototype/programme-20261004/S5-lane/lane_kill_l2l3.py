"""S5-A12 lane-owned real-SIGKILL L2/L3 loop (independent params).

Own child sleep (4 s), own ballast (1200 files + 6 MiB blob), own
delays: wall fractions [0.08, 0.25, 0.45, 0.65, 0.82] plus an
end-cluster [wall-0.40, wall-0.25, wall-0.12, wall-0.02, wall+0.10].
If the sweep yields no L3, up to 8 adaptive end-window rounds follow
(own delays still). Every round must converge via recover + re-invoke
with exactly one success invoke, <=2 begins, conservation ok.
Requires >=1 L2 and >=1 L3 overall. POSIX-only (group kill).

All run dirs under this lane's scratch. s005 read-only. stdlib-only.
"""
from __future__ import annotations

import hashlib
import json
import os
import shutil
import signal
import subprocess
import sys
import time
from pathlib import Path

LANE = Path(__file__).resolve().parent
SCRATCH = LANE / "scratch" / "lane-l2l3"
S005 = (Path(__file__).resolve().parents[3] / "prototype"
        / "successor-005")
sys.path.insert(0, str(S005))
import api  # noqa: E402

SLEEP_S = 4  # lane-owned (builder used 5)


def child_env(**extra) -> dict:
    env = dict(os.environ)
    env["PYTHONDONTWRITEBYTECODE"] = "1"
    for var in ("SUBSTRATE_CRASH_AFTER_APPENDS", "SUBSTRATE_CRASH_AT",
                "SUBSTRATE_CRASH_MID_APPEND",
                "SUBSTRATE_CRASH_MID_SIDE_WRITE", "PROC_PY"):
        env.pop(var, None)
    env.update(extra)
    return env


def cli(*args: str, env: dict | None = None) -> subprocess.CompletedProcess:
    return subprocess.run(
        [sys.executable, str(S005 / "release.py"), *args],
        cwd=str(S005), env=env or child_env(),
        stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)


def spawn_cli(*args: str) -> subprocess.Popen:
    return subprocess.Popen(
        [sys.executable, str(S005 / "release.py"), *args],
        cwd=str(S005), env=child_env(),
        stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True,
        start_new_session=True)


def kill_group(proc: subprocess.Popen) -> None:
    try:
        os.killpg(os.getpgid(proc.pid), signal.SIGKILL)
    except (OSError, ProcessLookupError):
        pass
    try:
        proc.kill()
    except OSError:
        pass


def ledger_lines(root: Path) -> list[dict]:
    out = []
    with open(root / "ledger.jsonl", encoding="utf-8") as fh:
        for line in fh:
            line = line.strip()
            if line:
                out.append(json.loads(line))
    return out


def proc_invokes(root: Path, key: str, errors: bool) -> list[dict]:
    out = []
    for e in ledger_lines(root):
        if e.get("kind") != "invoke":
            continue
        p = e["payload"]
        if p.get("capability") != "proc.exec":
            continue
        if p.get("proc", {}).get("idem_key") != key:
            continue
        if errors == ("error" in p):
            out.append(p)
    return out


def proc_begins_of(root: Path, key: str) -> list[dict]:
    return [e["payload"] for e in ledger_lines(root)
            if e.get("kind") == "proc_begin"
            and e["payload"].get("idem_key") == key]


def make_bundle() -> Path:
    bdir = SCRATCH / "bundles" / "lanelong"
    if bdir.exists():
        shutil.rmtree(bdir)
    bdir.mkdir(parents=True)
    big = b"x" * (6 * 1024 * 1024)  # lane-owned size (builder 10 MiB)
    (bdir / "big.bin").write_bytes(big)
    step = {"step": "long",
            "argv": ["python3", "-c",
                     f"import time; time.sleep({SLEEP_S}); "
                     f"open('done.txt','w').write('d')"],
            "declared_outputs": ["done.txt"], "timeout_s": 600}
    manifest = {"files": {"big.bin": hashlib.sha256(big).hexdigest()},
                "steps": [step]}
    (bdir / "MANIFEST.json").write_text(
        json.dumps(manifest, indent=2, sort_keys=True))
    return bdir


def one_round(root: Path, key: str, delay: float) -> str:
    child = spawn_cli("ops", "run-procedure", "--state-dir", str(root),
                      "--world", "W1", "--procedure", "lanelong",
                      "--key", key)
    time.sleep(delay)
    if child.poll() is None:
        kill_group(child)
    child.communicate(timeout=120)
    begins = proc_begins_of(root, key)
    oks = proc_invokes(root, key, errors=False)
    errs = proc_invokes(root, key, errors=True)
    assert errs == [], f"{key}: no error leg here, got {errs}"
    if oks:
        landing = "complete"
    elif not begins:
        landing = "no-trace"
    elif (Path(begins[0]["scratch"]) / "DONE.json").is_file():
        landing = "L3"
    else:
        landing = "L2"
    rec = api.recover_op(root)
    if landing == "L3":
        assert any(a["idem_key"] == key for a in rec["proc_adopted"]), key
    out = api.run_procedure(root, "W1", "lanelong", key)
    final = proc_invokes(root, key, errors=False)
    assert len(final) == 1, f"{key}/{landing}"
    assert len(proc_begins_of(root, key)) <= 2, key
    assert len(out["re_executed_steps"]) <= 1, key
    host, _ = api.open_run(root)
    assert host.verify_conservation()["ok"], key
    return landing


def guarded(root: Path, key: str, delay: float) -> tuple[str, str | None]:
    backup = SCRATCH / f"ledger-backup-{key}.jsonl"
    shutil.copy(root / "ledger.jsonl", backup)
    try:
        return one_round(root, key, delay), None
    except (RuntimeError, json.JSONDecodeError) as exc:
        if isinstance(exc, RuntimeError) and "disk-loss" not in str(exc):
            raise
        shutil.copy(backup, root / "ledger.jsonl")
        shutil.rmtree(root / "state" / "proc-scratch" / key,
                      ignore_errors=True)
        return one_round(root, key, delay), "L4-restored"


def main() -> int:
    assert os.name == "posix", "POSIX group-kill leg"
    if SCRATCH.exists():
        shutil.rmtree(SCRATCH)
    SCRATCH.mkdir(parents=True)
    t0 = time.monotonic()
    bdir = make_bundle()
    root = SCRATCH / "killloop"
    proc = cli("ops", "create-proc-world", "--state-dir", str(root),
               "--world", "W1", "--bundle", str(bdir), "--reason", "lane")
    assert proc.returncode == 0, proc.stderr
    ballast = root / "state" / "ballast"
    ballast.mkdir(parents=True)
    for i in range(1200):  # lane-owned count (builder 2000)
        (ballast / f"f{i:04d}.txt").write_text(f"lane-ballast-{i}")
    c0 = time.monotonic()
    proc = cli("ops", "run-procedure", "--state-dir", str(root),
               "--world", "W1", "--procedure", "lanelong",
               "--key", "K-cal")
    assert proc.returncode == 0, proc.stderr
    wall = time.monotonic() - c0
    assert wall > SLEEP_S, wall
    print(f"lane l2l3: calibration wall={wall:.2f}s", flush=True)
    delays = [f * wall for f in (0.08, 0.25, 0.45, 0.65, 0.82)]
    delays += [wall - 0.40, wall - 0.25, wall - 0.12, wall - 0.02,
               wall + 0.10]
    delays = [max(0.05, d) for d in delays]
    landings: dict[str, int] = {}
    n = 0
    for delay in delays:
        key = f"L{n:02d}"
        n += 1
        landing, note = guarded(root, key, delay)
        landings[landing] = landings.get(landing, 0) + 1
        if note:
            landings[note] = landings.get(note, 0) + 1
        print(f"lane l2l3 round {key} delay={delay:.2f}s -> {landing}"
              + (f" ({note})" if note else ""), flush=True)
    extra = 0
    while landings.get("L3", 0) == 0 and extra < 8:
        delay = max(0.05, wall - 0.30 + extra * 0.05)
        key = f"LX{extra:02d}"
        extra += 1
        landing, note = guarded(root, key, delay)
        landings[landing] = landings.get(landing, 0) + 1
        if note:
            landings[note] = landings.get(note, 0) + 1
        print(f"lane l2l3 adaptive {key} delay={delay:.2f}s -> {landing}"
              + (f" ({note})" if note else ""), flush=True)
    print(f"lane l2l3: landings={landings}", flush=True)
    assert landings.get("L2", 0) >= 1, "need >=1 L2"
    assert landings.get("L3", 0) >= 1, "need >=1 L3"
    print(f"lane l2l3: ALL CONVERGED wall={time.monotonic()-t0:.1f}s")
    return 0


if __name__ == "__main__":
    sys.exit(main())
