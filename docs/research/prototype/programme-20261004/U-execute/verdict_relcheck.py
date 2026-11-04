"""Independent relcheck artifact checker (successor-005 BUILT contract).

Contract:
    verdict_relcheck.py <report> <ledger> <artifacts> <pins>
    verdict_relcheck.py <report> --no-ledger --stamps DIR <artifacts> <pins>
prints exactly one line, ``RELCHECK-VALID`` (exit 0) or
``RELCHECK-INVALID: <reason>`` (exit 1). Stdout carries ONLY that line;
diagnostics go to stderr. Any internal failure (missing file, malformed
JSON, recomputation error) is INVALID with a reason, never a traceback
on stdout.

It MUST NOT trust the report. It recomputes identity hashes from frozen
bytes, reparses suite logs from hash-verified bytes, recomputes surface
sets from AST over frozen bytes, and cross-checks every claim against
the ledger (host lane) or the run log + step RESULT stamps (direct lane).

Layout notes (derived from the built bundle, not the draft):
  * <artifacts> is the proc-<key> dir itself: step outputs live at
    <artifacts>/<step>/<relpath> (host: .../proc-<key>/<step>;
    direct: .../artifacts/<step>).
  * --stamps DIR holds per-step <step>-RESULT.json files, either directly
    under DIR or under DIR/steps/; an optional DIR/direct-ledger.jsonl
    run log adds argv/input binding when present.
  * Kill-shape evidence: an unmatched begin's attempt dir is
    <artifacts>/<step>/attempt-<N>/ (N from the begin invoke_id's -aN
    suffix); it must lack DONE.json for the kill to pass as pre-DONE.
"""
from __future__ import annotations

import argparse
import ast
import hashlib
import json
import os
import re
import sys
from pathlib import Path

# Base step floor (the built bundle). The live universe is pins-driven:
# bind_step_universe() rebinds ALL_STEPS from pins["steps"] once per
# run (change legs add steps; pins can never drop a base step).
BASE_STEPS = ("identity", "suite-r1", "suite-r2", "suite-r3", "compat",
              "package")
ALL_STEPS = BASE_STEPS
SUITE_STEPS = ("suite-r1", "suite-r2", "suite-r3")
SUITE_TAGS = ("r1", "r2", "r3")
REPORT_KEYS = ("artifacts", "bundle_sha256", "compat", "mode", "nonce",
               "pins_sha256", "run_id", "vehicle", "vehicle_version",
               "verdict")
COMPAT_KEYS = ("identities", "pins_sha256", "suites", "surface", "verdict")
EXPECTED_INPUTS = ("params.json", "pins.json", "relcheck.py")

_RAN_RE = re.compile(r"^Ran (\d+) tests? in ", re.M)
_STATUS_RE = re.compile(r"^(OK|FAILED)(?: \(([^)]*)\))?\s*$", re.M)
_SKIP_PAREN_RE = re.compile(r"skipped=(\d+)")
_SKIP_VERBOSE_RE = re.compile(r"\.\.\. skipped[ :'\"]")


class Invalid(Exception):
    """Any check failure funnels through here -> one INVALID line."""


