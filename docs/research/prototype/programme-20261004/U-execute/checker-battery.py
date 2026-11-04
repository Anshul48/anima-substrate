"""Maintained battery for the U-execute relcheck checker.

Builds mutated fixtures under /tmp/neg-battery/fix from the preserved
NOTE-1 reports/ledgers plus the snapshotted step-artifact bytes in
U-execute/battery-bytes/, runs the checker per case, and asserts each
outcome. Stdout is the transcript persisted as
U-execute/checker-negatives.log. Exits nonzero if any expectation fails.
"""
import copy
import hashlib
import json
import shutil
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
WS = HERE.parent.parent.parent
CHECKER = HERE / "verdict_relcheck.py"
PINS = WS / "prototype/successor-005/vehicle/relcheck-pins.json"
HOST = WS / "prototype/successor-005/runs/note1-closure/artifacts/host"
DIRECT = WS / "prototype/successor-005/runs/note1-closure/artifacts/direct"
HOST_ART = HERE / "battery-bytes/host-art"
DIRECT_ART = HERE / "battery-bytes/direct-art"

ROOT = Path("/tmp/neg-battery/fix")
FAILURES = []


def sha(b: bytes) -> str:
    return hashlib.sha256(b).hexdigest()


def read_ledger(p: Path):
    return [json.loads(ln) for ln in p.read_text().splitlines()
            if ln.strip()]


def write_ledger(p: Path, entries):
    p.write_text("\n".join(json.dumps(e) for e in entries) + "\n")


def run_checker(args):
    proc = subprocess.run([sys.executable, str(CHECKER), *args],
                          capture_output=True, text=True)
    lines = proc.stdout.splitlines()
    assert len(lines) == 1, f"stdout not one line: {proc.stdout!r}"
    return proc.returncode, lines[0]


def check(name, args, expect_valid, expect_sub=""):
    rc, line = run_checker(args)
    if expect_valid:
        ok = (rc == 0 and line == "RELCHECK-VALID")
    else:
        ok = (rc == 1 and line.startswith("RELCHECK-INVALID: ")
              and expect_sub in line)
    flag = "PASS" if ok else "FAIL"
    print(f"[{flag}] {name}\n      -> rc={rc} {line}")
    if not ok:
        print(f"      EXPECT valid={expect_valid} sub={expect_sub!r}")
        FAILURES.append(name)


def fresh(tag):
    d = ROOT / tag
    if d.exists():
        shutil.rmtree(d)
    art = d / "artifacts"
    shutil.copytree(HOST_ART, art)
    rep = json.loads((HOST / "package/RELCHECK-REPORT.json").read_text())
    led = read_ledger(HOST / "ledger.jsonl")
    return d, art, rep, led


def rebind_package(rep_path, led):
    raw = rep_path.read_bytes()
    for e in led:
        if e.get("kind") == "invoke":
            p = e["payload"]
            if p.get("capability") == "proc.exec" \
                    and p.get("proc", {}).get("step") == "package":
                for a in p["proc"]["artifacts"]:
                    if a["relpath"] == "RELCHECK-REPORT.json":
                        a["sha256"] = sha(raw)
                        a["bytes"] = len(raw)


def commit(d, art, rep, led):
    rp = d / "report.json"
    lp = d / "ledger.jsonl"
    rp.write_text(json.dumps(rep, indent=2) + "\n")
    # Keep the fixture self-consistent: the artifacts copy of the report
    # tracks the fixture report file, and the ledger package claim tracks
    # both. Cases firing on earlier axes are unaffected.
    (art / "package" / "RELCHECK-REPORT.json").write_bytes(rp.read_bytes())
    rebind_package(rp, led)
    write_ledger(lp, led)
    return rp, lp, art


