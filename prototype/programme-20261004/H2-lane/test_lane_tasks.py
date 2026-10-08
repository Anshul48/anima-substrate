"""H2-lane novel-lane conformance tests (unittest, stdlib-only).

Builder tests for the H2 delta (L2-DESIGN §5, items H2.1/H2.2/H2.3):
schema-validated task-JSON lane path, content-derived routing inputs,
and the lane-override hook. Proves the §5 acceptance bar items (b)
and (c): loud schema refusals with no partials, derivation matching
hand-computed values on a pinned set, S1/S2-by-JSON == S1/S2-by-name
(byte-exact lanes + 655/0 + 310/500 + 2.61x calibration), override
recording, unset-hook byte-identity, conservation + kill-resume
convergence on a novel lane task, and clean inspect.

Run from the repo root:
    PYTHONDONTWRITEBYTECODE=1 python3 prototype/programme-20261004/H2-lane/test_lane_tasks.py

All run dirs live under H2-lane/.test-tmp/ (nothing is written
outside H2-lane/).
"""
from __future__ import annotations

import copy
import json
import os
import shutil
import subprocess
import sys
import time
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

from routing import (derive_routing_inputs, route,  # noqa: E402
                     validate_lane_task)
from pipeline import LaneCtx, run_sched_task  # noqa: E402
from routing import ChannelRegistry, HCoordinator  # noqa: E402
from resume import scan_succeeded  # noqa: E402
import sched_inputs as FI  # noqa: E402
import calibrate  # noqa: E402
import api  # noqa: E402


def _grid(task_id, holdings, adapter="list2slot/v1", **declared):
    """Novel lane task on the frozen S1 grid with novel holdings."""
    return {"task_id": task_id,
            "slots": copy.deepcopy(FI.SLOTS),
            "tasks": copy.deepcopy(FI.BASE_TASKS),
            "precedence": copy.deepcopy(FI.BASE_PREC),
            "prefs": copy.deepcopy(FI.BASE_PREFS),
            "holdings": holdings,
            "adapter": adapter,
            **declared}


HOLD_ALL_L = {"SC-L": {"req_tasks": ["A", "B", "C", "D"],
                       "prefs": ["A", "B", "C", "D"]},
              "SC-S": {"req_tasks": [], "prefs": []}}
HOLD_SPLIT4 = {"SC-L": {"req_tasks": ["A", "B"], "prefs": ["A", "B"]},
               "SC-S": {"req_tasks": ["C", "D"], "prefs": ["C", "D"]}}
HOLD_REQ_L_PREF_S = {"SC-L": {"req_tasks": ["A", "B", "C", "D"],
                              "prefs": []},
                     "SC-S": {"req_tasks": [],
                              "prefs": ["A", "B", "C", "D"]}}
HOLD_SPLIT3 = {"SC-L": {"req_tasks": ["A", "B"],
                        "prefs": ["A", "B", "C", "D"]},
               "SC-S": {"req_tasks": ["C", "D"], "prefs": []}}

# Pinned set: task_id -> (holdings, hand-computed derived_rounds,
# hand-computed derived_split, expected rule lane).
PINNED = {
    # S1-shaped: 2 rounds (L-req + L-pref), SC-S holds nothing.
    "H2T-CENTRAL": (HOLD_ALL_L, 2, False, "central"),
    # S2-shaped: 4 rounds, both sides hold reqs+prefs.
    "H2T-LOCAL4": (HOLD_SPLIT4, 4, True, "local"),
    # 2 rounds (L-req + S-pref); SC-S holds prefs only (still split).
    "H2T-SPLIT2": (HOLD_REQ_L_PREF_S, 2, True, "local"),
    # 3 rounds (L-req + S-req + L-pref); split.
    "H2T-SPLIT3": (HOLD_SPLIT3, 3, True, "local"),
}


def _pinned_task(task_id):
    hold, _, _, _ = PINNED[task_id]
    return _grid(task_id, copy.deepcopy(hold))


