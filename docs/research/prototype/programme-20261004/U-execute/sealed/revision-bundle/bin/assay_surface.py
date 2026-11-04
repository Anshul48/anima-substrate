#!/usr/bin/env python3
"""assay_surface.py — pre-flight pins/roster integrity assay (held-out revision).

Reads the staged pins.json, checks the suite-roster + surface-minimum schema
integrity, and always emits ASSAY-SURFACE.json. Infallible by design: every
failure mode is captured inside the report; exit status is always 0.
Stdlib only. Paths are CWD-relative (step workdir convention).
"""
import json
import os
import sys

OUTPUT = "ASSAY-SURFACE.json"
PIN_CANDIDATES = (
    os.path.join("inputs", "pins.json"),
    "pins.json",
)


def check_suite_roster(pins):
    """Every suite release: tree + programs[] with file/kind/log; unittest
    entries carry non-negative int expectations."""
    suites = pins.get("suites")
    if not isinstance(suites, dict) or not suites:
        return False, "suites missing or empty", 0
    n_programs = 0
    for rel, spec in suites.items():
        if not isinstance(spec, dict):
            return False, "suite %r not a mapping" % (rel,), n_programs
        if not spec.get("tree"):
            return False, "suite %r missing tree" % (rel,), n_programs
        programs = spec.get("programs")
        if not isinstance(programs, list) or not programs:
            return False, "suite %r has no programs" % (rel,), n_programs
        for i, prog in enumerate(programs):
            if not isinstance(prog, dict):
                return False, "suite %r program %d not a mapping" % (rel, i), n_programs
            for key in ("file", "kind", "log"):
                if not prog.get(key):
                    return False, "suite %r program %d missing %r" % (rel, i, key), n_programs
            if prog["kind"] == "unittest":
                for key in ("expect_tests", "expect_skipped"):
                    val = prog.get(key)
                    if not isinstance(val, int) or val < 0:
                        return False, "suite %r program %d bad %r" % (rel, i, key), n_programs
            n_programs += 1
    return True, "roster ok", n_programs


def check_surface_min(pins):
    """Every release: non-empty api_functions + cli_verbs string lists."""
    surface = pins.get("surface_min")
    if not isinstance(surface, dict) or not surface:
        return False, "surface_min missing or empty", 0
    n_funcs = 0
    for rel, spec in surface.items():
        if not isinstance(spec, dict):
            return False, "surface %r not a mapping" % (rel,), n_funcs
        for key in ("api_functions", "cli_verbs"):
            vals = spec.get(key)
            if not isinstance(vals, list) or not vals:
                return False, "surface %r empty %r" % (rel, key), n_funcs
            if not all(isinstance(v, str) and v for v in vals):
                return False, "surface %r %r has non-string" % (rel, key), n_funcs
        n_funcs += len(spec["api_functions"])
    return True, "surface minima ok", n_funcs


def check_cross_coverage(pins):
    """Every suite release has a surface minimum."""
    suites = pins.get("suites") or {}
    surface = pins.get("surface_min") or {}
    missing = sorted(set(suites) - set(surface))
    if missing:
        return False, "no surface minimum for: %s" % ",".join(missing)
    return True, "all suite releases covered"


def main(argv):
    step = "assay-surface"
    for i, arg in enumerate(argv):
        if arg == "--step" and i + 1 < len(argv):
            step = argv[i + 1]
    checks = []
    pins = None
    pins_source = None
    for cand in PIN_CANDIDATES:
        if os.path.isfile(cand):
            pins_source = cand
            break
    if pins_source is None:
        checks.append({"name": "pins_present", "pass": False,
                       "detail": "no staged pins.json found"})
        pins = {}
    else:
        try:
            with open(pins_source, "r", encoding="utf-8") as fh:
                pins = json.load(fh)
        except (OSError, ValueError) as exc:
            checks.append({"name": "pins_present", "pass": False,
                           "detail": "pins unreadable: %s" % exc})
            pins = {}
        else:
            checks.append({"name": "pins_present", "pass": True,
                           "detail": pins_source})
    if pins:
        ok, detail, n_programs = check_suite_roster(pins)
        checks.append({"name": "suite_roster", "pass": ok, "detail": detail,
                       "programs": n_programs})
        ok, detail, n_funcs = check_surface_min(pins)
        checks.append({"name": "surface_min", "pass": ok, "detail": detail,
                       "api_functions": n_funcs})
        ok, detail = check_cross_coverage(pins)
        checks.append({"name": "cross_coverage", "pass": ok, "detail": detail})
    report = {
        "assay": "surface-roster-integrity",
        "step": step,
        "pins_source": pins_source,
        "pass": all(c["pass"] for c in checks),
        "checks": checks,
    }
    try:
        with open(OUTPUT, "w", encoding="utf-8") as fh:
            json.dump(report, fh, indent=2, sort_keys=True)
            fh.write("\n")
    except OSError as exc:
        sys.stdout.write("assay-surface: OUTPUT WRITE FAILED: %s\n" % exc)
        return 0
    sys.stdout.write("assay-surface: pass=%s checks=%d output=%s\n"
                     % (report["pass"], len(checks), OUTPUT))
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main(sys.argv[1:]))
    except Exception as exc:  # infallible: still emit a report
        try:
            with open(OUTPUT, "w", encoding="utf-8") as fh:
                json.dump({"assay": "surface-roster-integrity",
                           "pass": False,
                           "checks": [{"name": "assay_crash", "pass": False,
                                       "detail": "%s: %s" % (type(exc).__name__, exc)}]},
                          fh, indent=2, sort_keys=True)
                fh.write("\n")
        except OSError:
            pass
        sys.stdout.write("assay-surface: pass=False (assay crashed, report emitted)\n")
        sys.exit(0)