def direct_relog(tag, mut):
    """Copy DIRECT stamps; rewrite the run log U-baseline-style.

    Each builder completion row becomes an attempt_start/attempt_end
    pair mirroring direct_run.py's row schemas exactly (end rows keep
    every builder evidence field); mut(ends_by_step, all_rows) applies
    case surgery (retry rows, rc flips, corrupt rows). Returns dd.
    """
    dd = ROOT / tag
    if dd.exists():
        shutil.rmtree(dd)
    dd.mkdir(parents=True)
    shutil.copytree(DIRECT / "steps", dd / "steps")
    base_rows = [json.loads(ln) for ln in
                 (DIRECT / "direct-ledger.jsonl").read_text().splitlines()
                 if ln.strip()]
    log_rows = []
    ends = {}
    for row in base_rows:
        step = row["step"]
        log_rows.append(
            {"event": "attempt_start", "run_id": "u-battery",
             "step": step, "attempt": 1,
             "started_at": "2026-10-06T12:00:00+00:00",
             "argv": row["argv"], "argv_sha256": row["argv_sha256"],
             "input_hashes": row["input_hashes"], "env_extra_keys": []})
        end = {"event": "attempt_end", "run_id": "u-battery",
               "step": step, "attempt": 1,
               "started_at": "2026-10-06T12:00:01+00:00",
               "rc": 0, "timed_out": False,
               "elapsed_s": row.get("elapsed_s", 0.0),
               "argv": row["argv"], "argv_sha256": row["argv_sha256"],
               "bundle_sha256": row["bundle_sha256"],
               "input_hashes": row["input_hashes"],
               "env_extra_keys": [], "artifacts": [],
               "truncated_stdout": False, "truncated_stderr": False,
               "stamp_hit": False}
        log_rows.append(end)
        ends[step] = end
    if mut:
        mut(ends, log_rows)
    (dd / "direct-ledger.jsonl").write_text(
        "\n".join(json.dumps(r) for r in log_rows) + "\n")
    return dd


