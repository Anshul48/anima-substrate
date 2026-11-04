"""verdict_relcheck.py — independent relcheck acceptance checker.

Usage::

    verdict_relcheck.py <report> <ledger> <artifacts> <pins> [--direct]

Prints exactly one line to stdout — ``RELCHECK-VALID`` (exit 0) or
``RELCHECK-INVALID: <reason>`` (exit 1) — and nothing else there;
diagnostics go to stderr. It MUST NOT trust the report: it recomputes
identity hashes from frozen bytes itself, cross-checks suite claims
against the ledger-recorded invokes + re-hashed log artifacts with
its own parsers, and re-derives the verdict rule. Direct mode reads
the direct runner's ledger instead of a host ledger; everything else
is identical.

Independence is deliberate: the surface extractor, the unittest log
parser, and the verdict rule are DUPLICATED here (not imported from
the bundle), so a shared-implementation bug cannot validate itself.
"""

from __future__ import annotations

import ast
import hashlib
import json
import sys
from pathlib import Path


class Invalid(Exception):
    pass


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()


def load_json(path: Path, what: str) -> dict:
    try:
        obj = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError) as exc:
        raise Invalid(f"{what} unreadable: {exc}") from exc
    if not isinstance(obj, dict):
        raise Invalid(f"{what} is not a JSON object")
    return obj


def load_jsonl(path: Path, what: str) -> list[dict]:
    try:
        lines = path.read_text(encoding="utf-8").splitlines()
    except OSError as exc:
        raise Invalid(f"{what} unreadable: {exc}") from exc
    entries = []
    for i, line in enumerate(lines):
        if not line.strip():
            continue
        try:
            obj = json.loads(line)
        except ValueError:
            raise Invalid(f"{what} line {i + 1} corrupt")
        if not isinstance(obj, dict):
            raise Invalid(f"{what} line {i + 1} is not an object")
        entries.append(obj)
    return entries


# Independent surface extractor (same CONTRACT as the bundle's:
# union of == literals against args.op/args.cmd and .add_parser()
# first args; sorted top-level api.py defs).
def cli_verbs_of(release_py: Path) -> list[str]:
    tree = ast.parse(release_py.read_text(encoding="utf-8"))
    verbs: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Compare) and len(node.ops) == 1 \
                and isinstance(node.ops[0], ast.Eq):
            sides = [node.left, *node.comparators]
            for attr_side, lit_side in (sides, sides[::-1]):
                if isinstance(attr_side, ast.Attribute) \
                        and attr_side.attr in ("op", "cmd") \
                        and isinstance(lit_side, ast.Constant) \
                        and isinstance(lit_side.value, str):
                    verbs.add(lit_side.value)
        elif isinstance(node, ast.Call) \
                and isinstance(node.func, ast.Attribute) \
                and node.func.attr == "add_parser" and node.args \
                and isinstance(node.args[0], ast.Constant) \
                and isinstance(node.args[0].value, str):
            verbs.add(node.args[0].value)
    return sorted(verbs)


def api_functions_of(api_py: Path) -> list[str]:
    tree = ast.parse(api_py.read_text(encoding="utf-8"))
    return sorted(n.name for n in tree.body
                  if isinstance(n, ast.FunctionDef))


def surface_of(tree_dir: Path) -> dict:
    rel = tree_dir / "release.py"
    api = tree_dir / "api.py"
    out = {"cli_verbs": [], "api_functions": [],
           "release_present": False, "api_present": False}
    if rel.is_file() and not rel.is_symlink():
        out["cli_verbs"] = cli_verbs_of(rel)
        out["release_present"] = True
    if api.is_file() and not api.is_symlink():
        out["api_functions"] = api_functions_of(api)
        out["api_present"] = True
    return out


