"""make_vehicle_pins.py — deterministic relcheck build tool (re-runnable).

Generates, deterministically, from pristine frozen bytes:
  vehicle/relcheck/pins.json       bundle pins (in-bundle, staged)
  vehicle/relcheck/MANIFEST.json   bundle manifest (files pins + steps)
  vehicle/relcheck-pins.json       full pins (checker/direct anchor)

Generation gates: frozen trees must match the in-tree
FROZEN-BASELINE (loud refusal otherwise — pins are never cut from
drifted bytes); successor IDENTITY files must agree byte-for-byte;
pristine suite generation-runs must pass (their observed counts
become the expects). Re-running on unchanged bytes yields
byte-identical outputs (the lane's reproducibility check).

Usage: PYTHONDONTWRITEBYTECODE=1 python3 make_vehicle_pins.py
(cwd anywhere; paths derive from this file). Suite generation runs
take a few minutes on fast disk; workdirs persist under /tmp.
"""

from __future__ import annotations

import hashlib
import json
import os
import sys
import time
from datetime import UTC, datetime
from pathlib import Path

HERE = Path(__file__).resolve().parent
S005 = HERE.parent
PROTO = S005.parent

TREES = {"s002": "successor-002", "s003": "successor-003",
         "s004": "successor-004", "r1": "release-20261004",
         "r2": "release-r2", "r3": "release-r3"}

IGNORE_TOP = ["runs", ".test-tmp", "__pycache__", ".hypothesis",
              ".pytest_cache"]

STEPS = ("identity", "suite-r1", "suite-r2", "suite-r3", "compat",
         "package")

ARTIFACTS = {
    "identity": ["IDENTITY-RESULT.json"],
    "suite-r1": ["SUITE-R1.json", "SUITE-R1-conformance.log",
                 "SUITE-R1-demo.log"],
    "suite-r2": ["SUITE-R2.json", "SUITE-R2-conformance.log",
                 "SUITE-R2-atomicity.log"],
    "suite-r3": ["SUITE-R3.json", "SUITE-R3-conformance.log",
                 "SUITE-R3-atomicity.log"],
    "compat": ["COMPAT-REPORT.json"],
    "package": ["RELCHECK-REPORT.json"]}

SUITES = {
    "r1": {"tree": "s002",
           "programs": [
               {"kind": "unittest", "file": "test_conformance.py",
                "log": "SUITE-R1-conformance.log"},
               {"kind": "demo", "file": "successor_demo.py",
                "args": [], "log": "SUITE-R1-demo.log"}]},
    "r2": {"tree": "s003",
           "programs": [
               {"kind": "unittest", "file": "test_conformance.py",
                "log": "SUITE-R2-conformance.log"},
               {"kind": "unittest", "file": "test_atomicity.py",
                "log": "SUITE-R2-atomicity.log"}]},
    "r3": {"tree": "s004",
           "programs": [
               {"kind": "unittest", "file": "test_conformance.py",
                "log": "SUITE-R3-conformance.log"},
               {"kind": "unittest", "file": "test_atomicity.py",
                "log": "SUITE-R3-atomicity.log"}]}}

SURFACE_TREES = {"r1": "s002", "r2": "s003", "r3": "s004"}

DEMO_MARKER = "integrated demo: OK"

TIMEOUT_S = 600


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()


def write_json(path: Path, obj: dict) -> bytes:
    data = (json.dumps(obj, indent=2, sort_keys=True) + "\n").encode(
        "utf-8")
    path.write_bytes(data)
    return data


def parse_shafile(path: Path) -> dict[str, str]:
    out: dict[str, str] = {}
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line:
            continue
        digest, _, rel = line.partition("  ")
        out[rel] = digest
    return out


def verify_frozen_against_baseline() -> dict[str, dict[str, str]]:
    """Gate 1: every baseline entry under the 6 trees must match.

    Returns {tag: {relpath: sha}} of the baseline slice (used to
    cross-check walk completeness later).
    """
    baseline = parse_shafile(S005 / "FROZEN-BASELINE.sha256")
    want_dirs = set(TREES.values())
    sliced: dict[str, dict[str, str]] = {t: {} for t in TREES}
    bad: list[str] = []
    for rel, digest in sorted(baseline.items()):
        top = rel.split("/", 1)[0] if "/" in rel else rel
        if top not in want_dirs:
            continue
        tag = next(t for t, d in TREES.items() if d == top)
        sub = rel[len(top) + 1:] if "/" in rel else ""
        if not sub:
            continue
        sliced[tag][sub] = digest
        if sub.split("/")[0] in set(IGNORE_TOP):
            continue  # runs/scratch are A9-covered, not pinned
        path = PROTO / rel
        if path.is_symlink() or not path.is_file():
            bad.append(f"{rel}: missing")
        elif sha256_file(path) != digest:
            bad.append(f"{rel}: MISMATCH vs FROZEN-BASELINE")
    if bad:
        raise SystemExit(f"REFUSING to cut pins: {len(bad)} frozen "
                         f"mismatches (first: {bad[:3]})")
    n = sum(len(v) for v in sliced.values())
    print(f"gate1 frozen-vs-baseline: {n} entries clean", flush=True)
    return sliced


