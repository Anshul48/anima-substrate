# r2 builder acceptance verdict — successor-003 release candidate

Date: 2026-10-04. Builder state: fresh dirs under `/tmp/r2build/*`
(never builder `runs/`); consumer interfaces only (`release.py` CLI +
`api.py` on frozen bytes with `/tmp` state); suites + calibrate from
byte-identical `/tmp` copies (diff -r clean, 0 lines × 4 copies) since
they scratch `.test-tmp/` in-tree. `PYTHONDONTWRITEBYTECODE=1`;
system `python3` = 3.12.3; `prototype/w1/.venv` pydantic = 2.13.5.
`successor-003/` + `successor-002/` never written (IDENTITY 45/45 +
41/41 before AND after; FROZEN-BASELINE 3639 + 1 expected live miss).

## Verdict: BUILDER-ACCEPT (all A1–A10 PASS; 1 low-severity finding F1)

All ten criteria PASS on observed evidence. Finding F1 (sharp edge,
off-procedure + loud + functionally repairable) is recorded, not
blocking; the independent lane judges. Preserved attempts:
`A8-consumer-attempt1-probebig.log`, `A8-consumer-attempt2-slice.log`
(probe bugs, fixed), `A10-edge-attempt1-overstrict.log` (over-strict
probe assertion led to F1's discovery) + `A10-F1-sharp-edge.md`.

## Per-criterion results

- A1 PASS (identity/build). IDENTITY 45/45 OK; regenerated vendor
  manifest matches frozen (54 files, `5f1f3789…`, file list equal);
  `sched_checker --self-check` OK; pydantic 2.13.5; python 3.12.3.
  (`A1-identity.log`)
- A2 PASS (demo spine, fresh `/tmp` state). Exit 0; S1/S2/S3 VALID
  4/4 lanes+bytes r1-identical (655/0, 310/500, 685/500); S4 5/5 via
  SC-FUSED; S6 4/4 via SC-L2/SC-S2; resume 0 re-invokes, pre-kill
  bytes identical, child rc=-9; SST champion_found $0; settle 5
  markers 0 stranded; 6 routing decisions; EVIDENCE exact fields
  56/56 vs `accept/EXPECTED.json`. (`A2-demo.log`, `A2-expected.log`)
- A3 PASS (carried suites). 9/9 conformance + 7/7 fission + 17/17
  successor (incl. SST $0/MATCH legs), all EXIT=0 from verified
  byte-identical copies. (`A3-*.log`)
- A4 PASS (atomicity). 27/27 OK, EXIT=0 (refusal proofs, boundary
  matrices, kill-during-recovery, real SIGKILLs). (`A4-atomicity.log`)
- A5 PASS (sampled kill matrices, consumer CLI, fresh `/tmp` state).
  119/119: settle N=1,2,5,7,8clean; fuse N=1,3,9,13,15clean +
  pre-spec; fission N=1,5,10,14,15clean + pre-spec (bare refuses
  iff partial); real SIGKILL landing; kill-during-recovery — every
  landing converged via `ops recover` (+ defined re-runs),
  conservation ok, 0 stranded, reuse serves after fuse recovery.
  (`A5-killmatrix.log`)
- A6 PASS (calibrate 2.61x bytes-only). 810 vs 310 = 2.61x
  reproduced; wording audit: all 10 ratio mentions bytes-scoped
  with explicit no-token/attention/cost disclaimers, no overclaim
  sentence. (`A6-calibrate.log`, `A6-wording.log`)
- A7 PASS (SST MATCH + refusal $0). MATCH 54/`5f1f3789…`; tamper-a-
  COPY refused rc=1 naming the file + hash drift, before any SST
  import; zero `../sst` / staging refs in `*.py` (real grep rc=1);
  A2 leg: TEST-only, champion_found, $0.0, pydantic 2.13.5,
  snapshot_unchanged, sst_file inside snapshot; pre/post MATCH.
  (`A7-sst.log`)
- A8 PASS (consumer coverage). 31/31: every CLI verb on fresh state
  (init/run/explain-route±json/inspect/fuse/reuse/fission/
  split-pair/settle/revise/revoke/quarantine/kill-resume/recover)
  + api.py direct (open_run/explain/inspect/recover/settle
  refusal with deny-only growth + zero partials) + negatives
  (run-after-revoke rc=1 ×3 durable, bogus-owner ValueError with
  no mutation, CLI `release: error:` shape rc=1).
  (`A8-consumer.log` + 2 preserved probe-bug attempts)
- A9 PASS (frozen intact). s003 45/45 + s002 41/41 after; baseline
  3639 + exactly the R1-note-E live miss; `.test-tmp/` residue
  clean; no writes outside `release-r2/` + `/tmp`; `../sst`
  untouched-by-builder. (`A9-frozen.log`)
- A10 PASS (edge/negative). 26/26: wrong-partition contradicts
  (then correct completes); torn-ledger recover refuses disk-loss
  + inspect loud; bare recover settles nothing (lifecycles
  byte-unchanged); unsettled-terminal inspect-readonly + settle
  exact error + zero partials; bad partitions ×4 + non-composite
  refused with ≤1 host_reopen growth; fission-args-without-partial
  refused; recover `--worlds COMPOSITE` blocked on partial (pinned
  path) with one-call complete+settle-children; revoked invoke
  denied + recorded. (`A10-edge.log`, `A10-F1-sharp-edge.md`)

## Finding F1 (LOW, not blocking — independent lane judges)

Direct `ops settle --worlds SC-FUSED` on a partial fission succeeds
(rc=0, custody-orthogonal per longstanding contract — verified on a
fresh baseline) and strands custody in the dissolved world; the next
`recover --fission` refuses loudly (`still holds custody (ledger
inconsistent)`); custody is operator-transferable back to exactness
but the `fission` entry then stays unappendable (loud). Off-procedure
(CONSUMER §6 mandates `ops recover` after a kill), loud at every
step, no contract clause promises otherwise. Suggested disposition:
record-only doc clarification (see `A10-F1-sharp-edge.md`); no tree
edit (frozen).
