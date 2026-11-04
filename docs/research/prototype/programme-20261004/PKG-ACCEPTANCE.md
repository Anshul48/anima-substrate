# PKG-ACCEPTANCE.md — anima-substrate 0.1.0 packaged candidate

Independent acceptance by a fresh auditor (own state dirs `/tmp/aud2-*`,
own ephemeral venv `/tmp/aud2-venv`; prior `/tmp/audit-*` material treated
as untrusted and never executed). All functional legs ran against the
INSTALLED wheel from outside the checkout (`cwd=/tmp`).

## Verdict: ACCEPT-WITH-NOTES

The source tree satisfies M1–M4 per the mandate addendum (§2 criteria),
the frozen predecessors are untouched, and the installed wheel behaves
identically to the tree. The `dist/` artifacts are STALE (built before
the README rewrite + SPDX pass) and MUST be rebuilt from the final tree
before publication — see NOTE-1. No behavioral or contract failure was
found; nothing in the notes requires a source change.

## Candidate identity

- Tree: `$REPO` (= the substrate checkout root)
  (`src/`, `tests/`, `examples/`, `docs/`, `PROVENANCE.md`, …).
- `dist/anima_substrate-0.1.0-py3-none-any.whl` (142653 B, built
  2026-10-07 18:20:48Z) and `dist/anima_substrate-0.1.0.tar.gz`
  (241865 B, built 18:20:24Z) — both predate the final tree edits
  (SPDX 18:21, PROVENANCE re-pin 18:22, README rewrite 18:28,
  .gitignore 18:40). Content delta fully characterized under NOTE-1.

## Per-check evidence

### 1. Wheel/sdist contents — PASS (with NOTE-1 staleness)

- Wheel: 45 entries — 31 `.py`, 8 `.json` fixtures (7 accept-pack +
  SST SNAPSHOT-MANIFEST), `accept/README.md`, LICENSE
  (`dist-info/licenses/LICENSE`), entry points. No tests, no
  prototype, no caches.
- Sdist: 79 entries; leak scan for `prototype`/`.venv`/`__pycache__`/
  `*.pyc`/`runs/`/`*.db` → NONE. LICENSE + PKG-INFO present.
- Wheel code vs tree `src/`: all 31 `.py` diffs are EXACTLY the one
  leading `# SPDX-License-Identifier` comment line (behaviorally nil);
  all 8 JSON fixtures byte-identical. Sdist `src/` == wheel `src/`.
- Sdist is internally consistent (31/31 PROVENANCE pins match its own
  `src/`); tree is internally consistent (31/31 match). But sdist
  README is the pre-rewrite "design proposal only … does not contain
  a new runtime" text — false of the contents (NOTE-1). Wheel
  METADATA embeds the same stale description.

Repro:

```sh
./.venv/bin/python -c "
import zipfile, tarfile
z = zipfile.ZipFile('dist/anima_substrate-0.1.0-py3-none-any.whl')
print(len(z.namelist()), 'wheel entries')
t = tarfile.open('dist/anima_substrate-0.1.0.tar.gz')
names = t.getnames()
print(len(names), 'sdist entries')
print('leaks:', [n for n in names if 'prototype' in n or '.venv' in n
      or '__pycache__' in n or n.endswith('.pyc') or '/runs/' in n
      or n.endswith('.db')] or 'NONE')"
```

### 2. Clean install + import + CLI outside checkout — PASS

- Fresh venv `/tmp/aud2-venv` (`python3 -m venv --without-pip`;
  ensurepip unavailable, so installed via project pip's
  `--python` flag — no network, local wheel only).
- From `cwd=/tmp`: `import anima_substrate` → `__version__ 0.1.0`,
  loaded from `/tmp/aud2-venv/.../site-packages` (checkout NOT on
  `sys.path`); 4 families registered
  (`relcheck@v1`, `relcheck@v2`, `sched@v1`, `sst@v1`).
- `anima-substrate --help` works; `families` lists all four;
  `init` + `inspect` on `/tmp/aud2-cli-state` OK.

Repro:

```sh
python3 -m venv --without-pip /tmp/aud2-venv
./.venv/bin/python -m pip --python /tmp/aud2-venv/bin/python install \
  dist/anima_substrate-0.1.0-py3-none-any.whl
cd /tmp && /tmp/aud2-venv/bin/python -c \
  "import anima_substrate as a; print(a.__version__, a.__file__)"
cd /tmp && /tmp/aud2-venv/bin/anima-substrate --help
```

