# H2-VERIFICATION — independent acceptance record (AUTH-1 gate)

- Verdict: **ACCEPT-WITH-NOTES** (all §5 items PASS on observed evidence).
- Verifier: independent lane (read + execute only; H2 source/docs
  untouched; /tmp scratch removed; .test-tmp/vrfy-* left auditable).
- Date: 2026-10-04. H2-lane/ bytes are exactly as the verifier checked
  them — this record lives here so the tree stays frozen.

## §5 bar (independently observed)

1. Suites green + accept: 9/9 + 7/7 + 18/18 + 17/17 (SST $0/MATCH
   legs) + FULL 27/27 atomicity (verifier ran all, not spots);
   calibrate 2.61x; snapshot MATCH 54/5f1f3789; demo exit 0. Own
   accept re-derivation with own mapping: 52/52 exact PASS;
   H2-vs-003 demo evidence differs only in path strings; lanes 6/6;
   S3 legacy rule kept. PASS.
2. Novel-lane conformance on the VERIFIER'S OWN 5-task grid (not
   builder fixtures): hand derivations matched exactly
   ((4,True)→local VALID 5/5 central=350/direct=590; (2,False)→
   central VALID 5/5); both override forms executed VALID with
   rule_lane/override/final_lane recorded; S1/S2-by-JSON == by-name
   (cmp-identical solutions + routing logs); 3 own malformed shapes
   refused rc=1 with zero ledger growth; unknown names raise;
   unset-hook ≡ explicit-None byte-identical. PASS.
3. Conservation + recovery: ok on all novel runs; own kill-resume
   (real Popen.kill rc=-9 mid-dialogue) converged VALID 5/5,
   re_executed_invokes=0, 0-stranded settle, clean inspect. PASS.
4. Frozen: s003 IDENTITY 45/45 (before/after/post-cleanup); H2
   IDENTITY 46/46 (before/after/final); FROZEN-BASELINE 1196/1196;
   exclusion audit honest (zero runs/test-tmp/pycache/venv/H2-lane/
   coordinator-log entries; all five frozen inputs covered). PASS.
5. Verdict: ACCEPT-WITH-NOTES (below). L2-execute unblocked
   coordinator-side (AUTH-2 was conditionally granted; conditions
   now reduce to step-0 crossover + frozen prereg).

## Audits (as tasked)

- Override plumbing: --lane-override reaches ONLY the lane path
  (validated before open_run); 4 bad shapes refused pre-work.
  Dead-code question RESOLVED: final_lane-on-legacy reachable only
  by direct hand-call (no in-tree caller); immaterial (3 additive
  spec'd keys; rule+lane identical to 003, S3 verified both trees).
- Rebrand: all 16 files hunk-verified docstring/path-only;
  minihost byte-identical (pin valid); accept/ 8/8 + vendor/ 57/57
  identical; delta confined to routing/api/release (244/97/52
  lines); REPORT/SUCCESSOR-REPORT identical. Non-goals byte-identical.
- Scope honesty: experimental labeling consistent (NOT successor-004,
  NOT a release); LIMITS-12 + ORG-OPS §8 accurate incl. the
  additive-fields caveat (confirmed); counts check out.

## Notes (record-only, accepted)

1. S4-followup.lane/S5.lane unmappable — pre-existing evidence-shape
   gap, equally true of successor-003, not an H2 regression. No action.
2. REPRODUCE.md line 6 relative-vs-"absolute" venv wording (line 34 +
   CONSUMER.md show the correct absolute form). Record-only; no tree
   edit (would break as-verified identity for a nit).
3. Verifier removed /tmp/h2-frozen-pre.sha256 under the clean-/tmp
   instruction; durable proofs re-verified in-tree. Lesson: future
   briefs tell verifiers to preserve /tmp proof files or copy them
   into the work dir before cleanup.
4. Verifier environment could not see ../sst (child filesystem scope),
   so "porcelain clean" had no direct referent there; substituted
   snapshot MATCH + vendor/baseline checks. COORDINATOR CLOSED THE
   GAP: ../sst porcelain 0 lines at df78f42, observed directly
   post-verification. Lesson: producer-porcelain checks are mine, not
   the children's, until child scope is confirmed.

## Acceptance mapping (L2-DESIGN §5 + AUTH-1)

Delta H2 only: yes. Bar items 1–4 PASS: yes. Independently verified:
yes. Frozen inputs intact: yes (s003 45/45, s002/r1 untouched,
SST clean).

**H2 status: ACCEPTED as an experimental host. H2-lane/ FROZEN
as-verified (46/46). AUTH-2 chain unblocked: L2-execute may proceed
to step-0 probes; continuation past step-0 requires the frozen abort
criterion to pass + prereg frozen to PREREG-LOG.**