class Base(unittest.TestCase):
    def setUp(self):
        self.root = HERE / ".test-tmp" / self._testMethodName
        if self.root.exists():
            shutil.rmtree(self.root)
        self.root.mkdir(parents=True)
        self.addCleanup(shutil.rmtree, self.root, True)

    def write_task(self, name, task):
        path = self.root / f"{name}.json"
        path.write_text(json.dumps(task, indent=2, sort_keys=True) + "\n",
                        encoding="utf-8")
        return path

    def ledger_entries(self, run_root):
        host, _ = api.open_run(run_root)
        return host.ledger_entries()

    def ledger_line_count(self, run_root):
        # Raw line count WITHOUT reopening: open_run appends a
        # host_reopen entry, so only the file itself proves no-partials.
        return len((Path(run_root) / "ledger.jsonl").read_text(
            encoding="utf-8").strip().splitlines())

    def routing_payloads(self, run_root):
        return [e["payload"] for e in self.ledger_entries(run_root)
                if e.get("kind") == "routing"]


class TestSchemaRefusals(Base):
    """H2.1: malformed task JSON refuses loudly, with no partial runs."""

    def mutate(self, fn):
        task = _pinned_task("H2T-LOCAL4")
        fn(task)
        return task

    def test_refusals(self):
        cases = {
            "missing-adapter": lambda t: t.pop("adapter"),
            "missing-holdings": lambda t: t.pop("holdings"),
            "missing-slots": lambda t: t.pop("slots"),
            "missing-task_id": lambda t: t.pop("task_id"),
            "empty-task_id": lambda t: t.update(task_id=""),
            "world-missing": lambda t: t["holdings"].pop("SC-S"),
            "world-extra": lambda t: t["holdings"].update(
                SC_X={"req_tasks": [], "prefs": []}),
            "unknown-req-ref": lambda t: t["holdings"]["SC-L"][
                "req_tasks"].__setitem__(0, "ZZ"),
            "unknown-pref-ref": lambda t: t["holdings"]["SC-S"][
                "prefs"].__setitem__(0, "ZZ"),
            "task-unheld": lambda t: t["holdings"]["SC-S"][
                "req_tasks"].remove("C"),
            "pref-unheld": lambda t: t["holdings"]["SC-L"][
                "prefs"].remove("A"),
            "task-held-twice": lambda t: t["holdings"]["SC-S"][
                "req_tasks"].append("A"),
            "pref-held-twice": lambda t: t["holdings"]["SC-L"][
                "prefs"].append("C"),
            "bad-adapter": lambda t: t.update(adapter="list2slot/v9"),
            "bad-window-slot": lambda t: t["tasks"]["A"].update(
                window=["S0", "S99"]),
            "bad-precedence": lambda t: t.update(precedence=[["A", "ZZ"]]),
            "bad-pref-task": lambda t: t["prefs"].update(ZZ="M0"),
        }
        for name, fn in cases.items():
            with self.subTest(name):
                with self.assertRaises(ValueError, msg=name):
                    validate_lane_task(self.mutate(fn), source=name)
        with self.assertRaises(ValueError):
            validate_lane_task(["not", "an", "object"])

    def test_no_partials_on_refusal(self):
        run = self.root / "refused"
        api.init_run(run)
        before = self.ledger_line_count(run)
        bad = self.write_task("bad", self.mutate(
            lambda t: t["holdings"].pop("SC-S")))
        with self.assertRaises(ValueError):
            api.run_tasks(run, tasks=[], task_json=[str(bad)])
        self.assertEqual(self.ledger_line_count(run), before)
        self.assertEqual(list((run / "artifacts").iterdir()), [])
        config = json.loads((run / "CONFIG.json").read_text(
            encoding="utf-8"))
        self.assertEqual(config["tasks_run"], [])
        # ... and a later valid run on the same root still works
        good = self.write_task("good", _pinned_task("H2T-LOCAL4"))
        out = api.run_tasks(run, tasks=[], task_json=[str(good)])
        self.assertTrue(out["tasks"]["H2T-LOCAL4"]["valid"])

    def test_unknown_names_still_raise(self):
        run = self.root / "names"
        api.init_run(run)
        before = self.ledger_line_count(run)
        for bad in (["S3"], ["S9"], ["S1", "S9"]):
            with self.assertRaises(ValueError, msg=bad):
                api.run_tasks(run, tasks=bad)
        self.assertEqual(self.ledger_line_count(run), before)

    def test_duplicate_ids_refused_before_work(self):
        run = self.root / "dup"
        api.init_run(run)
        before = self.ledger_line_count(run)
        f1 = self.write_task("d1", _pinned_task("H2T-LOCAL4"))
        f2 = self.write_task("d2", _pinned_task("H2T-LOCAL4"))
        with self.assertRaises(ValueError):
            api.run_tasks(run, tasks=[], task_json=[str(f1), str(f2)])
        s1 = self.write_task("s1", {**copy.deepcopy(FI.S1),
                                    "task_id": "S1"})
        with self.assertRaises(ValueError):
            api.run_tasks(run, tasks=["S1"], task_json=[str(s1)])
        self.assertEqual(self.ledger_line_count(run), before)