### 3. Quickstart vs installed package — PASS

`examples/quickstart.py` under `/tmp/aud2-venv/bin/python` from
`cwd=/tmp`: all 7 steps OK — 2 files pinned, relcheck
`valid=True checked=2`, close/reopen byte-identical, recover active
+ conservation ok, settle `stranded=0`. State in its own temp dir.

Repro: `cd /tmp && /tmp/aud2-venv/bin/python
$REPO/examples/quickstart.py`

### 4. M1 usable journey — PASS (mandate M1: ACCEPT)

Own leg `/tmp/aud2-legs/leg-m1.py`, fresh `/tmp/aud2-m1`, installed
wheel only. Own 5-file tree/seed (nested + top-level, distinct from
repo fixtures): relcheck run `valid=True checked=5`; world-file and
org-snapshot bytes identical across close/reopen (3 world files);
3 seeded errors (missing manifest / bad `manifest_version` /
missing tree) each raise naming the cause field AND a `fix:`; full
CLI journey (`init → family-create → family-run → org-snapshot ×2
equal → settle stranded=0`) on an external state dir. Limits filed
in README/ARCHITECTURE (process-crash-only, no fsync, toy scale).

### 5. M2 pinned participants — PASS (mandate M2: ACCEPT)

Own leg `/tmp/aud2-legs/leg-m2.py`, fresh `/tmp/aud2-m2`:

- ≥2 families side by side: `sched@v1` + own `aud2echo@v1` coexist
  in one state dir (sched valid; echo roundtrip OK).
- Zero-host-edit addition, stronger than the repo test: my echo
  family lives in `/tmp` (OUTSIDE the package), binds only
  `anima_substrate.host.api`, registers at runtime, and passes the
  public-surface AST rule (no private from-names, no `api._`).
- v1→v2 upgrade: `change` births `UP1-v2` with `derived_from=UP1`
  lineage; old pins re-run byte-identical (373 report bytes); v2
  world runs old (compat undeclared) and new tasks.
- The repo zero-host-edit test honestly proves its claim: I verified
  it AST-walks imports, restricts host binds to PUBLIC_HOST, refuses
  private from-names, refuses `api._` textually, enumerates EVERY
  family file (`rglob` cross-check), and pins re-export files
  host-free. Negative control confirmed (hostile `api._` text fails
  the rule). Residual gap (NOTE-4, doc-only): the test's text rule
  covers `api._` but not `pipeline._`/`routing._` — I grepped and
  found NO private-attribute use anywhere in `participants/`, and
  the only pipeline/routing binds are public CAP/REP/LIMIT
  constants in `sched/family.py`.
- Contract delta log present (`v1 is the initial filing`, no
  entries — correct, no §7 change occurred).

SST extra (`/tmp/aud2-legs/leg-m2sst.py`): wheel carries only
`sst/{SNAPSHOT-MANIFEST.json,__init__,manifest,staged}.py` —
manifest is digests/relpaths only (no `def `/`import ` bytes);
probe refuses unstaged root (names `SUBSTRATE_SST_ROOT`) and
missing tree; with the caller-staged sibling `../sst` (NOT package
bytes): probe MATCH, 54 files, pydantic 2.13.5, git pinned;
`sst@v1` create/run/recover → `champion_found`, $0, snapshot MATCH.
Skip wording in `test_sst_staging.py` is explicit
(`SUBSTRATE_SST_ROOT unset (SST is a caller-staged …)`), never
silent-green.

### 6. M3 persistent organization — PASS (mandate M3: ACCEPT)

Own leg `/tmp/aud2-legs/leg-m3.py`, fresh `/tmp/aud2-m3`:
relationship + live channel + J1 custody (`j1.budget` on nested
experiment) all byte-identical across reopen; fused composite
(`reuse` VALID) exported (6 files, 7 excerpts), imported into a
FRESH SEPARATE dir with explicit new grants (recorded verbatim),
`lineage_ok`, `derived_from=[SC-L, SC-S]`; bundle bytes unchanged
after consumption (every byte compared); fresh-dir world active and
`j1_work` VALID with full quality; vague/negative grants refused.
Kill-during-persist convergence is covered by the repo test
(`test_kill_during_channel_persist_converges`, in the suite run)
plus my observed kill legs below.

### 7. M4 experience loop — PASS (mandate M4: ACCEPT)

