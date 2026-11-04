# CONSUMER-DELTA.md — what r3 consumers get over r2

r3 = r2 (successor-003) + R3 gains, banked as successor-004.
Consumer surface shape is unchanged (no new verbs); one behavior
extension. Full procedures: `successor-004/CONSUMER.md`
(authoritative) + `INTERRUPTION-BOUNDARIES.md` (boundary map).

## New / changed

- **Atomic side-file guarantee.** EVERY whole-file side write on op
  paths (`worlds.json` specs, `CONFIG.json`, fusion/fission
  artifacts, recovery notes, `checkpoint.json`, args, verdicts,
  solutions) goes through `minihost.atomic_write_text` (same-dir
  temp + `os.replace`). Exact crash semantics: a kill (SIGKILL or
  equivalent) at ANY point — including INSIDE the write — leaves the
  target holding the OLD bytes or the NEW bytes, never a torn
  (truncated/mixed) file. Proven by construction tests (AST +
  runtime routing proofs), write-interior tests (deterministic
  mid-write crashes), and a 50-SIGKILL loop (0 torn). Orphan note: a
  kill between the temp write and the replace may leave a
  `<name>.tmp-<pid>` file next to the target; orphans are never
  read by any code path and are safe to delete.
- **Process-crash vs power-loss split.** The guarantee above is
  atomicity across a PROCESS crash only: no fsync is issued, so OS/
  machine power loss and genuine media loss stay the disk-loss
  class (LIMITS-2, out of scope, loud refusal). Every R3 durability
  sentence states this separation; nothing in r3 promises fsync-
  grade durability or multi-writer safety.
- **Torn-tail specified landing.** The ledger no-tear claim is
  WITHDRAWN: `close()` does not make a multi-byte append atomic, so
  a kill inside an append MAY tear the tail line. That landing is
  specified, not wished away — readers detect the unparseable tail
  and `ops recover` / `inspect` refuse loudly as disk-loss
  (`RuntimeError` / `release: error:`, "disk-loss", restore from
  backup). Tested deterministically (mid-append crashes, CLI + API)
  and covered by fixtures for torn `worlds.json`.
- **Classified unreadable-checkpoint refusal (behavior extension).**
  `reattach` on a torn `checkpoint.json` now refuses with a
  classified `ContractViolation` ("reattach refused: checkpoint …
  unreadable … torn files are the disk-loss class"), records a
  `deny`, and leaves the world suspended — instead of an
  unclassified error. Suspended worlds with missing/unreadable/
  mismatched checkpoints are likewise refused fail-closed-earlier
  by settleability checks ("reattach would fail").
- **Documented exceptions.** The SST child script's three in-sandbox
  evidence writes are the only non-atomic writes left (child-side,
  no kill boundary across them — proven by parent-SIGKILL-mid-SST-
  leg test: re-run converges TEST/champion/$0). `CONFIG.json`
  staleness is benign (nothing branches on `tasks_run`; follow-up
  runs extend). F1 WARNING kept in INTERRUPTION-BOUNDARIES.md §5:
  only `recover_op`'s TARGETED settle withholds a world inside an
  uncompleted partial fission — never `ops settle` such a composite
  directly (settle is custody-orthogonal and will strand custody,
  loudly detected).
- **Docs with R3 clauses.** CONSUMER.md (failure table: torn-side-
  file row, orphan note, §6 recovery step 5), ORG-OPS.md (atomicity
  clauses), LIMITS.md (item 2 narrowed), INTERRUPTION-
  BOUNDARIES.md (kill model §1, F1 WARNING §5, guarantees §7), new
  EVIDENCE.md (R3 result + construction/interior/kill-loop logs).

## Unchanged

- CLI/API shapes identical (`init/run/explain-route/inspect/ops
  fuse/fission/quarantine/revise/revoke/reuse/split-pair/kill-
  resume/settle/recover`; same api.py functions); explicit
  `--state-dir`, nothing written elsewhere.
- Routing rule (local iff ≥2 rounds AND split), lanes, fusion/
  fission/quarantine/reuse/lineage/revision/revocation/ruling/
  atomic-settle/kill-resume semantics on clean paths; demo metrics
  + accept fields + 2.61x numbers identical.
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

## Migration checklist (r2 → r3)

1. Point paths at `prototype/successor-004/` (rebrand map in
   RELEASE-RECORD.md §7; `accept/` + `vendor/` + REPORTs identical).
2. Keep clean-path flows as-is (no signature breaks, no new verbs).
3. Keep `ops recover` after any kill during settle/fusion/fission
   (CONSUMER.md §6 step 5); never `ops settle` a composite with a
   partial fission (finding F1 — still custody-orthogonal).
4. Treat `<name>.tmp-<pid>` files as benign orphans (delete or
   ignore; they are never read).
5. Rely on the new atomicity: side files land old-or-new after any
   kill (r2 code that defensively re-checked for torn specs after a
   crash can simplify, but need not change); expect loud disk-loss
   refusals — never silent partials — for torn ledger tails and
   genuinely torn files.
