# Contributing to substrate

Status: draft for the 0.1.0 release round. This file is owned by the
publication-docs builder; contract and evidence rules below are
summaries — the in-tree contracts and acceptance records govern.

## Dev setup

- Target: Linux/WSL2, system `python3` 3.12.3, `$0`, offline.
- The repo root carries a project virtualenv at `.venv/` (do not create
  one in `/tmp`, do not install into the system interpreter):

```sh
python3 -m venv .venv          # only if .venv is absent
.venv/bin/pip install pytest ruff   # test/lint only; runtime is stdlib-only
export PYTHONDONTWRITEBYTECODE=1
```

- Runtime code is **stdlib-only**, except the SST legs, which need a
  venv interpreter with pinned `pydantic` (prototype trees document
  their own venv; e.g. `prototype/w1/.venv`, pydantic 2.13.5).
  Never vendor third-party packages in-tree.

## Test commands

There is no `pyproject.toml` / `pytest.ini` yet (coordinator placeholder);
suites run as scripts or via unittest from the repo root:

```sh
# Example: successor-006 owed-repairs + J1 journey (~2 min, stdlib-only)
export PYTHONDONTWRITEBYTECODE=1
python3 prototype/successor-006/j1_demo.py
# expect: J1 journey: OK (10/10 PASS)
for t in test_coupling test_quarantine_repair test_j1 test_conformance \
         test_fission test_procedure_smoke; do
  python3 prototype/successor-006/$t.py
done
# expect: 48/48 OK
```

- `.venv/bin/pytest` and `.venv/bin/ruff` exist for the release round;
  per-tree suites predate them and stay runnable as plain scripts.
- Full reproduction index (all generations): `REPRODUCE-ALL.md`.
- Step-by-step CLI journeys live next to the code
  (e.g. `prototype/successor-006/RUNBOOK.md`); the two-minute review
  route is `prototype/programme-20261004/S6-REVIEW-ROUTE.md`.

## Lint

```sh
.venv/bin/ruff check prototype/    # no ruff config file exists yet —
.venv/bin/ruff format --check prototype/  # coordinator: add config before 0.1.0
```

Keep the tree warning-clean under the configured gate once it exists.

## Contract-change policy

1. **Frozen trees are read-only.** Banked generations
   (`successor-002` … `successor-006`, `release-*`, `H2-lane`,
   `U-execute` finals) are never edited; new work copies forward into
   a new tree with a `PROVENANCE.md` copy-forward record and per-file
   adaptation list (see `prototype/successor-006/PROVENANCE.md`).
2. **Contract edits need a delta.** Changes to
   `WORLD-CONTRACT-v1.md`, `ORG-OPS`, the CC1–CC9 coupling contract,
   or any frozen predicate/checker file require a filed contract delta
   (or `RULES-AMENDMENT` entry for experiment rules) **before** the
   code change; silent repair is forbidden.
3. **Prereg before execution.** Experiments file a hash-chained
   `PREREG-LOG` entry + countersign before the first non-throwaway run;
   predicate edits after filing mean a new entry + re-freeze.
4. **Banking is routine**, not an architectural decision: identity
   file + manifest + untouched predecessors, unless an explicit freeze
   hold says otherwise.
5. **Envelope discipline.** Every claim states its envelope
   (single-host, toy scale, TEST-only SST, process-crash-only, no
   fsync unless stated). Out-of-envelope behavior is unpromised; new
   paths file their own `LIMITS.md`.

## Evidence standards

- Re-run through **consumer interfaces on fresh state**; auditor
  state goes under `runs/` (fresh dirs) and `/tmp` only.
- Prove bytes before behavior: `sha256sum -c IDENTITY.sha256`
  (and snapshot-manifest checks where an SST leg exists).
- Independent acceptance lane before any banked claim: the auditor
  re-runs eval/derive/blinding from filed bytes and files their own
  verdict (precedent: `S6-ACCEPTANCE.md`, `U-execute/runs/
  INDEPENDENT-ACCEPTANCE.md`).
- Report negatives honestly and keep them: failed cells, VOID legs,
  superseded records (`.superseded-void`), and rater/auditor warts
  stay in the record with their cause named.
- Byte results are calibrated as bytes only — no token, attention,
  cost, or intelligence conversions (precedent: R8 `2.61x
  (bytes-only)`).
- No learning/discovery verbiage without a discriminating protocol:
  the Q4 negative and D-005 signal semantics bind all future work;
  no runs without a new hypothesis.
- Held-out authorship + sealed envelope + disclosed throwaway
  validation for any graded change content.