class TestDerivedRouting(Base):
    """H2.2: derivation matches hand-computed values; S1/S2 unchanged."""

    def test_pinned_derivation(self):
        for tid, (_, rounds, split, lane) in PINNED.items():
            with self.subTest(tid):
                task = _pinned_task(tid)
                self.assertEqual(validate_lane_task(task)["task_id"], tid)
                self.assertEqual(derive_routing_inputs(task),
                                 {"derived_rounds": rounds,
                                  "derived_split": split})
                d = route(task)
                self.assertEqual(d["rule_lane"], lane)
                self.assertEqual(d["final_lane"], lane)
                self.assertFalse(d["override"])
                self.assertEqual(d["inputs_derived_from"], "holdings")
                self.assertEqual(d["rule"],
                                 "local iff rounds>=2 AND split else central")

    def test_declared_fields_ignored_but_recorded(self):
        # S2-shaped holdings that LIE in declared fields -> still local.
        lie_local = _grid("H2T-LIE-LOCAL", copy.deepcopy(HOLD_SPLIT4),
                          expected_rounds=1, split_state=False)
        d = route(lie_local)
        self.assertEqual(d["rule_lane"], "local")
        self.assertEqual(d["inputs"], {"derived_rounds": 4,
                                       "derived_split": True})
        self.assertEqual(d["declared_ignored"], {"expected_rounds": 1,
                                                 "split_state": False})
        # S1-shaped holdings that LIE the other way -> still central.
        lie_central = _grid("H2T-LIE-CENTRAL", copy.deepcopy(HOLD_ALL_L),
                            expected_rounds=99, split_state=True)
        d = route(lie_central)
        self.assertEqual(d["rule_lane"], "central")
        self.assertEqual(d["declared_ignored"], {"expected_rounds": 99,
                                                 "split_state": True})
        # Absent declared fields record as {} (never an error).
        bare = _pinned_task("H2T-SPLIT3")
        self.assertEqual(route(bare)["declared_ignored"], {})

    def test_s1_s2_validate_and_route_as_before(self):
        for name, lane, rounds, split in (("S1", "central", 2, False),
                                          ("S2", "local", 4, True)):
            with self.subTest(name):
                task = copy.deepcopy(getattr(FI, name))
                validate_lane_task(task)
                derived = derive_routing_inputs(task)
                # Declared agrees with derived (the §5 guard condition).
                self.assertEqual(derived["derived_rounds"],
                                 task["expected_rounds"])
                self.assertEqual(derived["derived_split"],
                                 task["split_state"])
                d = route(task)
                self.assertEqual(d["rule_lane"], lane)
                self.assertEqual(d["final_lane"], lane)
                self.assertEqual(d["inputs"],
                                 {"derived_rounds": rounds,
                                  "derived_split": split})

    def test_legacy_s3_s4_s6_routing_unchanged(self):
        d3 = route({**copy.deepcopy(FI.S3), "task_id": "S3"})
        self.assertEqual(d3["lane"], "local")
        self.assertEqual(d3["rule_lane"], "local")
        self.assertEqual(
            d3["rule"],
            "local iff expected_rounds>=2 AND split_state else central")
        self.assertEqual(d3["inputs"], {"expected_rounds": 4,
                                        "split_state": True})
        self.assertFalse(d3["override"])
        self.assertEqual(api.explain_route_op("S4-followup")["lane"],
                         "fused-reuse")
        self.assertEqual(api.explain_route_op("S6-followup")["lane"],
                         "fission-reuse")
        self.assertEqual(api.explain_route_op("S3")["lane"], "local")


