"""Successor-002 routing calibration (stdlib-only, in-process).

Runs the SAME task (S2) through BOTH lanes on fresh hosts and reports
central-handled canonical-JSON bytes per lane plus the ratio. This is
the entire content of the calibrated "2-6x" claim: a serialized-bytes
ratio inside the task envelope — NO token/attention/cost equivalence
is claimed (see REPORT.md).

Run from the repo root:
    PYTHONDONTWRITEBYTECODE=1 python3 prototype/successor-002/calibrate.py

Scratch state lives under successor-002/.test-tmp/ and is removed
afterwards unless --out is given (evidence JSON only).
"""
from __future__ import annotations

import copy
import json
import shutil
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

from routing import ChannelRegistry, Coordinator, HCoordinator, setup_host
from pipeline import LaneCtx, run_sched_task
import sched_inputs as FI
import successor_demo as DEMO


def run_lane(lane: str, root: Path) -> dict:
    host = setup_host(root, DEMO.main_worlds(root / "state"))
    if lane == "central":
        ctx = LaneCtx("central", Coordinator(), ChannelRegistry())
    else:
        ctx = LaneCtx("local", HCoordinator(), ChannelRegistry())
    return run_sched_task(root, host, copy.deepcopy(FI.S2), ctx)


def calibrate(scratch: Path) -> dict:
    if scratch.exists():
        shutil.rmtree(scratch)
    c = run_lane("central", scratch / "central")
    l = run_lane("local", scratch / "local")
    assert c["valid"] and l["valid"]
    assert c["quality"] == c["prefs_total"] == 4
    assert l["quality"] == l["prefs_total"] == 4
    ratio = c["central_bytes"] / l["central_bytes"]
    return {
        "task": "S2 (identical inputs both lanes)",
        "unit": ("central-handled canonical-JSON bytes inside the task "
                 "envelope (coordinator.handle inputs; fragments central, "
                 "commitments local)"),
        "central_lane": {"central_bytes": c["central_bytes"],
                         "direct_bytes": c["direct_bytes"]},
        "local_lane": {"central_bytes": l["central_bytes"],
                       "direct_bytes": l["direct_bytes"]},
        "ratio_central_over_local": round(ratio, 2),
        "not_claimed": ("token/attention/cost equivalence, cross-task "
                        "generality, learned routing"),
    }


def main(argv: list[str]) -> int:
    scratch = HERE / ".test-tmp" / "calibrate"
    out = None
    for a in argv[1:]:
        if a.startswith("--out="):
            out = Path(a.split("=", 1)[1])
    rep = calibrate(scratch)
    shutil.rmtree(scratch, ignore_errors=True)
    try:
        (HERE / ".test-tmp").rmdir()  # remove parent iff left empty
    except OSError:
        pass
    print(f"S2-central: central={rep['central_lane']['central_bytes']} "
          f"direct={rep['central_lane']['direct_bytes']}")
    print(f"S2-local:   central={rep['local_lane']['central_bytes']} "
          f"direct={rep['local_lane']['direct_bytes']}")
    print(f"ratio central/local = "
          f"{rep['ratio_central_over_local']}x "
          f"(canonical-JSON bytes, task envelope only)")
    if out is not None:
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(json.dumps(rep, indent=2, sort_keys=True) + "\n",
                       encoding="utf-8")
        print(f"wrote {out}")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
