"""Successor-004 programmatic API (stdlib-only, except SST use).

The operable release surface over the demo-proven path. Every function
takes an explicit state dir; NOTHING is written outside successor-005/
(run state lives wherever the caller points --state-dir, which MUST be
inside this directory for release runs).

State layout under STATE_DIR (created by init_run):
    ledger.jsonl        the integrated ledger
    state/              per-world state dirs
    ROUTING-LOG.jsonl   routing decisions (mirrors ledger `routing`)
    artifacts/          solutions + fusion/fission records
    worlds.json         world descriptor specs (for reopen)
    CONFIG.json         release + run metadata
    sst-leg/            SST evidence (only when the SST leg runs)

Successor-005 procedure runs add (only in proc runs; sched layout
byte-identical): state/<W>/procedures/<name>/ (staged bundles),
state/proc-scratch/<key>/<step>-attempt<N>/ (per-step scratch),
artifacts/proc-<key>/<step>/ (collected outputs + RESULT.json).

Channels are IN-MEMORY ONLY (never persisted): open_run returns a fresh
registry. Ops that need a channel (fuse) ensure it exists first and say
so in their record.

Typical flow:
    import api
    api.init_run("runs/cli-01")
    api.run_tasks("runs/cli-01", ["S1", "S2"])
    api.fuse_op("runs/cli-01", "SC-L", "SC-S", "SC-FUSED", reason="...")
    api.fission_op("runs/cli-01", "SC-FUSED", "SC-L2", "SC-S2",
                   {"sched.requirements": "SC-L2", ...}, reason="...")
"""
from __future__ import annotations

import copy
import json
import os
import subprocess
import sys
import time
from datetime import UTC, datetime
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

from minihost import (ContractViolation, MiniHost, atomic_write_text,  # noqa: E402
                      maybe_crash_at)
from routing import (ChannelRegistry, Coordinator, HCoordinator,  # noqa: E402
                     finish_worlds, record_routing, route, setup_host,
                     world_record)
from resume import reapply_revocations, revoke_capability  # noqa: E402
from pipeline import (FUSED_CAPS, L_CAPS, L_REPS, Q_CAPS, S_CAPS, S_REPS,  # noqa: E402
                      LaneCtx, apply_revision, run_sched_task,
                      s3_resume_flow)
from resume import scan_succeeded  # noqa: E402
from fusion import (fission_worlds, fuse_worlds, quarantine_world,  # noqa: E402
                    reuse_composite)
import recover as RC  # noqa: E402
import procedure as PROC  # noqa: E402
from pipeline import run_split_pair_task  # noqa: E402
from sst_leg import run_sst_test_search  # noqa: E402
import sched_inputs as FI  # noqa: E402
import successor_demo as DEMO  # noqa: E402

RELEASE = "successor-005"

CAP_PRESETS: dict[str, tuple[list, list]] = {
    "L": (L_CAPS, L_REPS),
    "S": (S_CAPS, S_REPS),
    "FUSED": (FUSED_CAPS, [("sched-list", "v2"), ("sched-slot", "v2")]),
    "Q": (Q_CAPS, [("sched-list", "v1")]),
}

LANE_TASKS = {"S1": FI.S1, "S2": FI.S2}


# ------------------------------------------------------------- specs

def _spec(world_id: str, caps: list[tuple[str, str]],
          reps: list[tuple[str, str]],
          custodians: dict | None = None,
          procedures: list | None = None) -> dict:
    spec = {"world_id": world_id,
            "caps": [[n, v] for n, v in caps],
            "reps": [[n, v] for n, v in reps],
            "custodians": dict(custodians or {})}
    if procedures:
        # S5 R-A: additive-absent-when-empty — sched specs emit no
        # `procedures` key at all; proc worlds pin their table.
        spec["procedures"] = [dict(t) for t in procedures]
    return spec


def _read_specs(state_dir: Path) -> list[dict]:
    return json.loads((state_dir / "worlds.json").read_text(
        encoding="utf-8"))


