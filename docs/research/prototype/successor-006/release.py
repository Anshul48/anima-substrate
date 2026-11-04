"""Successor-004 release CLI (stdlib-only, except the SST leg).

    release.py init --state-dir DIR
    release.py run --state-dir DIR [--tasks S1,S2] [--with-sst]
    release.py explain-route (--task NAME | --task-json FILE) [--json]
    release.py inspect --state-dir DIR [--json]
    release.py ops fuse --state-dir DIR --a A --b B --fused F --reason R
    release.py ops fission --state-dir DIR --composite C --left L --right R \\
        --partition k1=L,k2=R --reason R
    release.py ops quarantine --state-dir DIR --world W --standby S \\
        --reason R [--create-standby]
    release.py ops revise --state-dir DIR --task T --from A --to B --reason R
    release.py ops revoke --state-dir DIR --world W --cap C --version V \\
        --reason R [--new-owner N]
    release.py ops reuse --state-dir DIR --composite C --followup S4|S6|FILE
    release.py ops split-pair --state-dir DIR --left L --right R \\
        --followup S6|FILE
    release.py ops kill-resume --state-dir DIR
    release.py ops settle --state-dir DIR --worlds A,B --reason R
    release.py ops recover --state-dir DIR [--worlds A,B] [--reason R]
        [--fission C --left L --right R --partition k=v,...]
    release.py ops create-proc-world --state-dir DIR --world W \\
        --bundle DIR --reason R [--sched-preset L|S|FUSED|Q]
    release.py ops run-procedure --state-dir DIR --world W \\
        --procedure P --key K [--inputs DIR]
    release.py ops quarantine-complete --state-dir DIR --world W \\
        --standby S --reason R
    release.py ops quarantine-rollback --state-dir DIR --world W \\
        --standby S --reason R
    release.py j1-init --state-dir DIR --project P --reason R
    release.py ops nest --state-dir DIR --project P --child C \\
        --delegate COST,TIME,INV --custody C1,C2 --reason R
    release.py ops j1-work --state-dir DIR --world W [--task T]
        [--verifier V]
    release.py ops j1-kill-resume --state-dir DIR --world W [--task T]
        [--verifier V]
    release.py ops j1-status --state-dir DIR [--json]
    release.py ops j1-export --state-dir DIR --composite C

All state is explicit via --state-dir (release runs keep it inside
successor-006/). Exit 0 on success; exit 1 with a `release: error:`
line on any failure (loud, no silent partial effects).
"""
from __future__ import annotations

import argparse
import copy
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

import api  # noqa: E402
import sched_inputs as FI  # noqa: E402

FOLLOWUPS = {"S4": FI.S4_FOLLOWUP, "S4-followup": FI.S4_FOLLOWUP,
             "S6": FI.S6_FISSION_FOLLOWUP,
             "S6-followup": FI.S6_FISSION_FOLLOWUP}


def _followup(value: str) -> dict:
    if value in FOLLOWUPS:
        return copy.deepcopy(FOLLOWUPS[value])
    return json.loads(Path(value).read_text(encoding="utf-8"))


def _partition(value: str) -> dict[str, str]:
    part: dict[str, str] = {}
    for item in value.split(","):
        key, eq, owner = item.partition("=")
        if not eq or not key or not owner:
            raise ValueError(f"bad --partition item {item!r} "
                             f"(want k=v,k2=v2)")
        part[key] = owner
    return part


def _delegate(value: str) -> dict:
    parts = value.split(",")
    if len(parts) != 3:
        raise ValueError(f"bad --delegate {value!r} (want COST,TIME,INV)")
    try:
        cost, time_s, inv = float(parts[0]), float(parts[1]), float(parts[2])
    except ValueError:
        raise ValueError(f"bad --delegate {value!r} (want COST,TIME,INV)")
    return {"max_cost_usd": cost, "max_time_s": time_s,
            "max_invocations": inv}


