# CONSUMER-DELTA.md — what r2 consumers get over r1

r2 = r1 (successor-002) + R1 gains, banked as successor-003.
Consumer surface shape is unchanged plus one added op. Full
procedures: `successor-003/CONSUMER.md` (authoritative) +
`INTERRUPTION-BOUNDARIES.md` (boundary map).

## New / changed

- **Atomic settle semantics.** `settle` (routing.finish_worlds,
  api.settle_op, `ops settle`) rehearses the whole batch first
  (ledger conserves NOW + `check_settleable` per world) and refuses
  with `ContractViolation` ("…; zero worlds dissolved") BEFORE any
  dissolve: ZERO partial dissolves, ZERO partial grant_returns,
  only a `deny` entry. Single-world settle-then-move (dissolve/
  fuse/fission paths) carries the same guarantee. r1 explicitly
  disclaimed this (r1 LIMITS-11); r2 promises it.
- **Ops recover procedures.** New `release.py ops recover` /
  `api.recover_op`: after a kill during settle/fusion/fission, it
  repairs `worlds.json` specs from the ledger, completes
  interrupted births/fusions automatically, completes ONE
  interrupted fission once you supply
  `--fission/--left/--right/--partition` (bare recover REFUSES
  with exact steps when a partial fission exists), and settles
  exactly `--worlds` (default: settles NOTHING — safe default).
  Re-running after a kill during recovery converges (all steps
  ledger-conditional). Loud refusals with exact operator steps for:
  wrong partition/names/presets (never silently diverges),
  partial quarantine (COMPLETE/ROLLBACK recipes; involved world
  blocked, others proceed), conservation violations, torn ledger
  (disk-loss class: restore from backup).
- **Interruption-boundary guarantees.** Kill at EVERY
  settle/fuse/fission boundary (entry-granular prefixes; kill
  cannot tear a ledger line) ⇒ defined partial state + recovery
  exercise, no silent partials. Landings: no-trace → re-run the
  op; mid-op → recover completes; entry-complete-but-specs-missing
  → spec repair + recovery note. `grant_settle` markers are
  SET-semantic (a marker-without-lifecycle crash may leave a
  benign duplicate on re-settle). Quarantine-transfer completion
  stays operator repair (detected + explicit steps, never silent).
- **Docs with R1 clauses.** CONSUMER.md (failure table + §6
  recovery procedure), ORG-OPS.md (settleability + R1 recovery
  promises), LIMITS.md (item 11 CLOSED, item 3 narrowed), new
  INTERRUPTION-BOUNDARIES.md (append maps, per-op partial states,
  guarantees), new EVIDENCE.md (R1 result + kill logs).

## Unchanged

- CLI/API shapes otherwise identical (`init/run/explain-route/
  inspect/ops fuse/fission/quarantine/revise/revoke/reuse/
  split-pair/kill-resume/settle`; same api.py functions +
  `recover_op`); explicit `--state-dir`, nothing written elsewhere.
- Routing rule (local iff ≥2 rounds AND split), lanes, fusion/
  fission/quarantine/reuse/lineage/revision/revocation/ruling
  semantics on clean paths; demo metrics + accept fields identical.
- SST leg: same vendored snapshot bytes (`5f1f3789…`, 54 files),
  TEST-only, champion_found, $0, SUBSTRATE-QUALIFIED posture (no
  SST-owner acceptance claimed). **`SST_VENV_PY` note:** defaults
  to the in-repo `prototype/w1/.venv/bin/python` (pydantic
  exactly 2.13.5, used for qualification); any interpreter with
  EXACTLY pydantic 2.13.5 works via override; any other version
  aborts the SST leg loudly (re-qualification required).
- `PYTHONDONTWRITEBYTECODE=1` required; wall-clock `at` excluded
  from byte-identity; channels in-memory-only; `retired`
  unexercised; toy scale; single-host; no learning; U-branch /
  real-producer consumption still blocked.

## Migration checklist (r1 → r2)

1. Point paths at `prototype/successor-003/` (rebrand map in
   RELEASE-RECORD.md §7; `accept/` + `vendor/` bytes identical).
2. Keep clean-path flows as-is (no signature breaks).
3. Adopt `ops recover` after any kill during settle/fusion/fission
   (CONSUMER.md §6 step 5); never `ops settle` a composite with a
   partial fission (finding F1 — settle is custody-orthogonal and
   will strand custody, loudly detected).
4. Rely on the new atomicity: settle refusals now guarantee zero
   partials (r1 code that defensively re-checked partial state
   after a refusal can simplify, but need not change).