Own leg `/tmp/aud2-legs/leg-m4.py` (own prereg wording/stamp
`2026-10-08T00:00:00Z`, own 2-vs-5-file tasks with disjoint
relpaths/distinct releases), fresh `/tmp/aud2-m4`:
prereg filed BEFORE any run and byte-intact after all runs;
propose→assess(POSITIVE)→retain with lineage + measured cost;
invalid proposal assessed NEGATIVE (P1 failed), retained-negative,
reuse blocked with `retained-negative` error; reuse VALID on task B
+ from-scratch baseline VALID (interventions 3 vs reuse 1);
compare agreement=True, `superiority_claimed=false`, costs +
interventions REPORTED. D-005 signal classes distinct (4/4,
separately re-observed). Banned-stem scan
(`discov*|invent*|learn*|superior*|breakthrough|novel*`, allowlisted
key stripped exactly as the repo test does) over installed
`recipes.py` + compare report + my prereg/entry → zero hits.

### 8. Kill legs — PASS (both observed by me)

Own leg `/tmp/aud2-legs/leg-kill.py`, fresh `/tmp/aud2-kill`:

- Real-SIGKILL resume: `kill_resume_op` → `child_rc=-9`,
  `re_executed_invokes=0`, S3 flow completes.
- Quarantine repair: crash hook `SUBSTRATE_CRASH_AFTER_APPENDS=4`
  → exit 42 mid-transfer; `recover_op` detects the partial (1
  transfer done); `quarantine_complete_op` completes (commitments
  moved, `recovered=true`, source suspended); conservation ok;
  detection silent after; `settle` clean.

### 9. Claims audit + frozen predecessors — PASS (notes filed)

- Durability wording: every `durab*`/`crash-atomic` claim carries
  the process-crash-only/no-fsync/LIMITS-2 scope (api.py:505-508,
  J1 header, CONTRACTS envelope, RECOVERY crash model, README
  limitations). No overclaim.
- `revoke … durably` docstring self-qualifies (LIMITS-2). OK.
- STC posture: README + TECHNICAL-REPORT consistently
  "explicitly unqualified (full-replay semantics only)". No STC
  execution in package. No overclaim.
- Calibration: `2.61x bytes-only (810 vs 310)` re-proven live by
  `test_calibrate_demo` (asserts 810/310/2.61), not carried on
  faith. No overclaim.
- "Tested" labels: disk-loss refusal → `test_torn_ledger_refuses_recover`
  exists; non-claims → `TestProcWording` tree-wide audit + A4 legs
  exist; CC1–CC9 → `test_coupling.py` (10 tests) exists. All in the
  suite run below. No dangling "tested".
- No learning/discovery/invention verbiage anywhere except
  negations ("No learning of any kind", "Beyond the finish line",
  "adaptation UNTESTED, not disproven"). Verified by grep over
  `src/` + all claim docs.
- Frozen predecessors untouched: `IDENTITY.sha256` verifies
  41/41 (s002), 45/45 (s003), 45/45 (s004), 56/56 (s005), 35/35
  (s006), zero failures; IDENTITY mtimes 2026-10-04→10-07 predate
  all packaging work. (Repo has no git history yet, so IDENTITY
  pins — not git — are the baseline; they are authoritative and
  green.) I wrote nothing outside `/tmp` and this verdict file;
  `src/`, `tests/`, frozen trees, neighbors, ANIMA untouched.

### 10. Spot-rerun — full `pytest tests/` (one process, project .venv)

The auditor ran the FULL suite (not the reduced milestone+wording
minimum), one process, `SUBSTRATE_SST_ROOT` unset (SST-conditional
skips expected):

```sh
./.venv/bin/python -m pytest tests/ -p no:cacheprovider
```

Result (observed 2026-10-08, wall 1195.13 s ≈ 19:55):

```text
207 passed, 11 skipped, 147 subtests passed in 1195.13s (0:19:55)
```

This matches the claimed `207 passed, 11 skipped (SST-conditional),
147 subtests` EXACTLY on all three numbers. Collection audit
corroborates the structure independently: 218 tests collected
(39+2+9+10+22+7+6+3+15+7+57+13+11+17) = 207+11; the 11 skips are
the 7 staged-SST legs + 1 wheel-build leg + 3 successor legs, all
with explicit skip reasons. Ruff (observed by auditor):
`ruff check` → "All checks passed!"; `ruff format --check` →
"48 files already formatted".

## Notes (all doc/packaging; no source change needed)