def _inputs_dir(value: str) -> dict:
    root = Path(value)
    if not root.is_dir():
        raise ValueError(f"--inputs {value!r} is not a directory")
    out: dict[str, bytes] = {}
    for path in sorted(root.rglob("*")):
        if path.is_symlink():
            raise ValueError(f"--inputs: symlink "
                             f"{path.relative_to(root).as_posix()!r} "
                             f"refused")
        if path.is_file():
            out[path.relative_to(root).as_posix()] = path.read_bytes()
    return out


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(prog="release.py",
                                description=__doc__.splitlines()[0])
    sub = p.add_subparsers(dest="cmd", required=True)

    q = sub.add_parser("init", help="create a fresh run root")
    q.add_argument("--state-dir", required=True)

    q = sub.add_parser("run", help="route + run lane tasks")
    q.add_argument("--state-dir", required=True)
    q.add_argument("--tasks", default="S1,S2")
    q.add_argument("--with-sst", action="store_true")

    q = sub.add_parser("explain-route", help="show the routing decision")
    q.add_argument("--task", default=None)
    q.add_argument("--task-json", default=None)
    q.add_argument("--json", action="store_true")

    q = sub.add_parser("inspect", help="read-only state summary")
    q.add_argument("--state-dir", required=True)
    q.add_argument("--json", action="store_true")

    ops = sub.add_parser("ops", help="org operations")
    osub = ops.add_subparsers(dest="op", required=True)

    q = osub.add_parser("fuse", help="OP-1 fuse two worlds")
    q.add_argument("--state-dir", required=True)
    q.add_argument("--a", required=True)
    q.add_argument("--b", required=True)
    q.add_argument("--fused", required=True)
    q.add_argument("--reason", required=True)
    q.add_argument("--preset", default="FUSED")

    q = osub.add_parser("fission", help="OP-6 fission a composite")
    q.add_argument("--state-dir", required=True)
    q.add_argument("--composite", required=True)
    q.add_argument("--left", required=True)
    q.add_argument("--right", required=True)
    q.add_argument("--partition", required=True)
    q.add_argument("--reason", required=True)
    q.add_argument("--left-preset", default="L")
    q.add_argument("--right-preset", default="S")

    q = osub.add_parser("quarantine", help="OP-5 quarantine a world")
    q.add_argument("--state-dir", required=True)
    q.add_argument("--world", required=True)
    q.add_argument("--standby", required=True)
    q.add_argument("--reason", required=True)
    q.add_argument("--create-standby", action="store_true")

    q = osub.add_parser("revise", help="OP-3 record a revision")
    q.add_argument("--state-dir", required=True)
    q.add_argument("--task", required=True)
    q.add_argument("--from", dest="frm", required=True)
    q.add_argument("--to", required=True)
    q.add_argument("--reason", required=True)

    q = osub.add_parser("revoke", help="OP-4 revoke a capability")
    q.add_argument("--state-dir", required=True)
    q.add_argument("--world", required=True)
    q.add_argument("--cap", required=True)
    q.add_argument("--version", required=True)
    q.add_argument("--reason", required=True)
    q.add_argument("--new-owner", default="")

    q = osub.add_parser("reuse", help="OP-2 reuse a composite")
    q.add_argument("--state-dir", required=True)
    q.add_argument("--composite", required=True)
    q.add_argument("--followup", required=True)

    q = osub.add_parser("split-pair", help="run a task via split children")
    q.add_argument("--state-dir", required=True)
    q.add_argument("--left", required=True)
    q.add_argument("--right", required=True)
    q.add_argument("--followup", required=True)

    q = osub.add_parser("kill-resume", help="real kill + S3 resume drill")
    q.add_argument("--state-dir", required=True)

    q = osub.add_parser("settle", help="settle worlds, verify 0 stranded")
    q.add_argument("--state-dir", required=True)
    q.add_argument("--worlds", required=True)
    q.add_argument("--reason", required=True)

    q = osub.add_parser("recover", help="recover after a kill (R1)")
    q.add_argument("--state-dir", required=True)
    q.add_argument("--worlds", default=None,
                   help="settle exactly these worlds (default: settle none)")
    q.add_argument("--reason", default="recover")
    q.add_argument("--fission", default=None,
                   help="complete partial fission of composite C")
    q.add_argument("--left", default=None)
    q.add_argument("--right", default=None)
    q.add_argument("--partition", default=None)
    q.add_argument("--left-preset", default="L")
    q.add_argument("--right-preset", default="S")

    q = osub.add_parser("create-proc-world",
                        help="S5 advertise a procedure world")
    q.add_argument("--state-dir", required=True)
    q.add_argument("--world", required=True)
    q.add_argument("--bundle", required=True)
    q.add_argument("--reason", required=True)
    q.add_argument("--sched-preset", default=None)

    q = osub.add_parser("run-procedure",
                        help="S5 run a table procedure")
    q.add_argument("--state-dir", required=True)
    q.add_argument("--world", required=True)
    q.add_argument("--procedure", required=True)
    q.add_argument("--key", required=True)
    q.add_argument("--inputs", default=None,
                   help="stage every file under DIR as step inputs")

    q = osub.add_parser("quarantine-complete",
                        help="R11 COMPLETE a partial quarantine-transfer")
    q.add_argument("--state-dir", required=True)
    q.add_argument("--world", required=True)
    q.add_argument("--standby", required=True)
    q.add_argument("--reason", default="recover")

    q = osub.add_parser("quarantine-rollback",
                        help="R11 ROLL BACK a partial quarantine-transfer")
    q.add_argument("--state-dir", required=True)
    q.add_argument("--world", required=True)
    q.add_argument("--standby", required=True)
    q.add_argument("--reason", default="recover")

    q = osub.add_parser("nest", help="J1 nest an experiment world")
    q.add_argument("--state-dir", required=True)
    q.add_argument("--project", required=True)
    q.add_argument("--child", required=True)
    q.add_argument("--delegate", required=True,
                   help="COST,TIME,INV sub-grant from the project")
    q.add_argument("--custody", required=True,
                   help="comma-separated custody classes to hand off")
    q.add_argument("--reason", required=True)
    q.add_argument("--preset", default="Q")

    q = osub.add_parser("j1-work", help="J1 run a work task")
    q.add_argument("--state-dir", required=True)
    q.add_argument("--world", required=True)
    q.add_argument("--task", default="J1-T1")
    q.add_argument("--verifier", default=None)

    q = osub.add_parser("j1-kill-resume",
                        help="J1 real kill + byte-identical resume drill")
    q.add_argument("--state-dir", required=True)
    q.add_argument("--world", required=True)
    q.add_argument("--task", default="J1-T1")
    q.add_argument("--verifier", default=None)

    q = osub.add_parser("j1-status",
                        help="J1 read-only responsibilities + evidence")
    q.add_argument("--state-dir", required=True)
    q.add_argument("--json", action="store_true")

    q = osub.add_parser("j1-export", help="J1 export a composite bundle")
    q.add_argument("--state-dir", required=True)
    q.add_argument("--composite", required=True)

    q = sub.add_parser("j1-init", help="create a fresh J1 run root")
    q.add_argument("--state-dir", required=True)
    q.add_argument("--project", required=True)
    q.add_argument("--reason", default="J1 project world")
    return p


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        return dispatch(args)
    except Exception as exc:  # loud failure, no traceback noise
        print(f"release: error: {type(exc).__name__}: {exc}",
              file=sys.stderr)
        return 1


