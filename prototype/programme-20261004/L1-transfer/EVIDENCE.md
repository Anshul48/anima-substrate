# L1 EVIDENCE — held-out recipe transfer (result: clean NEGATIVE)

- Written: 2026-10-04T14:22Z (after verdict, this file only)
- Verdict (mechanical, `runs/verdict.json` sha256
  `c24f526434b4bc1013993a5705473fb80ff55ffe0180351ddf5a7c4e3e7620eb`):
  P1 FAIL, P2 PASS, P3 FAIL → OVERALL NEGATIVE. Secondary: FAIL (tie).
  Calibration guard OK on all 36 runs. No tuning was performed; the
  negative matches the preregistered prediction exactly.

## 1. Result vs prereg thresholds

| check | threshold (PREREG.md) | observed | verdict |
|---|---|---|---|
| P1 conditional content | recipe differs from BOTH fixed paths on ≥2 held-out tasks | all 12 choices = reuse (differs from always-split on 12, from always-reuse on 0) | FAIL |
| P2 success parity | equal VALID rates, 12/12 both | recipe 12/12, baseline 12/12, quality full everywhere | PASS |
| P3 net gain (entries) | acquisition + recipe < baseline | 846 + 720 = 1566 vs 972 | FAIL |
| P3 net gain (invokes) | acquisition + recipe < baseline | 168 + 156 = 324 vs 180 | FAIL |
| calibration guard | S1=central 655/0, S2=local 310/500 every setup | 36/36 setups exact | OK |
| secondary | rule accuracy > always-central | `local-iff-rounds>=3` 5/8 vs baseline 5/8 (tie) | FAIL |

Per-task costs were perfectly task-content-independent: every reuse run
60 entries / 13 invokes, every split run 81 / 15, at all sizes (4/5/6).
Both arms share r1's deterministic solver, so success/quality cannot
differ; the cost gap is a fixed pipeline constant (21 entries, 2
invokes). The extracted recipe therefore has no task-conditional
content — there is no surface in the r1 envelope for org-path transfer
to grip. Secondary: 2 lane observations underdetermine the AND rule;
the preregistered tie-break picked `local-iff-rounds>=3`, tying the
default (my informal design-time guess of `local-iff-split` 7/8 was
wrong — the mechanical rule governed, as preregistered).

## 2. Order proof (prereg before execution)

File mtimes (UTC) + run stamps:
- `gen_tasks.py` 14:13:52 → `tasks/` 14:13:58 → `DESIGN.md` 14:14:32 →
  `PREREG.md` 14:14:50 → extraction 14:17:10–14:18:25 →
  transfer 14:18:40–14:19:49 → baseline 14:19:55–14:21:14 →
  secondary/verdict 14:21:14–14:21:18.
- `recipe.json` frozen at extraction end (mode 444), sha256
  `764a3b92b60cfbf0466b5d2d6a40c29c0d34701dd7c20eb591bf8153f1271cdc`,
  re-verified identical at transfer start (log line).
- No L1-TR-*/L1-TE-* task executed before 14:17:10Z (only throwaway
  `PROBE-*` tasks ran earlier; see §5).

## 3. Pins of everything consumed

- r1 `prototype/successor-002/`: `IDENTITY.sha256` 41/41 OK before
  (14:12Z) AND after (14:21Z, 0 non-OK lines); `find -newer` empty —
  r1 untouched. Consumed ONLY via `release.py` CLI subprocess.
- `gen_tasks.py` sha256 matches PREREG pin `e579da25…` (unchanged).
- All 18 train/test task hashes + secondary-descriptors hash match
  PREREG §1 (verify: `sha256sum tasks/*.json`).
- `harness.py` sha256
  `52485bb1c05c673a4efc1d9bed166fdb14b38f27df5aefe314403158ecbb2c18`
  (post smoke-fix version; fixes pre-date extraction, see §5).
- Env: `PYTHONDONTWRITEBYTECODE=1` on every call; no `__pycache__`/`.pyc`
  under L1-transfer; stdlib-only; $0; offline; no git repo present
  (identity via sha256, not commits).

## 4. Exact commands (repo root, `export PYTHONDONTWRITEBYTECODE=1`)

```
# task family (BEFORE prereg)
python3 prototype/programme-20261004/L1-transfer/gen_tasks.py --out tasks
# preregistered experiment (AFTER PREREG.md 14:14:50Z)
cd prototype/programme-20261004/L1-transfer
python3 harness.py extract    # 6 train x 2 arms -> recipe.json (frozen)
python3 harness.py transfer   # frozen recipe x 12 held-out
python3 harness.py baseline   # fixed split-pair x 12 held-out
python3 harness.py secondary  # routing-rule fit + 8 predictions
python3 harness.py verdict    # mechanical P1/P2/P3
```

Raw logs: `logs/extract|transfer|baseline/<task>-<arm>.json` (every CLI
call with rc/stdout/stderr, 36 files); run state:
`runs/extract|transfer|baseline/<task>-<arm>/` (ledgers, artifacts);
summaries: `runs/extraction-log.json`, `runs/transfer-log.json`,
`runs/baseline-log.json`, `runs/secondary-log.json`, `runs/verdict.json`.

## 5. Failures + fixes preserved (nothing hidden)

- Pre-prereg probe `PROBE-4` (hand-edited grid): `ValueError: no valid
  schedule` — kept in `probes/` + §DESIGN-2; motivated the
  solvability-preserving generator. Not part of the experiment.
- Harness smoke (throwaway `SMOKE` task, pre-extraction, allowed by
  PREREG §4): fix #1 settle only ACTIVE worlds (r1 refuses
  dissolved→dissolved); fix #2 keep full inspect stdout (log tail
  truncation broke JSON parse). Both pre-date extraction; smoke
  artifacts deleted; fixes logged here.
- Experiment runs: ZERO failures — 36/36 `ok=True`, 36/36 VALID.
  (Uniform success is itself the finding: no differential failure for
  a recipe to exploit.)
- Secondary expectation miss (§1): reported, procedure governed.

## 6. Uncertainties / blockers / limits (do not over-claim)

- Bytes-only, toy scale (4–6 tasks/slots), single-host, one solver.
- r1 canonical lane bytes are UNMEASURABLE on held-out tasks
  (`run` pinned to S1/S2 by the consumer interface) — the primary
  cost units (ledger entries, invokes) are proxies, clearly labeled.
- Isomorphic task family (label-permuted grids): tests conditionality,
  not far-transfer; a richer generator needs its own solvability story.
- The negative is envelope-relative: it shows r1's fixed pipelines
  leave no task-conditional recipe surface — not that recipe transfer
  is impossible in principle. L2 needs a host with content-sensitive
  path costs (or a learnable lane) before re-testing transfer.
