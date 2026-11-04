"""u-harness.py — U-execute leg harness (filed; sha pinned in entry).

Subcommands (PREREG §8): kill-watch | eval-leg | eval-u |
blind-present | derive-revised-pins | freeze-check | selftest.
No vehicle execution anywhere in selftest (synthetic bundles,
synthetic envelopes, closure bytes). Stdlib only.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import secrets
import shutil
import signal
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

HERE = Path(__file__).resolve().parent
WS = HERE.parent.parent.parent
S005 = WS / "prototype" / "successor-005"
DEFAULT_CHECKER = HERE / "verdict_relcheck.py"
UPINS_BASE = HERE / "frozen-pins.json"


class HarnessError(Exception):
    """Harness failure (usage/state/tooling) — never a leg verdict."""


def utcnow() -> str:
    return datetime.now(timezone.utc).isoformat()


def load_json(fp: Path, what: str):
    try:
        return json.loads(fp.read_text(encoding="utf-8"))
    except FileNotFoundError:
        raise HarnessError(f"{what} missing: {fp}")
    except (json.JSONDecodeError, UnicodeDecodeError) as exc:
        raise HarnessError(f"{what} malformed ({fp}): {exc}")


def sha_file(fp: Path) -> str:
    return hashlib.sha256(fp.read_bytes()).hexdigest()


def write_json(fp: Path, obj) -> None:
    fp.write_text(json.dumps(obj, indent=2, sort_keys=True) + "\n",
                  encoding="utf-8")


# ------------------------------------------------------------ kill-watch

def parse_signal(spec: str):
    """ledger:PATH:STEP[:KEY] | runlog:PATH:STEP -> (kind, path, step, key)."""
    parts = spec.split(":")
    if len(parts) < 3 or parts[0] not in ("ledger", "runlog"):
        raise HarnessError(f"bad --signal spec: {spec!r} "
                           "(ledger:PATH:STEP[:KEY] | runlog:PATH:STEP)")
    kind, path, step = parts[0], Path(parts[1]), parts[2]
    key = parts[3] if len(parts) > 3 else None
    if kind == "runlog" and key is not None:
        raise HarnessError("runlog signal takes no KEY")
    if not step:
        raise HarnessError("signal STEP must be non-empty")
    return kind, path, step, key


def signal_present(kind: str, path: Path, step: str, key) -> bool:
    if not path.is_file():
        return False
    try:
        lines = path.read_text(encoding="utf-8").splitlines()
    except OSError:
        return False
    for line in lines:
        if not line.strip():
            continue
        try:
            row = json.loads(line)
        except ValueError:
            continue
        if not isinstance(row, dict):
            continue
        if kind == "ledger":
            p = row.get("payload", {})
            if row.get("kind") == "proc_begin" \
                    and p.get("step") == step \
                    and (key is None or p.get("idem_key") == key):
                return True
        else:
            if row.get("event") == "attempt_start" \
                    and row.get("step") == step:
                return True
    return False


def pgid_alive(pgid: int) -> bool:
    try:
        os.killpg(pgid, 0)
    except ProcessLookupError:
        return False
    except PermissionError:
        return True
    return True


def _leader_dead(pgid: int) -> bool:
    """/proc leader liveness; zombies count as dead (an unreaped run
    is still a dead run — killpg alone would hang the wait loop on
    it). Linux per P12; falls back to killpg where /proc is absent.
    (Sub-second pid reuse could misread once; either error lands on
    the safe side — no kill is ever performed on doubt.)"""
    if not Path("/proc").is_dir():
        return not pgid_alive(pgid)
    try:
        with open(f"/proc/{pgid}/stat") as fh:
            state = fh.read().rsplit(")", 1)[1].split()[0]
    except FileNotFoundError:
        return True
    except (OSError, IndexError):
        return not pgid_alive(pgid)
    return state in ("Z", "X", "x")


def cmd_killwatch(args) -> int:
    """Timed process-group SIGKILL for kill legs (PREREG P10, §2(c)).

    Exits 0 = killed in-window; 2 = killed out-of-window (VOID
    trigger, C1); 1 = harness/leg error (no kill performed or victim
    already gone — operator reads leg state, never assumes a kill).
    """
    pgid = args.pgid
    if os.getpgrp() == pgid:
        raise HarnessError("watcher shares the victim process group; "
                           "run the victim under setsid and pass its pgid")
    kind, path, step, key = parse_signal(args.signal)
    lo, hi = args.window
    if signal_present(kind, path, step, key):
        raise HarnessError("step already started at watcher attach; "
                           "cannot time the kill (re-run the leg)")
    poll = args.poll
    deadline = time.monotonic() + args.signal_timeout
    t_signal = None
    while time.monotonic() < deadline:
        if _leader_dead(pgid):
            raise HarnessError("victim died before the kill step "
                               "started (no kill performed)")
        if signal_present(kind, path, step, key):
            t_signal = time.monotonic()
            break
        time.sleep(poll)
    if t_signal is None:
        raise HarnessError(f"kill-step signal never seen in "
                           f"{args.signal_timeout}s (VOID + investigate)")
    seen_wall = utcnow()
    time.sleep(max(0.0, args.delay - (time.monotonic() - t_signal)))
    try:
        os.killpg(pgid, signal.SIGKILL)
        delivery = "SIGKILL-delivered"
    except ProcessLookupError:
        raise HarnessError("victim exited between signal and kill "
                           "(no kill performed; evaluate the leg as-is)")
    t_kill = time.monotonic()
    kill_wall = utcnow()
    actual = t_kill - t_signal
    in_window = lo <= actual <= hi
    # Delivery is the outcome (SIGKILL is uncatchable); reaping is the
    # operator's. ESRCH here just means already reaped.
    post = "reaped" if not pgid_alive(pgid) else "unreaped-or-zombie"
    rec = {"pgid": pgid, "watcher_pgid": os.getpgrp(),
           "signal": {"spec": args.signal, "seen_at_wall": seen_wall},
           "delay": args.delay, "window": [lo, hi],
           "kill_at_wall": kill_wall, "actual_delay_s": round(actual, 3),
           "in_window": in_window, "victim": {"delivery": delivery,
                                              "post_state": post}}
    write_json(Path(args.log), rec)
    print(f"KILL-WATCH-{'OK' if in_window else 'VOID'} "
          f"in_window={in_window} delay={actual:.1f}s window=[{lo},{hi}]")
    return 0 if in_window else 2


# ---------------------------------------------------------- freeze-check

S_TAGS = frozenset({"s002", "s003", "s004"})  # successor trees ship
# IDENTITY.sha256 files (freeze authority); release snapshots (r-tags)
# are pinned only via the upins identity maps (checker authority).


def freeze_check(upins: dict) -> dict:
    """A-FROZEN: IDENTITY files (s-tags) + pins maps (all tags).

    Mixed belt+suspenders: the maps check (filed upins bytes) also
    guards against an IDENTITY file tampered to match drifted bytes.
    """
    sys.path.insert(0, str(HERE))
    import verdict_relcheck
    maps = verdict_relcheck.freeze_verify_roots(upins)
    out = {}
    for tag in sorted(upins["frozen"]):
        root = Path(upins["frozen"][tag])
        rec: dict = {"maps_ok": maps.get(tag) is None,
                     "maps_detail": maps.get(tag) or "MATCH"}
        if tag in S_TAGS:
            ident = root / "IDENTITY.sha256"
            if not ident.is_file():
                rec["file_error"] = "IDENTITY.sha256 missing"
            else:
                proc = subprocess.run(
                    ["sha256sum", "-c", "IDENTITY.sha256"],
                    cwd=root, capture_output=True, text=True)
                rec["file_ok"] = proc.returncode == 0
                rec["file_tail"] = (proc.stdout + proc.stderr)[-200:]
        rec["ok"] = rec["maps_ok"] and rec.get("file_ok", True) \
            and "file_error" not in rec
        out[tag] = rec
    return out


def cmd_freeze(args) -> int:
    """A-FROZEN pre/post leg check. 0 all-OK; 2 MISMATCH (abort
    trigger); 1 check error (missing IDENTITY file)."""
    upins = load_json(Path(args.upins), "upins")
    res = freeze_check(upins)
    write_json(Path(args.out), {"at": utcnow(), "roots": res})
    n_ok = sum(1 for r in res.values() if r["ok"])
    print(f"FREEZE-CHECK {n_ok}/{len(res)} roots OK")
    if any("file_error" in r for r in res.values()):
        return 1
    return 0 if n_ok == len(res) else 2


# ---------------------------------------------------------- blind-present

REDACT_EXPECTED = [
    "strip-if-present top-level run-identity keys: world_id, idem_key, "
    "nonce, run_id, mode",
    "strip-if-present arm-identifying absolute path prefixes -> <ROOT>",
    "strip-if-present per-program timing keys: elapsed_s",
    "keep: pins_sha256, identities, suites{ok,results[file,rc,ran,"
    "skipped,ok]}, surface, verdict",
]

PURPOSE_BOILERPLATE = ("release-lane pre-flight: would you file this "
                       "with a cut record?")


def _scrub(obj, roots):
    """Apply redaction rules; return (scrubbed, n_stripped_keys)."""
    n = [0]

    def rec(o):
        if isinstance(o, dict):
            return {k: rec(v) for k, v in o.items()
                    if not _drop_key(k, n)}
        if isinstance(o, list):
            return [rec(v) for v in o]
        if isinstance(o, str):
            for r in roots:
                if r and r in o:
                    o = o.replace(r, "<ROOT>")
            return o
        return o

    return rec(obj), n[0]


def _drop_key(k, n):
    if k in ("world_id", "idem_key", "nonce", "run_id", "mode",
             "elapsed_s"):
        n[0] += 1
        return True
    return False


def _find_leak(obj, roots) -> str | None:
    """Fail-closed leak scan: surviving banned keys/roots -> description."""
    found = []

    def rec(o):
        if isinstance(o, dict):
            for k, v in o.items():
                if k in ("world_id", "idem_key", "nonce", "run_id",
                         "mode", "elapsed_s"):
                    found.append(f"key:{k}")
                rec(v)
        elif isinstance(o, list):
            for v in o:
                rec(v)
        elif isinstance(o, str):
            for r in roots:
                if r and r in o:
                    found.append(f"root:{r[:24]}...")

    rec(obj)
    return "; ".join(sorted(set(found))) or None


def cmd_blind(args) -> int:
    """X/Y shuffle per leg (PREREG §3, C4). Prints X/Y shas only —
    the mapping stays sealed until that leg's scores are filed."""
    upins = load_json(Path(args.upins), "upins")
    filed = upins["u_execute"]["redaction_field_list"]
    if filed != REDACT_EXPECTED:
        raise HarnessError("upins redaction list != filed text; "
                           "refusing to freelance redaction")
    roots = [r for r in args.run_roots.split(",") if r]
    if len(roots) != 2:
        raise HarnessError("--run-roots needs exactly HROOT,DROOT")
    h = load_json(Path(args.h_compat), "H compat")
    d = load_json(Path(args.d_compat), "D compat")
    hr = load_json(Path(args.h_report), "H report")
    dr = load_json(Path(args.d_report), "D report")
    if hr.get("compat") != h:
        raise HarnessError("H live compat != embedded report.compat")
    if dr.get("compat") != d:
        raise HarnessError("D live compat != embedded report.compat")
    hs, _ = _scrub(h, roots)
    ds, _ = _scrub(d, roots)
    for label, rep in (("H", hs), ("D", ds)):
        leak = _find_leak(rep, roots)
        if leak:
            raise HarnessError(f"redaction incomplete on {label}: {leak}")
    out = Path(args.out_dir)
    out.mkdir(parents=True, exist_ok=True)
    x_is_h = bool(secrets.randbelow(2))
    x, y = (hs, ds) if x_is_h else (ds, hs)
    write_json(out / "X.json", x)
    write_json(out / "Y.json", y)
    (out / "PURPOSE.txt").write_text(PURPOSE_BOILERPLATE + "\n",
                                     encoding="utf-8")
    write_json(out / "MAPPING.sealed.json",
               {"leg": args.leg, "x_arm": "H" if x_is_h else "D",
                "y_arm": "D" if x_is_h else "H",
                "h_sha256": sha_file(Path(args.h_compat)),
                "d_sha256": sha_file(Path(args.d_compat)),
                "x_sha256": sha_file(out / "X.json"),
                "y_sha256": sha_file(out / "Y.json"),
                "at": utcnow()})
    print(f"BLIND-PRESENT leg={args.leg} "
          f"x={sha_file(out / 'X.json')[:8]} "
          f"y={sha_file(out / 'Y.json')[:8]} (mapping sealed)")
    return 0