class TestJsonEqualsName(Base):
    """S1/S2-by-JSON == S1/S2-by-name, byte-exact lanes + EXPECTED pins."""

    def run_named(self, name, run):
        api.init_run(run)
        return api.run_tasks(run, tasks=[name])

    def run_filed(self, name, run):
        api.init_run(run)
        path = self.write_task(f"{name}-file",
                               copy.deepcopy(getattr(FI, name)))
        return api.run_tasks(run, tasks=[], task_json=[str(path)])

    def test_s1_by_json_equals_by_name(self):
        self.assertEqualPair("S1", "central", 655, 0)

    def test_s2_by_json_equals_by_name(self):
        self.assertEqualPair("S2", "local", 310, 500)

    def assertEqualPair(self, name, lane, central, direct):
        out_named = self.run_named(name, self.root / f"{name}-named")
        out_filed = self.run_filed(name, self.root / f"{name}-filed")
        for out in (out_named, out_filed):
            m = out["tasks"][name]
            self.assertEqual(m["lane"], lane)
            self.assertTrue(m["valid"])
            self.assertEqual(m["quality"], 4)
            self.assertEqual(m["prefs_total"], 4)
            self.assertEqual(m["central_bytes"], central)
            self.assertEqual(m["direct_bytes"], direct)
        # Byte-exact lanes: solution artifacts identical bytes ...
        sol_named = (self.root / f"{name}-named" / "artifacts" /
                     f"solution-{name}.json").read_bytes()
        sol_filed = (self.root / f"{name}-filed" / "artifacts" /
                     f"solution-{name}.json").read_bytes()
        self.assertEqual(sol_named, sol_filed)
        # ... and identical routing payloads (incl. derived provenance).
        pay_named = self.routing_payloads(self.root / f"{name}-named")
        pay_filed = self.routing_payloads(self.root / f"{name}-filed")
        self.assertEqual(pay_named, pay_filed)
        self.assertEqual(pay_named[0]["inputs_derived_from"], "holdings")
        self.assertFalse(pay_named[0]["override"])

    def test_calibration_2_61x(self):
        rep = calibrate.calibrate(self.root / "cal")
        self.assertEqual(rep["central_lane"],
                         {"central_bytes": 810, "direct_bytes": 0})
        self.assertEqual(rep["local_lane"],
                         {"central_bytes": 310, "direct_bytes": 500})
        self.assertEqual(rep["ratio_central_over_local"], 2.61)