def _sha256_bytes(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


def _sha256_file(fp: Path) -> str:
    return _sha256_bytes(fp.read_bytes())


def _load_json(fp: Path, what: str) -> dict:
    try:
        data = json.loads(fp.read_text(encoding="utf-8"))
    except FileNotFoundError:
        raise Invalid(f"{what} missing: {fp}")
    except (json.JSONDecodeError, UnicodeDecodeError) as exc:
        raise Invalid(f"{what} malformed ({fp}): {exc}")
    if not isinstance(data, dict):
        raise Invalid(f"{what} ({fp}) is not a JSON object")
    return data


def _ledger_entries(ledger: Path) -> list[dict]:
    try:
        text = ledger.read_text(encoding="utf-8")
    except FileNotFoundError:
        raise Invalid(f"ledger missing: {ledger}")
    out = []
    for lineno, line in enumerate(text.splitlines(), 1):
        if not line.strip():
            continue
        try:
            entry = json.loads(line)
        except json.JSONDecodeError as exc:
            raise Invalid(f"ledger line {lineno} malformed: {exc}")
        if not isinstance(entry, dict):
            raise Invalid(f"ledger line {lineno} is not an object")
        out.append(entry)
    return out


def _argv_sha256(argv: list) -> str:
    # procedure.py: sha256 over json.dumps(argv, sort_keys=True) with
    # default separators.
    return _sha256_bytes(json.dumps(argv, sort_keys=True).encode())


# ---------------------------------------------------------------- schema

def check_envelope_schema(report: dict, pins: dict) -> dict:
    """Envelope + compat schema (report top level + compat block)."""
    for key in REPORT_KEYS:
        if key not in report:
            raise Invalid(f"report schema: missing key {key!r}")
    if report["verdict"] not in ("ACCEPT", "PARTIAL", "FAIL"):
        raise Invalid("report schema: verdict not ACCEPT/PARTIAL/FAIL")
    if report.get("vehicle") != "relcheck":
        raise Invalid("report schema: vehicle != 'relcheck'")
    if report.get("vehicle_version") != 1:
        raise Invalid("report schema: vehicle_version != 1")
    if report.get("mode") not in ("host", "direct"):
        raise Invalid("report schema: mode not host/direct")
    for key in ("nonce", "run_id"):
        if not isinstance(report.get(key), str) or not report[key]:
            raise Invalid(f"report schema: {key!r} not a nonempty string")
    if not isinstance(report.get("artifacts"), list):
        raise Invalid("report schema: artifacts not a list")
    for entry in report["artifacts"]:
        if not isinstance(entry, dict):
            raise Invalid("report schema: artifacts entry not a map")
        for key in ("step", "relpath", "bytes", "sha256"):
            if key not in entry:
                raise Invalid("report schema: artifacts entry "
                              f"missing {key!r}")
    compat = report.get("compat")
    if not isinstance(compat, dict):
        raise Invalid("report schema: compat not a map")
    for key in COMPAT_KEYS:
        if key not in compat:
            raise Invalid(f"report schema: compat missing key {key!r}")
    if compat["verdict"] not in ("ACCEPT", "PARTIAL", "FAIL"):
        raise Invalid("report schema: compat.verdict not "
                      "ACCEPT/PARTIAL/FAIL")
    if set(compat.get("identities", {})) != set(pins["identity"]):
        raise Invalid("report schema: compat.identities tags != pins tags")
    if set(compat.get("suites", {})) != set(pins["suites"]):
        raise Invalid("report schema: compat.suites tags != pins suites")
    if set(compat.get("surface", {})) != set(pins["surface_min"]):
        raise Invalid("report schema: compat.surface tags != pins tags")
    return report


def check_pins_schema(pins: dict) -> dict:
    for key in ("argv", "artifacts", "bin_relcheck_sha256",
                "bundle_sha256", "demo_marker", "frozen", "identity",
                "ignore_top", "pins_format", "pins_sha256", "steps",
                "suites", "surface_min", "surface_trees"):
        if key not in pins:
            raise Invalid(f"pins schema: missing key {key!r}")
    if pins["pins_format"] != 1:
        raise Invalid("pins schema: pins_format != 1")
    return pins


def bind_step_universe(pins: dict) -> None:
    """Rebind ALL_STEPS from pins["steps"] (both lanes call this once).

    The universe must be a duplicate-free list of non-empty strings
    covering every BASE_STEPS member, with per-step argv + artifacts
    pins present (fail closed: a pins file that drops a base step or
    starves a step of argv/artifacts can neither shrink nor smuggle
    the checked universe).
    """
    global ALL_STEPS
    steps = pins["steps"]
    if not isinstance(steps, list) or not steps \
            or any(not isinstance(s, str) or not s for s in steps) \
            or len(set(steps)) != len(steps):
        raise Invalid("pins schema: steps malformed")
    if not set(steps) >= set(BASE_STEPS):
        raise Invalid("pins schema: steps must cover the base step list")
    for step in steps:
        if step not in pins["argv"]:
            raise Invalid(f"pins schema: argv lacks step {step!r}")
        if step not in pins["artifacts"]:
            raise Invalid(f"pins schema: artifacts lacks step {step!r}")
    ALL_STEPS = tuple(steps)


def check_bundle_binding(report: dict, pins: dict) -> None:
    if report["bundle_sha256"] != pins["bundle_sha256"]:
        raise Invalid("bundle mismatch: report bundle_sha256 != pins")
    if report["pins_sha256"] != pins["pins_sha256"]:
        raise Invalid("pins mismatch: report pins_sha256 != pins")
    if report["compat"]["pins_sha256"] != pins["pins_sha256"]:
        raise Invalid("pins mismatch: compat pins_sha256 != pins")


# ------------------------------------------------------------- identity

def _scan_tree(root: Path, pinned: dict[str, str],
               ignore_top: set[str], tag: str) -> None:
    """Recompute every pinned hash; flag extras and symlinks."""
    if not root.is_dir():
        raise Invalid(f"identity {tag}: frozen root missing: {root}")
    for relpath, want in sorted(pinned.items()):
        fp = root / relpath
        if fp.is_symlink() or not fp.exists():
            if fp.is_symlink():
                raise Invalid(f"identity {tag}: pinned path is a "
                              f"symlink: {relpath}")
            raise Invalid(f"identity {tag}: pinned file gone: {relpath}")
        if not fp.is_file():
            raise Invalid(f"identity {tag}: pinned path not a file: "
                          f"{relpath}")
        got = _sha256_file(fp)
        if got != want:
            raise Invalid(f"identity {tag}: frozen bytes mismatch: "
                          f"{relpath}")
    extras: list[str] = []
    symlinks: list[str] = []
    for dirpath, dirnames, filenames in os.walk(root, followlinks=False):
        here = Path(dirpath)
        if here == root:
            dirnames[:] = [d for d in dirnames if d not in ignore_top]
        for name in dirnames:
            if (here / name).is_symlink():
                symlinks.append(str(Path(
                    os.path.relpath(here / name, root))))
        for name in filenames:
            fp = here / name
            rel = str(Path(os.path.relpath(fp, root)))
            if rel.split(os.sep)[0] in ignore_top:
                continue
            if fp.is_symlink():
                symlinks.append(rel)
            elif rel not in pinned:
                extras.append(rel)
    if symlinks:
        raise Invalid(f"identity {tag}: symlinks under frozen root: "
                      f"{sorted(symlinks)[:5]}")
    if extras:
        raise Invalid(f"identity {tag}: extras beyond pins: "
                      f"{sorted(extras)[:5]}")


def freeze_verify_roots(pins: dict) -> dict[str, str | None]:
    """A-FROZEN standalone: recompute every pinned identity hash +
    extras/symlink scan per tag (no report needed). Returns
    {tag: None-if-ok else error}. Used by u-harness freeze-check."""
    ignore_top = set(pins["ignore_top"])
    out: dict[str, str | None] = {}
    for tag, pinned in sorted(pins["identity"].items()):
        try:
            _scan_tree(Path(pins["frozen"][tag]), pinned, ignore_top,
                       tag)
        except Invalid as exc:
            out[tag] = str(exc)
        except OSError as exc:
            out[tag] = f"unreadable: {exc}"
        else:
            out[tag] = None
    return out


def check_identities(report: dict, pins: dict) -> None:
    """Recompute 6-tag identity from frozen bytes + extras/symlink scan."""
    ignore_top = set(pins["ignore_top"])
    compat_ids = report["compat"]["identities"]
    for tag, pinned in sorted(pins["identity"].items()):
        _scan_tree(Path(pins["frozen"][tag]), pinned, ignore_top, tag)
        claim = compat_ids.get(tag, {})
        if claim.get("match") is not True:
            raise Invalid(f"identity {tag}: recomputed MATCH but compat "
                          f"claims match={claim.get('match')!r}")
        if claim.get("files") != len(pinned):
            raise Invalid(f"identity {tag}: compat files={claim.get('files')} "
                          f"vs {len(pinned)} pinned")


# ---------------------------------------------------------------- ledger

def _success_invokes(entries: list[dict]) -> list[dict]:
    """All success proc.exec invokes (design 7.6 filter)."""
    out = []
    for entry in entries:
        if entry.get("kind") != "invoke":
            continue
        pay = entry.get("payload", {})
        if not isinstance(pay, dict):
            continue
        if pay.get("capability") != "proc.exec" or "error" in pay:
            continue
        if "result_ref" not in pay:
            continue
        proc = pay.get("proc", {})
        if not isinstance(proc, dict):
            continue
        out.append(pay)
    return out


def _begins(entries: list[dict]) -> list[dict]:
    out = []
    for entry in entries:
        if entry.get("kind") != "proc_begin":
            continue
        pay = entry.get("payload", {})
        if isinstance(pay, dict):
            out.append(pay)
    return out


def _attempt_no(invoke_id: str, step: str) -> int:
    match = re.search(r"-a(\d+)$", invoke_id)
    if not match:
        raise Invalid(f"ledger: {step}: invoke_id {invoke_id!r} lacks "
                      "-aN attempt suffix")
    return int(match.group(1))


def check_ledger_binding(report: dict, entries: list[dict], pins: dict,
                         artifacts: Path) -> dict[str, list[dict]]:
    """Bind ledger to pins: create/deny/pairing/argv/inputs/exit codes."""
    for entry in entries:
        if entry.get("kind") == "deny":
            raise Invalid("ledger: deny entry present")
    creates = [e for e in entries if e.get("kind") == "create"]
    if len(creates) != 1:
        raise Invalid(f"ledger: expected exactly 1 create, "
                      f"found {len(creates)}")
    procedures = creates[0].get("payload", {}).get("procedures", [])
    if not any(isinstance(t, dict)
               and t.get("bundle_sha256") == pins["bundle_sha256"]
               for t in procedures):
        raise Invalid("ledger: create binds no procedure table entry to "
                      "the pinned bundle")
    begins = _begins(entries)
    if not begins:
        raise Invalid("ledger: no proc_begin entries")
    keys = {b.get("idem_key") for b in begins}
    if len(keys) != 1 or None in keys:
        raise Invalid("ledger: proc_begin entries span "
                      f"{sorted(map(str, keys))}, want one idem key")
    key = next(iter(keys))
    for b in begins:
        if b.get("step") not in ALL_STEPS:
            raise Invalid(f"ledger: proc_begin names unknown step "
                          f"{b.get('step')!r}")
    invokes = [p for p in _success_invokes(entries)
               if p.get("proc", {}).get("idem_key") == key]
    for pay in invokes:
        if pay.get("proc", {}).get("step") not in ALL_STEPS:
            raise Invalid(f"ledger: invoke names unknown step "
                          f"{pay.get('proc', {}).get('step')!r}")
    by_step_inv: dict[str, list[dict]] = {}
    for pay in invokes:
        step = pay["proc"]["step"]
        bundle = pay["proc"].get("bundle_sha256")
        if bundle != pins["bundle_sha256"]:
            raise Invalid(f"ledger: {step}: invoke bundle {bundle} != pins")
        if pay["proc"].get("exit_code") != 0:
            raise Invalid(f"ledger: {step}: exit_code="
                          f"{pay['proc'].get('exit_code')}, want 0")
        if pay["proc"].get("timed_out") is not False:
            raise Invalid(f"ledger: {step}: timed_out is not false")
        # recovered is history metadata, not a verdict input: an honest
        # L3 adopt (kill lands between DONE and the invoke row) emits a
        # success invoke with recovered:true, while a pre-DONE kill plus
        # re-run emits a fresh invoke with recovered:false. Both shapes
        # are honest; the consistency axes above and below carry the
        # verdict. Kill attestation comes from experiment evidence
        # (harness log + ledger attempt counts), never this flag.
        by_step_inv.setdefault(step, []).append(pay)
    for step in ALL_STEPS:
        step_begins = [b for b in begins if b.get("step") == step]
        step_invokes = by_step_inv.get(step, [])
        if not step_begins:
            raise Invalid(f"ledger: step {step}: no proc_begin under key")
        if not step_invokes:
            raise Invalid(f"ledger: step {step}: no success invoke "
                          "under key")
        for b in step_begins:
            want_argv = _argv_sha256(pins["argv"][step])
            if b.get("argv_sha256") != want_argv:
                raise Invalid(f"ledger: {step}: argv_sha256 skew vs pins")
            inputs = b.get("input_hashes", {})
            if step in BASE_STEPS:
                if set(inputs) != set(EXPECTED_INPUTS):
                    raise Invalid(
                        f"ledger: {step}: input_hashes keys "
                        f"{sorted(inputs)} != pinned set")
            elif not {"params.json", "pins.json"} <= set(inputs):
                # Non-base (revised-universe) step inputs: subset rule
                # per RULES-AMENDMENT-2(f) — S5-DESIGN §3 asserts the
                # checker is content-agnostic within schema.
                # params/pins are always staged; extra program inputs
                # (a new step's own program) are advertise-bound via
                # bundle files[] re-hash but carry no pins value —
                # documented, same class as params.json
                # presence-only.
                raise Invalid(f"ledger: {step}: input_hashes lack "
                              f"params/pins: {sorted(inputs)}")
            if inputs.get("pins.json") != pins["pins_sha256"]:
                raise Invalid(f"ledger: {step}: input pins.json != "
                              "pins_sha256")
            if (step in BASE_STEPS or "relcheck.py" in inputs) \
                    and inputs.get("relcheck.py") != pins[
                        "bin_relcheck_sha256"]:
                raise Invalid(f"ledger: {step}: input relcheck.py != "
                              "pinned bin sha")
        begin_ids = [b.get("invoke_id") for b in step_begins]
        if len(set(begin_ids)) != len(begin_ids):
            raise Invalid(f"ledger: step {step}: duplicate begin "
                          "invoke_id")
        # Kill shape: every invoke matches a DISTINCT begin; every
        # unmatched begin must be a pre-DONE kill (no DONE.json in its
        # attempt dir under the artifacts operand).
        matched: set[str] = set()
        for pay in step_invokes:
            iid = pay.get("invoke_id")
            if iid not in begin_ids:
                raise Invalid(f"ledger: step {step}: invoke {iid!r} "
                              "matches no proc_begin")
            if iid in matched:
                raise Invalid(f"ledger: step {step}: two invokes match "
                              f"begin {iid!r}")
            matched.add(iid)
        for b in step_begins:
            if b.get("invoke_id") in matched:
                continue
            attempt = _attempt_no(str(b.get("invoke_id")), step)
            done = artifacts / step / f"attempt-{attempt}" / "DONE.json"
            if done.exists():
                raise Invalid(f"ledger: step {step}: unmatched begin "
                              f"{b.get('invoke_id')!r} has DONE.json "
                              "(completed work without an invoke)")
    return by_step_inv


def _verify_artifact_file(step: str, relpath: str, want_sha: str,
                          want_bytes: int | None, artifacts: Path) -> Path:
    fp = artifacts / step / relpath
    if not fp.is_file() or fp.is_symlink():
        raise Invalid(f"artifacts: missing file: {step}/{relpath}")
    raw = fp.read_bytes()
    if want_bytes is not None and len(raw) != want_bytes:
        raise Invalid(f"artifacts: {step}/{relpath}: bytes {len(raw)} "
                      f"!= claimed {want_bytes}")
    if _sha256_bytes(raw) != want_sha:
        raise Invalid(f"artifacts: {step}/{relpath}: sha256 mismatch")
    return fp


def check_ledger_artifacts(by_step_inv: dict[str, list[dict]],
                           artifacts: Path, pins: dict) -> None:
    """Ledger artifact lists must equal pins; bytes must recompute."""
    for step in ALL_STEPS:
        want_names = set(pins["artifacts"][step])
        for pay in by_step_inv[step]:
            listed = pay.get("proc", {}).get("artifacts", [])
            got_names = {a.get("relpath") for a in listed}
            if got_names != want_names:
                raise Invalid(f"ledger: {step}: artifact set "
                              f"{sorted(map(str, got_names))} != pins "
                              f"{sorted(want_names)}")
            for art in listed:
                _verify_artifact_file(step, art["relpath"], art["sha256"],
                                      art.get("bytes"), artifacts)


def check_report_artifact_table(report: dict, artifacts: Path,
                                pins: dict) -> None:
    """Report's artifact table: bytes recompute; covers non-package pins."""
    seen: set[tuple[str, str]] = set()
    for entry in report["artifacts"]:
        step, relpath = entry["step"], entry["relpath"]
        if step not in ALL_STEPS or step == "package":
            raise Invalid(f"report: artifact table names step {step!r}")
        _verify_artifact_file(step, relpath, entry["sha256"],
                              entry.get("bytes"), artifacts)
        seen.add((step, relpath))
    want: set[tuple[str, str]] = set()
    for step in ALL_STEPS:
        if step == "package":
            continue
        for relpath in pins["artifacts"][step]:
            want.add((step, relpath))
    if seen != want:
        raise Invalid("report: artifact table does not cover exactly "
                      "the pinned non-package outputs")


def check_report_bytes_bound(report_path: Path, report: dict,
                             package_sha: str) -> None:
    """The report file bytes must hash to the package step's claim."""
    raw = report_path.read_bytes()
    if _sha256_bytes(raw) != package_sha:
        raise Invalid("report: file bytes do not hash to the package "
                      "step's RELCHECK-REPORT.json claim")
    if json.loads(raw) != report:
        raise Invalid("report: file bytes reparse mismatch")


# ----------------------------------------------------------------- suites

def _parse_unittest(log: bytes, step: str, log_name: str) -> tuple[int, int]:
    """Parse unittest grammar from verified log bytes -> (ran, skipped)."""
    try:
        text = log.decode("utf-8", errors="strict")
    except UnicodeDecodeError:
        raise Invalid(f"suites: {step}: {log_name} not UTF-8")
    ran = _RAN_RE.findall(text)
    if not ran:
        raise Invalid(f"suites: {step}: {log_name}: no 'Ran N tests' line")
    status = _STATUS_RE.findall(text)
    if not status:
        raise Invalid(f"suites: {step}: {log_name}: no OK/FAILED line")
    word, paren = status[-1]
    if word == "FAILED":
        raise Invalid(f"suites: {step}: {log_name}: unittest FAILED")
    paren_skipped = _SKIP_PAREN_RE.search(paren or "")
    if paren_skipped:
        skipped = int(paren_skipped.group(1))
    else:
        skipped = len(_SKIP_VERBOSE_RE.findall(text))
    return int(ran[-1]), skipped


def check_suites(report: dict, artifacts: Path, pins: dict) -> None:
    """Per-tag suites: layout, grammar, expects, summary/compat agreement."""
    compat_suites = report["compat"]["suites"]
    for num, tag in enumerate(SUITE_TAGS, 1):
        step = f"suite-{tag}"
        spec = pins["suites"][tag]
        summary_name = f"SUITE-R{num}.json"
        summary = _load_json(artifacts / step / summary_name,
                             f"suite summary {tag}")
        if summary.get("pins_sha256") != pins["pins_sha256"]:
            raise Invalid(f"suites: {tag}: summary pins_sha256 skew")
        if summary.get("suite") != tag or summary.get("tree") != spec["tree"]:
            raise Invalid(f"suites: {tag}: summary suite/tree skew")
        results = summary.get("results")
        if not isinstance(results, list):
            raise Invalid(f"suites: {tag}: summary results not a list")
        programs = spec["programs"]
        if {r.get("file") for r in results} != {p["file"] for p in programs}:
            raise Invalid(f"suites: {tag}: summary programs != pins")
        by_file = {r["file"]: r for r in results}
        compat_results = compat_suites[tag].get("results", [])
        compat_by_file = {r.get("file"): r for r in compat_results}
        for prog in programs:
            res = by_file[prog["file"]]
            if res.get("kind") != prog["kind"]:
                raise Invalid(f"suites: {tag}: {prog['file']}: kind skew")
            if res.get("log") != prog["log"]:
                raise Invalid(f"suites: {tag}: {prog['file']}: log skew")
            if res.get("rc") != 0:
                raise Invalid(f"suites: {tag}: {prog['file']}: rc="
                              f"{res.get('rc')}, want 0")
            if res.get("ok") is not True:
                raise Invalid(f"suites: {tag}: {prog['file']}: ok not true")
            log_fp = artifacts / step / prog["log"]
            if not log_fp.is_file() or log_fp.is_symlink():
                raise Invalid(f"suites: {tag}: log missing: {prog['log']}")
            raw = log_fp.read_bytes()
            if len(raw) != res.get("log_bytes"):
                raise Invalid(f"suites: {tag}: {prog['log']}: bytes skew")
            if _sha256_bytes(raw) != res.get("log_sha256"):
                raise Invalid(f"suites: {tag}: {prog['log']}: sha skew")
            if prog["kind"] == "unittest":
                if res.get("ran") != prog["expect_tests"]:
                    raise Invalid(f"suites: {tag}: {prog['file']}: ran="
                                  f"{res.get('ran')} vs expect "
                                  f"{prog['expect_tests']}")
                if res.get("skipped") != prog["expect_skipped"]:
                    raise Invalid(f"suites: {tag}: {prog['file']}: skipped="
                                  f"{res.get('skipped')} vs expect "
                                  f"{prog['expect_skipped']}")
                ran, skipped = _parse_unittest(raw, tag, prog["log"])
                if ran != prog["expect_tests"]:
                    raise Invalid(f"suites: {tag}: {prog['log']}: log Ran "
                                  f"{ran} vs expect {prog['expect_tests']}")
                if skipped != prog["expect_skipped"]:
                    raise Invalid(f"suites: {tag}: {prog['log']}: log "
                                  f"skipped {skipped} vs expect "
                                  f"{prog['expect_skipped']}")
            elif prog["kind"] == "demo":
                if res.get("marker_found") is not True:
                    raise Invalid(f"suites: {tag}: {prog['file']}: "
                                  "marker_found not true")
                if pins["demo_marker"].encode() not in raw:
                    raise Invalid(f"suites: {tag}: {prog['log']}: demo "
                                  "marker absent from log bytes")
            else:
                raise Invalid(f"suites: {tag}: {prog['file']}: unknown "
                              f"kind {prog['kind']!r}")
            # Summary <-> compat agreement on the shared claim fields.
            compat_res = compat_by_file.get(prog["file"])
            if compat_res is None:
                raise Invalid(f"suites: {tag}: {prog['file']}: missing "
                              "from compat")
            for field in ("ok", "rc"):
                if compat_res.get(field) != res.get(field):
                    raise Invalid(f"suites: {tag}: {prog['file']}: compat "
                                  f"{field} disagrees with summary")
            for field in ("ran", "skipped"):
                if compat_res.get(field) != res.get(field, None):
                    raise Invalid(f"suites: {tag}: {prog['file']}: compat "
                                  f"{field} disagrees with summary")
        if summary.get("ok") is not True:
            raise Invalid(f"suites: {tag}: summary ok not true")
        if compat_suites[tag].get("ok") is not True:
            raise Invalid(f"suites: {tag}: compat ok not true")
        if not isinstance(summary.get("ledger_kinds"), list):
            raise Invalid(f"suites: {tag}: summary ledger_kinds not a list")
        if compat_surface_ledger(report, tag) != summary["ledger_kinds"]:
            raise Invalid(f"suites: {tag}: compat ledger_kinds disagree "
                          "with summary")


def compat_surface_ledger(report: dict, tag: str) -> list:
    return report["compat"]["surface"][tag].get("ledger_kinds")


# ---------------------------------------------------------------- surface

def _api_functions(tree_root: Path, tag: str) -> list[str]:
    fp = tree_root / "api.py"
    if not fp.is_file() or fp.is_symlink():
        raise Invalid(f"surface {tag}: api.py missing under frozen tree")
    try:
        tree = ast.parse(fp.read_bytes())
    except SyntaxError as exc:
        raise Invalid(f"surface {tag}: api.py unparseable: {exc}")
    return sorted(n.name for n in tree.body
                  if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef)))