# Independent unittest-log parser (same spec: exact OK line,
# FAILED fails, Ran N parsed, skipped=N parsed).
def parse_unittest_log(data: bytes) -> dict:
    text = data.decode("utf-8", errors="replace")
    ran = None
    for line in text.splitlines():
        s = line.strip()
        if s.startswith("Ran ") and " test" in s:
            try:
                ran = int(s.split()[1])
            except (ValueError, IndexError):
                pass
    failed = any(ln.strip().startswith("FAILED")
                 for ln in text.splitlines())
    ok_line = any(ln.strip() == "OK" or
                  (ln.strip().startswith("OK (") and
                   ln.strip().endswith(")"))
                  for ln in text.splitlines())
    skipped = 0
    for ln in text.splitlines():
        s = ln.strip()
        if "skipped=" in s:
            frag = s.split("skipped=", 1)[1]
            num = "".join(ch for ch in frag if ch.isdigit())
            if num:
                skipped = int(num)
    return {"ran": ran, "ok": bool(ok_line) and not failed,
            "skipped": skipped}


def verdict_rule(ident_ok: bool, suites_ok: bool,
                 surface_ok: bool) -> str:
    if ident_ok and suites_ok and surface_ok:
        return "ACCEPT"
    if ident_ok and suites_ok:
        return "PARTIAL"
    return "FAIL"


def argv_sha256(argv: list) -> str:
    """Replicate the host's argv hash byte-exactly.

    procedure.py records sha256(json.dumps(argv, sort_keys=True)
    .encode()) with DEFAULT separators; any deviation here would
    false-INVALID every run, which the readiness run would expose.
    """
    return hashlib.sha256(
        json.dumps(argv, sort_keys=True).encode()).hexdigest()


def check_schema(report: dict, pins: dict, direct: bool) -> None:
    for key in ("vehicle", "vehicle_version", "verdict", "nonce",
                "run_id", "mode", "bundle_sha256", "pins_sha256",
                "compat", "artifacts"):
        if key not in report:
            raise Invalid(f"report schema: missing {key!r}")
    if report["vehicle"] != "relcheck" \
            or report["vehicle_version"] != 1:
        raise Invalid("report schema: not a relcheck v1 report")
    want_mode = "direct" if direct else "host"
    if report["mode"] != want_mode:
        raise Invalid(f"report mode {report['mode']!r} != {want_mode}")
    if report["verdict"] not in ("ACCEPT", "PARTIAL", "FAIL"):
        raise Invalid("report schema: bad verdict")
    for key in ("bundle_sha256", "bin_relcheck_sha256",
                "pins_sha256", "frozen", "identity", "suites",
                "surface_min", "surface_trees", "ignore_top",
                "artifacts", "steps", "argv", "demo_marker"):
        if key not in pins:
            raise Invalid(f"pins schema: missing {key!r}")
    compat = report["compat"]
    for key in ("pins_sha256", "identities", "suites", "surface",
                "verdict"):
        if key not in compat:
            raise Invalid(f"compat schema: missing {key!r}")
    if compat["verdict"] != report["verdict"]:
        raise Invalid("package relocated a different verdict "
                      "than compat emitted")