def _write_specs(state_dir: Path, specs: list[dict]) -> None:
    # R3 (F2 fix): crash-atomic — a SIGKILL here leaves old-or-new
    # specs, never a torn worlds.json.
    atomic_write_text(state_dir / "worlds.json",
                      json.dumps(specs, indent=2, sort_keys=True) + "\n")


def _record_for(state_dir: Path, spec: dict):
    return world_record(
        state_dir / "state", spec["world_id"],
        [(n, v) for n, v in spec["caps"]],
        [(n, v) for n, v in spec["reps"]],
        custodians=dict(spec.get("custodians", {})),
        procedures=[dict(t) for t in spec.get("procedures", [])])


# ------------------------------------------------------------- open

def init_run(state_dir: str | Path) -> dict:
    """Create a fresh run root with SC-L + SC-S on one ledger."""
    root = Path(state_dir)
    if (root / "ledger.jsonl").exists():
        raise FileExistsError(f"run root already initialized: {root}")
    root.mkdir(parents=True, exist_ok=True)
    (root / "artifacts").mkdir(exist_ok=True)
    worlds = DEMO.main_worlds(root / "state")
    setup_host(root, worlds)
    specs = [_spec("SC-L", L_CAPS, L_REPS,
                   {"sched.requirements": "SC-L",
                    "sched.composite": "SC-L"}),
             _spec("SC-S", S_CAPS, S_REPS, {"sched.slots": "SC-S"})]
    _write_specs(root, specs)
    config = {"release": RELEASE,
              "created_utc": datetime.now(UTC).strftime("%Y%m%dT%H%M%SZ"),
              "worlds": ["SC-L", "SC-S"], "tasks_run": []}
    atomic_write_text(root / "CONFIG.json",
                      json.dumps(config, indent=2, sort_keys=True) + "\n")
    return {"state_dir": str(root), "worlds": ["SC-L", "SC-S"],
            "config": config}


def open_run(state_dir: str | Path) -> tuple[MiniHost, ChannelRegistry]:
    """Reopen a run root: replay the ledger, restore creation lineage,
    re-apply revocations.

    Lineage note: raw MiniHost.reopen keeps the lineage of the SUPPLIED
    descriptors (which only verify code_ref/caps/reps), so fusion /
    fission lineage would be lost on reopen. The ledger `create`
    payloads carry the authoritative creation lineage, so open_run
    restores it from there (the documented recovery procedure).
    """
    root = Path(state_dir)
    if not (root / "ledger.jsonl").exists():
        raise FileNotFoundError(f"not a run root (no ledger.jsonl): {root}")
    records = [_record_for(root, spec) for spec in _read_specs(root)]
    host = MiniHost.reopen(root / "state", root / "ledger.jsonl",
                           records, actor="host",
                           reason="api open_run")
    for e in host.ledger_entries():
        if e.get("kind") == "create":
            wid = e["payload"].get("world_id")
            if wid in host.worlds:
                host.worlds[wid].lineage = copy.deepcopy(
                    e["payload"].get("lineage", []))
                # S5: the ledger `create` payloads are likewise
                # authoritative for the creation-fixed procedure
                # table (absent ≡ empty).
                host.worlds[wid].procedures = copy.deepcopy(
                    e["payload"].get("procedures", []))
    reapply_revocations(host)
    return host, ChannelRegistry()


def _remember_creation(root: Path, world_id: str, caps, reps,
                       procedures: list | None = None) -> None:
    specs = _read_specs(root)
    if world_id not in {s["world_id"] for s in specs}:
        specs.append(_spec(world_id, caps, reps, procedures=procedures))
        _write_specs(root, specs)


# ------------------------------------------------------------- run