def _cli_verbs(tree_root: Path, tag: str) -> list[str]:
    fp = tree_root / "release.py"
    if not fp.is_file() or fp.is_symlink():
        raise Invalid(f"surface {tag}: release.py missing under frozen tree")
    try:
        tree = ast.parse(fp.read_bytes())
    except SyntaxError as exc:
        raise Invalid(f"surface {tag}: release.py unparseable: {exc}")
    verbs = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Call) \
                and getattr(node.func, "attr", "") == "add_parser" \
                and node.args \
                and isinstance(node.args[0], ast.Constant) \
                and isinstance(node.args[0].value, str):
            verbs.append(node.args[0].value)
    return sorted(verbs)


def check_surface(report: dict, pins: dict) -> None:
    """Recompute per-tag surface minima from AST over frozen bytes."""
    compat_surface = report["compat"]["surface"]
    for tag in SUITE_TAGS:
        tree_tag = pins["surface_trees"][tag]
        if pins["suites"][tag]["tree"] != tree_tag:
            raise Invalid(f"surface {tag}: pins suite tree vs "
                          "surface_trees skew")
        root = Path(pins["frozen"][tree_tag])
        if not root.is_dir():
            raise Invalid(f"surface {tag}: frozen root missing: {root}")
        claim = compat_surface[tag]
        if claim.get("tree") != tree_tag:
            raise Invalid(f"surface {tag}: compat tree skew")
        funcs = _api_functions(root, tag)
        verbs = _cli_verbs(root, tag)
        if sorted(claim.get("api_functions", [])) != funcs:
            raise Invalid(f"surface {tag}: compat api_functions differ "
                          "from AST recompute")
        if sorted(claim.get("cli_verbs", [])) != verbs:
            raise Invalid(f"surface {tag}: compat cli_verbs differ "
                          "from AST recompute")
        want_min = pins["surface_min"][tag]
        verbs_ok = set(want_min["cli_verbs"]) <= set(verbs)
        funcs_ok = set(want_min["api_functions"]) <= set(funcs)
        if not verbs_ok or not funcs_ok:
            raise Invalid(f"surface {tag}: recomputed surface misses "
                          "pinned minimum")
        if claim.get("verbs_ok") is not True \
                or claim.get("funcs_ok") is not True \
                or claim.get("minimum_ok") is not True:
            raise Invalid(f"surface {tag}: compat minimum flags not true")
        if claim.get("api_present") is not True \
                or claim.get("release_present") is not True:
            raise Invalid(f"surface {tag}: compat presence flags not true")


