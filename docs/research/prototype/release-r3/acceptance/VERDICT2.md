# r3 independent acceptance verdict (lane) — ACCEPT-WITH-NOTES

Date: 2026-10-04. Lane: independent (own N/params/mappings/probes,
fresh /tmp state, frozen bytes read-only, suites from diff-r-verified
copies). Builder verdict assessed, never trusted.

## Verdict: ACCEPT-WITH-NOTES (record-only; r3 freezes)

All A1–A10 PASS on lane-observed evidence. No new product findings;
two record-only notes. r3 may freeze.

## Per-criterion evidence (lane-observed)

- A1 PASS: IDENTITY 45/45; manifest regen byte-MATCH (cmp clean, 54
  files, 5f1f3789…); self-check OK; pydantic 2.13.5; python 3.12.3;
  zero in-tree writes (find-newer clean, no pycache).
- A2 PASS: demo exit 0; lanes+bytes r1-identical; S4 5/5; S6 4/4;
  resume 0 re-invokes rc=-9; SST champion_found $0; settle 5/0; 6
  routing decisions; OWN mapping 61/61 EXPECTED leaves.
- A3 PASS: 9/9 + 7/7 + 17/17 from verified copy.
- A4 PASS (full loop): 39/39 OK in 120.8s; measured fission wall
  0.17–0.32s; suite loop 8 in-window + 42 completed, 0 torn; lane's
  own 45 aimed kills (20/20 in-window + 25 near-wall incl. 6 mid-op
  converged), 0 torn, 1 benign orphan. (Covers the coordinator's
  weak-statistical-leg note on the builder's 43/50 completed run.)
- A5 PASS (81/81, own N): settle/fuse/fission legs + pre-spec +
  kill-during-recovery + real SIGKILL + MID-APPEND (prefix parses,
  tail torn, disk-loss refusal) + MID_SIDE_WRITE on two basenames
  (absent-artifact + stale-CONFIG landings converge). Conservation
  everywhere. One lane probe bug found+fixed (documented second
  recover), matching suite semantics.
- A6 PASS: 2.61x reproduced; ratio mentions bytes-scoped with
  disclaimers; durability audit: 12 durab* hits classified (5
  separations + 4 disclosed N2 + 2 kill-scoped + 1 test comment),
  5 power hits all disclaimers, zero fsync calls, no multi-writer
  claim, all never-torn claims kill-scoped + evidenced; N1/N2 pins
  as disclosed.
- A7 PASS: MATCH 54/5f1f3789; tamper-a-COPY rc=1 pre-import;
  zero producer refs; sst import behind Gate1+Gate2; TEST-only,
  champion_found, $0.0, pydantic 2.13.5, snapshot_unchanged.
- A8 PASS (22/22): 14 CLI verbs + 5 api calls + 3 negatives
  (revoked-run ContractViolation; bogus-owner pre-mutation refusal;
  exact ValueError + error shape).
- A9 PASS: s004 45/45 + s003 45/45 + s002 41/41 before AND after;
  baseline 4140 + exactly the 1 live miss (coordinator log,
  legitimate); r2's 27 files OK; newer-than-marker empty; no .pyc;
  .test-tmp empty; ../sst porcelain 0 @df78f42 (lane-visible,
  checked — no coordinator substitution needed). Builder's 2
  disclosed in-tree events re-verified content-neutral (manifest
  sha == IDENTITY pin; no pycache).
- A10 PASS (32/32): wrong-partition→correct; bad shapes
  bookkeeping-only; no-partial RuntimeError; torn ledger/checkpoint
  classified refusals (own world + tear depth); bare recover
  settles nothing; unsettled-terminal exact + deny-only; F1
  re-verified with §5 WARNING verbatim; N1/N2 pins exact.

## Records spot-checks (5+5, corroborated)

RELEASE-RECORD: 14 pins exact; accept/vendor/REPORTs byte-identical
to r2; builder counts exact in logs; r2 pins + R8 numbers live.
CONSUMER-DELTA: venv default + pydantic pin in code and measured;
verbs diff-clean; real .tmp orphans observed with no read path;
reattach deny+suspended live; F2 closure + withdrawn claim +
process/power split accurate.

## Record-only notes

1. accept/README.md (byte-identical carry) still references
   successor-002/ paths and "8/8" conformance (actual 9/9) —
   pre-existing across r1/r2/r3, frozen by policy, not r3's to fix.
2. Lane's first pydantic probe ran without the bytecode export;
   verified zero effect (find-newer clean everywhere).

## Acceptance mapping (RELEASE-PLAN.md A1–A10)

A1–A10 PASS: yes. F2 closure + ledger honesty + durability split:
yes, live-verified. Records accurate: yes. Frozen intact (all
three releases + SST): yes. Independently verified: yes.

**r3 status: ACCEPTED. successor-004/ + release-r3/ FROZEN.**
r3 = R3 gains (atomic side writes, interior-write coverage,
withdrawn ledger no-tear, process/power separation, F1/F2+N1/N2 doc
precision) as a usable release; r1/r2 remain frozen and
reproducible. Owned deferreds: N1/N2 narrowings (next docs pass),
quarantine-transfer/multi-writer/disk-loss/cross-host, U-branch
(BLOCKED behind I1–I6; re-scope decision with user), Q5 (user).