class TestOverrideHook(Base):
    """H2.3: override recorded + executed; unset hook byte-identical."""

    def test_override_against_rule_executes(self):
        run = self.root / "ov-central"
        api.init_run(run)
        path = self.write_task("t", _pinned_task("H2T-LOCAL4"))
        out = api.run_tasks(run, tasks=[], task_json=[str(path)],
                            lane_override="central")
        m = out["tasks"]["H2T-LOCAL4"]
        self.assertEqual(m["lane"], "central")
        self.assertTrue(m["valid"])
        self.assertEqual(m["quality"], 4)
        # Central execution: everything through the coordinator.
        self.assertEqual(m["direct_bytes"], 0)
        self.assertGreater(m["central_bytes"], 0)
        (payload,) = self.routing_payloads(run)
        self.assertEqual(payload["rule_lane"], "local")
        self.assertTrue(payload["override"])
        self.assertEqual(payload["final_lane"], "central")
        self.assertEqual(payload["lane"], "central")

    def test_override_matching_rule_recorded(self):
        run = self.root / "ov-local"
        api.init_run(run)
        path = self.write_task("t", _pinned_task("H2T-LOCAL4"))
        out = api.run_tasks(run, tasks=[], task_json=[str(path)],
                            lane_override={"H2T-LOCAL4": "local"})
        m = out["tasks"]["H2T-LOCAL4"]
        self.assertEqual(m["lane"], "local")
        self.assertGreater(m["direct_bytes"], 0)
        (payload,) = self.routing_payloads(run)
        self.assertEqual(payload["rule_lane"], "local")
        self.assertTrue(payload["override"])
        self.assertEqual(payload["final_lane"], "local")

    def test_override_map_none_entry_is_rule(self):
        run = self.root / "ov-none"
        api.init_run(run)
        path = self.write_task("t", _pinned_task("H2T-CENTRAL"))
        out = api.run_tasks(run, tasks=[], task_json=[str(path)],
                            lane_override={"H2T-CENTRAL": None})
        self.assertEqual(out["tasks"]["H2T-CENTRAL"]["lane"], "central")
        (payload,) = self.routing_payloads(run)
        self.assertFalse(payload["override"])

    def test_bad_overrides_refused_before_work(self):
        run = self.root / "ov-bad"
        api.init_run(run)
        before = self.ledger_line_count(run)
        path = self.write_task("t", _pinned_task("H2T-LOCAL4"))
        for bad in ("sideways", {"H2T-LOCAL4": "sideways"},
                    {"NOPE": "central"}, ["central"]):
            with self.subTest(bad=bad):
                with self.assertRaises(ValueError):
                    api.run_tasks(run, tasks=[], task_json=[str(path)],
                                  lane_override=bad)
        with self.assertRaises(ValueError):
            route(_pinned_task("H2T-LOCAL4"), lane_override="sideways")
        self.assertEqual(self.ledger_line_count(run), before)

    def test_unset_hook_byte_identical(self):
        api.init_run(self.root / "unset-default")
        out_d = api.run_tasks(self.root / "unset-default", tasks=["S1"])
        api.init_run(self.root / "unset-none")
        out_n = api.run_tasks(self.root / "unset-none", tasks=["S1"],
                              lane_override=None)
        for key in ("lane", "valid", "quality", "prefs_total",
                    "central_bytes", "direct_bytes"):
            self.assertEqual(out_d["tasks"]["S1"][key],
                             out_n["tasks"]["S1"][key])
        sol_d = (self.root / "unset-default" / "artifacts" /
                 "solution-S1.json").read_bytes()
        sol_n = (self.root / "unset-none" / "artifacts" /
                 "solution-S1.json").read_bytes()
        self.assertEqual(sol_d, sol_n)
        self.assertEqual(self.routing_payloads(self.root / "unset-default"),
                         self.routing_payloads(self.root / "unset-none"))


class TestNovelConservation(Base):
    """Conservation + settle + clean inspect on novel lane tasks."""

    def test_novel_both_lanes_conserve_and_settle(self):
        run = self.root / "novel-settle"
        api.init_run(run)
        paths = [self.write_task(tid, _pinned_task(tid))
                 for tid in ("H2T-CENTRAL", "H2T-SPLIT2", "H2T-SPLIT3")]
        out = api.run_tasks(run, tasks=[], task_json=[str(p) for p in paths])
        self.assertEqual(out["tasks"]["H2T-CENTRAL"]["lane"], "central")
        self.assertEqual(out["tasks"]["H2T-SPLIT2"]["lane"], "local")
        self.assertEqual(out["tasks"]["H2T-SPLIT3"]["lane"], "local")
        for m in out["tasks"].values():
            self.assertTrue(m["valid"])
            self.assertEqual(m["quality"], 4)
        host, _ = api.open_run(run)
        self.assertTrue(host.verify_conservation()["ok"])
        insp = api.inspect_state_op(run)
        self.assertTrue(insp["conservation"]["ok"])
        self.assertEqual(insp["worlds"]["SC-L"]["lifecycle"], "active")
        self.assertEqual(len(insp["routing"]), 3)
        fin = api.settle_op(run, ["SC-L", "SC-S"], reason="novel over")
        self.assertTrue(fin["conservation_ok"])
        host2, _ = api.open_run(run)
        self.assertTrue(host2.verify_conservation()["ok"])


