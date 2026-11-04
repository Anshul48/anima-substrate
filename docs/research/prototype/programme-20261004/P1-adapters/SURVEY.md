# SURVEY.md — P1 producer survey (2026-10-04, read-only)

Scope: SST + STC release posture for future substrate real-use (U-branch
enabler). Makes NO acceptance claim. All producer observations are
read-only (`git` inspect, file read/hash/parse only); no producer test
suite was executed and no producer file was written (porcelain
before/after at the end).

Substrate context: r1 (successor-002) consumes SST only via a
SUBSTRATE-QUALIFIED SNAPSHOT (`vendor/SNAPSHOT-MANIFEST.json`,
construction `substrate-snapshot-v1`, 54 files, hash
`5f1f37893b0f5ab9ff7dcf0ce2c60b287b51647e2f18f627eabf5510537cad96`)
with explicit NO-SST-OWNER-RELEASE-ACCEPTANCE labeling.

## 1. Exact pins (observed 2026-10-04 ~15:15–15:30Z)

### SST (`../sst`)

- HEAD: `df78f42894a65c48f524337a498032617689a013`
  (`df78f42 release(sst): task-to-result UI, honest budgets,
  live-model qualification`, 2026-10-04 10:11:11 +0000).
- Porcelain: CLEAN (0 lines). Branch: `main` only. Tags: NONE.
  `git describe`: `df78f42` (no tag reachable).
- `pyproject.toml`: `version = "0.1.0"` (no release versioning).
- Live tree == pinned snapshot: `sst/core/contracts.py` and
  `sst/search/controller.py` in the worktree hash-match the r1
  manifest entries (`28f3a561…`, `ced1db6d…`); self-test re-vendors
  54 files with hash `5f1f3789…` identical to the frozen manifest.

Key doc/file hashes (sha256, worktree == HEAD since clean):

| path | sha256 |
|---|---|
| `docs/FREEZE-MANIFEST.md` | `12390e92b2e685fe4476b2ec01fe607bf7b972fa32da5f401cbe214d9b187d4b` |
| `docs/STC-HANDOFF.md` | `68bd895de422d7a59d136122de0db0a4e2d5683e5cdc7646aa749d45ed17bda0` |
| `docs/SST-PROGRESS.md` | `93d687c4316b26e150c2ffded8d48c497bfd791fd9010d936a5de6b3b051e714` |
| `src/sst/core/contracts.py` | `28f3a561eab6086c857e5730af3ccdef2a3e72954543d3992efdbb6091f9f299` |
| `src/sst/search/controller.py` | `ced1db6d7e088f2e0a5a6aa01100fa0459346de2a02350b86402414edc1e4c3e` |

### STC (`../stc`)

- HEAD: `8fa8ac3abc4dcc42d0b7b2679eb512fcbdb1a990`
  (`docs(stc): live readiness packet + release-doc corrections`,
  2026-10-04 13:42:10 +0000; docs-only on top of `a9f2018` docs on
  top of `c1bd60a` feat).
- Porcelain: DIRTY — 28 lines (14 modified tracked: 2 docs +
  `sst_compat_probe.py` + 4 `src/stc/integration/*.py` + 6 tests;
  14 untracked paths incl. coordinator pastes, plans/logs, 6 nested
  evidence repos). `git describe`: `8fa8ac3-dirty`. Tags: NONE.
- Branches: `main` + 8 `feature/stc-task-*` branches.
- `pyproject.toml`: `version = "0.1.0"`.
- HEAD-vs-worktree split (material): at HEAD, `EXTERNAL_PINS["sst"]`
  = `079f4de6…` and the caller contract is revision
  INT-2026-09-13.2; the dirty worktree advances both to `df78f42` /
  INT-2026-10-04.1 UNCOMMITTED (incl. `STC-INDEPENDENT-VERIFY.md`
  rewritten around the df78f42 pin). The readiness packet (committed)
  still records 079f4de6 as authoritative and df78f42 as "AWAITS
  owner blessing" — the packet is stale relative to the worktree.

Key doc hashes (sha256; `cells marked HEAD` are `git show HEAD:path`
bytes; worktree differs where noted):

| path | HEAD sha256 | worktree |
|---|---|---|
| `docs/STC-LIVE-READINESS-PACKET.md` | `ce8bdddd776872d8a3dafe6625eac9d35d1d7b53ef9ed069f166a00bdaa66c48` | same (clean) |
| `docs/STC-DSH-RELEASE.md` | `abe479f36645c701b45e9cdb289ab6f1c88f27766b0ad16d103eb4fd92a35d90` | same (clean) |
| `docs/STC-DSH-RECORD.md` | `976203900c8b833ba6bb7d55e24db3e98a970454249302fca93e4ec0c3bf15ea` | same (clean) |
| `dsh-plugin-stc/DSH_PIN` | `d330ef4f3124f0400c39484f6d73f4578c21f157bfa442432ad138bf58074f81` | same (clean) |
| `docs/STC-SST-CALLER-CONTRACT.md` | `72dd5afc6e2ace026758b3d2411fb2c354b320cba550f793dce67322445563f1` | DIRTY (`a7ac87f3…`) |
| `src/stc/integration/lease_git.py` | `c632e4a7ba9198556c3f58d985533d2193c9c6ab4de9a8091e593291f4519185` | DIRTY (`2aab2b0f…`) |

