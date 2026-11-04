# M1-redux PREREG (FROZEN — bytes immutable after proceeding)

- Frozen: 2026-10-04 (UTC), BEFORE any non-throwaway execution. Step-0
  throwaway probes (`M1R-T0-*`) are the only H2 executions so far.
- Design: `DESIGN.md` (sha256 below). This file freezes the decision rule.
- Mode 444 after writing; sha256 recorded here-by-reference in
  `PREREG-LOG-ENTRY.md` (coordinator countersigns from the M1-redux report).

## 1. Frozen parameters

- Train: `M1R-TR-01..18` × {central, local} = 36 items.
- Test (held-out): `M1R-TE-01..18` × {central, local} = 36 items
  (`N_TEST_ITEMS = 36`). Descriptors disjoint from train and T0 (asserted).
- Model: per-group-mean, key
  `(n_tasks, nL_req, nS_req, nL_pref, nS_pref, lane)`; fallback = train
  lane-conditional mean (expected 0 uses; any use → VOID).
- Baselines: CONSTANT (train global mean); HOST-RULE (train mean per
  `(rule_lane(task), exec_lane)`).
- Metric: MAE over the 36 test items in `central_bytes`.
- Guards: S1,S2-by-name per phase must reproduce (655,0) + (310,500).

## 2. Task pins (verbatim `main/task-pins.sha256`)

File sha256: `96aa3a91c8134e532b3d92c954877d3405c2df70aa5786dd23a6e7f9e99b7c6e`

```
8b669159f7ef7218e51340518284a6a8fde0014c8b83b9119b25cc556eb65c89  M1R-TE-01.json
0259e46b06f966b62cb526ad2d73771c789a6d4e29f0bd21a862ab5e6a599d7c  M1R-TE-02.json
7bc324238b431be59dbf012f32a0c4072b658b324bdcdc2a9f009a7da48689d2  M1R-TE-03.json
93d2a568e2e91d2fca37b4b8ef4cb0cfa910a906faf1fd986983ebf5e60388fc  M1R-TE-04.json
d11fbf197c75c7b8c0f7da4e160996bacc20aaa20f0fcc286ad5ffbb1abf8e1c  M1R-TE-05.json
22cee220981413c4e3501600e7458b0a6973ef5461d406c5f83d85052509d904  M1R-TE-06.json
8d3dd9b4e05c15a65ead0dd896186e934c59de782ba4883b7a8822ae85bf9a5f  M1R-TE-07.json
c34f564ad0158be6f691862469cbf4aa25d49f6c574b9f1fe2574e84fb59f8dd  M1R-TE-08.json
3d968aebb30d9889668160bc6761402debb9ba792b9d8246b67a4ec219246b54  M1R-TE-09.json
bd2d01a679406935d01ebe8633ec99df7d3adf2cfd7138cd22360d09edd4db61  M1R-TE-10.json
38e52a9caa6a27da84a9e5b4a00dae6d02909c07e419d49a80b0820140974af8  M1R-TE-11.json
0114c8a72615a850bf2944d1f1c2a9da83dc92717bb6d8a993874a87a3782e27  M1R-TE-12.json
f410d53c562cf7f5ccd8fd0ff65d450767527ee2d7a11e6334eb11e0918db7af  M1R-TE-13.json
84a0cba13c1da3c9bc347b1c9d20239cd3609e3571d46a812f0dcf613a2e3ed0  M1R-TE-14.json
6564dc27394fc54e99c8c17c8cc5aa9bf53a2d813e598da5e5e2c4c75bb64b12  M1R-TE-15.json
1f1d744c7ad60b448374bbc6846b7efb6f2ff117851cda40b07cc10ae6ed9e28  M1R-TE-16.json
c03e2f6d378dbd352124c5320dce8754f3a87944ed00b074182838ac114e539f  M1R-TE-17.json
96dd28854384d4e50ba487cc681d128bd5336fc6ba9f1476605f1fee463e2def  M1R-TE-18.json
c0bab6b93852028a2359793dceb8af828bebe4e1e05ef1ab63637ccf9f7b0880  M1R-TR-01.json
2439041fbacd4b3b82545fafcff31e8d181193422bf0c75bda84411a983b5a1d  M1R-TR-02.json
c73def409e33905ed6e608707e2537040c139b5a00a561d1dddf5e6a09b9b549  M1R-TR-03.json
a4c893d45a1f06751f2f9680e28e9c99567c31697781bb3b26f3e31b18ff289e  M1R-TR-04.json
7528fe6e2ae311ba58ad27fea40e336b85a25db607c759d7bc022e09f422a29b  M1R-TR-05.json
42818e66df1ad1a61b11b2d83a95cbee1b73b33e82e4599d98d8f350f2ddc8d9  M1R-TR-06.json
3093779b591044d9a993dec653d8a034ed07224f2591cd6c60cea37e39de2032  M1R-TR-07.json
81531e01dfcb89fd6517622e0c1b4e1bb18fb431bff19fe96edb841d62fcc5ae  M1R-TR-08.json
ab9acc6d4f0ae2dbef80fc2e84c330395302c9e04a5588c52c3994decc9a6fe4  M1R-TR-09.json
894015a99d46b1861b8f4dec7a5a736b4a9e8e33d0998335bfe34dfcf5341b70  M1R-TR-10.json
10a79877915c4e21ba18df000d87dedf027e8a88ad833e7d10cf931f63051305  M1R-TR-11.json
11a78a541467f221d927ccaab6f24b7971000c54e722895f96a9c5e7b8deb617  M1R-TR-12.json
c09e665090840a2557a5dc76c68f3c66a5ce7f94b9263077addb6a73992d4365  M1R-TR-13.json
65ee0516c81474fd0694931592e99b265dc89f8e58504203f76073fb05ca361e  M1R-TR-14.json
ad45ea3516891c037c0c141fd3fdd9eced414f2fad1c21a9602ba414cdaacf56  M1R-TR-15.json
dd474811b2b5f105e4878f77ed781492c7bbe883ce72807ba5d613b6d3b45ea1  M1R-TR-16.json
3e89eb0a6884f4387a7bd05bc4805481b17a41c708f7a66c5381d21ccb9eef49  M1R-TR-17.json
891fc3549befc998342470204312807a1d6c5832ffe31a54d7fae5293a4722f8  M1R-TR-18.json
```