def check_host_ledger(entries: list[dict], pins: dict,
                      artifacts: Path) -> dict:
    """Cross-check the host ledger. Returns per-step invoke records."""
    key = artifacts.name
    if not key.startswith("proc-"):
        raise Invalid(f"artifacts dir {key!r} is not proc-<key>")
    key = key[len("proc-"):]
    creates = [e for e in entries if e.get("kind") == "create"]
    bound = False
    for entry in creates:
        for table in entry.get("payload", {}).get("procedures", []):
            if table.get("bundle_sha256") == pins["bundle_sha256"]:
                bound = True
    if not bound:
        raise Invalid("ledger: no create pins the report bundle")
    for entry in entries:
        payload = entry.get("payload", {})
        if entry.get("kind") == "deny" and "procedure" in payload:
            raise Invalid("ledger: procedure deny recorded "
                          f"({payload.get('reason', '')!r})")
    begins = [e for e in entries
              if e.get("kind") == "proc_begin"
              and e.get("payload", {}).get("idem_key") == key]
    invokes = [e for e in entries
               if e.get("kind") == "invoke"
               and e.get("payload", {}).get("capability")
               == "proc.exec"
               and e.get("payload", {}).get("proc", {}).get(
                   "idem_key") == key]
    steps: dict = {}
    for step in pins["steps"]:
        step_begins = [e for e in begins
                       if e.get("payload", {}).get("step") == step]
        step_invokes = [e for e in invokes
                        if e.get("payload", {}).get("proc", {}).get(
                            "step") == step]
        if len(step_begins) != 1 or len(step_invokes) != 1:
            raise Invalid(
                f"ledger: step {step!r} has "
                f"{len(step_begins)} begins/"
                f"{len(step_invokes)} invokes (want exactly 1/1)")
        begin, invoke = step_begins[0], step_invokes[0]
        bpay, ipay = begin["payload"], invoke["payload"]
        if bpay.get("bundle_sha256") != pins["bundle_sha256"]:
            raise Invalid(f"ledger: {step} begin binds a foreign "
                          f"bundle")
        if bpay.get("argv_sha256") != argv_sha256(pins["argv"][step]):
            raise Invalid(f"ledger: {step} argv skews vs manifest")
        if bpay.get("invoke_id") != ipay.get("invoke_id"):
            raise Invalid(f"ledger: {step} begin/invoke id skew")
        inputs = bpay.get("input_hashes", {})
        if inputs.get("relcheck.py") != pins["bin_relcheck_sha256"]:
            raise Invalid(f"ledger: {step} executed bytes differ "
                          f"from the bundle program pin")
        if inputs.get("pins.json") != pins["pins_sha256"]:
            raise Invalid(f"ledger: {step} ran against foreign pins")
        if "result_ref" not in ipay or "error" in ipay:
            raise Invalid(f"ledger: {step} invoke is not a success "
                          f"({ipay.get('error', '')!r})")
        proc = ipay["proc"]
        if proc.get("exit_code") != 0:
            raise Invalid(f"ledger: {step} exit_code "
                          f"{proc.get('exit_code')}")
        steps[step] = ipay
    return steps


def check_direct_ledger(records: list[dict], pins: dict) -> dict:
    steps: dict = {}
    for step in pins["steps"]:
        matches = [r for r in records if r.get("step") == step]
        if len(matches) != 1:
            raise Invalid(f"direct ledger: step {step!r} recorded "
                          f"{len(matches)}x (want exactly 1)")
        rec = matches[0]
        if rec.get("bundle_sha256") != pins["bundle_sha256"]:
            raise Invalid(f"direct ledger: {step} binds a foreign "
                          f"bundle")
        if rec.get("argv_sha256") != argv_sha256(pins["argv"][step]):
            raise Invalid(f"direct ledger: {step} argv skews")
        inputs = rec.get("input_hashes", {})
        if inputs.get("relcheck.py") != pins["bin_relcheck_sha256"]:
            raise Invalid(f"direct ledger: {step} executed bytes "
                          f"differ from the bundle program pin")
        if inputs.get("pins.json") != pins["pins_sha256"]:
            raise Invalid(f"direct ledger: {step} ran against "
                          f"foreign pins")
        if rec.get("rc") != 0:
            raise Invalid(f"direct ledger: {step} rc "
                          f"{rec.get('rc')}")
        steps[step] = rec
    return steps


def check_identity(report: dict, pins: dict) -> bool:
    """Recompute every identity hash from frozen bytes. No trust."""
    ignored = set(pins["ignore_top"])
    all_match = True
    compat_idents = report["compat"]["identities"]
    for tag in sorted(pins["identity"]):
        expected = pins["identity"][tag]
        frozen = Path(pins["frozen"][tag])
        bad = []
        for rel, want in sorted(expected.items()):
            path = frozen / rel
            if path.is_symlink() or not path.is_file():
                bad.append(f"{rel}: missing")
            elif sha256_file(path) != want:
                bad.append(f"{rel}: mismatch")
        extras = []
        for path in sorted(frozen.rglob("*")):
            if path.is_dir():
                continue
            rel = path.relative_to(frozen).as_posix()
            if rel.split("/")[0] in ignored:
                continue
            if path.is_symlink():
                extras.append(f"{rel}: symlink")
            elif rel not in expected:
                extras.append(rel)
        match = not bad and not extras
        all_match = all_match and match
        claim = compat_idents.get(tag, {})
        if claim.get("match") != match \
                or claim.get("files") != len(expected):
            raise Invalid(f"identity {tag}: report claims "
                          f"match={claim.get('match')} "
                          f"files={claim.get('files')}; recomputed "
                          f"match={match} files={len(expected)} "
                          f"(bad={bad[:3]} extras={extras[:3]})")
        if not match:
            print(f"note: identity {tag} MISMATCH is truthfully "
                  f"reported", file=sys.stderr)
    return all_match


