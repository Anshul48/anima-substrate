#!/usr/bin/env python3
"""U-execute leg driver — executes RUNBOOK.md §H/§D + reveal verbatim.

Sequential legs (P12 quiet-load): H-clean, D-clean, H-kill, D-kill,
reveal+derive, H-change, D-change. Every executing invocation is
printed and appended to the leg CMDS.log (touch attestation, C2).
Stops cleanly (no partial leg) if the box never quiets or a gate
fails; voids/aborts follow RUNBOOK/C1 (preserved, never silent).

Usage: python3 U-execute/run-legs.py [--legs H-clean,D-clean,...]
       (default: all six + reveal in RUNBOOK order)
"""
import json
import os
import shutil
import signal
import subprocess
import sys
import time

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", ".."))
U = os.path.join(ROOT, "prototype", "programme-20261004", "U-execute")
S5 = os.path.join(ROOT, "prototype", "successor-005")
UPINS = os.path.join(U, "frozen-pins.json")
VENV_PY = os.path.join(ROOT, "prototype", "w1", ".venv", "bin", "python")
BASE_BUNDLE = os.path.join(S5, "vehicle", "relcheck")

RUNS = os.path.join(U, "runs")
H_CC = os.path.join(RUNS, "H-CC")
H_K = os.path.join(RUNS, "H-K")

ORDER = ["H-clean", "D-clean", "H-kill", "D-kill", "REVEAL",
         "H-change", "D-change", "D-clean-R2", "D-kill-R2"]


def shlex_join(argv):
    out = []
    for a in argv:
        a = str(a)
        if any(c in a for c in " \t\n\"'\\$`"):
            a = "'" + a.replace("'", "'\\''") + "'"
        out.append(a)
    return " ".join(out)


class Leg:
    def __init__(self, name, dirname=None):
        self.name = name
        self.arm, self.leg = name.split("-", 1)
        self.dir = os.path.join(RUNS, dirname or name)
        os.makedirs(self.dir, exist_ok=True)
        self.cmds = open(os.path.join(self.dir, "CMDS.log"), "a")
        self.touches = 0

    def log(self, msg):
        line = "[%s] %s" % (time.strftime("%Y-%m-%dT%H:%M:%SZ",
                                          time.gmtime()), msg)
        print(line, flush=True)
        self.cmds.write(line + "\n")
        self.cmds.flush()

    def run(self, argv, touch=False, check=True, outfile=None, cwd=None):
        self.log("CMD: " + shlex_join(argv))
        t0 = time.time()
        env = dict(os.environ, PYTHONDONTWRITEBYTECODE="1")
        p = subprocess.run([str(a) for a in argv], cwd=cwd or ROOT, env=env,
                           stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                           text=True)
        wall = time.time() - t0
        self.log("rc=%d wall=%.1fs out_bytes=%d" % (p.returncode, wall,
                                                    len(p.stdout)))
        tail = p.stdout[-3000:]
        for ln in tail.splitlines():
            self.log("  | " + ln)
        if outfile:
            with open(outfile, "w") as f:
                f.write(p.stdout)
        if touch:
            self.touches += 1
            self.log("touch #%d" % self.touches)
        if check and p.returncode != 0:
            raise RuntimeError("%s failed rc=%d" % (argv[1], p.returncode))
        return p, wall


def load1():
    return float(open("/proc/loadavg").read().split()[0])


def wait_quiet(leg, limit=2.0, budget_s=21600):
    t0 = time.time()
    while True:
        v = load1()
        if v <= limit:
            leg.log("launch load %.2f <= %.1f OK" % (v, limit))
            return v
        if time.time() - t0 > budget_s:
            raise RuntimeError("box never quieted (load %.2f)" % v)
        leg.log("load %.2f > %.1f; waiting 60s" % (v, limit))
        time.sleep(60)


def freeze(leg, tag):
    out = os.path.join(leg.dir, "freeze-%s.json" % tag)
    leg.run([sys.executable, os.path.join(U, "u-harness.py"),
             "freeze-check", "--upins", UPINS, "--out", out])
    return out