def build_identity_maps(sliced: dict) -> dict[str, dict[str, str]]:
    """Walk frozen trees minus ignore-tops; cross-check coverage."""
    maps: dict[str, dict[str, str]] = {}
    for tag, dirname in sorted(TREES.items()):
        base = PROTO / dirname
        found: dict[str, str] = {}
        for path in sorted(base.rglob("*")):
            if path.is_dir():
                continue
            rel = path.relative_to(base).as_posix()
            if rel.split("/")[0] in set(IGNORE_TOP):
                continue
            if path.is_symlink():
                raise SystemExit(f"REFUSING: symlink in frozen "
                                 f"bytes: {dirname}/{rel}")
            found[rel] = sha256_file(path)
        # Walk must COVER the baseline slice (minus ignored tops):
        # anything the baseline pins outside scratch must be pinned.
        for rel in sliced[tag]:
            if rel.split("/")[0] in set(IGNORE_TOP):
                continue
            if rel not in found:
                raise SystemExit(f"REFUSING: walk missed baseline "
                                 f"entry {dirname}/{rel}")
            if found[rel] != sliced[tag][rel]:
                raise SystemExit(f"REFUSING: walk/baseline skew "
                                 f"{dirname}/{rel}")
        maps[tag] = found
        print(f"identity {tag}: {len(found)} files pinned",
              flush=True)
    return maps


def cross_check_successor_identities(maps: dict) -> None:
    """Gate 2: successor trees' own IDENTITY files must agree."""
    for tag in ("s002", "s003", "s004"):
        ident_path = PROTO / TREES[tag] / "IDENTITY.sha256"
        if not ident_path.is_file():
            raise SystemExit(f"REFUSING: {TREES[tag]} has no "
                             f"IDENTITY.sha256")
        for rel, digest in sorted(
                parse_shafile(ident_path).items()):
            if rel not in maps[tag]:
                raise SystemExit(
                    f"REFUSING: IDENTITY entry {rel} not in walk")
            if maps[tag][rel] != digest:
                raise SystemExit(
                    f"REFUSING: IDENTITY skew on {rel}")
    print("gate2 successor-IDENTITY cross-check: agree", flush=True)


def generation_suite_runs(maps: dict, relcheck) -> dict:
    """Gate 3: pristine suites pass; observed counts become expects.

    Runs every pinned suite program fresh on /tmp copies via the
    BUNDLE's own run/parse functions (consistency by construction;
    the checker keeps its independent parser). Any failure refuses
    the whole generation — expects are never cut from red bytes.
    """
    stamp = datetime.now(UTC).strftime("%Y%m%dT%H%M%SZ")
    work = Path(f"/tmp/s5pinwork-{stamp}")
    work.mkdir(parents=True)
    base_cwd = Path.cwd()
    suites = json.loads(json.dumps(SUITES))  # deep copy
    try:
        for stag in ("r1", "r2", "r3"):
            spec = suites[stag]
            tree = PROTO / TREES[spec["tree"]]
            tagdir = work / f"suite-{stag}"
            tagdir.mkdir()
            os.chdir(tagdir)
            copy = tagdir / f"copy-{stag}"
            relcheck.copy_frozen(tree, copy, IGNORE_TOP)
            for prog in spec["programs"]:
                if not (copy / prog["file"]).is_file():
                    raise SystemExit(
                        f"REFUSING: suite file missing: "
                        f"{spec['tree']}/{prog['file']}")
                t0 = time.monotonic()
                rec = relcheck.run_suite_program(
                    copy, prog, {"demo_marker": DEMO_MARKER})
                dt = time.monotonic() - t0
                if rec["rc"] != 0 or not rec.get("ok", False):
                    raise SystemExit(
                        f"REFUSING: pristine generation run failed:"
                        f" {stag}/{prog['file']} rc={rec['rc']} "
                        f"(see {tagdir / prog['log']})")
                if prog["kind"] == "unittest":
                    prog["expect_tests"] = rec["ran"]
                    prog["expect_skipped"] = rec["skipped"]
                print(f"generate {stag}/{prog['file']}: ok "
                      f"ran={rec.get('ran')} skipped="
                      f"{rec.get('skipped')} wall={dt:.1f}s",
                      flush=True)
    finally:
        os.chdir(base_cwd)
    print("gate3 pristine suite generation-runs: all green",
          flush=True)
    return suites