### TRACE (`../trace`) — presence/state only

- HEAD `a24a937009fec41e6dcb6d2ca31d3c1783ac97f7`
  (`feat(p4): ballot-pack evidence dossier…`), DIRTY (25 porcelain
  lines: 8 tracked incl. 5× `src/trace/v2/*.py`, rest untracked),
  tags NONE, many `cap-*` branches. Not consumed by any adapter.

## 2. Release posture per producer

### SST: stable envelope? Owner-declared stable? NO to both as phrased

- A `run_search`/`SearchResult` envelope EXISTS and is shape-stable in
  practice: frozen pydantic model (`contracts.py`), 8 keys
  (`tree_id`, `termination_reason`, `champion`, `alternatives`,
  `budget_consumed`, `provider_errors`, `gateway_bindings`,
  `event_log_ref`) — identical in source, substrate's `ENVELOPE_KEYS`,
  and both live-qual evidence envelopes (`run1/run2-envelope.json`).
  `ProviderKind.TEST` fixture path exists with deterministic
  controller tests (`tests/unit/test_controller.py` FakeGateway).
- But it is NOT owner-declared stable: `FREEZE-MANIFEST.md` declares
  only "`execute_search` stable"; `run_search` is "recommended" under
  a "**Proposed** contract (additive, backward compatible)" in
  `STC-HANDOFF.md`. "Proposed" ≠ frozen. Upgrade policy promises
  additive models/fields and re-pin-after-observed-consumption.
- NO owner-minted qualified release: no tags, no signed/content-hash
  release artifact, no CHANGELOG/release notes, `pyproject` 0.1.0.
  `df78f42` is a self-described "release(sst)" *commit* (clean,
  161/161 pytest + strict gates claimed in-message) — a good
  vendoring source, not a release identity substrate can cite for
  acceptance. The SST-side "Freeze only a qualified release"
  principle (coordinator prompt §7) is stated but has no minted
  output yet.

### STC: readiness packet claims, and what it is missing

The packet (`docs/STC-LIVE-READINESS-PACKET.md`, committed at HEAD)
claims/gates STC's OWN next spend window, nothing substrate-facing:

- Claims: dependency identity table (SST 079f4de6 authoritative,
  df78f42 candidate "AWAITS owner blessing"; Sail model/key/pricing);
  three acceptance legs (§2a quota-free pin-advance AFTER owner
  blessing, §2b paid calibration-first caller exercise ≤$0.39/run,
  §2c paid quality batch pilot-then-full); cost arithmetic (~$7 peak);
  hard caps ($5/$15/$4, $20 combined); stop conditions; a single
  decision ask (bless SST commit, approve legs+caps, provide key).
- Missing for substrate consumption: (a) the packet is not frozen —
  no tag, and the worktree already supersedes its SST pin; (b) it
  defines no substrate-facing envelope — STC's only caller contract
  (`STC-SST-CALLER-CONTRACT.md`) governs STC→SST (`execute_search`,
  `run_search` explicitly "newer optional surface: reported, never
  required"); (c) substrate-track mentions in STC are its INTERNAL
  `src/stc/substrate/` quality gates, not our substrate — no STC
  surface targets substrate consumption at all; (d) live legs are
  UNQUALIFIED by STC's own record (5/6 live nodes quota-blocked;
  "live deselected in gates" per D13); (e) gate evidence
  (backend 697/6, mypy 0/83, plugin 95/95, e2e 16, probe 6/6) is
  bound to older bases (78a3448/c1bd60a) and the current dirty tree
  (src+tests modified, pin advanced) has no fresh gate record.

## 3. 'Qualified for substrate consumption' — checklists

RECONCILED 2026-10-04 (coordinator correction to P1's gating): a full
commit hash plus a verified content manifest already identifies bytes;
tags and specially-named owner documents are NOT mandatory gates and
must not become release ceremony. The genuine requirements are the
owner's contract (stability/change-policy promise + consumer scope)
and the owner's acceptance evidence (gate record bound to the pinned
bytes). "Owner-minted" below means owner-authored bytes at a pinned
commit, in whatever file the owner chooses — not a tag, not a
mandated filename. A pin must still reference IMMUTABLE bytes (a
dirty worktree cannot be pinned — that is physics, not ceremony).

### SST checklist (unblocks: U-branch claim that substrate consumes a real SST release)

- [x] Q-SST-0 byte identity: full commit hash `df78f42…` + verified
      manifest (substrate-snapshot-v1, 54 files, `5f1f3789…`,
      re-verified MATCH). SATISFIED — citable today, no tag needed.