def run_tasks(state_dir: str | Path, tasks: list[str] | None = None,
              with_sst: bool = False) -> dict:
    """Route + run lane tasks (S1/S2) on the run root. Optionally the SST leg."""
    root = Path(state_dir)
    tasks = tasks or ["S1", "S2"]
    unknown = [t for t in tasks if t not in LANE_TASKS]
    if unknown:
        raise ValueError(f"run_tasks supports {sorted(LANE_TASKS)}; "
                         f"got {unknown} (S3 runs via kill_resume_op, "
                         f"S4/S6 via fuse/fission + reuse ops)")
    host, chans = open_run(root)
    routing_log = root / "ROUTING-LOG.jsonl"
    out: dict = {"state_dir": str(root), "tasks": {}}
    for name in tasks:
        task = copy.deepcopy(LANE_TASKS[name])
        decision = route(task)
        record_routing(host, decision, routing_log)
        if decision["lane"] == "central":
            ctx = LaneCtx("central", Coordinator(), chans)
        else:
            ctx = LaneCtx("local", HCoordinator(), chans)
        m = run_sched_task(root, host, task, ctx)
        out["tasks"][name] = {
            "lane": m["lane"], "valid": m["valid"],
            "quality": m["quality"], "prefs_total": m["prefs_total"],
            "central_bytes": m["central_bytes"],
            "direct_bytes": m["direct_bytes"],
            "solution_ref": m["solution_ref"]}
    if with_sst:
        out["SST"] = run_sst_test_search((root / "sst-leg").resolve())
    config = json.loads((root / "CONFIG.json").read_text(encoding="utf-8"))
    config["tasks_run"].extend(tasks)
    atomic_write_text(root / "CONFIG.json",
                      json.dumps(config, indent=2, sort_keys=True) + "\n")
    return out


# ------------------------------------------------------------- ops

def fuse_op(state_dir: str | Path, a: str, b: str, fused_id: str,
            reason: str, preset: str = "FUSED") -> dict:
    """Fuse worlds a+b into `fused_id` (ORG-OPS OP-1)."""
    root = Path(state_dir)
    host, chans = open_run(root)
    caps, reps = CAP_PRESETS[preset]
    chans.get(a, b)  # channels are in-memory: ensure-then-remove
    record = fuse_worlds(host, chans, a, b, fused_id,
                         _record_for(root, _spec(fused_id, caps, reps)),
                         "host", reason)
    maybe_crash_at("api:fuse:pre-spec")  # R1 kill boundary (test-only)
    _remember_creation(root, fused_id, caps, reps)
    atomic_write_text(root / "artifacts" / f"fusion-{fused_id}.json",
                      json.dumps(record, indent=2, sort_keys=True,
                                 default=str))
    return record


def fission_op(state_dir: str | Path, composite: str, left: str,
               right: str, partition: dict[str, str], reason: str,
               left_preset: str = "L", right_preset: str = "S") -> dict:
    """Fission `composite` into left+right per partition (ORG-OPS OP-6)."""
    root = Path(state_dir)
    host, chans = open_run(root)
    lcaps, lreps = CAP_PRESETS[left_preset]
    rcaps, rreps = CAP_PRESETS[right_preset]
    record = fission_worlds(
        host, chans, composite, left, right,
        _record_for(root, _spec(left, lcaps, lreps)),
        _record_for(root, _spec(right, rcaps, rreps)),
        partition, "host", reason)
    maybe_crash_at("api:fission:pre-spec")  # R1 kill boundary (test-only)
    _remember_creation(root, left, lcaps, lreps)
    _remember_creation(root, right, rcaps, rreps)
    atomic_write_text(root / "artifacts" / f"fission-{composite}.json",
                      json.dumps(record, indent=2, sort_keys=True,
                                 default=str))
    return record


def quarantine_op(state_dir: str | Path, world: str, standby: str,
                  reason: str, create_standby: bool = False) -> dict:
    """Quarantine `world` with transfer to `standby` (ORG-OPS OP-5)."""
    root = Path(state_dir)
    host, _ = open_run(root)
    if create_standby and standby not in host.worlds:
        caps, reps = CAP_PRESETS["Q"]
        from routing import GRANT_LIMITS
        host.create_world(_record_for(root, _spec(standby, caps, reps)),
                          "host", grant_limits=dict(GRANT_LIMITS))
        host.transition(standby, "active", "host",
                        reason="standby birth for quarantine")
        _remember_creation(root, standby, caps, reps)
    return quarantine_world(host, world, standby, "host", reason)