def assemble_inputs(leg, bundle_dir, bundle_sha, key, world_root, nonce,
                    run_id, mode):
    inp = os.path.join(leg.dir, "inputs")
    os.makedirs(inp, exist_ok=True)
    for fn in ("relcheck.py", "pins.json"):
        src = os.path.join(bundle_dir, fn)
        if not os.path.isfile(src):  # change legs: bundle may nest under bin/
            alt = os.path.join(bundle_dir, "bin", fn)
            src = alt if os.path.isfile(alt) else src
        shutil.copyfile(src, os.path.join(inp, fn))
    upins = json.load(open(UPINS))
    params = {"params_format": 1, "mode": mode, "nonce": nonce,
              "run_id": run_id, "idem_key": key,
              "run_root": os.path.abspath(world_root),
              "artifacts_dir": os.path.join(os.path.abspath(world_root),
                                            "artifacts", "proc-" + key),
              "bundle_sha256": bundle_sha,
              "frozen": upins["frozen"]}
    with open(os.path.join(inp, "params.json"), "w") as f:
        json.dump(params, f, sort_keys=True, indent=2)
    leg.log("inputs assembled from %s (bundle %s...)" %
            (bundle_dir, bundle_sha[:16]))
    return inp


def h_create(leg, root, world, bundle_dir):
    leg.run([sys.executable, os.path.join(S5, "release.py"), "ops",
             "create-proc-world", "--state-dir", root, "--world", world,
             "--bundle", bundle_dir, "--reason",
             "u-execute-%s" % leg.name])


def h_run_proc(leg, root, world, key, inputs, touch=True):
    p, wall = leg.run([sys.executable, os.path.join(S5, "release.py"),
                       "ops", "run-procedure", "--state-dir", root,
                       "--world",
                       world, "--procedure", "relcheck", "--key", key,
                       "--inputs", inputs], touch=touch, check=False)
    return p, wall


def h_inspect(leg, root):
    out = os.path.join(leg.dir, "inspect.json")
    leg.run([sys.executable, os.path.join(S5, "release.py"), "inspect",
             "--state-dir", root, "--json"], outfile=out)


def h_eval(leg, root, world, key, freeze_pre, extra=()):
    leg.run([sys.executable, os.path.join(U, "u-harness.py"), "eval-leg",
             "--arm", "H", "--leg", leg.leg, "--out",
             os.path.join(leg.dir, "LEG-VERDICT.json"), "--pins", UPINS,
             "--venv-py", VENV_PY, "--freeze-pre", freeze_pre,
             "--state-dir", root, "--world", world, "--procedure",
             "relcheck", "--key", key, "--touch-count", str(leg.touches),
             "--touch-log", os.path.join(leg.dir, "CMDS.log"),
             "--inspect-json", os.path.join(leg.dir, "inspect.json"),
             "--rubric-scores", "null"] + list(extra))


def frozen_flags():
    upins = json.load(open(UPINS))
    flags = []
    for tag in ("r1", "r2", "r3", "s002", "s003", "s004"):
        flags += ["--frozen", "%s=%s" % (tag, upins["frozen"][tag])]
    return flags


def d_run(leg, bundle_dir, work, run_id, pins, touch=True):
    p, wall = leg.run([sys.executable, os.path.join(U, "direct_run.py"),
                       "--bundle", bundle_dir, "--work", work] +
                      frozen_flags() + ["--pins", pins, "--run-id", run_id,
                                        "--nonce", run_id],
                      touch=touch, check=False)
    return p, wall


def d_eval(leg, work, bundle_dir, pins, freeze_pre):
    leg.run([sys.executable, os.path.join(U, "u-harness.py"), "eval-leg",
             "--arm", "D", "--leg", leg.leg, "--out",
             os.path.join(leg.dir, "LEG-VERDICT.json"), "--pins", pins,
             "--venv-py", VENV_PY, "--freeze-pre", freeze_pre,
             "--work", work, "--bundle", bundle_dir,
             "--rubric-scores", "null"])


def spawn_session(argv, cwd):
    env = dict(os.environ, PYTHONDONTWRITEBYTECODE="1")
    log = open(os.path.join(cwd, "spawn.log"), "ab")
    p = subprocess.Popen([str(a) for a in argv], cwd=ROOT, env=env,
                         stdout=log, stderr=subprocess.STDOUT,
                         start_new_session=True)
    return p, p.pid  # pgid == child pid (session leader)