- [ ] Q-SST-1 owner contract: owner-authored bytes at a pinned commit
      stating the consumed scope, the consumer (substrate), and the
      `run_search → SearchResult` (8 keys) + `ProviderKind.TEST`
      stability promise with a change policy (additive-only / bump).
      (Converts "proposed" to promised; any owner-chosen file.)
- [ ] Q-SST-2 owner acceptance evidence: owner-attested gate record
      (command + pass/fail counts) bound to the pinned bytes,
      reproducible $0. (In-message claims don't count; committed
      record does.)

Current: identity SATISFIED; 2 genuine gaps (contract + evidence).
Tags optional (convenience alias only, never a gate).

### STC checklist (unblocks: U-branch claim involving STC material)

- [ ] Q-STC-0 byte identity: a CLEAN commit hash (+ manifest of the
      consumed bytes). OPEN — today the tree is dirty with an
      uncommitted pin advance; nothing immutable to cite. (A tag is
      one way to bless it; a clean commit hash suffices.)
- [ ] Q-STC-1 artifact decision: owner names a substrate-consumable
      artifact, if any (today: none exists — first a design decision;
      "nothing — STC is not a substrate producer" also resolves it).
- [ ] Q-STC-2 owner contract + acceptance evidence for that artifact
      (same shape as Q-SST-1/2, once Q-STC-1 names the target).

Current: identity OPEN (needs clean commit, not ceremony);
artifact decision + contract/evidence genuinely missing.

## 4. Gaps (blocking U-branch acceptance)

1. No tags / minted releases on any producer (verified: `git tag`
   empty on SST, STC, TRACE).
2. SST `run_search`/TEST envelope stable-in-practice but only
   "proposed", not owner-declared stable.
3. STC tree dirty with src+test changes and an uncommitted SST pin
   advance; committed packet already stale vs worktree.
4. STC has no substrate-facing surface to qualify (all contracts are
   STC→SST / STC→DSH internal).
5. Live-model legs on both tracks explicitly UNQUALIFIED (SST dollar
   spend unmeasured by design; STC live nodes quota-blocked).
6. TRACE dirty + tagless; out of P1 scope beyond presence/state.

## 5. Producer porcelain before/after (untouched verification)

| producer | before (start of survey) | after (end of work) |
|---|---|---|
| SST | 0 lines (clean) | 0 lines (clean) |
| STC | 28 lines (14 M + 14 ??) | 27 lines: 14 M tracked byte-identical; one untracked dir (`?? demo-dossier-a5gILM/`) removed by an EXTERNAL concurrent actor (P1 issued zero producer-write commands — all P1 producer interactions were git-inspect/file-read/hash/copy-from; `git status/show` cannot delete) |
| TRACE | 25 lines | 25 lines (byte-identical — `diff` empty) |

Full before/after porcelain captures compared with `diff` (see
SELFTEST-EVIDENCE.log tail). Frozen substrate artifacts (r1,
successor-003) were read, never written. All P1 writes are confined
to `prototype/programme-20261004/P1-adapters/`.

## 6. Uncertainties

- Timestamps: pins observed ~15:15–15:30Z; producers may move after.
- STC's dirty-tree direction (df78f42 advance + test rework) suggests
  an owner window is active; the next STC HEAD may obsolete §1 pins —
  that is routine (deliberate re-pin), not a finding.
- Whether the SST owner intends `run_search` (vs `execute_search`)
  as the long-term consumer surface is unstated; the ask covers both.
- TRACE was not surveyed beyond presence/state per task scoping.

## 7. Refresh 2026-10-04 ~18:30Z (coordinator; earlier pins kept as history)

- STC HEAD is now `5c65427d7267e3bf37a9e56887ab51c5dfc46422`
  (`feat(stc): SST cand-02 pin adoption + honest-budget caller
  fixes`, 2026-10-04 18:22:52 +0000). `EXTERNAL_PINS["sst"]` at
  that commit = `df78f42…` COMMITTED — the §1 "uncommitted pin
  advance" blocker is STALE (superseded, not wrong at the time).
- STC worktree dirty again (17 porcelain lines: `.gitignore`,
  `live-pilot.py`, `pilot-tasks.py`, `stc-exec.ts`, untracked docs —
  owner active). The COMMIT `5c65427…` is immutable and citable
  regardless; pin the commit, never the worktree. No tags (optional).
- SST unchanged: `df78f42`, porcelain 0, no tags.
- Checklist deltas: Q-STC-0 may now cite `5c65427…` (+ manifest of
  consumed bytes when an artifact is named) — SATISFIABLE, pending
  Q-STC-1. Q-STC-1 (artifact decision) + Q-STC-2 (contract/evidence)
  still genuinely open; full STC release qualification still needs
  evidence. SST: Q-SST-0 satisfied (unchanged); Q-SST-1/2 still open.
