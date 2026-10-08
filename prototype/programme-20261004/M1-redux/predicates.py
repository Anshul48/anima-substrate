"""M1-redux preregistered predicates (FROZEN — sha256 pinned in PREREG.md).

The verdict script imports THIS module (never reimplements the predicates).
Quoted verbatim in PREREG.md (L1 lesson B).
"""
from __future__ import annotations

N_TEST_ITEMS = 36


def verdict(mae_model: float, mae_const: float, mae_rule: float,
            n_test_items: int, n_valid_test: int, fallback_uses: int,
            guards_ok: bool, ids_disjoint: bool) -> dict:
    """Apply the frozen M1-redux decision rule."""
    # P1: task-conditional mapping beats the constant predictor substantially
    P1 = (mae_model < 0.5 * mae_const)
    # P2: ... and beats the host-rule-derived predictor substantially
    P2 = (mae_model < 0.5 * mae_rule)
    # Validity gate: data + coverage + calibration (else VOID, not NEGATIVE)
    valid = ((n_test_items == N_TEST_ITEMS)
             and (n_valid_test == N_TEST_ITEMS)
             and (fallback_uses == 0)
             and guards_ok
             and ids_disjoint)
    if not valid:
        OVERALL = "VOID"
    elif P1 and P2:
        OVERALL = "PASS"
    else:
        OVERALL = "NEGATIVE"
    return {"P1": P1, "P2": P2, "valid": valid, "OVERALL": OVERALL}