def main() -> int:
    bundle = HERE / "relcheck"
    bin_path = bundle / "bin" / "relcheck.py"
    if not bin_path.is_file():
        print("make_vehicle_pins: bundle program missing",
              file=sys.stderr)
        return 1
    sys.path.insert(0, str(bundle / "bin"))
    import relcheck  # noqa: E402 - the bundle's own functions

    sliced = verify_frozen_against_baseline()
    maps = build_identity_maps(sliced)
    cross_check_successor_identities(maps)
    suites = generation_suite_runs(maps, relcheck)

    surface_min: dict = {}
    for stag in ("r1", "r2", "r3"):
        tree = PROTO / TREES[SURFACE_TREES[stag]]
        observed = relcheck.surface_of(tree)
        surface_min[stag] = {
            "cli_verbs": observed["cli_verbs"],
            "api_functions": observed["api_functions"]}
        print(f"surface-min {stag}: "
              f"{len(observed['cli_verbs'])} verbs, "
              f"{len(observed['api_functions'])} api fns",
              flush=True)

    bundle_pins = {"pins_format": 1, "ignore_top": IGNORE_TOP,
                   "identity": maps, "suites": suites,
                   "surface_min": surface_min,
                   "surface_trees": SURFACE_TREES,
                   "artifacts": ARTIFACTS, "steps": list(STEPS),
                   "demo_marker": DEMO_MARKER}
    pins_bytes = write_json(bundle / "pins.json", bundle_pins)
    bin_bytes = bin_path.read_bytes()
    # Machine-pinned venv interpreter for suite steps: their suite
    # children run from scratch copies lacking the relative w1/.venv
    # path, so the absolute override must travel via manifest env_extra
    # (host P3) into run_child's forwarding. Refuse rather than bake a
    # dangling path.
    venv_py = os.path.normpath(os.environ.get("SST_VENV_PY", "") or str(
        PROTO / "w1" / ".venv" / "bin" / "python"))
    if not Path(venv_py).is_file():
        raise SystemExit(
            f"REFUSING: venv interpreter unusable: {venv_py!r} "
            f"(export SST_VENV_PY)")
    print(f"venv interpreter pinned: {venv_py}", flush=True)
    manifest = {
        "files": {
            "bin/relcheck.py": hashlib.sha256(bin_bytes).hexdigest(),
            "pins.json": hashlib.sha256(pins_bytes).hexdigest()},
        "steps": [{"step": step,
                   "argv": ["python3", "inputs/relcheck.py",
                            "--step", step],
                   "declared_outputs": ARTIFACTS[step],
                   "timeout_s": TIMEOUT_S,
                   **({"env_extra": {"SST_VENV_PY": venv_py}}
                      if step.startswith("suite-") else {})}
                  for step in STEPS],
        "python": "system"}
    manifest_bytes = write_json(bundle / "MANIFEST.json", manifest)
    # Replicate procedure.canonical_manifest_bytes exactly: the
    # bundle sha is the sha of the canonical (not pretty) form.
    canonical = json.dumps(manifest, sort_keys=True,
                           separators=(",", ":"),
                           ensure_ascii=True).encode("ascii")
    bundle_sha = hashlib.sha256(canonical).hexdigest()
    full_pins = dict(bundle_pins)
    full_pins.update({
        "bundle_sha256": bundle_sha,
        "bin_relcheck_sha256": hashlib.sha256(bin_bytes).hexdigest(),
        "pins_sha256": hashlib.sha256(pins_bytes).hexdigest(),
        "frozen": {t: str(PROTO / d)
                   for t, d in sorted(TREES.items())},
        "trees": dict(TREES),
        "argv": {s: ["python3", "inputs/relcheck.py", "--step", s]
                 for s in STEPS}})
    full_bytes = write_json(HERE / "relcheck-pins.json", full_pins)
    print(f"wrote pins.json ({len(pins_bytes)} B), MANIFEST.json "
          f"({len(manifest_bytes)} B), relcheck-pins.json "
          f"({len(full_bytes)} B)", flush=True)
    print(f"bundle_sha256={bundle_sha}", flush=True)
    print(f"pins_sha256={hashlib.sha256(pins_bytes).hexdigest()}",
          flush=True)
    return 0


if __name__ == "__main__":
    sys.exit(main())