def check_artifacts_manifest(report: dict, artifacts: Path,
                             pins: dict) -> None:
    """Re-hash every manifest artifact. Pins-skew refuses."""
    seen = set()
    for entry in report["artifacts"]:
        step, rel = entry["step"], entry["relpath"]
        path = artifacts / step / rel
        if path.is_symlink() or not path.is_file():
            raise Invalid(f"artifact {step}/{rel} missing")
        data = path.read_bytes()
        if hashlib.sha256(data).hexdigest() != entry["sha256"] \
                or len(data) != entry["bytes"]:
            raise Invalid(f"artifact {step}/{rel} skews vs the "
                          f"manifest claim")
        seen.add((step, rel))
    for step in pins["steps"]:
        if step == "package":
            continue
        for name in pins["artifacts"][step]:
            if (step, name) not in seen:
                raise Invalid(f"artifact {step}/{name} absent "
                              f"from the manifest")
    # Every step summary embeds the pins it ran against; all must
    # equal the pins under check (anti-skew across arms and time).
    summaries = [artifacts / "identity"
                 / pins["artifacts"]["identity"][0]]
    for stag in ("r1", "r2", "r3"):
        summaries.append(artifacts / f"suite-{stag}"
                         / pins["artifacts"][f"suite-{stag}"][0])
    summaries.append(artifacts / "compat" / "COMPAT-REPORT.json")
    for path in summaries:
        try:
            obj = json.loads(path.read_bytes().decode("utf-8"))
        except (OSError, ValueError) as exc:
            raise Invalid(f"summary {path} unreadable: {exc}")
        if obj.get("pins_sha256") != pins["pins_sha256"]:
            raise Invalid(f"summary {path.name} ran against "
                          f"foreign pins")


def check_suites(report: dict, artifacts: Path, pins: dict) -> bool:
    """Cross-check suite claims vs re-hashed, re-parsed log bytes."""
    all_ok = True
    compat_suites = report["compat"]["suites"]
    for stag in ("r1", "r2", "r3"):
        spec = pins["suites"][stag]
        summary = load_json(
            artifacts / f"suite-{stag}"
            / pins["artifacts"][f"suite-{stag}"][0],
            f"suite-{stag} summary")
        if summary.get("pins_sha256") != pins["pins_sha256"]:
            raise Invalid(f"suite-{stag} summary ran against "
                          f"foreign pins")
        results = {r["file"]: r for r in summary.get("results", [])}
        claims = {r["file"]: r
                  for r in compat_suites[stag].get("results", [])}
        for prog in spec["programs"]:
            rec = results.get(prog["file"])
            claim = claims.get(prog["file"])
            if rec is None or claim is None:
                raise Invalid(f"suite-{stag}: {prog['file']} "
                              f"missing from summary/compat")
            log_data = (artifacts / f"suite-{stag}"
                        / prog["log"]).read_bytes()
            if prog["kind"] == "unittest":
                parsed = parse_unittest_log(log_data)
                truth = {"ran": parsed["ran"], "ok": parsed["ok"]
                         and rec.get("rc") == 0,
                         "skipped": parsed["skipped"]}
                want_ok = (rec.get("rc") == 0 and parsed["ok"]
                           and parsed["ran"] == prog["expect_tests"]
                           and parsed["skipped"]
                           == prog["expect_skipped"])
            else:
                marker = pins["demo_marker"]
                found = marker in log_data.decode(
                    "utf-8", errors="replace")
                truth = {"ran": None, "ok": rec.get("rc") == 0
                         and found, "skipped": None}
                want_ok = rec.get("rc") == 0 and found
            if rec.get("ok") != want_ok:
                raise Invalid(
                    f"suite-{stag}: {prog['file']} claims "
                    f"ok={rec.get('ok')}; re-parsed {truth}")
            for field in ("rc", "ran", "skipped", "ok"):
                if field in claim and claim[field] != rec.get(field) \
                        and not (claim[field] is None
                                 and field in ("ran", "skipped")
                                 and prog["kind"] == "demo"):
                    raise Invalid(
                        f"suite-{stag}: {prog['file']} compat "
                        f"claim {field}={claim[field]!r} != summary "
                        f"{rec.get(field)!r}")
            all_ok = all_ok and bool(rec.get("ok"))
        if compat_suites[stag].get("ok") != \
                all(r.get("ok") for r in results.values()):
            raise Invalid(f"suite-{stag}: compat ok flag skews")
    return all_ok