CHILD_PARTIAL = '''\
import sys
import time
from pathlib import Path

H2DIR = {h2dir!r}
ROOT = {root!r}
TASK = {taskpath!r}

sys.path.insert(0, H2DIR)
import json
import api
from pipeline import LaneCtx, build_clarify, build_formulate, fragment_rounds
from routing import ChannelRegistry, HCoordinator
from resume import execute_plan

task = json.loads(Path(TASK).read_text(encoding="utf-8"))
host, chans = api.open_run(ROOT)
ctx = LaneCtx("local", HCoordinator(), chans)
rounds = fragment_rounds(task)
owner, frag = rounds[0]
plan = [build_formulate(host, task, "SC-L", "v1", ctx),
        build_clarify(host, task, owner, frag, 1, len(rounds),
                      "v1", ctx,
                      "SC-S" if owner == "SC-L" else "SC-L")]
rep = execute_plan(host, plan)
assert rep["re_executed_invokes"] == 0, rep
Path(ROOT, "child.READY").write_text("ready", encoding="utf-8")
time.sleep(120)
'''


class TestNovelKillResume(Base):
    """Kill-resume converges on a novel lane task (kill-resume shape)."""

    def test_kill_resume_converges_on_novel_lane_task(self):
        run = self.root / "novel-kill"
        api.init_run(run)
        task = _pinned_task("H2T-LOCAL4")
        task_path = self.write_task("H2T-LOCAL4", task)
        child_py = self.root / "child_partial.py"
        child_py.write_text(CHILD_PARTIAL.format(
            h2dir=str(HERE), root=str(run), taskpath=str(task_path)),
            encoding="utf-8")
        child = subprocess.Popen(
            [sys.executable, str(child_py)],
            cwd=str(HERE), stdout=subprocess.PIPE, stderr=subprocess.PIPE,
            env={**os.environ, "PYTHONDONTWRITEBYTECODE": "1"})
        t0 = time.time()
        while not (run / "child.READY").exists():
            self.assertLess(time.time() - t0, 120, "child never READY")
            if child.poll() is not None:
                self.fail(f"child died early rc={child.returncode}: "
                          f"{child.stderr.read().decode()[-2000:]}")
            time.sleep(0.2)
        child.kill()  # Popen.kill(): SIGKILL/TerminateProcess
        _, err = child.communicate(timeout=60)
        self.assertNotEqual(child.returncode, 0)
        (run / "child.READY").unlink(missing_ok=True)
        # Parent reopens and finishes the SAME lane task via the
        # validated run path inputs (route + resume-by-skip).
        host, chans = api.open_run(run)
        prekill = scan_succeeded(host)
        self.assertIn(("sched.formulate", "H2T-LOCAL4", "formulate@v1"),
                      prekill)
        decision = route(copy.deepcopy(task))
        self.assertEqual(decision["rule_lane"], "local")
        m = run_sched_task(run, host, copy.deepcopy(task),
                           LaneCtx("local", HCoordinator(), chans),
                           prekill=prekill)
        self.assertTrue(m["valid"])
        self.assertEqual(m["quality"], 4)
        self.assertEqual(m["re_executed_invokes"], 0)
        self.assertIn("sched.formulate@formulate@v1", m["skipped"])
        self.assertIn("sched.clarify@clarify@r1", m["skipped"])
        self.assertTrue(host.verify_conservation()["ok"])
        insp = api.inspect_state_op(run)
        self.assertTrue(insp["conservation"]["ok"])
        fin = api.settle_op(run, ["SC-L", "SC-S"],
                            reason="novel kill-resume over")
        self.assertTrue(fin["conservation_ok"])


if __name__ == "__main__":
    unittest.main(verbosity=2)