def revise_op(state_dir: str | Path, task_id: str, frm: str, to: str,
              reason: str) -> dict:
    """Record a representation revision (ORG-OPS OP-3, ledger entry)."""
    root = Path(state_dir)
    host, _ = open_run(root)
    return apply_revision(host, task_id, {"from": frm, "to": to,
                                         "reason": reason})


def revoke_op(state_dir: str | Path, world: str, capability: str,
              version: str, reason: str, new_owner: str = "") -> dict:
    """Revoke a capability, durably (ORG-OPS OP-4; LIMITS-2 scope).

    Durable (LIMITS-2) = ledger-recorded on local disk across a process crash
    (re-applied after reopen); no fsync is issued, so power/media
    loss stays the disk-loss class (LIMITS-2, out of scope).
    """
    root = Path(state_dir)
    host, _ = open_run(root)
    return revoke_capability(host, world, capability, version,
                             actor="host", reason=reason,
                             new_owner=new_owner)


def reuse_op(state_dir: str | Path, composite: str,
             followup: dict) -> dict:
    """Reuse a fused composite on a follow-up task (ORG-OPS OP-2)."""
    root = Path(state_dir)
    host, _ = open_run(root)
    return reuse_composite(root, host, composite, followup)


def split_pair_op(state_dir: str | Path, task: dict, left: str,
                  right: str) -> dict:
    """Run a task through a fission-split pair (S6 pattern)."""
    root = Path(state_dir)
    host, _ = open_run(root)
    return run_split_pair_task(root, host, task, left, right)


def _init_proc_root(root: Path) -> None:
    """Initialize a procedure-run root (no sched worlds).

    Same file layout as init_run, but the host holds
    PROC_ROOT_HOLDINGS (minutes-adequate) instead of the sched
    envelope. Used only when create_proc_world targets an
    uninitialized dir; sched roots are byte-identical to before.
    """
    root.mkdir(parents=True, exist_ok=True)
    (root / "artifacts").mkdir(exist_ok=True)
    MiniHost(root / "state", root / "ledger.jsonl",
             root_holdings=dict(PROC.PROC_ROOT_HOLDINGS))
    _write_specs(root, [])
    config = {"release": RELEASE,
              "created_utc": datetime.now(UTC).strftime("%Y%m%dT%H%M%SZ"),
              "worlds": [], "tasks_run": []}
    atomic_write_text(root / "CONFIG.json",
                      json.dumps(config, indent=2, sort_keys=True) + "\n")


