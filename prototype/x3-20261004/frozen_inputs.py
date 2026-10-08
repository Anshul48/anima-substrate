"""X3 frozen task inputs. FROZEN before run 1; sha256 recorded in
FREEZE.json; NEVER edited after. x3_run.py refuses to run if the hash
differs from the frozen value (after the freeze step records it).
"""
from __future__ import annotations

SLOTS_T1 = {"S0": {"machine": "M0", "time": "t0"},
            "S1": {"machine": "M1", "time": "t0"},
            "S2": {"machine": "M0", "time": "t1"},
            "S3": {"machine": "M1", "time": "t1"}}

T1 = {
    "task_id": "T1",
    "slots": dict(SLOTS_T1),
    "tasks": {"A": {"window": ["S0", "S2"]}, "B": {"window": ["S1", "S3"]},
              "C": {"window": ["S0", "S1"]}, "D": {"window": ["S2", "S3"]}},
    "precedence": [["A", "B"], ["C", "D"]],
    "prefs": {"A": "M0", "B": "M1", "C": "M1", "D": "M0"},
    # Split across worlds: neither side can reach full quality alone.
    "holdings": {"X3-L": {"req_tasks": ["A", "B"], "prefs": ["A", "B"]},
                 "X3-S": {"req_tasks": ["C", "D"], "prefs": ["C", "D"]}},
    "adapter": "list2slot/v1",
}

T2 = {
    "task_id": "T2",
    "base": {
        "task_id": "T2-base",
        "slots": dict(SLOTS_T1),
        "tasks": {"A": {"window": ["S0", "S2"]}, "B": {"window": ["S1", "S3"]},
                  "C": {"window": ["S0", "S1"]}, "D": {"window": ["S2", "S3"]}},
        "precedence": [["A", "B"], ["C", "D"]],
        "prefs": {"A": "M0", "B": "M1", "C": "M1", "D": "M0"},
        "adapter": "list2slot/v1",
    },
    "revision": {
        "from": "list2slot/v1", "to": "list2slot/v2",
        "window_changes": {"B": ["S3"]},
        "declared_loss": ["preferences"],
    },
    "revised": {
        "task_id": "T2-v2",
        "slots": dict(SLOTS_T1),
        "tasks": {"A": {"window": ["S0", "S2"]}, "B": {"window": ["S3"]},
                  "C": {"window": ["S0", "S1"]}, "D": {"window": ["S2", "S3"]}},
        "precedence": [["A", "B"], ["C", "D"]],
        "prefs": {"A": "M0", "B": "M1", "C": "M1", "D": "M0"},
        "adapter": "list2slot/v2",
    },
    "revocation": {"capability": "slot.assign", "version": "1.0",
                   "from": "X3-S", "to": "X3-L",
                   "reason": "ownership change at v1->v2"},
    "holdings": {"X3-L": {"req_tasks": ["A", "B"], "prefs": ["A", "B"]},
                 "X3-S": {"req_tasks": ["C", "D"], "prefs": ["C", "D"]}},
}

T3 = {
    "task_id": "T3",
    "composite_from": "T1",
    "composite_task": {
        "task_id": "T1",
        "slots": dict(SLOTS_T1),
        "tasks": {"A": {"window": ["S0", "S2"]}, "B": {"window": ["S1", "S3"]},
                  "C": {"window": ["S0", "S1"]}, "D": {"window": ["S2", "S3"]}},
        "precedence": [["A", "B"], ["C", "D"]],
        "prefs": {"A": "M0", "B": "M1", "C": "M1", "D": "M0"},
    },
    "followup": {
        "task_id": "T3-followup",
        "slots": {**SLOTS_T1, "S4": {"machine": "M1", "time": "t2"}},
        "tasks": {"A": {"window": ["S0", "S2"]}, "B": {"window": ["S1", "S3"]},
                  "C": {"window": ["S0", "S1"]}, "D": {"window": ["S2", "S3"]},
                  "E": {"window": ["S4"]}},
        "precedence": [["A", "B"], ["C", "D"]],
        "prefs": {"A": "M0", "B": "M1", "C": "M1", "D": "M0", "E": "M1"},
    },
    "transfer": {"state_class": "sched.composite", "from": "X3-S",
                 "to": "X3-T", "continuity": "sha256-of-composite"},
}

TASKS = {"T1": T1, "T2": T2, "T3": T3}