def dispatch(args) -> int:
    if args.cmd == "init":
        rep = api.init_run(args.state_dir)
        print(f"initialized {rep['state_dir']}: worlds={rep['worlds']}")
    elif args.cmd == "j1-init":
        rep = api.j1_init(args.state_dir, args.project, args.reason)
        print(f"initialized {rep['state_dir']}: project={rep['project']} "
              f"custody={rep['custody']}")
    elif args.cmd == "run":
        tasks = [t for t in args.tasks.split(",") if t]
        rep = api.run_tasks(args.state_dir, tasks,
                            with_sst=args.with_sst)
        for name, m in rep["tasks"].items():
            print(f"{name}: lane={m['lane']} valid={m['valid']} "
                  f"quality={m['quality']}/{m['prefs_total']} "
                  f"central={m['central_bytes']} direct={m['direct_bytes']}")
        if "SST" in rep:
            s = rep["SST"]
            print(f"SST: snapshot={s['snapshot_check']} "
                  f"termination={s['termination_reason']} "
                  f"champion={s['champion']} cost=${s['cost_usd']}")
    elif args.cmd == "explain-route":
        rep = api.explain_route_op(args.task, args.task_json)
        if args.json:
            print(json.dumps(rep, indent=2, sort_keys=True))
        else:
            print(f"{rep.get('task_id')}: lane={rep.get('lane')}")
            print(f"  rule: {rep.get('rule')}")
            print(f"  reason: {rep.get('reason')}")
    elif args.cmd == "inspect":
        rep = api.inspect_state_op(args.state_dir)
        if args.json:
            print(json.dumps(rep, indent=2, sort_keys=True, default=str))
        else:
            print(f"state: {rep['state_dir']} "
                  f"entries={rep['ledger_entries']}")
            for wid, w in rep["worlds"].items():
                print(f"  {wid}: {w['lifecycle']} "
                      f"custody={sorted(w['custodians'])}")
            print(f"  routing: "
                  f"{[(r.get('task_id'), r.get('lane')) for r in rep['routing']]}")
            print(f"  conservation: {rep['conservation']}")
    elif args.cmd == "ops":
        return dispatch_ops(args)
    return 0