# ---------------------------------------------------- derive-revised-pins

def _all_json_files(root: Path):
    return sorted(p for p in root.rglob("*.json") if p.is_file())


def cmd_derive(args) -> int:
    """Reveal-time revised-pins derivation (PREREG C6).

    Exits 0 = derived; 2 = VOID trigger (envelope/shape failure, C6/C1);
    1 = harness error. Never repairs silently; transcripts everything.
    """
    notes: list[str] = []

    def note(s):
        notes.append(s)
        print(f"derive: {s}", flush=True)

    def void(s):
        note(f"VOID: {s}")
        write_json(Path(args.transcript),
                   {"at": utcnow(), "outcome": "VOID", "reason": s,
                    "notes": notes})
        print(f"DERIVE-RESULT VOID ({s})")
        return 2

    sealed = Path(args.sealed)
    bundle = sealed / "revision-bundle"
    man_path = sealed / "REVISION-MANIFEST.json"
    if not bundle.is_dir():
        return void("revision-bundle/ missing")
    if not man_path.is_file():
        return void("REVISION-MANIFEST.json missing")
    try:
        envelop = json.loads(man_path.read_text(encoding="utf-8"))
    except ValueError as exc:
        return void(f"envelope manifest malformed: {exc}")
    if not isinstance(envelop, dict):
        return void("envelope manifest not an object")
    base_upins = load_json(Path(args.base_upins), "base upins")
    base_bundle = Path(args.base_bundle)
    base_manifest = load_json(base_bundle / "MANIFEST.json",
                              "base MANIFEST")
    # Runnable revised bundle: as-is layout, else flat-assemble.
    if (bundle / "MANIFEST.json").is_file():
        rbundle = bundle
        note("envelope bundle layout: runnable as-is")
    else:
        cands = {"MANIFEST.json": [], "pins.json": [],
                 "relcheck.py": []}
        for fp in bundle.rglob("*"):
            if fp.is_file() and fp.name in cands:
                cands[fp.name].append(fp)
        if any(len(v) != 1 for v in cands.values()):
            return void("flat envelope lacks exactly-1 "
                        "MANIFEST.json/pins.json/relcheck.py")
        rbundle = Path(args.out).parent / "out-bundle"
        shutil.rmtree(rbundle, ignore_errors=True)
        (rbundle / "bin").mkdir(parents=True)
        shutil.copy(cands["MANIFEST.json"][0], rbundle / "MANIFEST.json")
        shutil.copy(cands["pins.json"][0], rbundle / "pins.json")
        shutil.copy(cands["relcheck.py"][0],
                     rbundle / "bin" / "relcheck.py")
        note("envelope bundle layout: flat-assembled by basename")
    # Role-based bundle files (robust to key-set drift; schema
    # verified, ambiguity fails closed).
    mroot, proot = rbundle / "MANIFEST.json", rbundle / "pins.json"
    try:
        rmanifest = json.loads(mroot.read_text(encoding="utf-8"))
    except (OSError, ValueError) as exc:
        return void(f"runnable MANIFEST unreadable: {exc}")
    try:
        rinpins = json.loads(proot.read_text(encoding="utf-8"))
    except (OSError, ValueError) as exc:
        return void(f"runnable in-bundle pins unreadable: {exc}")
    if not (isinstance(rmanifest, dict)
            and isinstance(rmanifest.get("steps"), list)
            and isinstance(rmanifest.get("files"), dict)):
        return void("runnable MANIFEST schema (steps+files)")
    if not (isinstance(rinpins, dict)
            and rinpins.get("pins_format") == 1
            and "suites" in rinpins and "artifacts" in rinpins
            and "steps" in rinpins):
        return void("runnable in-bundle pins schema")
    if "bundle_sha256" in rinpins:
        return void("in-bundle pins ambiguous (carries "
                    "bundle_sha256)")
    # Bundle binding: canonical sha must be recorded in the manifest.
    sys.path.insert(0, str(S005))
    from procedure import canonical_manifest_bytes
    rbundle_sha = hashlib.sha256(
        canonical_manifest_bytes(rmanifest)).hexdigest()
    hexes = set()

    def collect(o):
        if isinstance(o, str) and len(o) == 64 and all(
                c in "0123456789abcdef" for c in o):
            hexes.add(o)
        elif isinstance(o, dict):
            for v in o.values():
                collect(v)
        elif isinstance(o, list):
            for v in o:
                collect(v)

    collect(envelop)
    if rbundle_sha not in hexes:
        return void("envelope manifest does not record the revealed "
                    "bundle sha")
    note(f"bundle binding ok: {rbundle_sha[:16]}... recorded")
    if rbundle_sha == base_upins["bundle_sha256"]:
        return void("revealed bundle == base bundle (not a revision)")
    bin_cands = sorted(rbundle.rglob("relcheck.py"))
    if len(bin_cands) != 1:
        return void("bundle lacks exactly-1 relcheck.py")
    rbin_sha = sha_file(bin_cands[0])
    rpins_sha = sha_file(proot)
    for relpath, want in sorted(rmanifest.get("files", {}).items()):
        fp = rbundle / relpath
        if not fp.is_file() or sha_file(fp) != want:
            return void("revised MANIFEST files[] incoherent with "
                        f"disk: {relpath}")
    note("MANIFEST files[] coherent with disk")
    mfiles = envelop.get("files")
    if isinstance(mfiles, dict):
        for relpath, want in sorted(mfiles.items()):
            fp = rbundle / relpath
            if not fp.is_file() or sha_file(fp) != want:
                return void("envelope file claim contradicts disk: "
                            f"{relpath}")
        note("envelope file claims verified")
    # P9-conformance: the §3 (1+1+1) budget, mechanical
    # (RULES-AMENDMENT-2(f)). No removals anywhere; exactly one added
    # step carrying exactly one added declared output (base steps'
    # declared sets byte-equal); exactly one added suite target in
    # the existing tags; a program delta present (relcheck.py bytes
    # changed XOR one added bin/ program argv-referenced by the new
    # step).
    base_files = base_manifest.get("files", {})
    rev_files = rmanifest.get("files", {})
    base_steps = [s["step"] for s in base_manifest.get("steps", [])]
    rev_steps = [s["step"] for s in rmanifest.get("steps", [])]
    added_files = sorted(set(rev_files) - set(base_files))
    removed_files = sorted(set(base_files) - set(rev_files))
    if removed_files:
        return void(f"bundle files removed vs base: {removed_files}")
    if len(added_files) > 1:
        return void(f"bundle files added >1: {added_files}")
    if added_files and not added_files[0].startswith("bin/"):
        return void(f"added file not a bin/ program: {added_files}")
    added_steps = sorted(set(rev_steps) - set(base_steps))
    if set(base_steps) - set(rev_steps):
        return void("steps removed vs base")
    if len(added_steps) != 1:
        return void(f"steps added != 1: {added_steps}")
    note(f"steps added: {added_steps}")
    base_decl = {s["step"]: s["declared_outputs"]
                 for s in base_manifest["steps"]}
    rev_decl = {s["step"]: s["declared_outputs"]
                for s in rmanifest["steps"]}
    for s in base_steps:
        if rev_decl.get(s) != base_decl.get(s):
            return void(f"base step {s!r} declared outputs changed")
    new_out = rev_decl.get(added_steps[0], [])
    if len(new_out) != 1:
        return void("new step must declare exactly one output")
    note(f"outputs: +1 ({new_out[0]}) on {added_steps[0]}")
    base_suites = base_upins["suites"]
    rin_suites = rinpins.get("suites", {})
    if set(rin_suites) != set(base_suites):
        return void("suite tags differ vs base (targets, not tags)")
    base_progs = {(t, p["file"]) for t, s in base_suites.items()
                  for p in s["programs"]}
    rev_progs = {(t, p["file"]) for t, s in rin_suites.items()
                 for p in s.get("programs", [])}
    if base_progs - rev_progs:
        return void("suite programs removed vs base")
    if len(rev_progs - base_progs) != 1:
        return void("suite programs added != 1")
    note(f"programs: +1 {sorted(rev_progs - base_progs)}")
    relcheck_changed = (rev_files.get("bin/relcheck.py")
                        != base_files.get("bin/relcheck.py"))
    if added_files:
        want_base = os.path.basename(added_files[0])
        new_argv = next(s["argv"] for s in rmanifest["steps"]
                        if s["step"] == added_steps[0])
        if not any(isinstance(a, str)
                   and os.path.basename(a) == want_base
                   for a in new_argv):
            return void(f"added file {added_files[0]} not "
                        f"argv-referenced by {added_steps[0]}")
        note(f"program delta: added {added_files[0]} (argv-linked)")
    elif not relcheck_changed:
        return void("no program delta (relcheck.py identical, no "
                    "added file)")
    else:
        note("program delta: relcheck.py bytes changed")
    for tag, spec in rin_suites.items():
        for p in spec.get("programs", []):
            if p.get("kind") not in ("unittest", "demo"):
                return void(f"program kind invalid: {p}")
            if not p.get("log"):
                return void(f"program log missing: {p}")
    if list(rinpins.get("steps", [])) != rev_steps:
        return void("in-bundle pins steps != MANIFEST steps")
    # Vehicle pins: envelope copy if schema-valid, else graft.
    veh = None
    for fp in _all_json_files(sealed):
        if fp == man_path or fp in (mroot, proot):
            continue
        try:
            doc = json.loads(fp.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            continue
        if isinstance(doc, dict) and doc.get("pins_format") == 1 \
                and "bundle_sha256" in doc and "suites" in doc:
            if veh is not None:
                return void("ambiguous: >1 vehicle-pins candidate")
            veh = (fp, doc)
    derived: dict
    if veh is not None:
        vfp, vdoc = veh
        if vdoc.get("bundle_sha256") != rbundle_sha:
            return void("envelope vehicle pins bind a different bundle")
        if vdoc.get("bin_relcheck_sha256") != rbin_sha:
            return void("envelope vehicle pins bind a different bin")
        if vdoc.get("pins_sha256") != rpins_sha:
            return void("envelope vehicle pins bind different "
                        "in-bundle pins")
        derived = dict(vdoc)
        note(f"vehicle pins: envelope copy {vfp.name} verified")
    else:
        note("vehicle pins: absent — mechanical graft")
        argv = {s["step"]: s["argv"] for s in rmanifest["steps"]}
        derived = {
            "pins_format": 1,
            "ignore_top": base_upins["ignore_top"],
            "identity": base_upins["identity"],
            "frozen": base_upins["frozen"],
            "trees": base_upins["trees"],
            "surface_min": base_upins["surface_min"],
            "surface_trees": base_upins["surface_trees"],
            "steps": rev_steps,
            "argv": argv,
            "suites": rin_suites,
            "artifacts": rinpins["artifacts"],
            "demo_marker": base_upins["demo_marker"],
            "bundle_sha256": rbundle_sha,
            "bin_relcheck_sha256": rbin_sha,
            "pins_sha256": rpins_sha,
        }
    missing = [k for k in base_upins if k in (
        "argv", "artifacts", "bin_relcheck_sha256", "bundle_sha256",
        "demo_marker", "frozen", "identity", "ignore_top",
        "pins_format", "pins_sha256", "steps", "suites",
        "surface_min", "surface_trees", "trees") and k not in derived]
    if missing:
        return void(f"derived pins lack keys: {missing}")
    for step in derived["steps"]:
        if step not in derived["argv"] \
                or step not in derived["artifacts"]:
            return void(f"derived pins starve step {step!r}")
    if not set(derived["steps"]) >= set(base_upins["steps"]):
        return void("derived steps drop a base step")
    derived["u_execute"] = base_upins["u_execute"]
    derived["provenance"] = {
        "derived_from_envelope": sha_file(man_path),
        "base_upins_sha256": sha_file(Path(args.base_upins)),
        "deriver": f"u-harness.py {sha_file(Path(__file__))[:16]}",
        "at": utcnow(),
    }
    out = Path(args.out)
    write_json(out, derived)
    write_json(Path(args.transcript),
               {"at": utcnow(), "outcome": "DERIVED",
                "bundle_dir": str(rbundle),
                "derived_sha256": sha_file(out), "notes": notes})
    print(f"DERIVE-RESULT DERIVED {sha_file(out)[:16]} "
          f"(bundle {rbundle_sha[:8]})")
    return 0


# -------------------------------------------------------------- eval-leg

def run_checker(checker: Path, args: list[str]) -> tuple[int, str]:
    proc = subprocess.run([sys.executable, str(checker), *args],
                          capture_output=True, text=True)
    lines = proc.stdout.splitlines()
    if proc.returncode not in (0, 1) or len(lines) != 1 \
            or not lines[0].startswith("RELCHECK-"):
        raise HarnessError(
            f"checker broke the 1-line contract "
            f"(rc={proc.returncode}): {proc.stdout[:200]!r} "
            f"{proc.stderr[:200]!r}")
    return proc.returncode, lines[0]


def tolerant_jsonl(path: Path):
    """(rows|None, error|None) — corrupt evidence never crashes eval."""
    try:
        rows = [json.loads(ln) for ln in
                path.read_text(encoding="utf-8").splitlines()
                if ln.strip()]
    except FileNotFoundError:
        return None, f"missing: {path}"
    except (OSError, ValueError) as exc:
        return None, f"unreadable: {exc}"
    if any(not isinstance(r, dict) for r in rows):
        return None, "non-object row present"
    return rows, None


def d_rework(rows) -> dict:
    """C3 re-work counts from direct-ledger rows (literal formulas)."""
    starts: dict[str, list[int]] = {}
    end0_before: dict[str, bool] = {}
    for i, r in enumerate(rows):
        if r.get("event") == "attempt_start" and r.get("step"):
            starts.setdefault(r["step"], []).append(i)
    for step, idxs in starts.items():
        for j in idxs[1:]:
            prior = [r for r in rows[:j]
                     if r.get("event") == "attempt_end"
                     and r.get("step") == step and r.get("rc") == 0]
            if prior:
                end0_before[step] = True
                break
    steps = [s for s in starts if starts[s]]
    s_total = sum(len(v) for v in starts.values())
    completed = sum(1 for s in steps if end0_before.get(s))
    return {"attempts_total": s_total, "steps_attempted": len(steps),
            "completed_step_reruns": completed,
            "current_step_reruns": (s_total - len(steps)) - completed}


def h_begins(entries, key: str) -> dict[str, int]:
    out: dict[str, int] = {}
    for e in entries:
        if e.get("kind") == "proc_begin" \
                and e.get("payload", {}).get("idem_key") == key:
            step = e["payload"].get("step", "?")
            out[step] = out.get(step, 0) + 1
    return out


def bundle_posthash(bundle: Path, manifest: dict,
                    expected: str) -> tuple[bool, str]:
    """H post-hash: builder canonical rule + file re-hash + ASCII
    cross-check against the direct runner's rule (fail closed)."""
    sys.path.insert(0, str(HERE))
    sys.path.insert(0, str(S005))
    import direct_run
    from procedure import canonical_manifest_bytes
    files = manifest.get("files", {})
    broot = bundle.resolve()
    for relpath, want in sorted(files.items()):
        fp = (bundle / relpath).resolve()
        if fp != broot and broot not in fp.parents:
            return False, f"listed file escapes bundle: {relpath}"
        if not fp.is_file():
            return False, f"listed file missing: {relpath}"
        if sha_file(fp) != want:
            return False, f"hash mismatch: {relpath}"
    mine = hashlib.sha256(canonical_manifest_bytes(manifest)).hexdigest()
    theirs = direct_run.sha256_canonical(manifest)
    if mine != theirs:
        raise HarnessError("canonical-JSON rules disagree (non-ASCII "
                           "manifest?); refusing to guess the post-hash")
    if mine != expected:
        return False, "bundle sha != pins"
    return True, "MATCH"


def import_predicates():
    sys.path.insert(0, str(HERE))
    import predicates
    return predicates


def cmd_eval(args) -> int:
    """Evaluate one arm-leg → LEG-VERDICT.json (§6 cells + guards).

    Verdicts are data (exit 0 always on success); missing evidence or
    tool breakage is HarnessError (exit 1, retryable, never scored).
    """
    pu = import_predicates()
    arm, leg = args.arm, args.leg
    pins = load_json(Path(args.pins), "pins")
    venv_py = args.venv_py
    freeze_pre = load_json(Path(args.freeze_pre), "freeze-pre")
    frozen_pre_ok = all(r.get("ok") for r in
                        freeze_pre.get("roots", {}).values()) \
        and bool(freeze_pre.get("roots"))
    post = freeze_check(pins)
    frozen_post_ok = all(r.get("ok") for r in post.values())
    checker = Path(args.checker or DEFAULT_CHECKER)
    pred: dict = {}
    diag: dict = {}
    counts: dict = {}
    guards: dict = {}
    if arm == "H":
        if leg in ("clean", "kill") and not args.key:
            raise HarnessError(f"H {leg} needs --key")
        if leg == "change" and not (args.key_new and args.worlds):
            raise HarnessError("H change needs --key-new + --worlds")
        state = Path(args.state_dir)
        worlds = args.worlds.split(",") if args.worlds else []
        key = args.key_new if leg == "change" else args.key
        staged = state / "state" / args.world / "procedures" / \
            args.procedure
        manifest = load_json(staged / "MANIFEST.json", "staged MANIFEST")
        universe = [s["step"] for s in manifest["steps"]] \
            if leg == "change" else None
        ledger_p = state / "ledger.jsonl"
        entries, lerr = tolerant_jsonl(ledger_p)
        artifacts = state / "artifacts"
        report_p = artifacts / f"proc-{key}" / "package" / \
            "RELCHECK-REPORT.json"
        report = load_json(report_p, "package report")
        crc, cline = run_checker(
            checker, [str(report_p), str(ledger_p),
                      str(artifacts / f"proc-{key}"),
                      str(Path(args.pins))])
        pred["report_valid"] = pu.p_report_valid(cline)
        if entries is None:
            for name in ("steps_complete", "no_completed_rerun",
                         "kill_shape", "ledger_report_agree",
                         "hashes_recompute", "change_shape",
                         "sst_confined"):
                pred[name] = f"unevaluated: ledger {lerr}"
            counts["begins"] = {}
        else:
            uni = universe or pu.STEPS
            pred["steps_complete"] = pu.p_steps_complete(
                entries, key, universe)
            pred["no_completed_rerun"] = pu.p_no_completed_rerun(
                entries, key)
            pred["kill_shape"] = pu.p_kill_leg_shape(
                entries, key, universe)
            pred["ledger_report_agree"] = pu.p_ledger_report_agree(
                entries, key, report)
            pred["hashes_recompute"] = pu.p_hashes_recompute(
                entries, key, artifacts)
            pred["change_shape"] = pu.p_change_leg_shape(
                entries, key, tuple(worlds), universe) \
                if leg == "change" else "n/a (not change leg)"
            pred["sst_confined"] = pu.p_sst_snapshot_confined(
                entries, key, state, manifest, venv_py, universe)
            begins = h_begins(entries, key)
            counts["begins"] = begins
            counts["current_step_reruns"] = sum(
                max(0, begins.get(s, 0) - 1) for s in uni)
            counts["success_invokes"] = len(pu._success_invokes(
                entries, key))
            lower = 1 + max(0, sum(begins.values()) - len(uni))
            if args.touch_count < lower:
                raise HarnessError(
                    f"H touch undercount: claimed {args.touch_count} "
                    f"< ledger lower bound {lower}")
        inspect = load_json(Path(args.inspect_json), "inspect")
        pred["conservation"] = pu.p_conservation_ok(inspect)
        if not Path(args.touch_log).is_file():
            raise HarnessError("H touch log missing "
                               f"(attestation required): {args.touch_log}")
        pred["touch_cap"] = pu.p_touch_cap(args.touch_count, 2)
        counts["touches_claimed"] = args.touch_count
        counts["touch_log_sha256"] = sha_file(Path(args.touch_log))
        ok, detail = bundle_posthash(staged, manifest,
                                     pins["bundle_sha256"])
        guards["bundle_posthash"] = {"ok": ok, "detail": detail}
        guards["conservation"] = pred["conservation"] is True
        guards["touch_cap"] = pred["touch_cap"] is True
        guards["sst"] = pred["sst_confined"] is True
        validity = pred["report_valid"] is True \
            and pred["ledger_report_agree"] is True \
            and pred["hashes_recompute"] is True
        cells = {"validity": bool(validity)}
        if leg == "kill":
            cells["recovery"] = bool(
                validity and pred["kill_shape"] is True
                and pred["no_completed_rerun"] is True)
        if leg == "change":
            cells["adapt"] = bool(
                validity and pred["change_shape"] is True)
    else:
        work = Path(args.work)
        bundle = Path(args.bundle)
        manifest = load_json(bundle / "MANIFEST.json", "bundle MANIFEST")
        log_p = work / "direct-ledger.jsonl"
        rows, lerr = tolerant_jsonl(log_p)
        artifacts = work / "artifacts"
        report_p = artifacts / "package" / "RELCHECK-REPORT.json"
        report = load_json(report_p, "package report")
        crc, cline = run_checker(
            checker, [str(report_p), "--no-ledger", "--stamps",
                      str(work), str(artifacts), str(Path(args.pins))])
        pred["report_valid"] = pu.p_report_valid(cline)
        for name in ("steps_complete", "ledger_report_agree",
                     "hashes_recompute", "conservation"):
            pred[name] = "n/a (D, C3)"
        if rows is None:
            counts["rework"] = f"unavailable: log {lerr}"
        else:
            counts["rework"] = d_rework(rows)
        touches = load_json(work / "touches.json", "touches.json")
        pred["touch_cap"] = pu.p_touch_cap(touches["touches"], 2)
        counts["touches"] = touches["touches"]
        uni = [s["step"] for s in manifest["steps"]]
        pred["sst_confined"] = pu.d_confinement_slots(
            work, manifest, venv_py, uni)
        try:
            sys.path.insert(0, str(HERE))
            import direct_run
            got = direct_run.verify_bundle(bundle, manifest, pins)
            ok = got == pins["bundle_sha256"]
            detail = "MATCH" if ok else "bundle sha != pins"
        except ValueError as exc:
            ok, detail = False, str(exc)[:160]
        guards["bundle_posthash"] = {"ok": ok, "detail": detail}
        guards["touch_cap"] = pred["touch_cap"] is True
        guards["sst"] = pred["sst_confined"] is True
        cells = {"validity": bool(pred["report_valid"] is True)}
        if leg == "kill":
            cells["recovery"] = "n/a (D counts reported)"
        if leg == "change":
            cells["adapt"] = bool(cells["validity"])
    guards["frozen_pre"] = bool(frozen_pre_ok)
    guards["frozen_post"] = {"ok": bool(frozen_post_ok), "roots": post}
    guards["all"] = bool(frozen_pre_ok and frozen_post_ok
                         and guards["bundle_posthash"]["ok"]
                         and guards["touch_cap"] and guards["sst"]
                         and (guards.get("conservation", True) is True))
    scores = None
    if args.rubric_scores and args.rubric_scores != "null":
        scores = load_json(Path(args.rubric_scores), "rubric scores")
    provisional = scores is None
    if scores is None:
        cells["useful"] = None
    else:
        pred["rubric_bar"] = pu.p_rubric_bar(scores)
        cells["useful"] = bool(pred["rubric_bar"] is True)
    verdict = {"arm": arm, "leg": leg, "at": utcnow(),
               "checker": {"rc": crc, "line": cline},
               "predicates": pred, "diagnostics": diag,
               "counts": counts, "guards": guards, "cells": cells,
               "provisional": provisional}
    write_json(Path(args.out), verdict)
    snap = {k: v for k, v in cells.items()}
    print(f"LEG-VERDICT {arm}/{leg} cells={snap} "
          f"guards={guards['all']} provisional={provisional}")
    return 0


# -------------------------------------------------------------- eval-u

SIX = [("H", "clean"), ("H", "change"), ("H", "kill"),
       ("D", "clean"), ("D", "change"), ("D", "kill")]


def cmd_evalu(args) -> int:
    """Overall U verdict from six LEG-VERDICTs (§6 + C7 + C10)."""
    paths = [Path(p) for p in args.verdicts]
    if len(paths) != 6:
        raise HarnessError("eval-u needs exactly 6 verdicts")
    vs = [load_json(p, f"verdict {p}") for p in paths]
    keys = sorted((v["arm"], v["leg"]) for v in vs)
    if keys != sorted(SIX):
        raise HarnessError(f"verdict set != 6 arm-legs: {keys}")
    by = {(v["arm"], v["leg"]): v for v in vs}
    if not args.allow_provisional \
            and any(v["provisional"] for v in vs):
        raise HarnessError("scores pending (provisional verdicts)")
    provisional = any(v["provisional"] for v in vs)
    fails: list[str] = []
    for k in SIX:
        if not by[k]["guards"]["all"]:
            fails.append(f"guard:{k[0]}/{k[1]}")
    for leg in ("clean", "change", "kill"):
        if by[("D", leg)]["cells"]["validity"] is not True:
            fails.append(f"comparison-void:D/{leg}")
    hclean = by[("H", "clean")]["cells"]["validity"] is True
    hkill = by[("H", "kill")]["cells"].get("recovery") is True
    hchange = by[("H", "change")]["cells"].get("adapt") is True
    if not hclean:
        fails.append("H-clean-validity")
    if not hkill:
        fails.append("H-kill-recovery")
    if not hchange:
        fails.append("H-change-adapt")
    for k in SIX:
        u = by[k]["cells"].get("useful")
        if u is None:
            if not provisional:
                fails.append(f"rubric-missing:{k[0]}/{k[1]}")
        elif u is not True:
            fails.append(f"rubric-bar:{k[0]}/{k[1]}")
    if not (hkill or hchange):
        fails.append("no-H-exclusive-cell")
    if provisional:
        outcome = "PENDING-RUBRIC"
    elif fails:
        outcome = "HOST-VALUE-NOT-DEMONSTRATED"
    else:
        outcome = "HOST-VALUE-DEMONSTRATED"
    write_json(Path(args.out),
               {"at": utcnow(), "outcome": outcome,
                "failing": fails, "provisional": provisional})
    print(f"U-VERDICT {outcome} failing={fails}")
    return 0


# ------------------------------------------------------------ selftest

class Selftest:
    def __init__(self):
        self.fails: list[str] = []

    def check(self, name, cond, detail=""):
        flag = "PASS" if cond else "FAIL"
        extra = f" — {detail}" if detail and not cond else ""
        print(f"[{flag}] {name}{extra}", flush=True)
        if not cond:
            self.fails.append(name)


def t_predicates(st: Selftest) -> None:
    pu = import_predicates()
    host = S005 / "runs" / "note1-closure" / "artifacts" / "host"
    led = [json.loads(ln) for ln in
           (host / "ledger.jsonl").read_text().splitlines()
           if ln.strip()]
    rep = json.loads((host / "package" / "RELCHECK-REPORT.json")
                     .read_text())
    key = "s5a10readiness"
    man = json.loads((S005 / "vehicle" / "relcheck" / "MANIFEST.json")
                     .read_text())
    venv = str(WS / "prototype" / "w1" / ".venv" / "bin" / "python")
    import copy
    st.check("pred/steps_complete", pu.p_steps_complete(led, key))
    st.check("pred/no_completed_rerun",
             pu.p_no_completed_rerun(led, key))
    st.check("pred/kill_shape_clean_False",
             pu.p_kill_leg_shape(led, key) is False)
    st.check("pred/ledger_report_agree",
             pu.p_ledger_report_agree(led, key, rep))
    artroot = Path("/tmp/note1-ready/artifacts")
    if artroot.is_dir():
        st.check("pred/hashes_recompute",
                 pu.p_hashes_recompute(led, key, artroot))
        st.check("pred/sst_confined",
                 pu.p_sst_snapshot_confined(
                     led, key, Path("/tmp/note1-ready"), man, venv))
    else:
        st.check("pred/live-bytes-present", False, "/tmp wiped?")
    led2 = copy.deepcopy(led)
    b2 = copy.deepcopy(next(
        e for e in led2 if e.get("kind") == "proc_begin"
        and e["payload"].get("step") == "suite-r3"))
    b2["payload"]["invoke_id"] = "proc-s5a10readiness-suite-r3-a2"
    led2.append(b2)
    st.check("pred/kill_shape_rerun",
             pu.p_kill_leg_shape(led2, key) is True)
    led3 = copy.deepcopy(led)
    for e in led3:
        if e.get("kind") == "invoke" and e.get("payload", {}).get(
                "proc", {}).get("step") == "suite-r3":
            e["payload"]["proc"]["recovered"] = True
    st.check("pred/kill_shape_adopt",
             pu.p_kill_leg_shape(led3, key) is True)
    st.check("pred/universe_bites",
             pu.p_steps_complete(led, key, pu.STEPS + ["assay"])
             is False)
    st.check("pred/rubric_bar",
             pu.p_rubric_bar({"R1": 2, "R2": 1, "R3": 1}) is True
             and pu.p_rubric_bar({"R1": 2, "R2": 0, "R3": 2})
             is False)
    st.check("pred/touch_cap",
             pu.p_touch_cap(2) is True and pu.p_touch_cap(3) is False)
    st.check("pred/conservation",
             pu.p_conservation_ok({"conservation": {"ok": True}})
             is True
             and pu.p_conservation_ok({"conservation": {"ok": False}})
             is False)
    invs = [{"kind": "invoke",
             "payload": {"capability": "proc.exec",
                         "proc": {"idem_key": "k2", "step": s,
                                  "bundle_sha256": "N" * 64},
                         "result_ref": "x"}} for s in pu.STEPS]
    chg = [{"kind": "create",
            "payload": {"world_id": "w1", "procedures": [
                {"bundle_sha256": "B" * 64}]}},
           {"kind": "create",
            "payload": {"world_id": "w2", "procedures": [
                {"bundle_sha256": "N" * 64}]}}] + invs
    st.check("pred/change_shape",
             pu.p_change_leg_shape(chg, "k2", ("w1", "w2")) is True)
    chg2 = copy.deepcopy(chg)
    chg2[1]["payload"]["procedures"].append({"bundle_sha256": "B" * 64})
    st.check("pred/change_shape_overlap_False",
             pu.p_change_leg_shape(chg2, "k2", ("w1", "w2")) is False)


def t_dconfinement(st: Selftest, tmp: Path) -> None:
    pu = import_predicates()
    venv = str(WS / "prototype" / "w1" / ".venv" / "bin" / "python")
    man = {"steps": [{"step": "s1"}]}
    good = tmp / "dconf-good"
    (good / "scratch" / "s1" / "sst-leg").mkdir(parents=True)
    (good / "direct-ledger.jsonl").write_text(
        json.dumps({"event": "attempt_end", "step": "s1", "rc": 0,
                    "env_extra_keys": ["SST_VENV_PY"]}) + "\n"
        + json.dumps({"step": "s1", "rc": 0}) + "\n")
    st.check("dconf/good",
             pu.d_confinement_slots(good, man, venv, ["s1"]) is True)
    bad = tmp / "dconf-bad"
    (bad / "sst-leg").mkdir(parents=True)
    (bad / "direct-ledger.jsonl").write_text("{}\n")
    st.check("dconf/outside_scratch_False",
             pu.d_confinement_slots(bad, man, venv, ["s1"]) is False)
    net = tmp / "dconf-net"
    (net / "scratch" / "s1").mkdir(parents=True)
    (net / "direct-ledger.jsonl").write_text(
        json.dumps({"event": "net_send", "step": "s1"}) + "\n")
    st.check("dconf/net_event_False",
             pu.d_confinement_slots(net, man, venv, ["s1"]) is False)
    keyf = tmp / "dconf-key"
    (keyf / "scratch" / "s1").mkdir(parents=True)
    (keyf / "direct-ledger.jsonl").write_text(
        json.dumps({"event": "attempt_end", "step": "s1",
                    "env_extra_keys": ["MY_API_KEY"]}) + "\n")
    st.check("dconf/key_fragment_False",
             pu.d_confinement_slots(keyf, man, venv, ["s1"]) is False)
    nolog = tmp / "dconf-nolog"
    (nolog / "scratch" / "s1").mkdir(parents=True)
    st.check("dconf/missing_log_False",
             pu.d_confinement_slots(nolog, man, venv, ["s1"]) is False)


SYN_STEPS = ["identity", "suite-r1", "suite-r2", "suite-r3", "compat",
             "package"]


def synth_bundle(path: Path) -> dict:
    """Six trivial steps, checker-bindable input basenames
    (relcheck.py + pins.json + params.json shape the input_hashes)."""
    path.mkdir(parents=True, exist_ok=True)
    (path / "bin").mkdir(exist_ok=True)
    prog = ("import sys, pathlib\n"
            "pathlib.Path(sys.argv[1]).write_text('out:' + sys.argv[1])\n")
    (path / "bin" / "relcheck.py").write_text(prog)
    (path / "pins.json").write_text('{"synthetic": true}\n')
    files = {}
    for rel in ("bin/relcheck.py", "pins.json"):
        files[rel] = sha_file(path / rel)
    steps = [{"step": s,
              "argv": [sys.executable, "inputs/relcheck.py",
                       f"OUT-{s}.json"],
              "declared_outputs": [f"OUT-{s}.json"],
              "timeout_s": 60} for s in SYN_STEPS]
    manifest = {"files": files, "steps": steps}
    (path / "MANIFEST.json").write_text(json.dumps(manifest, indent=2))
    return manifest


def run_direct(bundle: Path, work: Path, *extra) -> subprocess.CompletedProcess:
    return subprocess.run(
        [sys.executable, str(HERE / "direct_run.py"), "--bundle",
         str(bundle), "--work", str(work), *extra],
        capture_output=True, text=True)


def t_runner(st: Selftest, tmp: Path) -> None:
    bundle = tmp / "synb"
    manifest = synth_bundle(bundle)
    work = tmp / "dwork"
    p = run_direct(bundle, work, "--frozen", "K=/tmp")
    st.check("run/full_rc0", p.returncode == 0, p.stderr[-200:])
    try:
        summary = json.loads(p.stdout)
    except ValueError:
        summary = {}
    st.check("run/steps_run_all",
             summary.get("steps_run") == SYN_STEPS, p.stdout[-200:])
    stamps_ok = all(
        (work / "steps" / f"{s}-RESULT.json").is_file() for s in
        SYN_STEPS)
    st.check("run/stamps_builder_paths", stamps_ok)
    stamp = json.loads(
        (work / "steps" / "identity-RESULT.json").read_text())
    st.check("run/stamp_shape",
             stamp.get("rc") == 0 and stamp.get("schema") == 3
             and isinstance(stamp.get("artifacts"), list)
             and "elapsed_s" in stamp)
    rows = [json.loads(ln) for ln in
            (work / "direct-ledger.jsonl").read_text().splitlines()]
    ends = [r for r in rows if r.get("event") == "attempt_end"]
    st.check("run/end_rows_bound",
             len(ends) == 6 and all(
                 r.get("rc") == 0 and "bundle_sha256" in r
                 for r in ends))
    runj = json.loads((work / "run.json").read_text())
    st.check("run/run_json",
             runj.get("mode") == "direct"
             and runj.get("touches_used") == 1)
    # Independent re-stage: dry-run elsewhere, compare input hashes.
    dry = tmp / "ddry"
    p = run_direct(bundle, dry, "--frozen", "K=/tmp", "--dry-run",
                   "--step", "identity")
    st.check("run/dryrun_rc0", p.returncode == 0, p.stderr[-200:])
    indep = {}
    for fp in (dry / "scratch" / "identity" / "inputs").iterdir():
        indep[fp.name] = sha_file(fp)
    logged = ends[0]["input_hashes"]
    # params.json is work-dir-relative by design (run_root paths);
    # bundle-file bytes must match independently. (params shape
    # equality modulo run paths was proven by the T8 dry-run diff.)
    st.check("run/input_hashes_independent",
             all(logged.get(k) == v for k, v in indep.items()
                 if k != "params.json")
             and "params.json" in logged
             and "params.json" in indep)
    # Bundle sha: builder rule vs runner output (non-circular).
    sys.path.insert(0, str(S005))
    from procedure import canonical_manifest_bytes
    expect = hashlib.sha256(
        canonical_manifest_bytes(manifest)).hexdigest()
    st.check("run/bundle_sha_builder_rule",
             runj.get("bundle_sha256") == expect)
    # Function-level checker binding on produced rows (full path:
    # pins from BUNDLE bytes, universe bound via filed validation).
    sys.path.insert(0, str(HERE))
    import verdict_relcheck
    fhash = {fp.name: sha_file(bundle / rel)
             for rel, fp in (("bin/relcheck.py",
                              bundle / "bin" / "relcheck.py"),
                             ("pins.json", bundle / "pins.json"))}
    synth_pins = {
        "steps": SYN_STEPS,
        "argv": {s["step"]: s["argv"] for s in manifest["steps"]},
        "artifacts": {s: [f"OUT-{s}.json"] for s in SYN_STEPS},
        "bundle_sha256": expect,
        "pins_sha256": fhash["pins.json"],
        "bin_relcheck_sha256": fhash["relcheck.py"],
    }
    try:
        verdict_relcheck.bind_step_universe(synth_pins)
        verdict_relcheck._check_run_log(work, synth_pins)
        bound_ok, detail = True, ""
    except Exception as exc:  # noqa: BLE001 — selftest records
        bound_ok, detail = False, f"{type(exc).__name__}: {exc}"
    finally:
        verdict_relcheck.ALL_STEPS = verdict_relcheck.BASE_STEPS
    st.check("run/checker_binds_rows", bound_ok, detail)
    # Resume: all skipped, touch 2; third touch refused.
    p = run_direct(bundle, work, "--frozen", "K=/tmp")
    try:
        summary2 = json.loads(p.stdout)
    except ValueError:
        summary2 = {}
    st.check("run/resume_skips",
             p.returncode == 0
             and summary2.get("steps_run") == []
             and summary2.get("touches_used") == 2, p.stderr[-200:])
    p = run_direct(bundle, work, "--frozen", "K=/tmp")
    st.check("run/third_touch_refused",
             p.returncode == 1 and "touch cap" in p.stderr)
    # Kill + resume on a slow step (fresh work dir).
    kb = tmp / "synb-kill"
    kb.mkdir()
    (kb / "bin").mkdir()
    (kb / "bin" / "relcheck.py").write_text(
        "import time, pathlib\ntime.sleep(30)\n"
        "pathlib.Path('SLOW.json').write_text('slow')\n")
    (kb / "pins.json").write_text("{}\n")
    kfiles = {rel: sha_file(kb / rel)
              for rel in ("bin/relcheck.py", "pins.json")}
    kman = {"files": kfiles, "steps": [
        {"step": "slow", "argv": [sys.executable,
                                 "inputs/relcheck.py"],
         "declared_outputs": ["SLOW.json"], "timeout_s": 120}]}
    (kb / "MANIFEST.json").write_text(json.dumps(kman))
    kwork = tmp / "kwork"
    proc = subprocess.Popen(
        [sys.executable, str(HERE / "direct_run.py"), "--bundle",
         str(kb), "--work", str(kwork), "--frozen", "K=/tmp"],
        start_new_session=True, stdout=subprocess.PIPE,
        stderr=subprocess.PIPE, text=True)
    try:
        klog = kwork / "direct-ledger.jsonl"
        t0 = time.monotonic()
        while time.monotonic() - t0 < 20:
            if klog.is_file() and "attempt_start" in klog.read_text():
                break
            time.sleep(0.2)
        started = klog.is_file() \
            and "attempt_start" in klog.read_text()
        st.check("run/kill_started", started)
        os.killpg(proc.pid, signal.SIGKILL)
        proc.wait(timeout=10)
        rows = [json.loads(ln) for ln in
                klog.read_text().splitlines() if ln.strip()]
        starts = [r for r in rows
                  if r.get("event") == "attempt_start"]
        endz = [r for r in rows if r.get("event") == "attempt_end"]
        st.check("run/kill_start_without_end",
                 len(starts) == 1 and not endz)
    finally:
        if proc.poll() is None:
            proc.kill()
            proc.wait()
    p = run_direct(kb, kwork, "--frozen", "K=/tmp")
    try:
        summary3 = json.loads(p.stdout)
    except ValueError:
        summary3 = {}
    st.check("run/kill_resume_reran",
             p.returncode == 0
             and summary3.get("steps_run") == ["slow"]
             and summary3.get("touches_used") == 2, p.stderr[-200:])
    # Bad manifest rejected pre-touch.
    bad = tmp / "synb-bad"
    shutil.copytree(bundle, bad)
    badman = json.loads((bad / "MANIFEST.json").read_text())
    badman["steps"][0]["env_extra"] = ["NOT-A-DICT"]
    (bad / "MANIFEST.json").write_text(json.dumps(badman))
    badwork = tmp / "badwork"
    p = run_direct(bad, badwork, "--frozen", "K=/tmp")
    st.check("run/bad_env_rejected_0touch",
             p.returncode == 1
             and not (badwork / "touches.json").exists())


def t_killwatch(st: Selftest, tmp: Path) -> None:
    sched = tmp / "sched.py"
    sched.write_text(
        "import json, sys, time\ntime.sleep(float(sys.argv[2]))\n"
        "open(sys.argv[1], 'a').write(json.dumps(\n"
        "    {'event': 'attempt_start', 'step': sys.argv[3]}) + chr(10))\n")
    procs: list[subprocess.Popen] = []

    def victim(secs):
        p = subprocess.Popen(["sleep", str(secs)],
                             start_new_session=True)
        procs.append(p)
        return p

    try:
        kw = tmp / "kw1"
        kw.mkdir()
        log = kw / "direct-ledger.jsonl"
        v = victim(30)
        procs.append(subprocess.Popen(
            [sys.executable, str(sched), str(log), "2", "slow"]))
        ns = argparse.Namespace(
            pgid=v.pid, signal=f"runlog:{log}:slow", delay=3,
            window=(1, 10), log=str(kw / "watch.json"), poll=0.2,
            signal_timeout=60)
        rc = cmd_killwatch(ns)
        rec = json.loads((kw / "watch.json").read_text())
        try:
            v.wait(timeout=10)
        except subprocess.TimeoutExpired:
            pass
        st.check("kw/in_window_rc0",
                 rc == 0 and rec["in_window"] is True
                 and v.returncode == -signal.SIGKILL)
        st.check("kw/delay_close",
                 abs(rec["actual_delay_s"] - 3) < 2.0)
        kw2 = tmp / "kw2"
        kw2.mkdir()
        log2 = kw2 / "direct-ledger.jsonl"
        v2 = victim(30)
        procs.append(subprocess.Popen(
            [sys.executable, str(sched), str(log2), "0.5", "slow"]))
        ns2 = argparse.Namespace(
            pgid=v2.pid, signal=f"runlog:{log2}:slow", delay=0.5,
            window=(5, 10), log=str(kw2 / "watch.json"), poll=0.2,
            signal_timeout=60)
        rc2 = cmd_killwatch(ns2)
        rec2 = json.loads((kw2 / "watch.json").read_text())
        try:
            v2.wait(timeout=10)
        except subprocess.TimeoutExpired:
            pass
        st.check("kw/out_of_window_rc2",
                 rc2 == 2 and rec2["in_window"] is False
                 and v2.returncode == -signal.SIGKILL)
        kw3 = tmp / "kw3"
        kw3.mkdir()
        log3 = kw3 / "direct-ledger.jsonl"
        log3.write_text('{"event": "attempt_start", "step": "s"}\n')
        v3 = victim(30)
        ns3 = argparse.Namespace(
            pgid=v3.pid, signal=f"runlog:{log3}:s", delay=1,
            window=(0, 9), log=str(kw3 / "watch.json"), poll=0.2,
            signal_timeout=60)
        try:
            cmd_killwatch(ns3)
            already = False
        except HarnessError as exc:
            already = "already started" in str(exc)
        st.check("kw/already_started_errors", already)
        v4 = victim(1)
        ns4 = argparse.Namespace(
            pgid=v4.pid,
            signal=f"runlog:{tmp}/kw4never:slow", delay=1,
            window=(0, 9), log=str(tmp / "kw4.json"), poll=0.2,
            signal_timeout=30)
        t0 = time.monotonic()
        try:
            cmd_killwatch(ns4)
            died = False
        except HarnessError as exc:
            died = "died before" in str(exc)
        st.check("kw/victim_dies_fast",
                 died and time.monotonic() - t0 < 15)
    finally:
        for p in procs:
            try:
                if p.poll() is None:
                    p.kill()
                p.wait(timeout=10)
            except Exception:  # noqa: BLE001 — cleanup best effort
                pass


def t_blind(st: Selftest, tmp: Path) -> None:
    h = HERE / "battery-bytes" / "host-art" / "compat" / \
        "COMPAT-REPORT.json"
    d = HERE / "battery-bytes" / "direct-art" / "compat" / \
        "COMPAT-REPORT.json"
    out = tmp / "blind"
    ns = argparse.Namespace(
        leg="clean", h_compat=str(h), d_compat=str(d),
        h_report=str(S005 / "runs" / "note1-closure" / "artifacts" /
                     "host" / "package" / "RELCHECK-REPORT.json"),
        d_report=str(S005 / "runs" / "note1-closure" / "artifacts" /
                     "direct" / "package" / "RELCHECK-REPORT.json"),
        upins=str(UPINS_BASE),
        run_roots="/tmp/note1-ready,/tmp/note1-ready-direct",
        out_dir=str(out))
    st.check("blind/rc0", cmd_blind(ns) == 0)
    m = json.loads((out / "MAPPING.sealed.json").read_text())
    x = json.loads((out / "X.json").read_text())
    hj = json.loads(h.read_text())
    dj = json.loads(d.read_text())
    want_x = hj if m["x_arm"] == "H" else dj
    st.check("blind/mapping_consistent",
             x == want_x and m["x_arm"] != m["y_arm"]
             and (out / "PURPOSE.txt").is_file())
    st.check("blind/noop_witness",
             {m["x_sha256"], m["y_sha256"]}
             == {m["h_sha256"], m["d_sha256"]})


def t_freeze(st: Selftest, tmp: Path) -> None:
    upins = json.loads(UPINS_BASE.read_text())
    res = freeze_check(upins)
    st.check("freeze/all_ok", all(r["ok"] for r in res.values()))
    st.check("freeze/mixed_mechanics",
             all("maps_ok" in r for r in res.values())
             and all("file_ok" in r for t, r in res.items()
                     if t in S_TAGS))
    tam = tmp / "fz-tamper"
    shutil.copytree(upins["frozen"]["r2"], tam / "r2")
    first = next(f for f in sorted(upins["identity"]["r2"])
                 if (tam / "r2" / f).stat().st_size > 0)
    fp = tam / "r2" / first
    raw = bytearray(fp.read_bytes())
    raw[0] ^= 0x01
    fp.write_bytes(bytes(raw))
    up2 = json.loads(UPINS_BASE.read_text())
    up2["frozen"]["r2"] = str(tam / "r2")
    res2 = freeze_check(up2)
    st.check("freeze/tamper_detected",
             res2["r2"]["ok"] is False
             and "mismatch" in res2["r2"]["maps_detail"])
    tam3 = tmp / "fz-extra"
    shutil.copytree(upins["frozen"]["r2"], tam3 / "r2")
    (tam3 / "r2" / "UNPINNED.txt").write_text("extra\n")
    up3 = json.loads(UPINS_BASE.read_text())
    up3["frozen"]["r2"] = str(tam3 / "r2")
    res3 = freeze_check(up3)
    st.check("freeze/extras_detected",
             res3["r2"]["ok"] is False
             and "extras" in res3["r2"]["maps_detail"])


def t_bundle(st: Selftest) -> None:
    upins = json.loads(UPINS_BASE.read_text())
    bundle = S005 / "vehicle" / "relcheck"
    manifest = json.loads((bundle / "MANIFEST.json").read_text())
    ok, detail = bundle_posthash(bundle, manifest,
                                 upins["bundle_sha256"])
    st.check("bundle/posthash_match", ok, detail)


def synth_envelope(root: Path, tamper: str | None = None,
                   with_vehicle: bool = False,
                   shape: str = "add") -> Path:
    """Synthetic C6 envelope from base bytes (never touches sealed/).

    shape: "add" (new bin program + step + output + target) |
    "modify" (relcheck byte-flip + step + output + target).
    tamper: None | "nosha" (manifest omits bundle sha) | "bind"
    (MANIFEST edited post-seal) | "fileadd" (orphan 4th file: added
    bin file no step argv-references).
    """
    base = S005 / "vehicle" / "relcheck"
    sealed = root
    rb = sealed / "revision-bundle"
    shutil.copytree(base, rb, ignore=shutil.ignore_patterns(
        "__pycache__"))
    man = json.loads((rb / "MANIFEST.json").read_text())
    if shape == "add":
        (rb / "bin" / "synth_assay.py").write_text("# synthetic\n")
        man["files"]["bin/synth_assay.py"] = sha_file(
            rb / "bin" / "synth_assay.py")
        assay_argv = ["python3", "inputs/synth_assay.py"]
    else:
        rel = rb / "bin" / "relcheck.py"
        raw = bytearray(rel.read_bytes())
        raw[10] ^= 0x01
        rel.write_bytes(bytes(raw))
        man["files"]["bin/relcheck.py"] = sha_file(rel)
        assay_argv = ["python3", "inputs/relcheck.py", "--step",
                      "assay"]
    man["steps"].append(
        {"step": "assay", "argv": assay_argv,
         "declared_outputs": ["ASSAY.json"], "timeout_s": 600})
    inpins = json.loads((rb / "pins.json").read_text())
    inpins["steps"].append("assay")
    inpins["artifacts"]["assay"] = ["ASSAY.json"]
    inpins["suites"]["r1"]["programs"].append(
        {"kind": "demo", "file": "synth_demo.py",
         "log": "SUITE-R1-demo.log"})
    (rb / "pins.json").write_text(json.dumps(inpins, indent=2))
    man["files"]["pins.json"] = sha_file(rb / "pins.json")
    if tamper == "fileadd":
        (rb / "bin" / "extra.py").write_text("# extra\n")
        man["files"]["bin/extra.py"] = sha_file(rb / "bin" / "extra.py")
    (rb / "MANIFEST.json").write_text(json.dumps(man, indent=2))
    sys.path.insert(0, str(S005))
    from procedure import canonical_manifest_bytes
    rb_sha = hashlib.sha256(
        canonical_manifest_bytes(man)).hexdigest()
    envelop: dict = {"synthetic": True,
                     "revised_bundle_sha256": rb_sha}
    if with_vehicle:
        upins = json.loads(UPINS_BASE.read_text())
        veh = {k: upins[k] for k in upins if k not in (
            "u_execute", "provenance")}
        veh["steps"] = [s["step"] for s in man["steps"]]
        veh["argv"] = {s["step"]: s["argv"] for s in man["steps"]}
        veh["suites"] = inpins["suites"]
        veh["artifacts"] = inpins["artifacts"]
        veh["bundle_sha256"] = rb_sha
        veh["bin_relcheck_sha256"] = sha_file(rb / "bin" / "relcheck.py")
        veh["pins_sha256"] = sha_file(rb / "pins.json")
        (rb / "relcheck-pins.json").write_text(json.dumps(veh))
    if tamper == "nosha":
        del envelop["revised_bundle_sha256"]
    (sealed / "REVISION-MANIFEST.json").write_text(
        json.dumps(envelop, indent=2))
    if tamper == "bind":
        (rb / "MANIFEST.json").write_text(
            (rb / "MANIFEST.json").read_text().replace(
                '"assay"', '"assayX"', 1))
    return sealed


def t_derive(st: Selftest, tmp: Path) -> None:
    base_upins = UPINS_BASE
    base_bundle = S005 / "vehicle" / "relcheck"

    def run(sealed, tag):
        out = tmp / f"{tag}.pins.json"
        tr = tmp / f"{tag}.transcript.json"
        ns = argparse.Namespace(
            sealed=str(sealed), base_upins=str(base_upins),
            base_bundle=str(base_bundle), out=str(out),
            transcript=str(tr))
        return cmd_derive(ns), out, tr

    want_steps = ["identity", "suite-r1", "suite-r2", "suite-r3",
                  "compat", "package", "assay"]
    rc, out, _ = run(synth_envelope(tmp / "syn-goodadd"), "goodadd")
    doc = json.loads(out.read_text()) if out.is_file() else {}
    st.check("derive/graft_add_ok",
             rc == 0 and doc.get("steps") == want_steps)
    rc, out, _ = run(synth_envelope(tmp / "syn-goodmodify",
                                    shape="modify"), "goodmodify")
    doc = json.loads(out.read_text()) if out.is_file() else {}
    st.check("derive/graft_modify_ok",
             rc == 0 and doc.get("steps") == want_steps)
    rc, _, _ = run(synth_envelope(tmp / "syn-nosha", "nosha"),
                   "nosha")
    st.check("derive/nosha_void", rc == 2)
    rc, _, _ = run(synth_envelope(tmp / "syn-bind", "bind"), "bind")
    st.check("derive/bind_void", rc == 2)
    rc, _, tr = run(synth_envelope(tmp / "syn-fileadd", "fileadd",
                                   shape="modify"), "fileadd")
    trd = json.loads(tr.read_text()) if tr.is_file() else {}
    st.check("derive/orphan_file_void",
             rc == 2 and "argv-referenced" in trd.get("reason", ""))
    rc, out5, tr5 = run(synth_envelope(
        tmp / "syn-veh", with_vehicle=True, shape="modify"), "veh")
    tr = json.loads(tr5.read_text()) if tr5.is_file() else {}
    st.check("derive/envelope_copy_ok",
             rc == 0 and any("envelope copy" in n
                             for n in tr.get("notes", [])))


def cmd_selftest(args) -> int:
    """Full harness selftest (synthetic + closure bytes; 0 vehicle
    execution; never reads sealed/). Transcript = stdout."""
    tmp = Path("/tmp/uh-selftest")
    shutil.rmtree(tmp, ignore_errors=True)
    tmp.mkdir(parents=True)
    st = Selftest()
    print("== predicates ==", flush=True)
    t_predicates(st)
    print("== d-confinement ==", flush=True)
    t_dconfinement(st, tmp)
    print("== runner ==", flush=True)
    t_runner(st, tmp)
    print("== kill-watch ==", flush=True)
    t_killwatch(st, tmp)
    print("== blind ==", flush=True)
    t_blind(st, tmp)
    print("== freeze+bundle ==", flush=True)
    t_freeze(st, tmp)
    t_bundle(st)
    print("== derive ==", flush=True)
    t_derive(st, tmp)
    print("---", flush=True)
    if st.fails:
        print(f"SELFTEST FAIL: {len(st.fails)}: {st.fails}")
        return 1
    print("SELFTEST PASS: all expectations met")
    return 0


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(prog="u-harness.py")
    sub = p.add_subparsers(dest="cmd", required=True)
    q = sub.add_parser("kill-watch")
    q.add_argument("--pgid", type=int, required=True)
    q.add_argument("--signal", required=True)
    q.add_argument("--delay", type=float, required=True)
    q.add_argument("--window", nargs=2, type=float, required=True)
    q.add_argument("--log", required=True)
    q.add_argument("--poll", type=float, default=0.5)
    q.add_argument("--signal-timeout", type=float, default=1800.0)
    q = sub.add_parser("eval-leg")
    q.add_argument("--arm", choices=["H", "D"], required=True)
    q.add_argument("--leg", choices=["clean", "change", "kill"],
                   required=True)
    q.add_argument("--out", required=True)
    q.add_argument("--checker", default=None)
    q.add_argument("--pins", required=True)
    q.add_argument("--venv-py", required=True)
    q.add_argument("--freeze-pre", required=True)
    q.add_argument("--rubric-scores", default="null")
    q.add_argument("--state-dir", default=None)
    q.add_argument("--world", default=None)
    q.add_argument("--procedure", default=None)
    q.add_argument("--key", default=None)
    q.add_argument("--key-new", default=None)
    q.add_argument("--worlds", default=None)
    q.add_argument("--touch-count", type=int, default=None)
    q.add_argument("--touch-log", default=None)
    q.add_argument("--inspect-json", default=None)
    q.add_argument("--work", default=None)
    q.add_argument("--bundle", default=None)
    q = sub.add_parser("eval-u")
    q.add_argument("--verdicts", nargs=6, required=True)
    q.add_argument("--out", required=True)
    q.add_argument("--allow-provisional", action="store_true")
    q = sub.add_parser("blind-present")
    q.add_argument("--leg", required=True)
    q.add_argument("--h-compat", required=True)
    q.add_argument("--d-compat", required=True)
    q.add_argument("--h-report", required=True)
    q.add_argument("--d-report", required=True)
    q.add_argument("--upins", required=True)
    q.add_argument("--run-roots", required=True)
    q.add_argument("--out-dir", required=True)
    q = sub.add_parser("derive-revised-pins")
    q.add_argument("--sealed", required=True)
    q.add_argument("--base-upins", required=True)
    q.add_argument("--base-bundle", required=True)
    q.add_argument("--out", required=True)
    q.add_argument("--transcript", required=True)
    q = sub.add_parser("freeze-check")
    q.add_argument("--upins", required=True)
    q.add_argument("--out", required=True)
    sub.add_parser("selftest")
    return p


def main(argv=None) -> int:
    args = build_parser().parse_args(argv)
    try:
        if args.cmd == "kill-watch":
            return cmd_killwatch(args)
        if args.cmd == "eval-leg":
            return cmd_eval(args)
        if args.cmd == "eval-u":
            return cmd_evalu(args)
        if args.cmd == "blind-present":
            return cmd_blind(args)
        if args.cmd == "derive-revised-pins":
            return cmd_derive(args)
        if args.cmd == "freeze-check":
            return cmd_freeze(args)
        if args.cmd == "selftest":
            return cmd_selftest(args)
    except HarnessError as exc:
        print(f"U-HARNESS-ERROR: {exc}", file=sys.stderr)
        return 1
    raise AssertionError("unreachable")


if __name__ == "__main__":
    sys.exit(main())