def kill_leg_h(leg, root, world, key, inputs):
    argv = [sys.executable, os.path.join(S5, "release.py"), "ops",
             "run-procedure",
            "--state-dir", root, "--world", world, "--procedure",
            "relcheck", "--key", key, "--inputs", inputs]
    leg.log("CMD(session): " + shlex_join(argv))
    proc, pgid = spawn_session(argv, leg.dir)
    leg.log("spawned pgid=%d" % pgid)
    leg.touches += 1
    leg.log("touch #1 (attempt 1)")
    w, _ = leg.run([sys.executable, os.path.join(U, "u-harness.py"),
                    "kill-watch", "--pgid", str(pgid), "--signal",
                    "ledger:%s/ledger.jsonl:suite-r3:%s" % (root, key),
                    "--delay", "55.4", "--window", "27.7", "83.0",
                    "--log", os.path.join(leg.dir, "kill.json"),
                    "--poll", "0.2"], check=False)
    rc = proc.wait()
    leg.log("reaped attempt-1 rc=%d; watcher rc=%d" % (rc, w.returncode))
    if w.returncode == 2:
        leg.log("VOID: out-of-window kill (C1)")
        return "VOID"
    if w.returncode != 0:
        raise RuntimeError("kill-watch failed rc=%d" % w.returncode)
    # resume, same key
    p, wall = h_run_proc(leg, root, world, key, inputs)
    if p.returncode != 0 and "adopt" in p.stdout.lower():
        leg.touches -= 1  # refused resume = 0 touches (RUNBOOK)
        leg.log("adopt-needed refusal (0 touches); recover touch")
        leg.run([sys.executable, os.path.join(S5, "release.py"), "ops",
                 "recover", "--state-dir", root,
                 "--reason", "u-execute-kill-resume"], touch=True)
        p, wall = h_run_proc(leg, root, world, key, inputs)
    if p.returncode != 0:
        return leg_failed(leg, "H-kill-resume", p.returncode)
    leg.log("resume wall=%.1fs touches=%d" % (wall, leg.touches))
    return "OK"


def kill_leg_d(leg, bundle_dir, work, run_id, pins):
    argv = ([sys.executable, os.path.join(U, "direct_run.py"), "--bundle",
            bundle_dir, "--work", work] + frozen_flags() +
           ["--pins", pins, "--run-id", run_id, "--nonce", run_id])
    leg.log("CMD(session): " + shlex_join(argv))
    proc, pgid = spawn_session(argv, leg.dir)
    leg.log("spawned pgid=%d" % pgid)
    leg.touches += 1
    leg.log("touch #1 (attempt 1)")
    w, _ = leg.run([sys.executable, os.path.join(U, "u-harness.py"),
                    "kill-watch", "--pgid", str(pgid), "--signal",
                    "runlog:%s/direct-ledger.jsonl:suite-r3" % work,
                    "--delay", "55.7", "--window", "27.9", "83.6",
                    "--log", os.path.join(leg.dir, "kill.json"),
                    "--poll", "0.2"], check=False)
    rc = proc.wait()
    leg.log("reaped attempt-1 rc=%d; watcher rc=%d" % (rc, w.returncode))
    if w.returncode == 2:
        leg.log("VOID: out-of-window kill (C1)")
        return "VOID"
    if w.returncode != 0:
        raise RuntimeError("kill-watch failed rc=%d" % w.returncode)
    p, wall = d_run(leg, bundle_dir, work, run_id, pins)
    if p.returncode != 0:
        return leg_failed(leg, "D-kill-resume", p.returncode)
    leg.log("resume wall=%.1fs touches=%d" % (wall, leg.touches))
    return "OK"


def leg_failed(leg, what, rc):
    """Record a leg procedure failure and let the driver continue (C11-003)."""
    leg.log("PROCEDURE-FAILED %s rc=%d — evidence preserved, continuing"
            % (what, rc))
    with open(os.path.join(leg.dir, "LEG-STATUS.json"), "w") as f:
        json.dump({"status": "PROCEDURE-FAILED", "what": what, "rc": rc,
                   "at": time.strftime("%Y-%m-%dT%H:%M:%SZ",
                                       time.gmtime()),
                   "note": "coordinator records the leg verdict by hand; "
                           "eval-leg needs a package report (C11-NOTE-003)"},
                  f, indent=1, sort_keys=True)
    freeze(leg, "post")
    leg.log("freeze-post kept (frozen-intact evidence)")
    return "FAILED"


