## M1-REDUX 2026-10-04T16:42:17Z

- experiment: M1-redux (grid+holdings → per-lane central_bytes on held-out
  lane descriptors; ACCEPTED H2 host; step-0 PROCEED with 26 observations)
- work_dir: prototype/programme-20261004/M1-redux/
- prev_hash: af809304fc61ba4698292232f1d8ff7a54c3a066df2815b67013dbf82cf88f0e
- prev_basis: sha256 of the PREREG-LOG.md genesis section bytes
  (## GENESIS line through end-of-file, 394 bytes as read 2026-10-04;
  coordinator to verify/recompute at append)
- prereg: PREREG.md sha256 cfe4f633840337abe96aca6743c69d691ef59c10762fa2edfdcb9a621a58d33c
- design: DESIGN.md sha256 89c0f0d95aebbdc88c8dcef564dbbaed1a21643f2de60ef77a86be20352f5556
- predicates: predicates.py sha256 a1089fb58c4952f8f566c689ebbc3d71fbd6e93e98b891bb5379039656935235
- predicates_note: exact coded predicates; verdict imports this module
  (never reimplements); quoted verbatim in PREREG.md section 3
- tasks: main/task-pins.sha256 sha256 96aa3a91c8134e532b3d92c954877d3405c2df70aa5786dd23a6e7f9e99b7c6e
- tasks_note: 36 pins (18 train M1R-TR-01..18 + 18 test M1R-TE-01..18,
  all 9-char IDs, disjoint from each other and from M1R-T0-* probes)
- generator: gen_main.py sha256 34fb6e618fc890605870abd00f9bd7b7f06dcfa1d04bfa66e6aea234d65effb0
- generator_note: deterministic; regeneration verified byte-identical
  (sha256sum -c 36/36) before freezing
- harness: harness.py sha256 28ff96906c8e1d058420a93638d73ecf522ff6f3a191e7db64017f484edaed7d
- runner: run_main.py sha256 7aebd2e46d629f23d7adf1faef8b8a11ce492e496e43942ff4a30e2bf722b76f
- rule: N_TEST_ITEMS=36; P1=(mae_model < 0.5*mae_const);
  P2=(mae_model < 0.5*mae_rule); valid=(36 test items present AND VALID,
  fallback_uses==0, both phase guards reproduce S1 655/0 + S2 310/500,
  TR/TE/T0 IDs pairwise disjoint); OVERALL=PASS iff valid AND P1 AND P2,
  VOID iff not valid, else NEGATIVE
- model: per-group-mean over (n_tasks,nL_req,nS_req,nL_pref,nS_pref,lane);
  baselines CONSTANT (train global mean) + HOST-RULE (train mean per
  (rule_lane, exec_lane)); metric MAE on central_bytes
- entry_hash_basis: sha256 of this entry body EXCLUDING this entry_hash
  line (all bytes above it, verbatim)
- entry_hash: e077d5e49797cdac01d2e59b912f6010d4c27e3d8eeb0fc2d13018b912b93de5