# ---------------------------------------------------------------- verdict

def check_verdict_rule(report: dict) -> None:
    """Relocation check + ACCEPT recompute (all axes already enforced)."""
    compat = report["compat"]
    if compat["verdict"] != report["verdict"]:
        raise Invalid(f"verdict: compat {compat['verdict']} != package "
                      f"{report['verdict']} (relocation skew)")
    if report["verdict"] != "ACCEPT":
        raise Invalid(f"verdict: report {report['verdict']}, all evidence "
                      "recomputes ACCEPT")
    if compat["verdict"] != "ACCEPT":
        raise Invalid("verdict: compat verdict not ACCEPT")


def check_result_files(artifacts: Path) -> None:
    """Cross-check per-step RESULT files when present in artifacts."""
    for step in ALL_STEPS:
        fp = artifacts / step / "RESULT.json"
        if not fp.exists():
            continue
        res = _load_json(fp, f"RESULT {step}")
        rc = res.get("rc", res.get("exit_code"))
        if rc != 0:
            raise Invalid(f"RESULT {step}: rc={rc}, want 0")


# ------------------------------------------------------------- lanes

def _run_ledger(report_p: Path, ledger_p: Path, artifacts: Path,
                pins_p: Path) -> None:
    report = check_envelope_schema(_load_json(report_p, "report"),
                                   _load_json(pins_p, "pins"))
    pins = check_pins_schema(_load_json(pins_p, "pins"))
    bind_step_universe(pins)
    if report["mode"] != "host":
        raise Invalid("mode skew: ledger lane requires mode 'host'")
    check_bundle_binding(report, pins)
    check_identities(report, pins)
    entries = _ledger_entries(ledger_p)
    by_step_inv = check_ledger_binding(report, entries, pins, artifacts)
    check_ledger_artifacts(by_step_inv, artifacts, pins)
    check_report_artifact_table(report, artifacts, pins)
    package = [a for a in by_step_inv["package"][0]["proc"]["artifacts"]
               if a["relpath"] == "RELCHECK-REPORT.json"]
    if not package:
        raise Invalid("ledger: package invoke lacks RELCHECK-REPORT.json")
    check_report_bytes_bound(report_p, report, package[0]["sha256"])
    check_suites(report, artifacts, pins)
    check_surface(report, pins)
    check_result_files(artifacts)
    check_verdict_rule(report)