def base_bundle_sha():
    return json.load(open(UPINS))["bundle_sha256"]


def do_clean_h():
    leg = Leg("H-clean")
    wait_quiet(leg)
    fpre = freeze(leg, "pre")
    key, world = "uclean-h1", "U-clean"
    inp = assemble_inputs(leg, BASE_BUNDLE, base_bundle_sha(), key, H_CC,
                          "uclean-h1", "uclean-h1", "host")
    h_create(leg, H_CC, world, BASE_BUNDLE)
    p, wall = h_run_proc(leg, H_CC, world, key, inp)
    if p.returncode != 0:
        return leg_failed(leg, "H-clean", p.returncode)
    leg.log("clean wall=%.1fs" % wall)
    if wall < 60:
        raise RuntimeError("I4 ABORT: honest clean wall <60s")
    h_inspect(leg, H_CC)
    freeze(leg, "post")
    h_eval(leg, H_CC, world, key, fpre)


def do_clean_d():
    leg = Leg("D-clean")
    wait_quiet(leg)
    fpre = freeze(leg, "pre")
    work = os.path.join(leg.dir, "work")
    p, wall = d_run(leg, BASE_BUNDLE, work, "uclean-d1", UPINS)
    if p.returncode != 0:
        return leg_failed(leg, "D-clean", p.returncode)
    leg.log("clean wall=%.1fs" % wall)
    if wall < 60:
        raise RuntimeError("I4 ABORT: honest clean wall <60s")
    freeze(leg, "post")
    d_eval(leg, work, BASE_BUNDLE, UPINS, fpre)


def do_kill_h():
    leg = Leg("H-kill")
    wait_quiet(leg)
    fpre = freeze(leg, "pre")
    key, world = "ukill-h1", "U-kill"
    inp = assemble_inputs(leg, BASE_BUNDLE, base_bundle_sha(), key, H_K,
                          "ukill-h1", "ukill-h1", "host")
    h_create(leg, H_K, world, BASE_BUNDLE)
    res = kill_leg_h(leg, H_K, world, key, inp)
    if res == "FAILED":
        return res  # leg_failed already froze; coordinator records verdict
    h_inspect(leg, H_K)
    freeze(leg, "post")
    h_eval(leg, H_K, world, key, fpre)
    return res


def do_kill_d():
    leg = Leg("D-kill")
    wait_quiet(leg)
    fpre = freeze(leg, "pre")
    work = os.path.join(leg.dir, "work")
    res = kill_leg_d(leg, BASE_BUNDLE, work, "ukill-d1", UPINS)
    if res == "FAILED":
        return res  # leg_failed already froze; coordinator records verdict
    freeze(leg, "post")
    d_eval(leg, work, BASE_BUNDLE, UPINS, fpre)
    return res


def do_reveal():
    leg = Leg("REVEAL-x", dirname="reveal")  # evidence-only leg dir
    p, _ = leg.run([sys.executable, os.path.join(U, "u-harness.py"),
                    "derive-revised-pins", "--sealed",
                    os.path.join(U, "sealed"), "--base-upins", UPINS,
                    "--base-bundle", BASE_BUNDLE, "--out",
                    os.path.join(leg.dir, "revised-pins.json"),
                    "--transcript",
                    os.path.join(leg.dir, "derive-transcript.json")],
                   check=False)
    if p.returncode == 2:
        leg.log("VOID: incomplete-envelope reveal (C6/C1)")
        return None
    if p.returncode != 0:
        raise RuntimeError("derive failed rc=%d" % p.returncode)
    t = json.load(open(os.path.join(leg.dir, "derive-transcript.json")))
    leg.log("DERIVED bundle_dir=%s pins=%s" %
            (t.get("bundle_dir"), t.get("derived_pins_sha256",
                                        t.get("pins_sha256", "?"))))
    return t


