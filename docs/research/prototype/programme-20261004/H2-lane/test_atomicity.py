"""H2-lane R1 atomic-settle + interruption-boundary tests.

In-process refusal-atomicity proofs (fast) plus fault-injection kills
at EVERY ledger boundary of settle/fuse/fission through the consumer
CLI (release.py), including repeated kills, kill-during-recovery, and
real SIGKILLs. Recovery always goes through `ops recover`.

Run from the repo root:
    PYTHONDONTWRITEBYTECODE=1 python3 prototype/programme-20261004/H2-lane/test_atomicity.py

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

from minihost import ContractViolation  # noqa: E402
from routing import (ChannelRegistry, HCoordinator, finish_worlds,  # noqa: E402
                     setup_host, world_record)
from pipeline import (FUSED_CAPS, L_CAPS, L_REPS, S_CAPS, S_REPS,  # noqa: E402
                      LaneCtx, run_sched_task)
from fusion import fission_worlds, fuse_worlds  # noqa: E402
import sched_inputs as FI  # noqa: E402
import successor_demo as DEMO  # noqa: E402
import api  # noqa: E402

PARTITION = {"sched.composite": "SC-L2",
             "sched.requirements": "SC-L2",
             "sched.slots": "SC-S2"}
PARTITION_CLI = "sched.composite=SC-L2,sched.requirements=SC-L2,sched.slots=SC-S2"

CRASH_RC = 42


def child_env(**extra) -> dict:
    env = dict(os.environ)
    env["PYTHONDONTWRITEBYTECODE"] = "1"
    env.pop("SUBSTRATE_CRASH_AFTER_APPENDS", None)
    env.pop("SUBSTRATE_CRASH_AT", None)
    env.update(extra)
    return env


def cli(*args: str, env: dict | None = None) -> subprocess.CompletedProcess:
    return subprocess.run(
        [sys.executable, str(HERE / "release.py"), *args],
        cwd=str(HERE), env=env or child_env(),
        stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)


def inspect_json(root: Path) -> dict:
    proc = cli("inspect", "--state-dir", str(root), "--json")
    assert proc.returncode == 0, proc.stderr
    return json.loads(proc.stdout)


def ledger_lines(root: Path) -> list[dict]:
    out = []
    with open(root / "ledger.jsonl", encoding="utf-8") as fh:
        for line in fh:
            line = line.strip()
            if line:
                out.append(json.loads(line))
    return out


def kinds_of(root: Path) -> dict[str, int]:
    kinds: dict[str, int] = {}
    for e in ledger_lines(root):
        kinds[e["kind"]] = kinds.get(e["kind"], 0) + 1
    return kinds


class Base(unittest.TestCase):
    def setUp(self):
        self.root = HERE / ".test-tmp" / self._testMethodName
        if self.root.exists():
            shutil.rmtree(self.root)
        self.root.mkdir(parents=True)
        self.addCleanup(shutil.rmtree, self.root, True)

    def main_host(self):
        worlds = DEMO.main_worlds(self.root / "state")
        pristine = copy.deepcopy(worlds)
        host = setup_host(self.root, worlds)
        return host, pristine

    def cli_run(self, name: str, tasks=("S1", "S2")) -> Path:
        root = self.root / name
        proc = cli("init", "--state-dir", str(root))
        self.assertEqual(proc.returncode, 0, proc.stderr)
        proc = cli("run", "--state-dir", str(root),
                   "--tasks", ",".join(tasks))
        self.assertEqual(proc.returncode, 0, proc.stderr)
        return root

    def fresh_copy(self, template: Path, name: str) -> Path:
        dest = self.root / name
        if dest.exists():
            shutil.rmtree(dest)
        shutil.copytree(template, dest)
        return dest

class TestAtomicRefusal(Base):
    """Refusal/failure leaves ZERO partial dissolves (in-process)."""

    def test_refuse_unknown_world_zero_partials(self):
        host, _ = self.main_host()
        run_sched_task(self.root, host, FI.S1, _central_ctx())
        n_before = len(host.ledger_entries())
        with self.assertRaises(ContractViolation) as ctx:
            finish_worlds(host, ["SC-L", "SC-NOPE"], reason="t")
        self.assertIn("zero worlds dissolved", str(ctx.exception))
        self.assertEqual(host.worlds["SC-L"].lifecycle, "active")
        self.assertEqual(host.worlds["SC-S"].lifecycle, "active")
        fresh = host.ledger_entries()[n_before:]
        self.assertEqual([e["kind"] for e in fresh], ["deny"])
        host.verify_conservation()

    def test_refuse_unsettled_terminal_probe_zero_partials(self):
        # LIMITS-11's example: a pre-existing unsettled terminal used to
        # strand fresh dissolves; now the batch refuses up front.
        host, _ = self.main_host()
        run_sched_task(self.root, host, FI.S1, _central_ctx())
        host.append("lifecycle", {"world_id": "SC-GHOST", "from": "active",
                                  "to": "dissolved", "reason": "probe"},
                    actor="host")
        n_before = len(host.ledger_entries())
        with self.assertRaises(ContractViolation) as ctx:
            finish_worlds(host, ["SC-L", "SC-S"], reason="t")
        self.assertIn("zero worlds dissolved", str(ctx.exception))
        self.assertEqual(host.worlds["SC-L"].lifecycle, "active")
        self.assertEqual(host.worlds["SC-S"].lifecycle, "active")
        fresh = host.ledger_entries()[n_before:]
        self.assertEqual([e["kind"] for e in fresh], ["deny"])
        markers = [e for e in host.ledger_entries()
                   if e.get("kind") == "grant_settle"]
        self.assertEqual(markers, [])
        with self.assertRaises(ContractViolation):
            host.verify_conservation()  # pre-existing violation intact

    def test_refuse_residual_holdings_single_world(self):
        host, _ = self.main_host()
        run_sched_task(self.root, host, FI.S1, _central_ctx())
        host.holdings["SC-L"]["max_cost_usd"] += 5.0  # white-box fault
        n_before = len(host.ledger_entries())
        with self.assertRaises(ContractViolation):
            host.settle_grants("SC-L", "host", "t")
        self.assertEqual(host.worlds["SC-L"].lifecycle, "active")
        fresh = host.ledger_entries()[n_before:]
        self.assertEqual([e["kind"] for e in fresh], ["deny"])
        with self.assertRaises(ContractViolation):
            finish_worlds(host, ["SC-L", "SC-S"], reason="t")
        self.assertEqual(host.worlds["SC-S"].lifecycle, "active")

    def test_refuse_suspended_missing_checkpoint_both_orders(self):
        for order in (["SC-L", "SC-S"], ["SC-S", "SC-L"]):
            with self.subTest(order=order):
                root = self.root / f"ord-{order[0]}"
                root.mkdir(parents=True)
                worlds = DEMO.main_worlds(root / "state")
                host = setup_host(root, worlds)
                run_sched_task(root, host, FI.S1, _central_ctx())
                host.suspend("SC-S", "host", "probe",
                             pending_effects=[])
                (Path(host.worlds["SC-S"].instance_state_dir)
                 / "checkpoint.json").unlink()
                n_before = len(host.ledger_entries())
                with self.assertRaises(ContractViolation) as ctx:
                    finish_worlds(host, list(order), reason="t")
                self.assertIn("zero worlds dissolved", str(ctx.exception))
                self.assertEqual(host.worlds["SC-L"].lifecycle, "active")
                self.assertEqual(host.worlds["SC-S"].lifecycle,
                                 "suspended")
                fresh = host.ledger_entries()[n_before:]
                self.assertEqual([e["kind"] for e in fresh], ["deny"])
                host.verify_conservation()

    def test_check_settleable_side_effect_free(self):
        host, _ = self.main_host()
        run_sched_task(self.root, host, FI.S1, _central_ctx())
        ledger_before = (self.root / "ledger.jsonl").read_bytes()
        hold_before = copy.deepcopy(host.holdings)
        life_before = {w: r.lifecycle for w, r in host.worlds.items()}
        plan = host.check_settleable("SC-L")
        self.assertEqual(plan["world_id"], "SC-L")
        self.assertFalse(plan["needs_reattach"])
        with self.assertRaises(ContractViolation):
            host.check_settleable("SC-NOPE")
        host.holdings["SC-S"]["max_time_s"] += 999.0
        with self.assertRaises(ContractViolation):
            host.check_settleable("SC-S")
        self.assertEqual((self.root / "ledger.jsonl").read_bytes(),
                         ledger_before)
        self.assertEqual({w: r.lifecycle for w, r in host.worlds.items()},
                         life_before)
        hold_after = copy.deepcopy(host.holdings)
        hold_after["SC-S"]["max_time_s"] -= 999.0
        self.assertEqual(hold_after, hold_before)

    def test_fuse_rejects_unsettleable_before_mutation(self):
        host, _ = self.main_host()
        chans = ChannelRegistry()
        run_sched_task(self.root, host, FI.S2,
                       LaneCtx("local", HCoordinator(), chans))
        host.holdings["SC-S"]["max_invocations"] += 50.0
        fused_rec = world_record(self.root / "state", "SC-FUSED",
                                 FUSED_CAPS,
                                 [("sched-list", "v2"),
                                  ("sched-slot", "v2")])
        n_before = len(host.ledger_entries())
        with self.assertRaises(ContractViolation):
            fuse_worlds(host, chans, "SC-L", "SC-S", "SC-FUSED",
                        fused_rec, "host", "must not happen")
        self.assertNotIn("SC-FUSED", host.worlds)
        self.assertEqual(len(host.ledger_entries()), n_before)

    def test_fission_rejects_unsettleable_before_mutation(self):
        host, _ = self.main_host()
        chans = ChannelRegistry()
        run_sched_task(self.root, host, FI.S2,
                       LaneCtx("local", HCoordinator(), chans))
        fused_rec = world_record(self.root / "state", "SC-FUSED",
                                 FUSED_CAPS,
                                 [("sched-list", "v2"),
                                  ("sched-slot", "v2")])
        fuse_worlds(host, chans, "SC-L", "SC-S", "SC-FUSED",
                    fused_rec, "host", "setup fusion")
        host.holdings["SC-FUSED"]["max_cost_usd"] += 2.0
        l2 = world_record(self.root / "state", "SC-L2", L_CAPS, L_REPS)
        s2 = world_record(self.root / "state", "SC-S2", S_CAPS, S_REPS)
        n_before = len(host.ledger_entries())
        with self.assertRaises(ContractViolation):
            fission_worlds(host, chans, "SC-FUSED", "SC-L2", "SC-S2",
                           l2, s2, dict(PARTITION), "host", "must not")
        self.assertNotIn("SC-L2", host.worlds)
        self.assertEqual(len(host.ledger_entries()), n_before)


def _central_ctx():
    from routing import Coordinator
    return LaneCtx("central", Coordinator(), ChannelRegistry())


class TestCrashSettle(Base):
    """Kill at EVERY settle boundary (CLI), then recover (CLI)."""

    def test_settle_every_boundary(self):
        template = self.cli_run("settle-template")
        probe = self.fresh_copy(template, "growth-probe")
        before = len(ledger_lines(probe))
        proc = cli("ops", "settle", "--state-dir", str(probe),
                   "--worlds", "SC-L,SC-S", "--reason", "probe")
        self.assertEqual(proc.returncode, 0, proc.stderr)
        growth = len(ledger_lines(probe)) - before
        self.assertEqual(growth, 7)  # reopen + 2 x (return+marker+life)
        for n in range(1, growth + 2):
            with self.subTest(boundary=n):
                root = self.fresh_copy(template, f"settle-n{n}")
                proc = cli("ops", "settle", "--state-dir", str(root),
                           "--worlds", "SC-L,SC-S", "--reason", "kill",
                           env=child_env(
                               SUBSTRATE_CRASH_AFTER_APPENDS=str(n)))
                if n > growth:
                    self.assertEqual(proc.returncode, 0, proc.stderr)
                else:
                    self.assertEqual(proc.returncode, CRASH_RC)
                # inspect stays readable after the kill (fail-closed read)
                state = inspect_json(root)
                self.assertIn("conservation", state)
                # recover converges: both dissolved, 0 stranded
                proc = cli("ops", "recover", "--state-dir", str(root),
                           "--worlds", "SC-L,SC-S", "--reason", "rec")
                self.assertEqual(proc.returncode, 0, proc.stderr)
                state = inspect_json(root)
                self.assertEqual(state["worlds"]["SC-L"]["lifecycle"],
                                 "dissolved")
                self.assertEqual(state["worlds"]["SC-S"]["lifecycle"],
                                 "dissolved")
                self.assertTrue(state["conservation"]["ok"])
                kinds = kinds_of(root)
                self.assertGreaterEqual(
                    kinds.get("grant_settle", 0), 2)
                if n == 3:
                    # crashed between marker + lifecycle: the re-settle
                    # leaves a second (benign, set-semantic) marker
                    marks = [e for e in ledger_lines(root)
                             if e.get("kind") == "grant_settle"
                             and e["payload"].get("world_id") == "SC-L"]
                    self.assertEqual(len(marks), 2)
                print(f"settle N={n}: rc={CRASH_RC if n <= growth else 0} "
                      f"-> recovered markers={kinds.get('grant_settle')}")


class TestCrashFuse(Base):
    """Kill at EVERY fusion boundary (CLI), then recover (CLI)."""

    def test_fuse_every_boundary(self):
        template = self.cli_run("fuse-template")
        probe = self.fresh_copy(template, "growth-probe")
        before = len(ledger_lines(probe))
        proc = cli("ops", "fuse", "--state-dir", str(probe),
                   "--a", "SC-L", "--b", "SC-S", "--fused", "SC-FUSED",
                   "--reason", "probe")
        self.assertEqual(proc.returncode, 0, proc.stderr)
        growth = len(ledger_lines(probe)) - before
        self.assertEqual(growth, 14)
        for n in range(1, growth + 2):
            with self.subTest(boundary=n):
                root = self.fresh_copy(template, f"fuse-n{n}")
                proc = cli("ops", "fuse", "--state-dir", str(root),
                           "--a", "SC-L", "--b", "SC-S",
                           "--fused", "SC-FUSED", "--reason", "kill",
                           env=child_env(
                               SUBSTRATE_CRASH_AFTER_APPENDS=str(n)))
                if n > growth:
                    self.assertEqual(proc.returncode, 0, proc.stderr)
                    crash_rc = 0
                else:
                    self.assertEqual(proc.returncode, CRASH_RC)
                    crash_rc = CRASH_RC
                proc = cli("ops", "recover", "--state-dir", str(root),
                           "--reason", "rec")
                self.assertEqual(proc.returncode, 0, proc.stderr)
                state = inspect_json(root)
                if "SC-FUSED" not in state["worlds"]:
                    # kill before the first op append: no trace, so the
                    # op simply never happened -- re-run it cleanly.
                    self.assertEqual(n, 1)
                    proc = cli("ops", "fuse", "--state-dir", str(root),
                               "--a", "SC-L", "--b", "SC-S",
                               "--fused", "SC-FUSED", "--reason",
                               "re-run after pre-op kill")
                    self.assertEqual(proc.returncode, 0, proc.stderr)
                    state = inspect_json(root)
                self.assertEqual(state["worlds"]["SC-FUSED"]["lifecycle"],
                                 "active")
                self.assertEqual(state["worlds"]["SC-L"]["lifecycle"],
                                 "dissolved")
                self.assertEqual(state["worlds"]["SC-S"]["lifecycle"],
                                 "dissolved")
                self.assertEqual(
                    state["worlds"]["SC-FUSED"]["custodians"],
                    {"sched.composite": "SC-FUSED",
                     "sched.requirements": "SC-FUSED",
                     "sched.slots": "SC-FUSED"})
                kinds = kinds_of(root)
                self.assertEqual(kinds.get("fusion", 0), 1)
                self.assertTrue(state["conservation"]["ok"])
                specs = {s["world_id"] for s in json.loads(
                    (root / "worlds.json").read_text(encoding="utf-8"))}
                self.assertIn("SC-FUSED", specs)
                fused_art = root / "artifacts" / "fusion-SC-FUSED.json"
                note = (root / "artifacts"
                        / "recovery-fusion-SC-FUSED.json")
                self.assertTrue(fused_art.exists() or note.exists())
                # the recovered composite serves reuse (descriptors OK)
                proc = cli("ops", "reuse", "--state-dir", str(root),
                           "--composite", "SC-FUSED", "--followup", "S4")
                self.assertEqual(proc.returncode, 0, proc.stderr)
                print(f"fuse N={n}: crash_rc={crash_rc} recovered + "
                      f"reuse OK")


class TestCrashFission(Base):
    """Kill at EVERY fission boundary; partition refusal; recover."""

    def fission_template(self) -> Path:
        root = self.cli_run("fission-template")
        proc = cli("ops", "fuse", "--state-dir", str(root),
                   "--a", "SC-L", "--b", "SC-S", "--fused", "SC-FUSED",
                   "--reason", "template fusion")
        self.assertEqual(proc.returncode, 0, proc.stderr)
        return root

    def test_fission_every_boundary(self):
        template = self.fission_template()
        probe = self.fresh_copy(template, "growth-probe")
        before = len(ledger_lines(probe))
        proc = cli("ops", "fission", "--state-dir", str(probe),
                   "--composite", "SC-FUSED", "--left", "SC-L2",
                   "--right", "SC-S2", "--partition", PARTITION_CLI,
                   "--reason", "probe")
        self.assertEqual(proc.returncode, 0, proc.stderr)
        growth = len(ledger_lines(probe)) - before
        self.assertEqual(growth, 14)
        for n in range(1, growth + 2):
            with self.subTest(boundary=n):
                root = self.fresh_copy(template, f"fission-n{n}")
                proc = cli("ops", "fission", "--state-dir", str(root),
                           "--composite", "SC-FUSED", "--left", "SC-L2",
                           "--right", "SC-S2", "--partition",
                           PARTITION_CLI, "--reason", "kill",
                           env=child_env(
                               SUBSTRATE_CRASH_AFTER_APPENDS=str(n)))
                if n > growth:
                    self.assertEqual(proc.returncode, 0, proc.stderr)
                else:
                    self.assertEqual(proc.returncode, CRASH_RC)
                # bare recover: refuses IFF a partial fission exists
                bare = cli("ops", "recover", "--state-dir", str(root),
                           "--reason", "rec")
                if bare.returncode != 0:
                    self.assertIn("need operator input", bare.stderr)
                    proc = cli(
                        "ops", "recover", "--state-dir", str(root),
                        "--reason", "rec", "--fission", "SC-FUSED",
                        "--left", "SC-L2", "--right", "SC-S2",
                        "--partition", PARTITION_CLI)
                    self.assertEqual(proc.returncode, 0, proc.stderr)
                state = inspect_json(root)
                if state["worlds"]["SC-FUSED"]["lifecycle"] == "active" \
                        and kinds_of(root).get("fission", 0) == 0:
                    # kill before the first op append: no trace, so the
                    # op simply never happened -- re-run it cleanly.
                    self.assertEqual(n, 1)
                    proc = cli("ops", "fission", "--state-dir", str(root),
                               "--composite", "SC-FUSED", "--left",
                               "SC-L2", "--right", "SC-S2", "--partition",
                               PARTITION_CLI, "--reason",
                               "re-run after pre-op kill")
                    self.assertEqual(proc.returncode, 0, proc.stderr)
                    state = inspect_json(root)
                self.assertEqual(state["worlds"]["SC-FUSED"]["lifecycle"],
                                 "dissolved")
                self.assertEqual(state["worlds"]["SC-L2"]["lifecycle"],
                                 "active")
                self.assertEqual(state["worlds"]["SC-S2"]["lifecycle"],
                                 "active")
                self.assertEqual(
                    state["worlds"]["SC-L2"]["custodians"],
                    {"sched.composite": "SC-L2",
                     "sched.requirements": "SC-L2"})
                self.assertEqual(state["worlds"]["SC-S2"]["custodians"],
                                 {"sched.slots": "SC-S2"})
                kinds = kinds_of(root)
                self.assertEqual(kinds.get("fission", 0), 1)
                self.assertTrue(state["conservation"]["ok"])
                print(f"fission N={n}: bare_rc={bare.returncode} "
                      f"-> converged")

    def test_fission_wrong_partition_refused(self):
        template = self.fission_template()
        root = self.fresh_copy(template, "fission-wrongpart")
        proc = cli("ops", "fission", "--state-dir", str(root),
                   "--composite", "SC-FUSED", "--left", "SC-L2",
                   "--right", "SC-S2", "--partition", PARTITION_CLI,
                   "--reason", "kill",
                   env=child_env(SUBSTRATE_CRASH_AFTER_APPENDS="9"))
        self.assertEqual(proc.returncode, CRASH_RC)
        bad = ("sched.composite=SC-S2,sched.requirements=SC-L2,"
               "sched.slots=SC-L2")
        proc = cli("ops", "recover", "--state-dir", str(root),
                   "--reason", "rec", "--fission", "SC-FUSED",
                   "--left", "SC-L2", "--right", "SC-S2",
                   "--partition", bad)
        self.assertNotEqual(proc.returncode, 0)
        self.assertIn("contradicts", proc.stderr)
        # ... and the correct partition still completes afterwards
        proc = cli("ops", "recover", "--state-dir", str(root),
                   "--reason", "rec", "--fission", "SC-FUSED",
                   "--left", "SC-L2", "--right", "SC-S2",
                   "--partition", PARTITION_CLI)
        self.assertEqual(proc.returncode, 0, proc.stderr)


class TestPreSpecCrash(Base):
    """Kill between ledger-complete and worlds.json write."""

    def test_fuse_pre_spec_withheld_then_repaired(self):
        root = self.cli_run("prespec-fuse")
        proc = cli("ops", "fuse", "--state-dir", str(root),
                   "--a", "SC-L", "--b", "SC-S", "--fused", "SC-FUSED",
                   "--reason", "kill",
                   env=child_env(SUBSTRATE_CRASH_AT="api:fuse:pre-spec"))
        self.assertEqual(proc.returncode, CRASH_RC)
        kinds = kinds_of(root)
        self.assertEqual(kinds.get("fusion", 0), 1)  # ledger complete
        specs = {s["world_id"] for s in json.loads(
            (root / "worlds.json").read_text(encoding="utf-8"))}
        self.assertNotIn("SC-FUSED", specs)  # ... but specs stale
        # the composite reopens WITHHELD: its invokes deny (fail-closed)
        host, _ = api.open_run(root)
        with self.assertRaises(ContractViolation):
            host.invoke("SC-FUSED", "SC-FUSED", "sched.reuse", "1.0",
                        host.store_args("SC-FUSED", "pre", {}),
                        lambda: "never")
        # recover repairs the specs; reuse serves again
        rep = api.recover_op(root)
        self.assertEqual(rep["specs_repaired"], ["SC-FUSED"])
        self.assertEqual(rep["fusions_completed"], [])
        proc = cli("ops", "reuse", "--state-dir", str(root),
                   "--composite", "SC-FUSED", "--followup", "S4")
        self.assertEqual(proc.returncode, 0, proc.stderr)
        note = (root / "artifacts"
                / "recovery-fusion-SC-FUSED.json")
        self.assertTrue(note.exists())

    def test_fission_pre_spec_repaired(self):
        root = self.cli_run("prespec-fission")
        proc = cli("ops", "fuse", "--state-dir", str(root),
                   "--a", "SC-L", "--b", "SC-S", "--fused", "SC-FUSED",
                   "--reason", "setup")
        self.assertEqual(proc.returncode, 0, proc.stderr)
        proc = cli("ops", "fission", "--state-dir", str(root),
                   "--composite", "SC-FUSED", "--left", "SC-L2",
                   "--right", "SC-S2", "--partition", PARTITION_CLI,
                   "--reason", "kill",
                   env=child_env(
                       SUBSTRATE_CRASH_AT="api:fission:pre-spec"))
        self.assertEqual(proc.returncode, CRASH_RC)
        self.assertEqual(kinds_of(root).get("fission", 0), 1)
        rep = api.recover_op(root)
        self.assertEqual(sorted(rep["specs_repaired"]),
                         ["SC-L2", "SC-S2"])
        self.assertEqual(rep["fissions_completed"], [])
        state = inspect_json(root)
        self.assertEqual(state["worlds"]["SC-L2"]["lifecycle"], "active")
        self.assertTrue(state["conservation"]["ok"])


class TestRepeatedKills(Base):
    """Kill during recovery converges on re-run (all ops)."""

    def test_settle_kill_during_recovery(self):
        root = self.cli_run("rep-settle")
        proc = cli("ops", "settle", "--state-dir", str(root),
                   "--worlds", "SC-L,SC-S", "--reason", "kill",
                   env=child_env(SUBSTRATE_CRASH_AFTER_APPENDS="4"))
        self.assertEqual(proc.returncode, CRASH_RC)
        proc = cli("ops", "recover", "--state-dir", str(root),
                   "--worlds", "SC-L,SC-S", "--reason", "rec",
                   env=child_env(SUBSTRATE_CRASH_AFTER_APPENDS="3"))
        self.assertEqual(proc.returncode, CRASH_RC)
        proc = cli("ops", "recover", "--state-dir", str(root),
                   "--worlds", "SC-L,SC-S", "--reason", "rec")
        self.assertEqual(proc.returncode, 0, proc.stderr)
        state = inspect_json(root)
        self.assertTrue(state["conservation"]["ok"])
        self.assertEqual(state["worlds"]["SC-L"]["lifecycle"],
                         "dissolved")
        # idempotent: re-recover is a clean no-op-ish report
        rep = api.recover_op(root, ["SC-L", "SC-S"])
        self.assertEqual(sorted(rep["settle_already_terminal"]),
                         ["SC-L", "SC-S"])
        self.assertIsNone(rep["settle"])

    def test_fuse_kill_during_recovery(self):
        root = self.cli_run("rep-fuse")
        proc = cli("ops", "fuse", "--state-dir", str(root),
                   "--a", "SC-L", "--b", "SC-S", "--fused", "SC-FUSED",
                   "--reason", "kill",
                   env=child_env(SUBSTRATE_CRASH_AFTER_APPENDS="6"))
        self.assertEqual(proc.returncode, CRASH_RC)
        proc = cli("ops", "recover", "--state-dir", str(root),
                   "--reason", "rec",
                   env=child_env(SUBSTRATE_CRASH_AFTER_APPENDS="5"))
        self.assertEqual(proc.returncode, CRASH_RC)
        proc = cli("ops", "recover", "--state-dir", str(root),
                   "--reason", "rec")
        self.assertEqual(proc.returncode, 0, proc.stderr)
        state = inspect_json(root)
        self.assertEqual(state["worlds"]["SC-FUSED"]["lifecycle"],
                         "active")
        self.assertEqual(kinds_of(root).get("fusion", 0), 1)
        self.assertTrue(state["conservation"]["ok"])

    def test_fission_kill_during_recovery(self):
        root = self.cli_run("rep-fission")
        proc = cli("ops", "fuse", "--state-dir", str(root),
                   "--a", "SC-L", "--b", "SC-S", "--fused", "SC-FUSED",
                   "--reason", "setup")
        self.assertEqual(proc.returncode, 0, proc.stderr)
        proc = cli("ops", "fission", "--state-dir", str(root),
                   "--composite", "SC-FUSED", "--left", "SC-L2",
                   "--right", "SC-S2", "--partition", PARTITION_CLI,
                   "--reason", "kill",
                   env=child_env(SUBSTRATE_CRASH_AFTER_APPENDS="8"))
        self.assertEqual(proc.returncode, CRASH_RC)
        rec = ["ops", "recover", "--state-dir", str(root),
               "--reason", "rec", "--fission", "SC-FUSED",
               "--left", "SC-L2", "--right", "SC-S2",
               "--partition", PARTITION_CLI]
        proc = cli(*rec, env=child_env(
            SUBSTRATE_CRASH_AFTER_APPENDS="4"))
        self.assertEqual(proc.returncode, CRASH_RC)
        proc = cli(*rec)
        self.assertEqual(proc.returncode, 0, proc.stderr)
        state = inspect_json(root)
        self.assertEqual(state["worlds"]["SC-L2"]["lifecycle"], "active")
        self.assertEqual(kinds_of(root).get("fission", 0), 1)
        self.assertTrue(state["conservation"]["ok"])

    def test_kill_during_spec_repair(self):
        root = self.cli_run("rep-spec")
        proc = cli("ops", "fuse", "--state-dir", str(root),
                   "--a", "SC-L", "--b", "SC-S", "--fused", "SC-FUSED",
                   "--reason", "kill",
                   env=child_env(SUBSTRATE_CRASH_AFTER_APPENDS="6"))
        self.assertEqual(proc.returncode, CRASH_RC)
        proc = cli("ops", "recover", "--state-dir", str(root),
                   "--reason", "rec",
                   env=child_env(SUBSTRATE_CRASH_AT="recover:pre-spec"))
        self.assertEqual(proc.returncode, CRASH_RC)
        proc = cli("ops", "recover", "--state-dir", str(root),
                   "--reason", "rec")
        self.assertEqual(proc.returncode, 0, proc.stderr)
        state = inspect_json(root)
        self.assertEqual(state["worlds"]["SC-FUSED"]["lifecycle"],
                         "active")
        self.assertTrue(state["conservation"]["ok"])

    def test_full_flow_with_kills_at_every_op(self):
        # init -> run -> fuse(kill) -> recover -> reuse -> fission(kill)
        # -> recover -> split-pair -> settle(kill) -> recover: the whole
        # demo spine with a kill inside every mutating op.
        root = self.cli_run("flow")
        proc = cli("ops", "fuse", "--state-dir", str(root),
                   "--a", "SC-L", "--b", "SC-S", "--fused", "SC-FUSED",
                   "--reason", "kill",
                   env=child_env(SUBSTRATE_CRASH_AFTER_APPENDS="6"))
        self.assertEqual(proc.returncode, CRASH_RC)
        proc = cli("ops", "recover", "--state-dir", str(root),
                   "--reason", "rec")
        self.assertEqual(proc.returncode, 0, proc.stderr)
        proc = cli("ops", "reuse", "--state-dir", str(root),
                   "--composite", "SC-FUSED", "--followup", "S4")
        self.assertEqual(proc.returncode, 0, proc.stderr)
        proc = cli("ops", "fission", "--state-dir", str(root),
                   "--composite", "SC-FUSED", "--left", "SC-L2",
                   "--right", "SC-S2", "--partition", PARTITION_CLI,
                   "--reason", "kill",
                   env=child_env(SUBSTRATE_CRASH_AFTER_APPENDS="9"))
        self.assertEqual(proc.returncode, CRASH_RC)
        proc = cli("ops", "recover", "--state-dir", str(root),
                   "--reason", "rec", "--fission", "SC-FUSED",
                   "--left", "SC-L2", "--right", "SC-S2",
                   "--partition", PARTITION_CLI)
        self.assertEqual(proc.returncode, 0, proc.stderr)
        proc = cli("ops", "split-pair", "--state-dir", str(root),
                   "--left", "SC-L2", "--right", "SC-S2",
                   "--followup", "S6")
        self.assertEqual(proc.returncode, 0, proc.stderr)
        proc = cli("ops", "settle", "--state-dir", str(root),
                   "--worlds", "SC-L2,SC-S2", "--reason", "kill",
                   env=child_env(SUBSTRATE_CRASH_AFTER_APPENDS="4"))
        self.assertEqual(proc.returncode, CRASH_RC)
        proc = cli("ops", "recover", "--state-dir", str(root),
                   "--worlds", "SC-L2,SC-S2", "--reason", "rec")
        self.assertEqual(proc.returncode, 0, proc.stderr)
        state = inspect_json(root)
        self.assertTrue(state["conservation"]["ok"])
        self.assertEqual(
            sorted(state["conservation"]["settled_terminals"]),
            ["SC-FUSED", "SC-L", "SC-L2", "SC-S", "SC-S2"])


class TestRealKill(Base):
    """Real SIGKILL (not the hook) at staggered delays, then recover."""

    def kill_run(self, root: Path, op_args: list[str],
                 delay: float) -> str:
        child = subprocess.Popen(
            [sys.executable, str(HERE / "release.py"), *op_args],
            cwd=str(HERE), env=child_env(),
            stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        time.sleep(delay)
        try:
            child.kill()
            killed = True
        except ProcessLookupError:
            killed = False
        child.communicate(timeout=60)
        if child.returncode == 0:
            return "completed-before-kill"
        self.assertTrue(killed)
        self.assertLess(child.returncode, 0)
        return "killed"

    def test_sigkill_settle(self):
        template = self.cli_run("kill-settle-template")
        for i, delay in enumerate((0.05, 0.2, 0.5)):
            with self.subTest(delay=delay):
                root = self.fresh_copy(template, f"kill-settle-{i}")
                landing = self.kill_run(
                    root, ["ops", "settle", "--state-dir", str(root),
                           "--worlds", "SC-L,SC-S", "--reason", "kill"],
                    delay)
                proc = cli("ops", "recover", "--state-dir", str(root),
                           "--worlds", "SC-L,SC-S", "--reason", "rec")
                self.assertEqual(proc.returncode, 0, proc.stderr)
                state = inspect_json(root)
                self.assertTrue(state["conservation"]["ok"])
                self.assertEqual(state["worlds"]["SC-L"]["lifecycle"],
                                 "dissolved")
                print(f"sigkill settle delay={delay}: {landing} -> "
                      f"converged")

    def test_sigkill_fuse(self):
        template = self.cli_run("kill-fuse-template")
        for i, delay in enumerate((0.05, 0.2, 0.5)):
            with self.subTest(delay=delay):
                root = self.fresh_copy(template, f"kill-fuse-{i}")
                landing = self.kill_run(
                    root, ["ops", "fuse", "--state-dir", str(root),
                           "--a", "SC-L", "--b", "SC-S",
                           "--fused", "SC-FUSED", "--reason", "kill"],
                    delay)
                proc = cli("ops", "recover", "--state-dir", str(root),
                           "--reason", "rec")
                self.assertEqual(proc.returncode, 0, proc.stderr)
                state = inspect_json(root)
                if "SC-FUSED" not in state["worlds"]:
                    landing += "+no-trace-rerun"
                    proc = cli("ops", "fuse", "--state-dir", str(root),
                               "--a", "SC-L", "--b", "SC-S",
                               "--fused", "SC-FUSED", "--reason",
                               "re-run after pre-op kill")
                    self.assertEqual(proc.returncode, 0, proc.stderr)
                    state = inspect_json(root)
                self.assertEqual(state["worlds"]["SC-FUSED"]["lifecycle"],
                                 "active")
                self.assertEqual(kinds_of(root).get("fusion", 0), 1)
                self.assertTrue(state["conservation"]["ok"])
                print(f"sigkill fuse delay={delay}: {landing} -> "
                      f"converged")

    def test_sigkill_fission(self):
        template = self.cli_run("kill-fission-template")
        proc = cli("ops", "fuse", "--state-dir", str(template),
                   "--a", "SC-L", "--b", "SC-S", "--fused", "SC-FUSED",
                   "--reason", "template fusion")
        self.assertEqual(proc.returncode, 0, proc.stderr)
        for i, delay in enumerate((0.05, 0.2, 0.5)):
            with self.subTest(delay=delay):
                root = self.fresh_copy(template, f"kill-fission-{i}")
                landing = self.kill_run(
                    root, ["ops", "fission", "--state-dir", str(root),
                           "--composite", "SC-FUSED", "--left", "SC-L2",
                           "--right", "SC-S2", "--partition",
                           PARTITION_CLI, "--reason", "kill"],
                    delay)
                bare = cli("ops", "recover", "--state-dir", str(root),
                           "--reason", "rec")
                if bare.returncode != 0:
                    proc = cli("ops", "recover", "--state-dir",
                               str(root), "--reason", "rec", "--fission",
                               "SC-FUSED", "--left", "SC-L2", "--right",
                               "SC-S2", "--partition", PARTITION_CLI)
                    self.assertEqual(proc.returncode, 0, proc.stderr)
                state = inspect_json(root)
                if state["worlds"]["SC-FUSED"]["lifecycle"] == "active" \
                        and kinds_of(root).get("fission", 0) == 0:
                    landing += "+no-trace-rerun"
                    proc = cli("ops", "fission", "--state-dir", str(root),
                               "--composite", "SC-FUSED", "--left",
                               "SC-L2", "--right", "SC-S2", "--partition",
                               PARTITION_CLI, "--reason",
                               "re-run after pre-op kill")
                    self.assertEqual(proc.returncode, 0, proc.stderr)
                    state = inspect_json(root)
                self.assertEqual(state["worlds"]["SC-FUSED"]["lifecycle"],
                                 "dissolved")
                self.assertEqual(kinds_of(root).get("fission", 0), 1)
                self.assertTrue(state["conservation"]["ok"])
                print(f"sigkill fission delay={delay}: {landing} -> "
                      f"converged")


class TestDetection(Base):
    """Forensics: quarantine/conservation/torn/input refusal paths."""

    def test_partial_quarantine_detected_with_steps(self):
        root = self.root / "qdetect"
        api.init_run(root)
        api.run_tasks(root, ["S1"])
        host, _ = api.open_run(root)
        host.suspend("SC-L", "host", "drill", pending_effects=[
            {"commitment": "sched.composite", "to": "SC-S"},
            {"commitment": "sched.requirements", "to": "SC-S"}])
        host.transfer_custody("sched.composite", "SC-L", "SC-S",
                              actor="host",
                              reason="quarantine transfer: drill",
                              continuity="commitment-handoff")
        rep = api.recover_op(root)
        self.assertEqual(len(rep["partial_quarantines"]), 1)
        self.assertEqual(rep["partial_quarantines"][0]["world"], "SC-L")
        self.assertIn("SC-L", rep["quarantine_operator_steps"][0])
        self.assertIn("OPERATOR REPAIR",
                      rep["quarantine_operator_steps"][0])
        # involved world blocked; uninvolved worlds still settle
        with self.assertRaises(RuntimeError):
            api.recover_op(root, ["SC-L"])
        rep2 = api.recover_op(root, ["SC-S"])
        self.assertIsNotNone(rep2["settle"])

    def test_conservation_violation_refuses_recover(self):
        root = self.root / "violated"
        api.init_run(root)
        api.run_tasks(root, ["S1"])
        host, _ = api.open_run(root)
        host.append("lifecycle", {"world_id": "SC-GHOST",
                                  "from": "active", "to": "dissolved",
                                  "reason": "probe"}, actor="host")
        with self.assertRaises(ContractViolation) as ctx:
            api.recover_op(root)
        self.assertIn("fails conservation", str(ctx.exception))

    def test_torn_ledger_refuses_recover(self):
        root = self.root / "torn"
        api.init_run(root)
        api.run_tasks(root, ["S1"])
        with open(root / "ledger.jsonl", "a", encoding="utf-8") as fh:
            fh.write('{"seq": 9999, "torn": "no-close-brace"\n')
        with self.assertRaises(RuntimeError) as ctx:
            api.recover_op(root)
        self.assertIn("disk-loss", str(ctx.exception))
        proc = cli("inspect", "--state-dir", str(root))
        self.assertNotEqual(proc.returncode, 0)

    def test_fission_args_without_partial_refused(self):
        root = self.cli_run("nopartial")
        with self.assertRaises(RuntimeError) as ctx:
            api.recover_op(root, fission="SC-FUSED", left="SC-L2",
                           right="SC-S2", partition=dict(PARTITION))
        self.assertIn("nothing to complete", str(ctx.exception))

    def test_bare_recover_settles_nothing_by_default(self):
        root = self.cli_run("safe-default")
        rep = api.recover_op(root)
        self.assertTrue(rep["settle_skipped_no_worlds"])
        self.assertIsNone(rep["settle"])
        host, _ = api.open_run(root)
        self.assertEqual(host.worlds["SC-L"].lifecycle, "active")
        self.assertEqual(host.worlds["SC-S"].lifecycle, "active")

    def test_partial_fission_blocks_settle_until_completed(self):
        root = self.cli_run("blocked")
        proc = cli("ops", "fuse", "--state-dir", str(root),
                   "--a", "SC-L", "--b", "SC-S", "--fused", "SC-FUSED",
                   "--reason", "setup")
        self.assertEqual(proc.returncode, 0, proc.stderr)
        proc = cli("ops", "fission", "--state-dir", str(root),
                   "--composite", "SC-FUSED", "--left", "SC-L2",
                   "--right", "SC-S2", "--partition", PARTITION_CLI,
                   "--reason", "kill",
                   env=child_env(SUBSTRATE_CRASH_AFTER_APPENDS="8"))
        self.assertEqual(proc.returncode, CRASH_RC)
        with self.assertRaises(RuntimeError):
            api.recover_op(root, ["SC-FUSED"])
        # one call completes the fission AND settles the children
        rep = api.recover_op(root, ["SC-L2", "SC-S2"],
                             fission="SC-FUSED", left="SC-L2",
                             right="SC-S2", partition=dict(PARTITION))
        self.assertEqual(len(rep["fissions_completed"]), 1)
        self.assertIsNotNone(rep["settle"])
        host, _ = api.open_run(root)
        self.assertTrue(host.verify_conservation()["ok"])


if __name__ == "__main__":
    unittest.main(verbosity=2)
