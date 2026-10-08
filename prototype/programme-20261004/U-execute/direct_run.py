"""Direct-arm baseline runner for relcheck (S5 design section 5.1).

BASELINE FORM (S5 section 10.1 Q4 PIN DECISION): direct_run.py is THE
baseline form. The Makefile template stays unfrozen scaffolding
(step_from_manifest.py will not be written). This file freezes at
U-prereg (sha256 pinned, PREREG P15); the Makefile is not part of the
freeze.

Provenance of the bundle contract below (pre-freeze repair):
- Staged inputs + params shape: derived from OBSERVED S5-A10 readiness
  staging (S5-lane/scratch/lane-readiness-direct/scratch/<step>/inputs/,
  byte-identical across steps) plus the built MANIFEST.json. Every
  manifest-listed file is staged under inputs/<basename> as a
  byte-identical copy; params.json is runner-authored
  ({run_root, artifacts_dir, bundle_sha256, frozen, mode, nonce,
  params_format, run_id}, sorted keys, indent 2). Verified by a
  field-for-field --dry-run diff against observed staging (see
  baseline-smoke.log). Per-step scratch beyond inputs/ (frozen-*
  copies, nested work dirs) is step-program runtime output, NOT runner
  staging: the MANIFEST declares no per-step inputs, so per-step
  differences cannot come from the runner.
- env_extra: dict {VAR: value} per the built MANIFEST (suite steps
  carry {SST_VENV_PY: abspath}); forwarded non-empty-only. The draft
  key-list + env_extra_values form is rejected loudly.
- argv_sha256: sha256 over json.dumps of the BARE argv list with
  DEFAULT separators -- the host procedure (host procedure.py
  argv_sha256 lines, read as spec). STAMP_SCHEMA=2 marks this
  procedure (1 = never-frozen draft wrap, rejected).
- argv runs VERBATIM with cwd=scratch/<step> (built argv references
  inputs/relcheck.py relatively). No <BUNDLE> substitution.

Section 5.1 contract (competent direct procedure, make-style resume):
- SAME step programs, byte-identical bundle (inputs held equal,
  section 5.2(a); runner verifies bundle sha256 at startup).
- One stamp file per step: steps/<step>-RESULT.json {artifacts,
  elapsed_s, rc} (builder evidence shape + runner resume extras).
  ``resume`` (= default: completed stamps skip, current step re-runs).
- Timeouts IDENTICAL: same timeout_s values read from the same
  MANIFEST.json bytes the host arm advertises from.
- No ledger, no hash-chain theater beyond stamps + a run log.
- Honest re-work counting (R2): attempt_start/attempt_end record pairs
  per attempt (a killed attempt leaves a start with no end, countable),
  stamp hits/misses audited in direct-ledger.jsonl. Attempt_end rows
  carry the builder evidence fields (argv/argv_sha256/input_hashes/
  bundle_sha256/elapsed_s/rc/step) so the U checker binds them exactly
  like builder direct rows (extra keys ignored); non-end rows are
  harness liveness evidence, skipped by the checker.

Usage:
    direct_run.py --bundle DIR --work DIR --frozen KEY=ABSPATH [...]
                  [--pins FILE] [--run-id ID] [--nonce N]
                  [--step NAME] [--force STEP...]
    direct_run.py --bundle DIR --work DIR --frozen KEY=ABSPATH [...]
                  --dry-run [--step NAME]
    direct_run.py --bundle DIR --work DIR --audit

Work layout (all under --work, never in frozen trees):
    scratch/<step>/inputs/   staged manifest files (basename copies)
                             + runner-authored params.json
    scratch/<step>/          step cwd; declared outputs collected here
    artifacts/<step>/        collected declared outputs (copies)
                             + stdout.log/stderr.log (1 MiB caps)
    steps/<step>-RESULT.json JSON {artifacts, elapsed_s, rc} (builder
                             evidence shape) + resume extras {schema,
                             step, argv_sha256, run_id, at}
    direct-ledger.jsonl      attempt_start/attempt_end/skip records
                             (builder-bound end rows + audit rows)
    touches.json             cumulative touches {touches, cap, history}
    run.json                 latest invocation summary

Touch accounting (section 5.2(d), PREREG P11): one CLI invocation that
executes work = 1 touch (resume = 1; --step/--force invocations each
count 1 and are disclosed in touches.json history). Touches accumulate
per work dir (one leg); cap is 2 -- an invocation that would exceed
the cap REFUSES before executing anything (over-cap would VOID the
leg). Pure inspection (--audit) and assembly-only --dry-run = 0
touches: neither records a touch nor executes a step.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import shutil
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

# Stamp schema version: 1 = never-frozen draft (canonical-wrap argv hash),
# rejected. 2 = never-frozen draft (host-parity hash, .stamps layout),
# rejected. 3 = builder-compatible evidence shape (steps/*-RESULT.json
# + direct-ledger.jsonl end rows). Frozen with this file.
STAMP_SCHEMA = 3
# Direct run log name (builder evidence contract).
LEDGER_NAME = "direct-ledger.jsonl"
# Runner-authored params.json format marker (matches observed staging).
PARAMS_FORMAT = 1
# Touch cap per leg per arm (section 5.2(d), PREREG P11).
TOUCH_CAP = 2
STDOUT_CAP = STDERR_CAP = 1024 * 1024  # same caps as host arm (P5)


def utcnow() -> str:
    return datetime.now(timezone.utc).isoformat()


def sha256_file(fp: Path) -> str:
    return hashlib.sha256(fp.read_bytes()).hexdigest()


def sha256_canonical(obj: dict) -> str:
    """Bundle sha256: canonical-JSON bytes (section 1.3).

    Confirmed against the built bundle: recomputing over the built
    MANIFEST.json yields the observed bundle_sha256.
    """
    return hashlib.sha256(
        json.dumps(obj, sort_keys=True,
                   separators=(",", ":")).encode("utf-8")).hexdigest()


def argv_sha256(argv: list) -> str:
    """Step argv hash: sha256 over the BARE argv list, DEFAULT separators.

    Host parity (host procedure.py argv_sha256 lines, read as spec):
    ``sha256(json.dumps(argv, sort_keys=True).encode())``. sort_keys is
    a no-op for lists; default separators (", ", ": ") are load-bearing.
    """
    return hashlib.sha256(
        json.dumps(argv, sort_keys=True).encode("utf-8")).hexdigest()


def load_manifest(bundle: Path) -> dict:
    """Read MANIFEST.json from the bundle; validate minimal shape."""
    mf = json.loads((bundle / "MANIFEST.json").read_text(encoding="utf-8"))
    if not isinstance(mf.get("steps"), list) or not mf["steps"]:
        raise ValueError("manifest: steps missing/empty")
    for s in mf["steps"]:
        for k in ("step", "argv", "declared_outputs", "timeout_s"):
            if k not in s:
                raise ValueError(f"manifest: step missing {k!r}: {s}")
        if not isinstance(s["argv"], list) or not s["argv"]:
            raise ValueError(f"manifest: step {s['step']}: argv must be "
                             "a non-empty list (no shell, P1 parity)")
        if any(not isinstance(a, str) for a in s["argv"]):
            raise ValueError(f"manifest: step {s['step']}: argv entries "
                             "must be strings")
        extra = s.get("env_extra")
        if extra is not None and not isinstance(extra, dict):
            raise ValueError(
                f"manifest: step {s['step']}: env_extra must be a dict "
                f"{{VAR: value}} (built contract); got "
                f"{type(extra).__name__} -- the draft key-list form is "
                "rejected")
        if "env_extra_values" in s:
            raise ValueError(
                f"manifest: step {s['step']}: env_extra_values is a "
                "removed draft form; env_extra carries values directly")
        if isinstance(extra, dict):
            for k, v in extra.items():
                if v is not None and not isinstance(v, str):
                    raise ValueError(
                        f"manifest: step {s['step']}: env_extra[{k!r}] "
                        "must be a string (empty/null = not forwarded)")
    if "files" in mf and not isinstance(mf["files"], dict):
        raise ValueError("manifest: files must be a {relpath: sha256} dict")
    return mf


def verify_bundle(bundle: Path, manifest: dict, pins: dict | None) -> str:
    """Hash every manifest-listed file; return bundle sha256.

    Bundle sha256 = sha256 over canonical-JSON manifest bytes (section
    1.3). Every staged file re-hashed against manifest pins (advertise-
    time validation parity, section 1.1).
    """
    broot = bundle.resolve()
    files = manifest.get("files", {})
    for relpath, want in sorted(files.items()):
        fp = (bundle / relpath).resolve()
        if fp != broot and broot not in fp.parents:
            raise ValueError(f"bundle: listed file escapes bundle: {relpath}")
        if not fp.is_file():
            raise ValueError(f"bundle: listed file missing: {relpath}")
        if sha256_file(fp) != want:
            raise ValueError(f"bundle: hash mismatch: {relpath}")
    got = sha256_canonical(manifest)
    if pins is not None and got != pins.get("bundle_sha256"):
        raise ValueError("bundle sha256 != pinned bundle_sha256")
    return got


def parse_frozen(pairs: list[str]) -> dict[str, str]:
    """Parse --frozen KEY=ABSPATH flags into an abspath mapping.

    Validated pre-touch (fail fast, costs nothing): keys non-empty and
    unique, paths absolute and existing. Values are normalized with
    abspath (no symlink resolution: predictable, matches observed).
    """
    frozen: dict[str, str] = {}
    for item in pairs or []:
        key, sep, path = item.partition("=")
        if not sep or not key or not path:
            raise ValueError(f"--frozen must be KEY=ABSPATH, got {item!r}")
        if key in frozen:
            raise ValueError(f"--frozen duplicate key: {key!r}")
        if not os.path.isabs(path):
            raise ValueError(f"--frozen {key!r}: path must be absolute: "
                             f"{path!r}")
        if not os.path.exists(path):
            raise ValueError(f"--frozen {key!r}: path does not exist: "
                             f"{path!r}")
        frozen[key] = os.path.abspath(path)
    if not frozen:
        raise ValueError("--frozen KEY=ABSPATH is required (at least one; "
                         "params must carry frozen roots)")
    return frozen


def build_params(work: Path, bundle_sha256: str, frozen: dict[str, str],
                 run_id: str, nonce: str) -> dict:
    """Runner-authored params.json content (observed shape, direct mode)."""
    root = os.path.abspath(work)
    return {
        "run_root": root,
        "artifacts_dir": os.path.join(root, "artifacts"),
        "bundle_sha256": bundle_sha256,
        "frozen": dict(sorted(frozen.items())),
        "mode": "direct",
        "nonce": nonce,
        "params_format": PARAMS_FORMAT,
        "run_id": run_id,
    }


def stage_inputs(bundle: Path, manifest: dict, scratch_step: Path,
                 params: dict) -> dict[str, str]:
    """Stage scratch/<step>/inputs/; return {name: sha256} of staged bytes.

    Every manifest-listed file is copied under inputs/<basename>
    (byte-identical); params.json is runner-authored (sorted keys,
    indent 2, trailing newline -- matches observed staging bytes).
    """
    inputs_dir = scratch_step / "inputs"
    if inputs_dir.exists():
        shutil.rmtree(inputs_dir)
    inputs_dir.mkdir(parents=True)
    hashes: dict[str, str] = {}
    seen: dict[str, str] = {}
    for relpath in sorted(manifest.get("files", {})):
        base = os.path.basename(relpath.replace("\\", "/"))
        if not base or base in (".", "..") or "/" in base:
            raise ValueError(f"bundle file has unstageable name: {relpath!r}")
        if base in seen:
            raise ValueError(f"bundle basename collision under inputs/: "
                             f"{relpath!r} vs {seen[base]!r}")
        seen[base] = relpath
        data = (bundle / relpath).read_bytes()  # hash-verified at startup
        (inputs_dir / base).write_bytes(data)
        hashes[base] = hashlib.sha256(data).hexdigest()
    if "params.json" in hashes:
        raise ValueError("bundle must not ship params.json "
                         "(runner-authored)")
    text = json.dumps(params, sort_keys=True, indent=2) + "\n"
    (inputs_dir / "params.json").write_text(text, encoding="utf-8")
    hashes["params.json"] = sha256_file(inputs_dir / "params.json")
    return hashes


def stamp_path(work: Path, step: str) -> Path:
    return work / "steps" / f"{step}-RESULT.json"


def _backfill_result_mirror(work: Path, step: str) -> None:
    """Copy a valid stamp into artifacts/<step>/RESULT.json if absent.

    C11-NOTE-004: keeps stamp-hit skips consistent with the
    H-parity mirror that run_step writes on success.
    """
    sp = stamp_path(work, step)
    mirror = work / "artifacts" / step / "RESULT.json"
    try:
        if mirror.is_file() or not sp.is_file():
            return
        mirror.parent.mkdir(parents=True, exist_ok=True)
        mtmp = mirror.with_suffix(".tmp")
        mtmp.write_text(sp.read_text(encoding="utf-8"), encoding="utf-8")
        os.replace(mtmp, mirror)
    except OSError:
        pass  # best effort; the next real run rewrites the mirror


def stamp_valid(work: Path, step: str, manifest_step: dict) -> bool:
    """A stamp skips the step iff present AND outputs still match hashes.

    Stamp-miss audit (R2): callers log hit/miss per step into
    direct-ledger.jsonl.
    """
    sp = stamp_path(work, step)
    if not sp.is_file():
        return False
    try:
        claimed = json.loads(sp.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, UnicodeDecodeError):
        return False
    if claimed.get("schema") != STAMP_SCHEMA:
        return False
    if claimed.get("argv_sha256") != argv_sha256(manifest_step["argv"]):
        return False
    for a in claimed.get("artifacts", []):
        fp = work / "artifacts" / step / a["relpath"]
        if not fp.is_file() or sha256_file(fp) != a["sha256"]:
            return False
    return claimed.get("rc") == 0


def read_touches(work: Path) -> dict:
    """Cumulative touch record for this work dir (one leg)."""
    fp = work / "touches.json"
    if not fp.is_file():
        return {"touches": 0, "cap": TOUCH_CAP, "history": []}
    try:
        rec = json.loads(fp.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, UnicodeDecodeError):
        raise ValueError("touches.json malformed; refusing to guess the "
                         "touch count (delete the work dir to restart "
                         "the leg)")
    if not isinstance(rec.get("touches"), int) or rec["touches"] < 0:
        raise ValueError("touches.json has a bad touch count; refusing")
    return rec


def record_touch(work: Path, run_id: str, step: str | None,
                 force: list[str]) -> dict:
    """Append one touch (this invocation executes work). Returns record."""
    rec = read_touches(work)
    rec["touches"] += 1
    rec["cap"] = TOUCH_CAP
    rec.setdefault("history", []).append(
        {"run_id": run_id, "at": utcnow(), "step": step,
         "force": list(force or [])})
    fp = work / "touches.json"
    tmp = fp.with_suffix(".tmp")
    tmp.write_text(json.dumps(rec, sort_keys=True, indent=2),
                   encoding="utf-8")
    os.replace(tmp, fp)  # atomic: a killed invocation still counts
    return rec


def next_attempt(work: Path, step: str) -> int:
    """1 + prior attempt_start records for step (kill-visible counting)."""
    fp = work / LEDGER_NAME
    if not fp.is_file():
        return 1
    n = 0
    for line in fp.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        try:
            r = json.loads(line)
        except (json.JSONDecodeError, UnicodeDecodeError):
            continue
        if r.get("event") == "attempt_start" and r.get("step") == step:
            n += 1
    return n + 1


def build_env(scratch: Path, manifest_step: dict) -> tuple[dict, list[str]]:
    """Minimal child env + manifest env_extra forwarded non-empty-only."""
    env = {"PATH": os.environ.get("PATH", ""),
           "PYTHONDONTWRITEBYTECODE": "1",
           "HOME": str(scratch), "TMPDIR": str(scratch)}
    forwarded: list[str] = []
    extra = manifest_step.get("env_extra") or {}
    for k, v in extra.items():
        if v is None or v == "":
            continue  # non-empty-only
        if not isinstance(v, str):
            raise ValueError(f"step {manifest_step['step']}: "
                             f"env_extra[{k!r}] must be a string")
        env[k] = v
        forwarded.append(k)
    return env, sorted(forwarded)


def run_step(bundle: Path, work: Path, manifest: dict,
             manifest_step: dict, params: dict, run_id: str,
             attempt: int, log_fh) -> dict:
    """Execute one step fresh; collect outputs; write stamp. Returns record.

    argv runs VERBATIM with cwd=scratch/<step> (built argv references
    inputs/relcheck.py relatively). An attempt_start record is logged
    BEFORE spawn so a killed attempt stays countable (R2).
    """
    step = manifest_step["step"]
    scratch = work / "scratch" / step
    if scratch.exists():
        shutil.rmtree(scratch)
    scratch.mkdir(parents=True)
    dest = work / "artifacts" / step
    if dest.exists():
        shutil.rmtree(dest)
    dest.mkdir(parents=True)
    input_hashes = stage_inputs(bundle, manifest, scratch, params)
    argv = list(manifest_step["argv"])
    env, forwarded = build_env(scratch, manifest_step)
    digest = argv_sha256(argv)
    log_fh.write(json.dumps(
        {"event": "attempt_start", "run_id": run_id, "step": step,
         "attempt": attempt, "started_at": utcnow(), "argv": argv,
         "argv_sha256": digest, "input_hashes": input_hashes,
         "env_extra_keys": forwarded}, sort_keys=True) + "\n")
    log_fh.flush()
    t0 = time.monotonic()
    try:
        proc = subprocess.run(
            argv, cwd=scratch, env=env, stdin=subprocess.DEVNULL,
            stdout=subprocess.PIPE, stderr=subprocess.PIPE,
            timeout=manifest_step["timeout_s"])
        rc, timed_out = proc.returncode, False
    except subprocess.TimeoutExpired as exc:
        proc_out, proc_err = exc.stdout or b"", exc.stderr or b""
        rc, timed_out = 124, True
    else:
        proc_out, proc_err = proc.stdout, proc.stderr
    elapsed = time.monotonic() - t0
    (dest / "stdout.log").write_bytes(proc_out[:STDOUT_CAP])
    (dest / "stderr.log").write_bytes(proc_err[:STDERR_CAP])
    artifacts = []
    for rel in manifest_step["declared_outputs"]:
        fp = scratch / rel
        if fp.is_file():
            data = fp.read_bytes()
            out = dest / rel
            out.parent.mkdir(parents=True, exist_ok=True)
            out.write_bytes(data)
            artifacts.append({"relpath": rel,
                              "sha256": hashlib.sha256(data).hexdigest(),
                              "bytes": len(data)})
    record = {"event": "attempt_end", "run_id": run_id, "step": step,
              "attempt": attempt, "started_at": utcnow(), "rc": rc,
              "bundle_sha256": params["bundle_sha256"],
              "timed_out": timed_out, "elapsed_s": round(elapsed, 3),
              "argv": argv, "argv_sha256": digest,
              "input_hashes": input_hashes, "env_extra_keys": forwarded,
              "artifacts": artifacts,
              "truncated_stdout": len(proc_out) > STDOUT_CAP,
              "truncated_stderr": len(proc_err) > STDERR_CAP,
              "stamp_hit": False}
    log_fh.write(json.dumps(record, sort_keys=True) + "\n")
    log_fh.flush()
    if rc != 0:
        raise RuntimeError(f"step {step} failed: rc={rc} "
                           f"(timed_out={timed_out})")
    stamp = {"artifacts": artifacts, "elapsed_s": round(elapsed, 3),
             "rc": 0, "schema": STAMP_SCHEMA, "step": step,
             "argv_sha256": record["argv_sha256"], "run_id": run_id,
             "at": utcnow()}
    sp = stamp_path(work, step)
    sp.parent.mkdir(parents=True, exist_ok=True)
    stamp_text = json.dumps(stamp, sort_keys=True, indent=2)
    tmp = sp.with_suffix(".tmp")
    tmp.write_text(stamp_text, encoding="utf-8")
    os.replace(tmp, sp)  # atomic stamp commit (no torn-stamp skips)
    # H-parity mirror (C11-NOTE-004): the built package step reads
    # artifacts/<step>/RESULT.json (MiniHost writes it on H). The
    # stamp already carries the exact artifacts block package
    # consumes; mirror the same bytes so D completes the bundle.
    mirror = work / "artifacts" / step / "RESULT.json"
    mirror.parent.mkdir(parents=True, exist_ok=True)
    mtmp = mirror.with_suffix(".tmp")
    mtmp.write_text(stamp_text, encoding="utf-8")
    os.replace(mtmp, mirror)
    return record


def _validate_common(args) -> tuple[Path, Path, dict, dict | None, str]:
    """Shared validation for run/dry-run (0 touches: no execution)."""
    bundle, work = Path(args.bundle), Path(args.work)
    manifest = load_manifest(bundle)
    pins = (json.loads(Path(args.pins).read_text(encoding="utf-8"))
            if args.pins else None)
    bundle_sha = verify_bundle(bundle, manifest, pins)
    steps = manifest["steps"]
    if pins is not None and [s["step"] for s in steps] != pins.get("steps"):
        raise ValueError("manifest step list != pinned STEPS (R1 parity)")
    if args.step and args.step not in [s["step"] for s in steps]:
        raise ValueError(f"unknown step: {args.step}")
    return bundle, work, manifest, pins, bundle_sha


def cmd_run(args) -> int:
    bundle, work, manifest, _pins, bundle_sha = _validate_common(args)
    frozen = parse_frozen(args.frozen)  # pre-touch: typos cost nothing
    run_id = args.run_id or utcnow()
    nonce = args.nonce or run_id
    work.mkdir(parents=True, exist_ok=True)
    prior = read_touches(work)
    if prior["touches"] + 1 > TOUCH_CAP:
        with open(work / LEDGER_NAME, "a", encoding="utf-8") as log_fh:
            log_fh.write(json.dumps(
                {"event": "touch_refused", "run_id": run_id,
                 "touches": prior["touches"], "cap": TOUCH_CAP,
                 "at": utcnow()}, sort_keys=True) + "\n")
        raise ValueError(
            f"touch cap {TOUCH_CAP} per leg exceeded "
            f"(already used {prior['touches']}); refusing -- over-cap "
            "would VOID the leg (A-TOUCH). --audit still available.")
    touch_rec = record_touch(work, run_id, args.step, args.force)
    params = build_params(work, bundle_sha, frozen, run_id, nonce)
    (work / "run.json").write_text(json.dumps(
        {"run_id": run_id, "nonce": nonce, "mode": "direct",
         "bundle_sha256": bundle_sha,
         "steps": [s["step"] for s in manifest["steps"]],
         "frozen": params["frozen"],
         "touches_used": touch_rec["touches"], "touches_cap": TOUCH_CAP,
         "started_at": utcnow()}, sort_keys=True, indent=2),
        encoding="utf-8")
    ran, skipped = [], []
    with open(work / LEDGER_NAME, "a", encoding="utf-8") as log_fh:
        for s in manifest["steps"]:
            name = s["step"]
            if args.step and name != args.step:
                continue
            if name in (args.force or []) or not stamp_valid(work, name, s):
                if stamp_path(work, name).is_file() and \
                        name not in (args.force or []):
                    log_fh.write(json.dumps(
                        {"event": "stamp_invalid_rerun", "run_id": run_id,
                         "step": name, "stamp_hit": False,
                         "note": "stamp present but invalid; re-running",
                         "at": utcnow()}, sort_keys=True) + "\n")
                run_step(bundle, work, manifest, s, params, run_id,
                         next_attempt(work, name), log_fh)
                ran.append(name)
            else:
                log_fh.write(json.dumps(
                    {"event": "stamp_hit_skip", "run_id": run_id,
                     "step": name, "stamp_hit": True, "rc": 0,
                     "at": utcnow()}, sort_keys=True) + "\n")
                skipped.append(name)
                # Backfill the H-parity mirror if missing (C11-004).
                _backfill_result_mirror(work, name)
    print(json.dumps({"run_id": run_id, "bundle_sha256": bundle_sha,
                      "touches_used": touch_rec["touches"],
                      "touches_cap": TOUCH_CAP,
                      "steps_run": ran, "steps_skipped": skipped}))
    return 0


def cmd_dryrun(args) -> int:
    """0-touch assembly: stage inputs + report the plan (no execution)."""
    bundle, work, manifest, _pins, bundle_sha = _validate_common(args)
    frozen = parse_frozen(args.frozen)
    run_id = args.run_id or utcnow()
    nonce = args.nonce or run_id
    work.mkdir(parents=True, exist_ok=True)
    params = build_params(work, bundle_sha, frozen, run_id, nonce)
    plan = []
    for s in manifest["steps"]:
        name = s["step"]
        if args.step and name != args.step:
            continue
        scratch = work / "scratch" / name
        scratch.mkdir(parents=True, exist_ok=True)
        input_hashes = stage_inputs(bundle, manifest, scratch, params)
        argv = list(s["argv"])
        _env, forwarded = build_env(scratch, s)
        plan.append({"step": name, "argv": argv,
                     "argv_sha256": argv_sha256(argv),
                     "env_extra_keys": forwarded,
                     "input_hashes": input_hashes,
                     "inputs_dir": str(scratch / "inputs")})
        if shutil.which(argv[0]) is None:
            print(f"dry-run warning: argv[0] not on PATH: {argv[0]!r}",
                  file=sys.stderr)
    print(json.dumps({"run_id": run_id, "bundle_sha256": bundle_sha,
                      "params": params, "steps": plan,
                      "touches_used": 0}, sort_keys=True, indent=2))
    return 0


def cmd_audit(args) -> int:
    """0-touch inspection: stamp validity (no execution, no writes)."""
    bundle, work = Path(args.bundle), Path(args.work)
    manifest = load_manifest(bundle)
    rows = []
    for s in manifest["steps"]:
        name = s["step"]
        rows.append({"step": name,
                     "stamp_valid": stamp_valid(work, name, s)})
    print(json.dumps(rows, indent=2, sort_keys=True))
    return 0


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="direct relcheck baseline")
    ap.add_argument("--bundle", required=True)
    ap.add_argument("--work", required=True)
    ap.add_argument("--pins", default=None)
    ap.add_argument("--run-id", default=None)
    ap.add_argument("--nonce", default=None)
    ap.add_argument("--frozen", action="append", default=[],
                    help="KEY=ABSPATH frozen root (repeatable, required "
                         "for run/dry-run)")
    ap.add_argument("--step", default=None)
    ap.add_argument("--force", nargs="*", default=[])
    ap.add_argument("--audit", action="store_true")
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args(argv)
    try:
        if args.audit and args.dry_run:
            raise ValueError("--audit and --dry-run are mutually exclusive")
        if args.force and (args.audit or args.dry_run):
            raise ValueError("--force is meaningless with --audit/--dry-run")
        if args.audit:
            return cmd_audit(args)
        if args.dry_run:
            return cmd_dryrun(args)
        return cmd_run(args)
    except (ValueError, RuntimeError, OSError) as exc:
        print(f"DIRECT-BASELINE-ERROR: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