def create_proc_world(state_dir: str | Path, world_id: str,
                      bundle_dir: str | Path, reason: str,
                      sched_preset: str | None = None) -> dict:
    """Advertise a procedure world (S5 §1.1/§1.8).

    Validates the caller bundle (ValueError naming the defect, zero
    ledger effect), stages a host-owned copy under
    state/<W>/procedures/<name>/, creates the world with
    caps=[proc.exec@v1] (+ the sched preset's caps for hybrid
    worlds) and the creation-fixed `procedures` table, funds it
    with PROC_GRANT_LIMITS, and activates it. On an uninitialized
    dir, initializes a procedure-run root first (minutes-adequate
    host holdings); on an existing root, opens it.
    """
    root = Path(state_dir)
    src = Path(bundle_dir)
    name = PROC.validate_procedure_name(src.name)
    if not (root / "ledger.jsonl").exists():
        _init_proc_root(root)
    host, _ = open_run(root)
    # Pre-stage duplicate check (create_world would refuse after
    # staging; refuse before any side effect instead). host.worlds
    # covers every lifecycle incl. retired (ids never reused).
    if world_id in host.worlds:
        raise ContractViolation(
            f"world_id {world_id!r} already used (ids never reused)")
    if sched_preset is not None and sched_preset not in CAP_PRESETS:
        raise ValueError(f"unknown sched_preset {sched_preset!r} "
                         f"(want one of {sorted(CAP_PRESETS)})")
    staged_dir = root / "state" / world_id / "procedures" / name
    manifest, bundle_sha = PROC.stage_bundle(src, staged_dir)
    table = [{"name": name, "bundle_sha256": bundle_sha,
              "manifest_ref": str(staged_dir / PROC.MANIFEST_NAME),
              "steps": [s["step"] for s in manifest["steps"]]}]
    if sched_preset is None:
        caps: list = [(PROC.PROC_CAP, PROC.PROC_VER)]
        reps: list = []
    else:
        preset_caps, preset_reps = CAP_PRESETS[sched_preset]
        caps = list(preset_caps) + [(PROC.PROC_CAP, PROC.PROC_VER)]
        reps = list(preset_reps)
    rec = world_record(root / "state", world_id, caps, reps,
                       procedures=table)
    host.create_world(rec, "host",
                      grant_limits=dict(PROC.PROC_GRANT_LIMITS))
    host.transition(world_id, "active", "host",
                    reason=f"proc birth: {reason}")
    maybe_crash_at("api:create-proc-world:pre-spec")
    _remember_creation(root, world_id, caps, reps, procedures=table)
    return {"state_dir": str(root), "world_id": world_id,
            "procedure": name, "bundle_sha256": bundle_sha,
            "manifest_ref": table[0]["manifest_ref"],
            "steps": table[0]["steps"],
            "grant": dict(PROC.PROC_GRANT_LIMITS),
            "sched_preset": sched_preset}


def run_procedure(state_dir: str | Path, world_id: str, procedure: str,
                  idem_key: str, inputs: dict | None = None) -> dict:
    """Execute a table procedure (S5 §1.8): all steps in order with
    skip-match. Returns {skipped, executed, re_executed_steps,
    child_executions, results}."""
    root = Path(state_dir)
    host, _ = open_run(root)
    rep = PROC.run_procedure(host, root, world_id, procedure,
                             idem_key, inputs)
    rep["state_dir"] = str(root)
    rep["world_id"] = world_id
    rep["procedure"] = procedure
    rep["idem_key"] = idem_key
    return rep


def settle_op(state_dir: str | Path, worlds: list[str],
              reason: str) -> dict:
    """Settle-then-dissolve worlds with 0-stranded verification.

    Successor-003: atomic on refusal (zero partial dissolves; see
    routing.finish_worlds). Kill-during-settle recovery: recover_op.
    """
    root = Path(state_dir)
    host, _ = open_run(root)
    return finish_worlds(host, worlds, reason=reason)


def _recovery_note(root: Path, kind: str, wid: str, seq: int | None,
                   entry: dict, completed: bool) -> str | None:
    """Write artifacts/recovery-<kind>-<id>.json when the original record
    file is missing (kill between ledger-complete and artifact write).
    Timestamp-free (C6-style): deterministic bytes."""
    orig = root / "artifacts" / f"{kind}-{wid}.json"
    note_path = root / "artifacts" / f"recovery-{kind}-{wid}.json"
    if orig.exists() or note_path.exists():
        return None
    atomic_write_text(note_path, json.dumps(
        {"kind": kind, "id": wid, "ledger_seq": seq,
         "completed_by_recovery": completed, "ledger_entry": entry,
         "note": "ledger entry is authoritative; the original record "
                 "file was lost to a kill (or never written)"},
        indent=2, sort_keys=True) + "\n")
    return str(note_path)