- NOTE-1 (must-fix before publication): rebuild `dist/` from the
  final tree. Current wheel+sdist predate the README rewrite and
  SPDX pass: sdist README still says "design proposal only … does
  not contain a new runtime" (false of the contents) and the wheel
  METADATA embeds that stale text; both artifacts' `.py` lack only
  the SPDX comment line (proven behaviorally nil, fixtures
  identical, both halves internally PROVENANCE-consistent — but the
  published pair must be byte-coherent with the tree). Rebuild,
  re-verify install + quickstart + IDENTITY-style pins, then ship.
- NOTE-2 (pre-existing, coordinator-owned): LICENSE copyright owner
  is still `[YEAR] [OWNER]` placeholder (LICENSE-AUDIT M1/M2
  blocking). Disclosed in CHANGELOG "Open before release" and the
  pyproject license string; acceptable for an alpha candidate, must
  resolve before any public release.
- NOTE-3 (FIXED DURING AUDIT, verified by re-read): the README
  install block the auditor first read said `pip install
  anima-substrate` (implying PyPI publication of unreleased 0.1.0).
  At 2026-10-08 07:03:49Z, while this audit was running, the tree
  README was amended to `pip install
  dist/anima_substrate-0.1.0-py3-none-any.whl   # local artifact`
  plus "(PyPI publication pending; install from the release asset
  for now.)" — exactly the install the auditor executed, now
  literally documented (mandate M1 install clause satisfied).
  `src/` is provably untouched by the amendment (39/39 PROVENANCE
  pins still match). No action remains except ensuring NOTE-1's
  dist rebuild picks up the amended README.
- NOTE-4 (FIXED DURING AUDIT, verified by re-read): CONTRACTS.md
  Part 2 said families bind "host.api / host.minihost" while `sched`
  also binds public `host.pipeline`/`host.routing` constants. At
  2026-10-08 07:04:10Z the parenthetical was amended to "(plus
  public `host.pipeline` / `host.routing` constants where a family
  needs them)" — now accurate (auditor grepped: only public
  CAP/REP/LIMIT constants; zero private-attribute use in
  `participants/`). The one suite test reading CONTRACTS.md
  (`test_contract_file_lists_all_items`) only asserts CC1–CC9
  presence, so the amendment cannot perturb the suite. No action
  remains except NOTE-1's rebuild picking it up.
- NOTE-5: sdist→wheel rebuild not verifiable in this offline env
  (hatchling backend absent from `./.venv`, which carries only
  pytest/ruff/build/packaging). Sdist contents verified complete
  (`pyproject.toml` + `PKG-INFO` present); re-verify at rebuild
  time (NOTE-1) where the backend is available.

## Counts

- Full suite (auditor-observed): 207 passed, 11 skipped, 147
  subtests passed, 0 failed (1195.13 s).
- Auditor legs (own scripts, installed wheel, fresh state): M1,
  M2, M2-SST (staged live: MATCH/54/pydantic-2.13.5/pinned),
  M3, M4, kill-A (SIGKILL rc=-9, 0 re-invokes), kill-B
  (quarantine repair) — all PASS.
- Frozen IDENTITY: 41+45+45+56+35 OK, 0 FAIL.
- Ruff: check clean, format clean (48 files).

## Repro index (auditor legs)

```sh
V=/tmp/aud2-venv/bin/python
cd /tmp && $V /tmp/aud2-legs/leg-m1.py     # M1 journey + errors + CLI
cd /tmp && $V /tmp/aud2-legs/leg-m2.py     # families + echo + upgrade
cd /tmp && $V /tmp/aud2-legs/leg-m2sst.py  # SST staging/refusal/staged
cd /tmp && $V /tmp/aud2-legs/leg-m3.py     # persist + composite
cd /tmp && $V /tmp/aud2-legs/leg-m4.py     # loop + invalid + wording
cd /tmp && $V /tmp/aud2-legs/leg-kill.py   # SIGKILL + quarantine repair
./.venv/bin/python -m pytest tests/ -p no:cacheprovider   # full suite
./.venv/bin/python -m ruff check src tests examples
./.venv/bin/python -m ruff format --check src tests examples
```

Ephemeral state (`/tmp/aud2-*`, `/tmp/aud2-venv`, `/tmp/aud2-legs`,
`/tmp/aud2-sdist`, quickstart temp dirs) is throwaway; the venv is
removed after handoff per constraints.