def dispatch_ops(args) -> int:
    if args.op == "fuse":
        rec = api.fuse_op(args.state_dir, args.a, args.b, args.fused,
                           args.reason, preset=args.preset)
        print(f"fused {rec['parents']} -> {rec['fused_id']}; "
              f"removed={rec['removed_mechanism']}")
    elif args.op == "fission":
        rec = api.fission_op(args.state_dir, args.composite, args.left,
                             args.right, _partition(args.partition),
                             args.reason,
                             left_preset=args.left_preset,
                             right_preset=args.right_preset)
        print(f"fissioned {rec['composite']} -> {rec['children']}; "
              f"restored={rec['restored_mechanism']}")
    elif args.op == "quarantine":
        rec = api.quarantine_op(args.state_dir, args.world,
                                args.standby, args.reason,
                                create_standby=args.create_standby)
        print(f"quarantined {rec['world_id']} -> {rec['standby']}; "
              f"commitments={rec['commitments']}")
    elif args.op == "revise":
        entry = api.revise_op(args.state_dir, args.task, args.frm,
                              args.to, args.reason)
        print(f"revision recorded seq={entry['seq']}: "
              f"{args.frm} -> {args.to}")
    elif args.op == "revoke":
        entry = api.revoke_op(args.state_dir, args.world, args.cap,
                              args.version, args.reason,
                              new_owner=args.new_owner)
        print(f"revoke recorded seq={entry['seq']}: "
              f"{args.world}:{args.cap}@{args.version}")
    elif args.op == "reuse":
        m = api.reuse_op(args.state_dir, args.composite,
                         _followup(args.followup))
        print(f"reuse via {m['via']}: valid={m['valid']} "
              f"quality={m['quality']}/{m['prefs_total']}")
    elif args.op == "split-pair":
        m = api.split_pair_op(args.state_dir, _followup(args.followup),
                              args.left, args.right)
        print(f"split-pair via {m['via']}: valid={m['valid']} "
              f"quality={m['quality']}/{m['prefs_total']}")
    elif args.op == "kill-resume":
        rep = api.kill_resume_op(args.state_dir)
        m = rep["S3"]
        print(f"kill-resume: child_rc={rep['child_rc']} "
              f"valid={m['valid']} quality={m['quality']}/{m['prefs_total']} "
              f"re_executed={m['re_executed_invokes']}")
    elif args.op == "settle":
        worlds = [w for w in args.worlds.split(",") if w]
        rep = api.settle_op(args.state_dir, worlds, args.reason)
        print(f"settled {rep['settled_terminals']}: "
              f"markers={rep['grant_settle_markers']} stranded=0")
    elif args.op == "create-proc-world":
        rep = api.create_proc_world(args.state_dir, args.world,
                                    args.bundle, args.reason,
                                    sched_preset=args.sched_preset)
        print(f"proc-world {rep['world_id']}: procedure={rep['procedure']} "
              f"bundle={rep['bundle_sha256'][:16]}... "
              f"steps={rep['steps']}")
    elif args.op == "run-procedure":
        inputs = _inputs_dir(args.inputs) if args.inputs else None
        rep = api.run_procedure(args.state_dir, args.world,
                               args.procedure, args.key, inputs)
        print(f"run-procedure {rep['procedure']}/{rep['idem_key']}: "
              f"skipped={rep['skipped']} executed={rep['executed']} "
              f"re_executed={rep['re_executed_steps']} "
              f"child_executions={rep['child_executions']}")
    elif args.op == "quarantine-complete":
        rec = api.quarantine_complete_op(args.state_dir, args.world,
                                         args.standby, args.reason)
        print(f"quarantine completed {rec['world_id']} -> "
              f"{rec['standby']}; transfers={len(rec['transfers'])} "
              f"pending_source={rec['pending_source']}")
    elif args.op == "quarantine-rollback":
        rec = api.quarantine_rollback_op(args.state_dir, args.world,
                                         args.standby, args.reason)
        print(f"quarantine rolled back {rec['world_id']} <- "
              f"{rec['standby']}; "
              f"reversed={len(rec['transfers_reversed'])}")
    elif args.op == "nest":
        custody = [c for c in args.custody.split(",") if c]
        rec = api.nest_op(args.state_dir, args.project, args.child,
                          _delegate(args.delegate), custody,
                          args.reason, child_preset=args.preset)
        print(f"nested {rec['child']} in {rec['project']}: "
              f"delegation={rec['delegation']} custody={rec['custody']}")
    elif args.op == "j1-work":
        m = api.j1_work_op(args.state_dir, args.world, args.task,
                           verifier=args.verifier)
        print(f"j1-work {m['task_id']} via {m['world']}: valid={m['valid']} "
              f"quality={m['quality']}/{m['prefs_total']} "
              f"re_executed={m['re_executed_invokes']}")
    elif args.op == "j1-kill-resume":
        rep = api.j1_kill_resume_op(args.state_dir, args.world, args.task,
                                    verifier=args.verifier)
        print(f"j1-kill-resume: child_rc={rep['child_rc']} "
              f"valid={rep['valid']} "
              f"quality={rep['quality']}/{rep['prefs_total']} "
              f"re_executed={rep['re_executed_invokes']}")
    elif args.op == "j1-status":
        rep = api.j1_status_op(args.state_dir)
        if args.json:
            print(json.dumps(rep, indent=2, sort_keys=True, default=str))
        else:
            print(f"state: {rep['state_dir']}")
            for wid, w in rep["worlds"].items():
                print(f"  {wid}: {w['lifecycle']} "
                      f"custody={w['custody']} verdicts={w['verdicts']}")
            print(f"  delegations={len(rep['delegations'])} "
                  f"nests={len(rep['nests'])} "
                  f"solutions={rep['solutions']}")
            print(f"  conservation: {rep['conservation']}")
    elif args.op == "j1-export":
        rep = api.j1_export_op(args.state_dir, args.composite)
        print(f"exported {rep['composite']}: "
              f"derived_from={rep['derived_from']} "
              f"solutions={rep['solutions']}")
    elif args.op == "recover":
        worlds = ([w for w in args.worlds.split(",") if w]
                  if args.worlds is not None else None)
        part = (_partition(args.partition)
                if args.partition is not None else None)
        rep = api.recover_op(args.state_dir, worlds, args.reason,
                             fission=args.fission, left=args.left,
                             right=args.right, partition=part,
                             left_preset=args.left_preset,
                             right_preset=args.right_preset)
        print(f"recover: specs_repaired={rep['specs_repaired']} "
              f"births={rep['births_completed']} "
              f"fusions={[f['fused_id'] for f in rep['fusions_completed']]} "
              f"fissions={[f['composite'] for f in rep['fissions_completed']]} "
              f"proc_adopted={[(a['step'], a['idem_key']) for a in rep['proc_adopted']]} "
              f"proc_rerunnable={[(r['step'], r['idem_key']) for r in rep['proc_rerunnable']]}")
        if rep["partial_quarantines"]:
            print(f"recover: PARTIAL QUARANTINE(S) need operator repair:")
            for step in rep["quarantine_operator_steps"]:
                print(f"  {step}")
        if rep["settle"] is not None:
            s = rep["settle"]
            print(f"recover: settled {s['settled_terminals']}: "
                  f"markers={s['grant_settle_markers']} stranded=0")
        elif rep["settle_skipped_no_worlds"]:
            print("recover: settle skipped (no --worlds given)")
        if rep["recovery_notes"]:
            print(f"recover: notes={rep['recovery_notes']}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