def _resolve_stamp(stamps: Path, step: str) -> Path:
    direct = stamps / f"{step}-RESULT.json"
    if direct.is_file():
        return direct
    nested = stamps / "steps" / f"{step}-RESULT.json"
    if nested.is_file():
        return nested
    raise Invalid(f"--no-ledger: missing stamp for {step}")


def _check_run_log(stamps: Path, pins: dict) -> None:
    """Direct run-log binding (argv/inputs/rc) when the log is present.

    Binds one row per step: builder rows (no "event" key) bind as-is;
    U-baseline rows bind only event == "attempt_end" (attempt_start /
    skip / audit rows are harness liveness evidence, not checker-bound;
    a non-end row naming a step outside the universe still fails).
    Last end row per step wins: retry-after-failure converges like the
    host lane's success-only binding (superseded failures stay preserved
    in the log, auditable and harness-counted).
    """
    log = stamps / "direct-ledger.jsonl"
    if not log.exists():
        return
    try:
        lines = log.read_text(encoding="utf-8").splitlines()
    except OSError:
        raise Invalid(f"--no-ledger: cannot read {log}")
    bound: dict[str, dict] = {}
    for lineno, line in enumerate(lines, 1):
        if not line.strip():
            continue
        try:
            row = json.loads(line)
        except json.JSONDecodeError as exc:
            raise Invalid(f"--no-ledger: run log line {lineno} "
                          f"malformed: {exc}")
        if not isinstance(row, dict):
            raise Invalid(f"--no-ledger: run log line {lineno} "
                          "not an object")
        ev = row.get("event")
        if ev is not None and ev != "attempt_end":
            audit_step = row.get("step")
            if audit_step is not None and audit_step not in ALL_STEPS:
                raise Invalid(f"--no-ledger: audit row names step "
                              f"{audit_step!r}")
            continue
        step = row.get("step")
        if step not in ALL_STEPS:
            raise Invalid(f"--no-ledger: run log names step {step!r}")
        bound[step] = row
    for step, row in bound.items():
        if row.get("argv") != pins["argv"][step]:
            raise Invalid(f"--no-ledger: {step}: argv skew vs pins")
        if row.get("argv_sha256") != _argv_sha256(pins["argv"][step]):
            raise Invalid(f"--no-ledger: {step}: argv_sha256 skew")
        inputs = row.get("input_hashes", {})
        if inputs.get("pins.json") != pins["pins_sha256"]:
            raise Invalid(f"--no-ledger: {step}: input pins.json skew")
        if inputs.get("relcheck.py") != pins["bin_relcheck_sha256"]:
            raise Invalid(f"--no-ledger: {step}: input relcheck.py skew")
        if row.get("bundle_sha256") != pins["bundle_sha256"]:
            raise Invalid(f"--no-ledger: {step}: bundle skew")
        if row.get("rc") != 0:
            raise Invalid(f"--no-ledger: {step}: rc={row.get('rc')}")
    missing = [s for s in ALL_STEPS if s not in bound]
    if missing:
        raise Invalid(f"--no-ledger: run log missing steps {missing}")


