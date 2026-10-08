# Final acceptance plan (item 5) — successor-002 release candidate

Verifier: independent lane (authority to challenge evaluator,
invariants, integrated behavior). Method: consumer interfaces only
(CLI + programmatic API per CONSUMER.md), fresh state dirs, declared
Linux setup. Builder tests + coordinator reruns are separate evidence
and do not substitute for this pass. Each check: PASS/FAIL with
observed values; any FAIL blocks the freeze until fixed + affected
checks rerun.

## A1. Routing with valid outcomes

- Run central + local legs via the consumer path on the frozen
  `accept/` inputs. Expect: VALID per independent checker (verifier
  re-checks solutions with its own checker invocation, not the demo's
  word), quality meets `accept/` expectations, routing matches the
  logged rule (local iff ≥2 expected rounds AND split state).

## A2. Central-traffic accounting

- Recompute central vs direct bytes from durable state (receipts +
  ledger), not from printed summaries. Confirm the S2-shaped ratio on
  the acceptance inputs and that the report's 2–6× wording is
  calibrated to central-handled canonical-JSON bytes inside the task
  envelope (no token/attention/cost equivalence language remains).

## A3. Fusion, custody, mechanism removal, reuse

- Execute fusion through the consumer path. Verify: lineage entries
  (derived_from ×2 + fusion record), ≥1 custody transfer with
  giver-actor, lifecycle moves with settle markers, before/after
  mechanism inventory showing exactly the removed channel, and
  follow-up reuse through the fused composite with resolvable lineage.

## A4. Fission

- Execute fission of the fused composite. Verify: partition record,
  custody back-transfer, lifecycle moves, lineage naming the split
  fusion, both children independently operable afterwards, conservation
  holds, 0 stranded.

## A5. Revision + revocation with accountable refusals

- Mid-task revision (v1→v2 declared loss) + capability revocation.
  Verify: stale-proposal void by ruling only (no unilateral void),
  revoked invoke raises with recorded deny, re-propose by the new
  owner validates, revocation durable across reopen.

## A6. Interruption/resume + separation path

- Forced termination mid-run via the consumer path: resume with 0
  re-executed invokes, byte-identical pre-kill artifacts, exactly the
  declared reopen markers. Quarantine drill: failed participant
  suspended, commitment transferred, probe denied with recorded deny,
  standby completes, both settle.

## A7. Conservation + terminal settlement

- Replay every acceptance ledger independently (verifier's own replay,
  not the host's word): conservation ok, all terminals settled,
  0 stranded holdings. Hand-written unsettled-terminal ledger must be
  rejected with the exact error.

## A8. Dependency verification + mismatch refusal

- Regenerate the vendor snapshot manifest with the documented
  construction and compare to the frozen manifest (must match). Tamper
  a COPY of one snapshot file and confirm the release refuses with a
  loud identity error before any SST import. Confirm no `../sst`
  runtime references remain (grep) and the SST tree is untouched by
  the release (within-run pre/post manifest identical).

## A9. Packaged-artifact reproduction

- Copy the release directory to a scratch path (simulating another
  person's checkout), follow CONSUMER.md setup from scratch, rerun the
  acceptance inputs. Expect identical VALID/quality/routing outcomes
  (paths and timestamps excepted). No reliance on the builder's
  working environment, /tmp evidence, or mutable staging.

## A10. Contract conformance sampling

- Pick ≥3 ORG-OPS clauses + ≥3 v1 clauses (C1–C7) and test each through
  the consumer path (not just the builder's unit tests): invoke
  consume-on-success-only + error shape, deny/suspend signatures,
  checkpoint identity refusal, custody giver-actor rule, lineage
  resolvability. Any clause that fails as specified is a FAIL with
  the exact deviation quoted.

## Verdict levels

- ACCEPT: all A1–A10 PASS.
- ACCEPT-WITH-NOTES: all PASS with low-severity record notes (builder
  fixes records, no behavior change, coordinator confirms).
- REJECT: any FAIL — builder fixes, verifier reruns affected checks.
  Failed candidates and findings are preserved, never overwritten.
