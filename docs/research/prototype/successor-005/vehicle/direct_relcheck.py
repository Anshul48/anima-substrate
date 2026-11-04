"""direct_relcheck.py — THROWAWAY readiness aid (NOT release code).

Runs the IDENTICAL relcheck bundle bytes step by step WITHOUT the
host (plain subprocesses, no ledger): the S5-A10 direct baseline.
The U-execute direct arm (§5 make-style runner) is lane-owned; this
script exists only to prove the bundle bytes produce a VALID report
outside the host. Disclosed per R-D; never shipped as release.

Usage::

    direct_relcheck.py <bundle_dir> <pins_file> <outdir>
        [--nonce N] [--run-id R]

Layout: <outdir>/scratch/<step>/ (cwd + inputs), <outdir>/artifacts/
<step>/ (declared outputs + stdio logs + RESULT.json),
<outdir>/direct-ledger.jsonl (one record per step).
"""

from __future__ import annotations

import hashlib
import json
import os
import subprocess
import sys
import time
from pathlib import Path

STEP_TIMEOUT_S = 600.0


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def argv_sha256(argv: list) -> str:
    return hashlib.sha256(
        json.dumps(argv, sort_keys=True).encode()).hexdigest()


def run_step(argv: list[str], cwd: Path) -> tuple:
    cwd = Path(os.path.abspath(cwd))
    env = {"PATH": os.environ.get("PATH", ""),
           "PYTHONDONTWRITEBYTECODE": "1",
           "HOME": str(cwd), "TMPDIR": str(cwd)}
    # Mirror the bundle runner: forward the absolute venv override.
    # Direct children run from scratch copies that lack the relative
    # w1/.venv path, so without the override their SST legs refuse
    # loudly. Forwarded ONLY when non-empty (sst_leg treats a missing
    # var as "use default"; an empty string would poison it).
    venv = os.environ.get("SST_VENV_PY", "")
    if venv.strip():
        env["SST_VENV_PY"] = venv
    child = subprocess.Popen(
        argv, cwd=str(cwd), env=env, stdin=subprocess.DEVNULL,
        stdout=subprocess.PIPE, stderr=subprocess.PIPE,
        start_new_session=True)
    t0 = time.monotonic()
    try:
        out, err = child.communicate(timeout=STEP_TIMEOUT_S)
    except subprocess.TimeoutExpired:
        try:
            if os.name == "posix":
                import signal
                os.killpg(child.pid, signal.SIGKILL)
            else:  # pragma: no cover - best effort on Windows
                child.kill()
        finally:
            out, err = child.communicate()
        return -9, out or b"", err or b"", STEP_TIMEOUT_S
    return child.returncode, out or b"", err or b"", \
        time.monotonic() - t0


def main(argv: list[str]) -> int:
    positional: list[str] = []
    nonce, run_id = "direct-readiness", "direct-s5a10"
    toks = list(argv[1:])
    while toks:
        tok = toks.pop(0)
        if tok == "--nonce" and toks:
            nonce = toks.pop(0)
        elif tok == "--run-id" and toks:
            run_id = toks.pop(0)
        elif tok.startswith("--"):
            print(f"direct: unknown option {tok}", file=sys.stderr)
            return 2
        else:
            positional.append(tok)
    if len(positional) != 3:
        print("usage: direct_relcheck.py <bundle> <pins> <outdir> "
              "[--nonce N] [--run-id R]", file=sys.stderr)
        return 2
    bundle, pins_file, outdir = Path(positional[0]), \
        Path(positional[1]), Path(os.path.abspath(positional[2]))
    try:
        relcheck_bytes = (bundle / "bin" / "relcheck.py").read_bytes()
        pins_bytes = (bundle / "pins.json").read_bytes()
        pins = json.loads((pins_file).read_text(encoding="utf-8"))
        bundle_pins = json.loads(pins_bytes.decode("utf-8"))
    except (OSError, ValueError) as exc:
        print(f"direct: cannot load bundle/pins: {exc}",
              file=sys.stderr)
        return 1
    for key in ("bundle_sha256", "frozen", "argv"):
        if key not in pins:
            print(f"direct: pins file missing {key!r} (refusing)",
                  file=sys.stderr)
            return 1
    for key in ("identity", "suites", "surface_min", "surface_trees",
                "ignore_top", "artifacts", "steps", "demo_marker"):
        if bundle_pins.get(key) != pins.get(key):
            print(f"direct: bundle pins skew vs pins file on {key!r}"
                  f" (refusing)", file=sys.stderr)
            return 1
    artifacts_dir = outdir / "artifacts"
    ledger_path = outdir / "direct-ledger.jsonl"
    if outdir.exists():
        print(f"direct: refusing to reuse existing {outdir}",
              file=sys.stderr)
        return 1
    params = {"params_format": 1, "mode": "direct", "nonce": nonce,
              "run_id": run_id, "run_root": str(outdir),
              "artifacts_dir": str(artifacts_dir),
              "bundle_sha256": pins["bundle_sha256"],
              "frozen": pins["frozen"]}
    params_bytes = (json.dumps(params, indent=2, sort_keys=True)
                    + "\n").encode("utf-8")
    input_hashes = {"relcheck.py": sha256_bytes(relcheck_bytes),
                    "pins.json": sha256_bytes(pins_bytes),
                    "params.json": sha256_bytes(params_bytes)}
    ledger_lines = []
    for step in pins["steps"]:
        scratch = outdir / "scratch" / step
        inputs_dir = scratch / "inputs"
        inputs_dir.mkdir(parents=True)
        (inputs_dir / "relcheck.py").write_bytes(relcheck_bytes)
        (inputs_dir / "pins.json").write_bytes(pins_bytes)
        (inputs_dir / "params.json").write_bytes(params_bytes)
        step_argv = pins["argv"][step]
        rc, out, err, dt = run_step(step_argv, scratch)
        print(f"direct {step}: rc={rc} elapsed={dt:.1f}s",
              flush=True)
        step_dir = artifacts_dir / step
        step_dir.mkdir(parents=True)
        (step_dir / "stdout.log").write_bytes(out)
        (step_dir / "stderr.log").write_bytes(err)
        collected = []
        for name in pins["artifacts"][step]:
            src = scratch / name
            if src.is_symlink() or not src.is_file():
                print(f"direct {step}: declared output {name!r} "
                      f"missing (loud)", file=sys.stderr)
                return 1
            data = src.read_bytes()
            (step_dir / name).write_bytes(data)
            collected.append({"relpath": name,
                              "sha256": sha256_bytes(data),
                              "bytes": len(data)})
        result = {"rc": rc, "elapsed_s": round(dt, 3),
                  "artifacts": collected}
        (step_dir / "RESULT.json").write_text(
            json.dumps(result, indent=2, sort_keys=True) + "\n",
            encoding="utf-8")
        ledger_lines.append({"step": step, "argv": step_argv,
                             "argv_sha256": argv_sha256(step_argv),
                             "rc": rc, "elapsed_s": round(dt, 3),
                             "input_hashes": input_hashes,
                             "bundle_sha256": pins["bundle_sha256"]})
        ledger_path.write_text(
            "".join(json.dumps(r, sort_keys=True) + "\n"
                    for r in ledger_lines), encoding="utf-8")
        if rc != 0:
            print(f"direct {step}: FAILED rc={rc} (stopping)",
                  file=sys.stderr)
            return 1
    print(f"direct: all {len(pins['steps'])} steps rc=0",
          flush=True)
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