def _run_no_ledger(report_p: Path, stamps: Path, artifacts: Path,
                   pins_p: Path) -> None:
    report = check_envelope_schema(_load_json(report_p, "report"),
                                   _load_json(pins_p, "pins"))
    pins = check_pins_schema(_load_json(pins_p, "pins"))
    bind_step_universe(pins)
    if report["mode"] != "direct":
        raise Invalid("mode skew: --no-ledger lane requires mode 'direct'")
    check_bundle_binding(report, pins)
    check_identities(report, pins)
    _check_run_log(stamps, pins)
    package_sha = ""
    for step in ALL_STEPS:
        stamp = _load_json(_resolve_stamp(stamps, step), f"stamp {step}")
        rc = stamp.get("rc", stamp.get("exit_code"))
        if rc != 0:
            raise Invalid(f"--no-ledger: stamp {step} rc={rc}, want 0")
        listed = stamp.get("artifacts", [])
        got_names = {a.get("relpath") for a in listed}
        if got_names != set(pins["artifacts"][step]):
            raise Invalid(f"--no-ledger: stamp {step}: artifact set "
                          "!= pins")
        for art in listed:
            _verify_artifact_file(step, art["relpath"], art["sha256"],
                                  art.get("bytes"), artifacts)
            if step == "package" and art["relpath"] == "RELCHECK-REPORT.json":
                package_sha = art["sha256"]
    if not package_sha:
        raise Invalid("--no-ledger: package stamp lacks "
                      "RELCHECK-REPORT.json")
    check_report_artifact_table(report, artifacts, pins)
    check_report_bytes_bound(report_p, report, package_sha)
    check_suites(report, artifacts, pins)
    check_surface(report, pins)
    check_result_files(artifacts)
    check_verdict_rule(report)


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="relcheck artifact checker")
    ap.add_argument("report", type=Path)
    ap.add_argument("ledger_or_nothing", nargs="?", type=Path, default=None)
    ap.add_argument("artifacts", type=Path)
    ap.add_argument("pins", type=Path)
    ap.add_argument("--no-ledger", action="store_true")
    ap.add_argument("--stamps", type=Path, default=None)
    args = ap.parse_args(argv)
    try:
        if args.no_ledger:
            if args.ledger_or_nothing is not None or args.stamps is None:
                raise Invalid("usage: verdict_relcheck.py <report> "
                              "--no-ledger --stamps DIR <artifacts> <pins>")
            _run_no_ledger(args.report, args.stamps, args.artifacts,
                           args.pins)
        else:
            if args.ledger_or_nothing is None:
                raise Invalid("usage: verdict_relcheck.py <report> <ledger> "
                              "<artifacts> <pins>")
            _run_ledger(args.report, args.ledger_or_nothing, args.artifacts,
                        args.pins)
    except Invalid as exc:
        print(f"RELCHECK-INVALID: {exc}")
        return 1
    print("RELCHECK-VALID")
    return 0


if __name__ == "__main__":
    sys.exit(main())