def check_surface(report: dict, pins: dict) -> bool:
    """Recompute surfaces from frozen bytes; minimums must hold."""
    ok = True
    for stag in ("r1", "r2", "r3"):
        tree = Path(pins["frozen"][pins["surface_trees"][stag]])
        try:
            observed = surface_of(tree)
        except (OSError, ValueError) as exc:
            raise Invalid(f"surface {stag} unreadable: {exc}")
        claim = report["compat"]["surface"].get(stag, {})
        for field in ("cli_verbs", "api_functions",
                      "release_present", "api_present"):
            if claim.get(field) != observed[field]:
                raise Invalid(f"surface {stag}: report {field} "
                              f"skews vs recomputation")
        if not isinstance(claim.get("ledger_kinds"), list):
            raise Invalid(f"surface {stag}: ledger_kinds missing")
        minimum = pins["surface_min"][stag]
        verbs_ok = set(minimum["cli_verbs"]) <= set(
            observed["cli_verbs"])
        funcs_ok = set(minimum["api_functions"]) <= set(
            observed["api_functions"])
        if claim.get("verbs_ok") != verbs_ok \
                or claim.get("funcs_ok") != funcs_ok \
                or claim.get("minimum_ok") != (verbs_ok and funcs_ok):
            raise Invalid(f"surface {stag}: minimum flags skew")
        ok = ok and verbs_ok and funcs_ok
    return ok


def main(argv: list[str]) -> int:
    args = [a for a in argv[1:] if a != "--direct"]
    direct = "--direct" in argv[1:]
    if len(args) != 4:
        print("usage: verdict_relcheck.py <report> <ledger> "
              "<artifacts> <pins> [--direct]", file=sys.stderr)
        return 1
    report_path, ledger_path, artifacts, pins_path = \
        (Path(args[0]), Path(args[1]), Path(args[2]), Path(args[3]))
    try:
        report = load_json(report_path, "report")
        pins = load_json(pins_path, "pins")
        check_schema(report, pins, direct)
        if report["bundle_sha256"] != pins["bundle_sha256"]:
            raise Invalid("report binds a foreign bundle sha")
        if report["pins_sha256"] != pins["pins_sha256"]:
            raise Invalid("report ran against foreign pins")
        ledger_entries = load_jsonl(ledger_path, "ledger")
        if direct:
            check_direct_ledger(ledger_entries, pins)
        else:
            check_host_ledger(ledger_entries, pins, artifacts)
        ident_ok = check_identity(report, pins)
        check_artifacts_manifest(report, artifacts, pins)
        suites_ok = check_suites(report, artifacts, pins)
        surface_ok = check_surface(report, pins)
        rule = verdict_rule(ident_ok, suites_ok, surface_ok)
        if rule != report["verdict"]:
            raise Invalid(f"verdict rule recomputes {rule}; "
                          f"report claims {report['verdict']}")
        print("RELCHECK-VALID")
        return 0
    except Invalid as exc:
        print(f"RELCHECK-INVALID: {exc}")
        return 1
    except Exception as exc:  # even crashes speak the one line
        print(f"RELCHECK-INVALID: internal: {type(exc).__name__}: "
              f"{exc}")
        import traceback
        traceback.print_exc(file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main(sys.argv))