def recover_op(state_dir: str | Path, worlds: list[str] | None = None,
               reason: str = "recover", fission: str | None = None,
               left: str | None = None, right: str | None = None,
               partition: dict[str, str] | None = None,
               left_preset: str = "L",
               right_preset: str = "S") -> dict:
    """Recover a run after a kill: repair + complete, loudly (R1).

    Steps: reopen (replay); repair worlds.json specs missing for
    ledger-known worlds; refuse fail-closed when conservation fails;
    complete interrupted births + fusions automatically; complete ONE
    interrupted fission when --fission/--left/--right/--partition name
    it (refuses with exact operator steps otherwise); detect (never
    silently complete) partial quarantines; settle exactly `worlds`
    (default: settle NOTHING -- pass --worlds explicitly; mass
    dissolve is never a default).

    Raises RuntimeError (operator input needed, steps in message) or
    ContractViolation (fail-closed state violation). Re-running after
    a kill during recovery converges (every step is ledger-
    conditional). See INTERRUPTION-BOUNDARIES.md.

    Successor-005: also adopts side-complete procedure steps (L3:
    DONE present, no invoke — verified then adopted with ONE
    recovered invoke) and reports re-runnable ones (L2: killed
    mid-step — re-invoke the same key) as `proc_adopted` /
    `proc_rerunnable` / `proc_nothing_to_do`. Recovery never spawns.
    """
    root = Path(state_dir)
    try:
        host, _ = open_run(root)
    except ValueError as exc:
        raise RuntimeError(
            f"recovery refused: ledger or worlds.json unreadable "
            f"({exc}); torn files are the disk-loss class "
            f"(LIMITS-2, out of scope): restore from backup, never "
            f"hand-edit; see INTERRUPTION-BOUNDARIES.md") from exc
    try:
        specs = _read_specs(root)
    except FileNotFoundError:
        specs = []
    idx = RC.ledger_index(host)
    repaired = RC.repair_specs(root, host, idx, specs)
    if repaired:
        host, _ = open_run(root)
        idx = RC.ledger_index(host)
    try:
        conservation = host.verify_conservation()
    except ContractViolation as exc:
        raise ContractViolation(
            f"recovery refused: ledger fails conservation ({exc}); "
            f"resolve the violation first (inspect via "
            f"`release.py inspect --state-dir {root} --json`; see "
            f"INTERRUPTION-BOUNDARIES.md), then re-run recover") from exc
    partials_f = RC.detect_partial_fusions(host, idx)
    partials_s = RC.detect_partial_fissions(host, idx)
    skip = set()
    for pf in partials_f:
        skip.add(pf["composite"])
        skip.update(pf["parents"])
    for ps in partials_s:
        skip.add(ps["composite"])
        skip.update(ps["children_created"])
    births = RC.run_births(host, idx, RC.plan_births(host, idx, skip))
    fusions_completed = []
    for pf in partials_f:
        rec = RC.complete_fusion(host, pf["composite"], "host", reason)
        fusions_completed.append(
            {"fused_id": rec["fused_id"], "parents": rec["parents"],
             "transfers": len(rec["transfers"])})
    idx = RC.ledger_index(host)
    partials_s = RC.detect_partial_fissions(host, idx)
    fissions_completed: list[dict] = []
    fission_args = (fission, left, right, partition)
    if partials_s:
        if not all(fission_args):
            names = ", ".join(p["composite"] for p in partials_s)
            detail = "; ".join(
                f"{p['composite']}: children={p['children_created']} "
                f"transfers={p['transfers_done']}" for p in partials_s)
            raise RuntimeError(
                f"partial fission(s) of {names} need operator input "
                f"({detail}): re-run recover with --fission C --left L "
                f"--right R --partition k=v,... (+ presets when "
                f"non-default); the supplied partition must agree "
                f"with recorded progress")
        if fission not in {p["composite"] for p in partials_s}:
            raise RuntimeError(
                f"no partial fission of {fission} "
                f"(partial now: "
                f"{[p['composite'] for p in partials_s]}); "
                f"nothing to complete")
        lcaps, lreps = CAP_PRESETS[left_preset]
        rcaps, rreps = CAP_PRESETS[right_preset]
        rec = RC.complete_fission(host, root, fission, left, right,
                                  partition, lcaps, lreps, rcaps, rreps,
                                  "host", reason)
        fissions_completed.append(
            {"composite": rec["composite"],
             "children": rec["children"],
             "transfers": len(rec["transfers"])})
    elif any(fission_args):
        raise RuntimeError(
            f"--fission/--left/--right/--partition given but no "
            f"partial fission exists; nothing to complete")
    idx = RC.ledger_index(host)
    # S5: adopt-if-complete (L3) + report re-runnable steps (L2).
    # Adopt runs BEFORE the settle phase so one call can adopt and
    # then settle; rerunnable (L2) needs no withholding (a killed
    # mid-step attempt is consistent-but-incomplete, like a
    # half-executed sched plan — settling abandons it cleanly, and
    # re-invoke after settle refuses loudly by the not-active rule).
    # Recovery never spawns (adopt + report only).
    proc_rec = PROC.proc_recover(host, root)
    idx = RC.ledger_index(host)
    partials_q = RC.detect_partial_quarantines(host, idx)
    q_steps = [RC.quarantine_operator_steps(p) for p in partials_q]
    blocked = {p["world"] for p in partials_q}
    # structural guard: never settle a world still inside an
    # uncompleted partial fusion/fission (complete it first).
    still_blocked = set(blocked)
    for pf in RC.detect_partial_fusions(host, idx):
        still_blocked.add(pf["composite"])
        still_blocked.update(pf["parents"])
    for ps in RC.detect_partial_fissions(host, idx):
        still_blocked.add(ps["composite"])
        still_blocked.update(ps["children_created"])
    notes = []
    for fid, info in idx["fusions"].items():
        note = _recovery_note(root, "fusion", fid, info["seq"],
                              info["payload"],
                              fid in {f["fused_id"]
                                      for f in fusions_completed})
        if note:
            notes.append(note)
    for cid, info in idx["fission"].items():
        note = _recovery_note(root, "fission", cid, info["seq"],
                              info["payload"],
                              cid in {f["composite"]
                                      for f in fissions_completed})
        if note:
            notes.append(note)
    settle_rep: dict | None = None
    already: list[str] = []
    if worlds is None:
        active = sorted(w for w, r in host.worlds.items()
                        if r.lifecycle in ("active", "suspended"))
    else:
        for w in worlds:
            if w in still_blocked:
                raise RuntimeError(
                    f"recovery refused to settle {w}: inside an "
                    f"uncompleted partial op (complete it first)")
        known = [w for w in worlds if w in host.worlds]
        unknown = [w for w in worlds if w not in host.worlds]
        already = sorted(w for w in known
                         if host.worlds[w].lifecycle
                         not in ("active", "suspended"))
        active = sorted(w for w in known
                        if host.worlds[w].lifecycle
                        in ("active", "suspended")) + unknown
        if active:
            settle_rep = finish_worlds(host, active, reason=reason)
    return {"state_dir": str(root), "specs_repaired": repaired,
            "births_completed": births,
            "conservation_before_completion": {
                "ok": True,
                "settled_terminals":
                    conservation["settled_terminals"]},
            "fusions_completed": fusions_completed,
            "fissions_completed": fissions_completed,
            "fissions_still_partial":
                [p["composite"] for p in partials_s
                 if p["composite"] not in
                 {f["composite"] for f in fissions_completed}],
            "partial_quarantines": partials_q,
            "quarantine_operator_steps": q_steps,
            "recovery_notes": notes,
            "proc_adopted": proc_rec["adopted"],
            "proc_rerunnable": proc_rec["rerunnable"],
            "proc_nothing_to_do": proc_rec["nothing_to_do"],
            "settle_targets": active if worlds is not None else [],
            "settle_already_terminal": already,
            "settle_skipped_no_worlds": worlds is None,
            "settle": settle_rep}