def do_change_h(rev):
    leg = Leg("H-change")
    wait_quiet(leg)
    fpre = freeze(leg, "pre")
    bundle_dir = rev["bundle_dir"]
    bundle_sha = rev.get("revised_bundle_sha256",
                         json.load(open(os.path.join(
                             RUNS, "reveal",
                             "revised-pins.json")))["bundle_sha256"])
    key, world = "uchange-h1", "U-change"
    inp = assemble_inputs(leg, bundle_dir, bundle_sha, key, H_CC,
                          "uchange-h1", "uchange-h1", "host")
    h_create(leg, H_CC, world, bundle_dir)
    p, wall = h_run_proc(leg, H_CC, world, key, inp)
    if p.returncode != 0:
        return leg_failed(leg, "H-change", p.returncode)
    leg.log("change wall=%.1fs" % wall)
    h_inspect(leg, H_CC)
    freeze(leg, "post")
    h_eval(leg, H_CC, world, key, fpre,
           extra=("--key-new", key, "--worlds", "U-clean,U-change"))


def do_change_d(rev):
    leg = Leg("D-change")
    wait_quiet(leg)
    fpre = freeze(leg, "pre")
    work = os.path.join(leg.dir, "work")
    pins = os.path.join(RUNS, "reveal", "revised-pins.json")
    p, wall = d_run(leg, rev["bundle_dir"], work, "uchange-d1", pins)
    if p.returncode != 0:
        return leg_failed(leg, "D-change", p.returncode)
    leg.log("change wall=%.1fs" % wall)
    freeze(leg, "post")
    d_eval(leg, work, rev["bundle_dir"], pins, fpre)


def do_clean_d2():
    """C1 re-run of voided D-clean: identical params, fresh dir (C11-004)."""
    leg = Leg("D-clean", dirname="D-clean-R2")
    wait_quiet(leg)
    fpre = freeze(leg, "pre")
    work = os.path.join(leg.dir, "work")
    p, wall = d_run(leg, BASE_BUNDLE, work, "uclean-d1", UPINS)
    if p.returncode != 0:
        return leg_failed(leg, "D-clean-R2", p.returncode)
    leg.log("clean wall=%.1fs" % wall)
    if wall < 60:
        raise RuntimeError("I4 ABORT: honest clean wall <60s")
    freeze(leg, "post")
    d_eval(leg, work, BASE_BUNDLE, UPINS, fpre)


def do_kill_d2():
    """C1 re-run of voided D-kill: identical params, fresh dir (C11-004)."""
    leg = Leg("D-kill", dirname="D-kill-R2")
    wait_quiet(leg)
    fpre = freeze(leg, "pre")
    work = os.path.join(leg.dir, "work")
    res = kill_leg_d(leg, BASE_BUNDLE, work, "ukill-d1", UPINS)
    if res == "FAILED":
        return res
    freeze(leg, "post")
    d_eval(leg, work, BASE_BUNDLE, UPINS, fpre)
    return res


FUN = {"H-clean": do_clean_h, "D-clean": do_clean_d, "H-kill": do_kill_h,
       "D-kill": do_kill_d, "H-change": None, "D-change": None,
       "D-clean-R2": do_clean_d2, "D-kill-R2": do_kill_d2}


def main():
    want = sys.argv[1].split(",") if len(sys.argv) > 1 else list(ORDER)
    if "--legs" in want:
        want = sys.argv[sys.argv.index("--legs") + 1].split(",")
    rev = None
    results = {}
    for name in want:
        if name not in ORDER:
            raise SystemExit("unknown leg %s" % name)
        print("=" * 60, flush=True)
        print("LEG", name, flush=True)
        if name == "REVEAL":
            rev = do_reveal()
            if rev is None:
                print("REVEAL VOID — change legs blocked; stopping")
                return 2
            results[name] = "DERIVED"
        elif name in ("H-change", "D-change"):
            if rev is None:
                rp = os.path.join(RUNS, "reveal", "derive-transcript.json")
                if not os.path.isfile(rp):
                    raise SystemExit("no reveal transcript; run REVEAL first")
                rev = json.load(open(rp))
            r = (do_change_h if name == "H-change" else do_change_d)(rev)
            results[name] = r or "OK"
        else:
            r = FUN[name]()
            results[name] = r or "OK"
        print("LEG DONE", name, results[name], flush=True)
    bad = {k: v for k, v in results.items() if v not in ("OK", "DERIVED")}
    if bad:
        print("COMPLETE-WITH-FAILURES", json.dumps(bad, sort_keys=True))
    else:
        print("ALL LEGS COMPLETE")
    return 0


if __name__ == "__main__":
    sys.exit(main())