Generator pin: `gen_main.py` sha256
`34fb6e618fc890605870abd00f9bd7b7f06dcfa1d04bfa66e6aea234d65effb0`
(deterministic; regen verified byte-identical pre-freeze).

## 3. Thresholds — EXACT coded predicates (verbatim; L1 lesson B)

`predicates.py` sha256:
`a1089fb58c4952f8f566c689ebbc3d71fbd6e93e98b891bb5379039656935235`

The verdict script imports `predicates.verdict` (never reimplements it).
Verbatim file content:

```python
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
```

## 4. Analysis rules (frozen)

- Single `harness.py` evaluation run after ALL 74 executions (no
  peeking-and-tuning; harness sha256 at freeze:
  `28ff96906c8e1d058420a93638d73ecf522ff6f3a191e7db64017f484edaed7d`).
  Runner `run_main.py` sha256 at freeze:
  `7aebd2e46d629f23d7adf1faef8b8a11ce492e496e43942ff4a30e2bf722b76f`.
- No task replacement/re-rolls; missing/invalid test data → VOID.
- Secondaries advisory only (per-size MAE, plain-vs-permuted MAE,
  max-abs-err, entries/invokes invariance, direct_bytes descriptives).
- `DESIGN.md` sha256 at freeze:
  `89c0f0d95aebbdc88c8dcef564dbbaed1a21643f2de60ef77a86be20352f5556`.

## 5. Design-time expectation (NOT a result)

If step-0 structure holds: model MAE O(0–30) (placement residual in 6/18
size-5/6 cells, central lane only; all other cells near-exact incl.
permuted identities), const/rule MAEs O(50–100) → P1∧P2 PASS with margin.
A P1∧P2 PASS is a calibrated cost mapping, NOT transfer (see DESIGN §9).