def kill_resume_op(state_dir: str | Path, timeout_s: int = 180) -> dict:
    """Real kill-resume drill: spawn the S3 partial child, Popen.kill()
    it, reopen, and finish the S3 adaptation flow (revise + revoke +
    ruling + void + re-propose + verify). Requires ACTIVE SC-L/SC-S
    (fresh init, or pre-fusion state)."""
    root = Path(state_dir).resolve()
    host, _ = open_run(root)
    for wid in ("SC-L", "SC-S"):
        if host.worlds[wid].lifecycle != "active":
            raise RuntimeError(
                f"kill_resume_op needs active SC-L/SC-S "
                f"({wid} is {host.worlds[wid].lifecycle})")
    del host
    child = subprocess.Popen(
        [sys.executable, str(HERE / "successor_demo.py"),
         "--child-partial", str(root)],
        cwd=str(HERE), stdout=subprocess.PIPE, stderr=subprocess.PIPE,
        env={**os.environ, "PYTHONDONTWRITEBYTECODE": "1"})
    t0 = time.time()
    while not (root / "child.READY").exists():
        if time.time() - t0 > timeout_s:
            child.kill()
            raise RuntimeError("kill_resume_op: child never READY")
        if child.poll() is not None:
            raise RuntimeError(
                f"kill_resume_op: child died early rc={child.returncode}")
        time.sleep(0.2)
    child.kill()
    out, err = child.communicate(timeout=60)
    if child.returncode == 0:
        raise RuntimeError("kill_resume_op: child exited, not killed")
    host, chans = open_run(root)
    prekill = scan_succeeded(host)
    ctx = LaneCtx("local", HCoordinator(), chans)
    m3 = s3_resume_flow(root, host, FI.S3, ctx, prekill)
    (root / "child.READY").unlink(missing_ok=True)
    return {"child_rc": child.returncode, "S3": m3,
            "child_stderr_tail": err.decode()[-300:]}