def main():
    print("checker-negatives battery")
    print(f"checker: {CHECKER}")
    print(f"pins sha: {sha(PINS.read_bytes())[:16]}")
    print(f"host report: {sha((HOST/'package/RELCHECK-REPORT.json').read_bytes())[:8]} "
          f"direct report: {sha((DIRECT/'package/RELCHECK-REPORT.json').read_bytes())[:8]}")
    print("--- positives ---")
    # P1: pristine host lane (live bytes, preserved report+ledger).
    check("P1 host VALID (preserved)", [
        str(HOST / "package/RELCHECK-REPORT.json"),
        str(HOST / "ledger.jsonl"), str(HOST_ART), str(PINS)], True)
    # P2: pristine direct lane.
    check("P2 direct VALID (preserved)", [
        str(DIRECT / "package/RELCHECK-REPORT.json"), "--no-ledger",
        "--stamps", str(DIRECT), str(DIRECT_ART), str(PINS)], True)

    print("--- negatives: report/bundle/schema ---")
    d, art, rep, led = fresh("n1-foreign-bundle")
    rep["bundle_sha256"] = "0" * 64
    rp, lp, _ = commit(d, art, rep, led)
    check("N1 foreign bundle", [str(rp), str(lp), str(art), str(PINS)],
          False, "bundle mismatch")

    d, art, rep, led = fresh("n2-schema-envelope")
    del rep["nonce"]
    rp, lp, _ = commit(d, art, rep, led)
    check("N2 schema hole (nonce)", [str(rp), str(lp), str(art), str(PINS)],
          False, "missing key 'nonce'")

    d, art, rep, led = fresh("n3-schema-compat")
    del rep["compat"]["surface"]
    rp, lp, _ = commit(d, art, rep, led)
    check("N3 schema hole (compat.surface)",
          [str(rp), str(lp), str(art), str(PINS)],
          False, "compat missing key 'surface'")

    d, art, rep, led = fresh("n4a-verdict-outer")
    rep["verdict"] = "FAIL"
    rp, lp, _ = commit(d, art, rep, led)
    check("N4a flipped verdict (outer only)",
          [str(rp), str(lp), str(art), str(PINS)],
          False, "relocation skew")

    d, art, rep, led = fresh("n4b-verdict-both")
    rep["verdict"] = "FAIL"
    rep["compat"]["verdict"] = "FAIL"
    rp, lp, _ = commit(d, art, rep, led)
    check("N4b flipped verdict (both)",
          [str(rp), str(lp), str(art), str(PINS)],
          False, "recomputes ACCEPT")

    print("--- negatives: ledger ---")
    d, art, rep, led = fresh("n5a-ledger-drop-invoke")
    led = [e for e in led if not (
        e.get("kind") == "invoke"
        and e.get("payload", {}).get("proc", {}).get("step") == "suite-r2")]
    rp, lp, _ = commit(d, art, rep, led)
    check("N5a corrupt ledger (invoke removed)",
          [str(rp), str(lp), str(art), str(PINS)],
          False, "no success invoke")

    d, art, rep, led = fresh("n5b-ledger-malformed")
    rp, lp, _ = commit(d, art, rep, led)
    with open(lp, "a") as fh:
        fh.write("{bad json\n")
    check("N5b corrupt ledger (malformed line)",
          [str(rp), str(lp), str(art), str(PINS)], False, "malformed")

    d, art, rep, led = fresh("n6-argv-skew")
    for e in led:
        if e.get("kind") == "proc_begin" \
                and e["payload"].get("step") == "identity":
            h = e["payload"]["argv_sha256"]
            e["payload"]["argv_sha256"] = h[:-1] + ("0" if h[-1] != "0" else "1")
    rp, lp, _ = commit(d, art, rep, led)
    check("N6 argv skew", [str(rp), str(lp), str(art), str(PINS)],
          False, "argv_sha256 skew")

    d, art, rep, led = fresh("n6b-input-skew")
    for e in led:
        if e.get("kind") == "proc_begin" \
                and e["payload"].get("step") == "compat":
            e["payload"]["input_hashes"]["pins.json"] = "f" * 64
    rp, lp, _ = commit(d, art, rep, led)
    check("N6b input-hash skew", [str(rp), str(lp), str(art), str(PINS)],
          False, "input pins.json")

    d, art, rep, led = fresh("n18-base-extra-input")
    for e in led:
        if e.get("kind") == "proc_begin" \
                and e["payload"].get("step") == "compat":
            e["payload"]["input_hashes"]["smuggled.py"] = "0" * 64
    rp, lp, _ = commit(d, art, rep, led)
    check("N18 base step extra input (exactness kept)",
          [str(rp), str(lp), str(art), str(PINS)],
          False, "!= pinned set")

    print("--- negatives: bytes/grammar ---")
    d, art, rep, led = fresh("n7-log-flip")
    rp, lp, _ = commit(d, art, rep, led)
    logp = art / "suite-r2" / "SUITE-R2-conformance.log"
    raw = bytearray(logp.read_bytes())
    raw[100] ^= 0x01
    logp.write_bytes(bytes(raw))
    check("N7 log-byte flip", [str(rp), str(lp), str(art), str(PINS)],
          False, "sha256 mismatch")

    d, art, rep, led = fresh("n11-grammar-lie")
    rp, lp, _ = commit(d, art, rep, led)
    logp = art / "suite-r1" / "SUITE-R1-conformance.log"
    raw = logp.read_bytes().replace(b"Ran 9 tests", b"Ran 8 tests")
    assert raw != logp.read_bytes()
    logp.write_bytes(raw)
    summ_p = art / "suite-r1" / "SUITE-R1.json"
    summ = json.loads(summ_p.read_text())
    for r in summ["results"]:
        if r["file"] == "test_conformance.py":
            r["log_bytes"] = len(raw)
            r["log_sha256"] = sha(raw)
    summ_p.write_text(json.dumps(summ, indent=2) + "\n")
    summ_raw = summ_p.read_bytes()
    for a in rep["artifacts"]:
        if a["step"] == "suite-r1" and a["relpath"].endswith("conformance.log"):
            a["sha256"] = sha(raw)
            a["bytes"] = len(raw)
        if a["step"] == "suite-r1" and a["relpath"] == "SUITE-R1.json":
            a["sha256"] = sha(summ_raw)
            a["bytes"] = len(summ_raw)
    rp.write_text(json.dumps(rep, indent=2) + "\n")
    (art / "package" / "RELCHECK-REPORT.json").write_bytes(rp.read_bytes())
    for e in led:
        if e.get("kind") == "invoke":
            p = e["payload"]
            if p.get("capability") == "proc.exec" \
                    and p.get("proc", {}).get("step") == "suite-r1":
                for a in p["proc"]["artifacts"]:
                    if a["relpath"].endswith("conformance.log"):
                        a["sha256"] = sha(raw)
                        a["bytes"] = len(raw)
                    if a["relpath"] == "SUITE-R1.json":
                        a["sha256"] = sha(summ_raw)
                        a["bytes"] = len(summ_raw)
    rebind_package(rp, led)
    write_ledger(lp, led)
    check("N11 grammar lie (hash-consistent)",
          [str(rp), str(lp), str(art), str(PINS)], False, "log Ran 8")

    d, art, rep, led = fresh("n12-compat-skew")
    for r in rep["compat"]["suites"]["r2"]["results"]:
        if r["file"] == "test_atomicity.py":
            r["ran"] = 26
    rp, lp, _ = commit(d, art, rep, led)
    check("N12 summary/compat skew",
          [str(rp), str(lp), str(art), str(PINS)],
          False, "compat ran disagrees")

    print("--- negatives: kill shape ---")
    d, art, rep, led = fresh("n8-invoke-no-begin")
    for e in led:
        if e.get("kind") == "invoke" \
                and e.get("payload", {}).get("proc", {}).get("step") == "suite-r1":
            e["payload"]["invoke_id"] = "proc-s5a10readiness-suite-r1-a9"
    rp, lp, _ = commit(d, art, rep, led)
    check("N8 invoke without begin",
          [str(rp), str(lp), str(art), str(PINS)],
          False, "matches no proc_begin")

    d, art, rep, led = fresh("p3-unmatched-no-done")
    extra = copy.deepcopy(next(
        e for e in led if e.get("kind") == "proc_begin"
        and e["payload"].get("step") == "suite-r1"))
    extra["payload"]["invoke_id"] = "proc-s5a10readiness-suite-r1-a2"
    extra["payload"]["scratch"] = extra["payload"]["scratch"].replace(
        "attempt1", "attempt2")
    led.append(extra)
    rp, lp, _ = commit(d, art, rep, led)
    check("P3 unmatched begin, no DONE (kill pre-DONE passes)",
          [str(rp), str(lp), str(art), str(PINS)], True)

    # P4: adopt shape — pristine ledger except recovered:true on one
    # success invoke (honest L3 adopt-if-complete: kill lands between
    # DONE and the invoke row, resume adopts without re-running).
    d, art, rep, led = fresh("p4-adopt-recovered")
    for e in led:
        if e.get("kind") == "invoke" \
                and e.get("payload", {}).get("proc", {}).get("step") == "suite-r1":
            e["payload"]["proc"]["recovered"] = True
    rp, lp, _ = commit(d, art, rep, led)
    check("P4 adopt shape, recovered:true (kill-during-adopt passes)",
          [str(rp), str(lp), str(art), str(PINS)], True)

    # P5: kill then adopt — attempt 1 killed pre-DONE (unmatched begin,
    # no DONE), attempt 2 adopted (invoke linked to the a2 begin with
    # recovered:true). Both honest shapes compose.
    d, art, rep, led = fresh("p5-kill-plus-adopt")
    extra = copy.deepcopy(next(
        e for e in led if e.get("kind") == "proc_begin"
        and e["payload"].get("step") == "suite-r1"))
    extra["payload"]["invoke_id"] = "proc-s5a10readiness-suite-r1-a2"
    extra["payload"]["scratch"] = extra["payload"]["scratch"].replace(
        "attempt1", "attempt2")
    led.append(extra)
    for e in led:
        if e.get("kind") == "invoke" \
                and e.get("payload", {}).get("proc", {}).get("step") == "suite-r1":
            e["payload"]["invoke_id"] = \
                "proc-s5a10readiness-suite-r1-a2"
            e["payload"]["proc"]["recovered"] = True
            e["payload"]["proc"]["attempt"] = 2
    rp, lp, _ = commit(d, art, rep, led)
    check("P5 unmatched begin + recovered:true (kill+adopt passes)",
          [str(rp), str(lp), str(art), str(PINS)], True)

    # P6: pins-driven universe — a synthetic 7th step ("assay") added
    # to a pins copy is evidence-bound (ledger begin+invoke, argv,
    # inputs, artifacts, report-table coverage) and verdict-neutral
    # (compat untouched). Tests the revised-universe mechanism the
    # change leg relies on; a faithful revision is proven live.
    d, art, rep, led = fresh("p6-seven-step-universe")
    pins7 = json.loads(PINS.read_text())
    assay_argv = ["python3", "inputs/relcheck.py", "--step", "assay"]
    pins7["steps"] = list(pins7["steps"]) + ["assay"]
    pins7["argv"]["assay"] = assay_argv
    pins7["artifacts"]["assay"] = ["ASSAY.json"]
    pinp = d / "pins7.json"
    pinp.write_text(json.dumps(pins7, indent=2) + "\n")
    assay_beg = copy.deepcopy(next(
        e for e in led if e.get("kind") == "proc_begin"
        and e["payload"].get("step") == "compat"))
    assay_beg["payload"]["step"] = "assay"
    assay_beg["payload"]["invoke_id"] = "proc-s5a10readiness-assay-a1"
    assay_beg["payload"]["argv_sha256"] = hashlib.sha256(
        json.dumps(assay_argv, sort_keys=True).encode()).hexdigest()
    # Scratch value left as copied (synthetic; scratch paths are not
    # checker-bound — the kill-shape DONE probe uses the artifacts dir).
    # Fourth input key exercises the non-base subset rule (value
    # unbound by design — same class as params.json presence-only).
    assay_beg["payload"]["input_hashes"]["assay_surface.py"] = "f" * 64
    led.append(assay_beg)
    assay_bytes = b'{"assay": "pass", "pins_ok": true}\n'
    assay_sha = sha(assay_bytes)
    assay_inv = copy.deepcopy(next(
        e for e in led if e.get("kind") == "invoke"
        and e.get("payload", {}).get("proc", {}).get("step") == "compat"))
    assay_inv["payload"]["invoke_id"] = "proc-s5a10readiness-assay-a1"
    assay_inv["payload"]["proc"]["step"] = "assay"
    assay_inv["payload"]["proc"]["artifacts"] = [
        {"relpath": "ASSAY.json", "sha256": assay_sha,
         "bytes": len(assay_bytes)}]
    (art / "assay").mkdir(parents=True)
    (art / "assay" / "ASSAY.json").write_bytes(assay_bytes)
    (art / "assay" / "RESULT.json").write_text('{"rc": 0}\n')
    assay_inv["payload"]["result_ref"] = str(art / "assay" / "RESULT.json")
    led.append(assay_inv)
    rep["artifacts"].append({"step": "assay", "relpath": "ASSAY.json",
                            "sha256": assay_sha, "bytes": len(assay_bytes)})
    rp, lp, _ = commit(d, art, rep, led)
    check("P6 seven-step pins universe (assay evidence-bound, VALID)",
          [str(rp), str(lp), str(art), str(pinp)], True)

    d, art, rep, led = fresh("n9-done-unmatched")
    extra = copy.deepcopy(next(
        e for e in led if e.get("kind") == "proc_begin"
        and e["payload"].get("step") == "suite-r1"))
    extra["payload"]["invoke_id"] = "proc-s5a10readiness-suite-r1-a2"
    extra["payload"]["scratch"] = extra["payload"]["scratch"].replace(
        "attempt1", "attempt2")
    led.append(extra)
    rp, lp, _ = commit(d, art, rep, led)
    adir = art / "suite-r1" / "attempt-2"
    adir.mkdir(parents=True)
    (adir / "DONE.json").write_text('{"ok": true}\n')
    check("N9 DONE present on unmatched begin",
          [str(rp), str(lp), str(art), str(PINS)], False, "has DONE.json")

    d, art, rep, led = fresh("n10-deny")
    led.append({"actor": "RELCHECK", "at": "2026-10-06T11:33:00+00:00",
                "contract_version": "0", "kind": "deny",
                "payload": {"reason": "synthetic"}, "seq": 999})
    rp, lp, _ = commit(d, art, rep, led)
    check("N10 deny present", [str(rp), str(lp), str(art), str(PINS)],
          False, "deny entry present")

    print("--- lane negatives ---")
    check("N13 ledger lane on direct report", [
        str(DIRECT / "package/RELCHECK-REPORT.json"),
        str(HOST / "ledger.jsonl"), str(DIRECT_ART), str(PINS)],
        False, "mode skew")
    # Direct-lane stamp rc flip.
    dd = ROOT / "n14-direct-rc"
    if dd.exists():
        shutil.rmtree(dd)
    dd.mkdir(parents=True)
    shutil.copytree(DIRECT / "steps", dd / "steps")
    shutil.copy(DIRECT / "direct-ledger.jsonl", dd / "direct-ledger.jsonl")
    sp = dd / "steps" / "suite-r1-RESULT.json"
    stamp = json.loads(sp.read_text())
    stamp["rc"] = 1
    sp.write_text(json.dumps(stamp, indent=2) + "\n")
    check("N14 direct stamp rc=1", [
        str(DIRECT / "package/RELCHECK-REPORT.json"), "--no-ledger",
        "--stamps", str(dd), str(DIRECT_ART), str(PINS)],
        False, "stamp suite-r1 rc=1")
    # Direct-lane run-log argv skew.
    dd = ROOT / "n15-direct-argv"
    if dd.exists():
        shutil.rmtree(dd)
    dd.mkdir(parents=True)
    shutil.copytree(DIRECT / "steps", dd / "steps")
    rows = [json.loads(ln) for ln in
            (DIRECT / "direct-ledger.jsonl").read_text().splitlines()]
    rows[0]["argv"] = ["python3", "inputs/evil.py", "--step", "identity"]
    (dd / "direct-ledger.jsonl").write_text(
        "\n".join(json.dumps(r) for r in rows) + "\n")
    check("N15 direct run-log argv skew", [
        str(DIRECT / "package/RELCHECK-REPORT.json"), "--no-ledger",
        "--stamps", str(dd), str(DIRECT_ART), str(PINS)],
        False, "argv skew")

    print("--- direct U-baseline log shape ---")
    dd = direct_relog("p7-direct-worker2-log", None)
    check("P7 direct worker2-format log (end rows bind, VALID)", [
        str(DIRECT / "package/RELCHECK-REPORT.json"), "--no-ledger",
        "--stamps", str(dd), str(DIRECT_ART), str(PINS)], True)

    def _retry(ends, rows):
        first = ends["suite-r1"]
        first["rc"] = 1
        rows.append({"event": "attempt_start", "run_id": "u-battery",
                     "step": "suite-r1", "attempt": 2,
                     "started_at": "2026-10-06T12:00:02+00:00",
                     "argv": first["argv"],
                     "argv_sha256": first["argv_sha256"],
                     "input_hashes": first["input_hashes"],
                     "env_extra_keys": []})
        rows.append(dict(first, attempt=2, rc=0,
                         started_at="2026-10-06T12:00:03+00:00"))

    dd = direct_relog("p8-direct-retry", _retry)
    check("P8 direct retry converges (last end row binds, VALID)", [
        str(DIRECT / "package/RELCHECK-REPORT.json"), "--no-ledger",
        "--stamps", str(dd), str(DIRECT_ART), str(PINS)], True)

    def _fail(ends, rows):
        ends["suite-r1"]["rc"] = 1

    dd = direct_relog("n16-direct-final-rc", _fail)
    check("N16 direct final rc=1", [
        str(DIRECT / "package/RELCHECK-REPORT.json"), "--no-ledger",
        "--stamps", str(dd), str(DIRECT_ART), str(PINS)],
        False, "suite-r1: rc=1")

    def _nonobject(ends, rows):
        rows.append(["not", "an", "object"])

    dd = direct_relog("n17-direct-nonobject", _nonobject)
    check("N17 direct log non-object row", [
        str(DIRECT / "package/RELCHECK-REPORT.json"), "--no-ledger",
        "--stamps", str(dd), str(DIRECT_ART), str(PINS)],
        False, "not an object")

    print("---")
    if FAILURES:
        print(f"BATTERY FAIL: {len(FAILURES)} case(s): {FAILURES}")
        return 1
    print("BATTERY PASS: all expectations met")
    return 0


if __name__ == "__main__":
    sys.exit(main())