# ------------------------------------------------------------- read

def explain_route_op(task_name: str | None = None,
                     task_json: str | Path | None = None) -> dict:
    """Apply the routing rule to a named task (S1/S2/S3) or a JSON file."""
    if task_json is not None:
        task = json.loads(Path(task_json).read_text(encoding="utf-8"))
    elif task_name in ("S1", "S2"):
        task = copy.deepcopy(LANE_TASKS[task_name])
    elif task_name == "S3":
        task = {**copy.deepcopy(FI.S3), "task_id": "S3"}
    elif task_name in ("S4-followup", "S4"):
        return {"task_id": "S4-followup", "lane": "fused-reuse",
                "rule": "post-fusion composite reuse",
                "reason": "follow-ups run through the fused composite, "
                          "not through the routing rule"}
    elif task_name in ("S6-followup", "S6"):
        return {"task_id": "S6-followup", "lane": "fission-reuse",
                "rule": "post-fission split-pair reuse",
                "reason": "follow-ups run through the fission children, "
                          "not through the routing rule"}
    else:
        raise ValueError("explain_route_op needs task_name in "
                         "S1/S2/S3/S4-followup/S6-followup or task_json")
    return route(task)


def inspect_state_op(state_dir: str | Path) -> dict:
    """Read-only summary: worlds, ledger kinds, routing, conservation."""
    root = Path(state_dir)
    host, _ = open_run(root)
    worlds = {wid: {"lifecycle": rec.lifecycle,
                    "custodians": dict(rec.custodians),
                    "capabilities": sorted(c.name + "@" + c.version
                                           for c in rec.capabilities)}
              for wid, rec in sorted(host.worlds.items())}
    kinds: dict[str, int] = {}
    for e in host.ledger_entries():
        kinds[e.get("kind", "?")] = kinds.get(e.get("kind", "?"), 0) + 1
    routing = [e["payload"] for e in host.ledger_entries()
               if e.get("kind") == "routing"]
    try:
        conservation = host.verify_conservation()
    except Exception as exc:  # read-only probe: report, don't raise
        conservation = {"ok": False, "error": f"{type(exc).__name__}: {exc}"}
    return {"state_dir": str(root), "worlds": worlds,
            "ledger_entries": sum(kinds.values()), "kinds": kinds,
            "routing": routing, "conservation": conservation}
