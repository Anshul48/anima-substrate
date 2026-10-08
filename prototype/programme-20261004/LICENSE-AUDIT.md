# LICENSE-AUDIT.md — substrate Apache-2.0 publication audit (2026-10-07)

Scope: what the new package would redistribute or derive from, who must be
attributed, and what must be kept/removed. READ-ONLY audit; this file is the
only write. The coordinator owns LICENSE/NOTICE creation — §4 below is draft
content only, not a filed notice.

Method: in-tree file reads + import scans + hash-manifest comparison; sibling
repos (`../sst`, `../stc`, `../ANIMA`) inspected read-only for license/author
facts only. Substrate is NOT a git repo (no commit history exists); SST/STC
git logs were read where cited.

## 1. Verified authorship table

| # | Claim | Evidence (verified) | Status |
|---|---|---|---|
| A1 | Substrate has no LICENSE/NOTICE/COPYING file | `ls` at root: absent | VERIFIED — must be created by coordinator |
| A2 | No copyright/author header in any substrate-authored file | Full-tree grep (excl. `.venv`, `sst-snapshot`, evidence/runs artifacts) for `copyright\|licensed under\|all rights\|spdx\|author:`: zero hits in substrate-authored bytes | VERIFIED |
| A3 | No git authorship for substrate | `git log`: "not a git repository" | VERIFIED — no commits to attribute |
| A4 | Only human name+email in-tree is about STC, not substrate | `STC-548615a-ASSESSMENT.md:12`: "Author/committer: Anshul48 <anshulraj48@gmail.com>" — a recorded observation of STC repo commits | VERIFIED — not substrate authorship |
| A5 | Substrate prose attributes work to roles, never humans | `coordinator`, `builder`, `lane`, `auditor`, `worker`, `user` throughout (e.g. COMPLETION-MAP.md, IDENTITY.json `computed_by: substrate coordinator closeout`, FREEZE.json `freezer: hardened-pilot-builder`) | VERIFIED |
| A6 | The directing "user" is unnamed in-tree | "user"/"user-authored"/"user-reinforced" used without a name (COMPLETION-MAP.md §§1–3, README.md) | VERIFIED — name missing |
| A7 | OS username appears in absolute paths (NOT authorship) | `/mnt/c/Users/<user>/...` in REPRODUCE-ALL.md, docs/SUBSTRATE-DIRECTION.md, vendor PROVENANCE.md copy-time paths, run EVIDENCE.json `solution_ref`s; `C:\Users\anshu\...` in PENDING-B1-B2-REVIEW-2026-10-05.md | VERIFIED — path artifact; scrub before publication (privacy, not license) |
| A8 | SST authorship (sibling, for attribution of vendored bytes) | `../sst/pyproject.toml`: `license = { text = "Apache-2.0" }`, `authors = [{ name = "Advanced Agentic Coding Team" }]`; git log: `SST Architect <sst@system.local>` (3 commits, no remote); NO LICENSE/NOTICE file in SST repo; NO per-file headers in any of the 54 vendored files | VERIFIED |
| A9 | STC authorship (sibling, contextual — nothing vendored) | `../stc/LICENSE`: Apache-2.0 full text + appendix `Copyright 2026 STC Contributors`; `../stc/pyproject.toml`: `authors = [{ name = "Anshul48", email = "anshulraj48@gmail.com" }]`; git log: predominantly `Anshul48 <anshulraj48@gmail.com>` | VERIFIED |
| A10 | ANIMA authorship | No LICENSE file; out of scope (nothing copied — see §2). Authorship not established, not needed | NOT NEEDED unless copied |

MISSING (coordinator must resolve before filing LICENSE/NOTICE):

- M1. Substrate copyright owner: legal name/entity + year(s). Nothing
  in-tree answers this. Candidates the coordinator must confirm with the
  human: the unnamed "user", or a team/entity name.
- M2. Whether agent-authored bytes (builders/lanes/auditors) are assigned
  to that owner — a human decision, not discoverable in-tree.

## 2. Redistribution / derivation inventory

### 2a. Project-original code (all successor/lane trees) — KEEP

Carry chains are documented and stay inside the project:

- `minihost.py` lineage: reuse-demo-001 → successor-001 → … → successor-006
  (sha `d01049a9…`, byte-pinned by tests; VENDORING.md + PROVENANCE.md per tree).
- s002←s001, s006←s005 copy-forward records list every carried/adapted/new file.
- w1 → w1-harden (FREEZE.w1 anchor), reuse-demo-001, x3-20261004: standalone originals.
- Programme lanes (H2-lane, P1-adapters, L1/L2, M1/M1-redux, S5-*, U-execute,
  RealUse-design), successor-contract, release-*/closeout records, docs/:
  substrate-authored prose + code.

Import scan verdict: every `.py` outside `vendor/sst-snapshot/` and `.venv/`
imports stdlib + intra-tree modules only, EXCEPT the SST-leg consumers
(`sst_leg.py`, `verify_snapshot.py`, `make_snapshot_manifest.py`,
`sst_child_test.py`, `sst_check.py`, test files), which import the vendored
`sst.*` snapshot and external `pydantic` (venv-provided, never copied
in-tree — verified: no `pydantic*` outside `*.venv*`).

- successor-006 is fully stdlib-only (SST leg deliberately NOT carried;
  `with_sst=True` refuses loudly). It is the cleanest publication candidate.

### 2b. SST snapshot bytes vendored INTO substrate — YES, in 5 trees

| Location | Content | Identity |
|---|---|---|
| successor-002/vendor/sst-snapshot/ | 54 files (~492K): 50 `*.py` + `py.typed` + 3 visualizer assets | df78f42, `substrate-snapshot-v1`, `5f1f3789…` |
| successor-003/vendor/sst-snapshot/ | identical (`diff -rq` vs s002: clean) | same |
| successor-004/vendor/sst-snapshot/ | identical bytes (same manifest hash `5f1f3789…`) | same |
| successor-005/vendor/sst-snapshot/ | identical bytes (same manifest hash) | same |
| programme-20261004/H2-lane/vendor/sst-snapshot/ | identical snapshot bytes (same manifest hash; dir larger only due to sibling docs) | same |

- Source: `../sst/src` at clean commit `df78f42…`, method `cp -r` minus
  `__pycache__/` only (vendor/PROVENANCE.md, `diff -r` recorded).
- SST tests/docs/evidence were NOT copied (out of scope per P1 VENDORING.md).
- successor-001 carries NO SST bytes: its `sst_leg.py` points at external
  `../sst/.delivery/cand-02` staging; its `runs/` hold manifests/hashes only.
- successor-006 carries NO SST bytes (no `vendor/` at all).
- Test/snapshot dirs (`sst-work/`, `search-work/`): contain only
  project-authored fixtures (`toy.py` = `def add…`, `math_mod.py` =
  1-line `def mul…`, `test_math.py`) plus generated sqlite `.db`/ledger
  runtime artifacts. NO SST source in any of them (verified by path scan).
- `sst_child_test.py` docstring says "Modeled on the snapshot
  tests/unit/test_controller.py pattern" — idea-level reference; SST's tests
  are not in-tree so no lines could have been copied from them in-tree.
  Low risk; kept as-is.

### 2c. STC material in-tree — NONE (hashes + prose only)

- P1-adapters/ contains 9 substrate-original files (adapters, pins, selftest,
  docs). NO STC documents or code are vendored: PINS.json holds sha256
  hashes of 8fa8ac3-era STC docs; VENDORING.md copies STC bytes to /tmp at
  verify time (never redistributed, never in-tree).
- STC-548615a-ASSESSMENT.md / STC-CONSUMER-BOUNDARY.md contain paraphrase and
  pin tables, no pasted STC code.
- Publication scope: P1-adapters code itself is substrate-original and may
  ship; it ships zero STC bytes. The STC *documents* it can verify stay
  external by design ("re-pin only when pursuing STC consumption" — not pursued).

### 2d. ANIMA packet — OUT OF SCOPE, confirmed no copies

- Zero files/dirs matching `*anima*` in-tree (excluding `.venv`).
- 5 `.md` files reference ANIMA by citation only (sibling paths
  `../ANIMA/context/…`, decision IDs `D-001..D-017`, `IDEA-MAP:NN` locators;
  COMPLETION-MAP.md has 18 such locators). No verbatim excerpts pasted.
- Recommendation: keep citations; do not copy packet content (ANIMA has no
  license file — any future copying needs owner clearance).

### 2e. Third-party code/dependencies — NONE redistributed

| Item | Where | Ships? |
|---|---|---|
| pydantic, aiohttp, httpx, click, rich, … (SST runtime deps) | `prototype/w1/.venv/`, root `.venv/` only | NO — venvs are regenerable tool output, must be excluded |
| pytest/ruff/build | root `.venv/` only | NO — same |
| `__pycache__/` bytecode | scattered | NO — regenerable, exclude |
| SST `py.typed` + visualizer css/js/README | inside the 54-file snapshot | YES — part of item §2b, same obligations |

## 3. Per-item license, obligations, recommendation

| # | Item | License | Notice obligations if shipped | Recommendation |
|---|---|---|---|---|
| T1 | Substrate-original code/docs (all trees, incl. P1-adapters code, fixtures, accept packs) | To be Apache-2.0 (new grant; owner per M1) | New LICENSE file + per-file or root attribution once, by coordinator | GO — keep |
| T2 | SST snapshot bytes (5 identical copies, §2b) | Apache-2.0 **declared in `../sst/pyproject.toml` only** — no LICENSE file, no per-file headers, no NOTICE in SST repo | Apache-2.0 §4: (a) include full License text; (b) retain attribution notices — the only one that exists is the pyproject `authors` string; (c) state changes (`__pycache__/` removal only — already recorded in vendor/PROVENANCE.md); (d) no NOTICE file exists to retain | CONDITIONAL GO — see options below |
| T3 | STC bytes | Apache-2.0 (`Copyright 2026 STC Contributors`) — but ZERO bytes in-tree | None (nothing shipped) | GO — keep current state (hashes/prose only); NO-GO on any future vendoring without re-audit |
| T4 | ANIMA content | Unknown (no license file) — ZERO bytes in-tree | None (nothing shipped) | GO — citations only; NO-GO on copying without owner clearance |
| T5 | `.venv/` trees (2), `__pycache__/`, `*.db` run artifacts | Mixed third-party / regenerable | N/A — do not ship | NO-GO — exclude from package |
| T6 | `runs/` evidence dirs (ledgers, EVIDENCE.json) | Project-generated, but embed absolute machine-username paths | Privacy scrub if shipped | EXCLUDE or scrub — evidence is not package code |
| T7 | Docs with absolute username paths (REPRODUCE-ALL.md, SUBSTRATE-DIRECTION.md, vendor PROVENANCE.md) | N/A (paths, not code) | Generalize to `$U/substrate`-style placeholders | SCRUB before publication |

T2 options (coordinator decision):

- Option A (cleanest): EXCLUDE all five `vendor/sst-snapshot/` dirs from the
  publication; document fetch-by-pin (`VENDORING.md` procedure already
  specifies it: clean `df78f42` + `verify_snapshot.py`). s002–s005/H2-lane
  SST legs then require the operator to stage SST; s006 is unaffected
  (stdlib-only). No third-party bytes ship at all.
- Option B: SHIP the snapshot (deduplicate to ONE copy + references) with
  (i) Apache-2.0 LICENSE text, (ii) NOTICE entry per §4 draft, (iii) the
  existing vendor/PROVENANCE.md as the §4(b) changes statement. Residual
  risk: the Apache-2.0 grant rests on a pyproject declaration, not a
  LICENSE file — ask the SST owner to add a LICENSE file (or written
  confirmation) to close the chain.

## 4. NOTICE-file draft content (draft only — coordinator files it)

Required only if T2-Option-B (shipping SST bytes) is chosen. If Option A,
no NOTICE file is needed (no third-party bytes shipped).

```text
Substrate
Copyright [YEAR] [OWNER — see M1; must be supplied by the human]

Licensed under the Apache License, Version 2.0 ...

This product includes software from the SST project:

  SST (State Space Tree) search engine, snapshot of src/ at commit
  df78f42894a65c48f524337a498032617689a013 ("df78f42 release(sst):
  task-to-result UI, honest budgets, live-model qualification",
  2026-10-04), construction substrate-snapshot-v1, 54 files,
  snapshot_hash 5f1f37893b0f5ab9ff7dcf0ce2c60b287b51647e2f18f627eabf5510537cad96.
  Declared license: Apache-2.0 (per SST pyproject.toml; SST repo carries
  no separate LICENSE file at time of audit).
  Declared authors: Advanced Agentic Coding Team (per SST pyproject.toml).
  Source: sibling ../sst tree (read-only copy; __pycache__/ removed only —
  see vendor/PROVENANCE.md). NO SST-owner release acceptance is claimed.
```

## 5. Go / no-go summary

- GO: all substrate-original code/docs/fixtures (T1), STC posture as-is (T3),
  ANIMA posture as-is (T4).
- CONDITIONAL GO: SST snapshot bytes (T2) — Option A (exclude) preferred;
  Option B (ship once + LICENSE + NOTICE + owner LICENSE request) acceptable.
- NO-GO: `.venv/` trees, bytecode, run `.db` artifacts (T5); unscrubbed
  absolute username paths (T6/T7).
- BLOCKING on coordinator: M1 (copyright owner name/year), M2 (assignment of
  agent-authored bytes), T2 option choice, T2-Option-B SST-owner LICENSE request.

## 6. Conflicts / risks

1. SST's Apache-2.0 grant is pyproject-declared only (no LICENSE file,
   no headers). The redistribution chain is weaker than a normal
   Apache-2.0 dependency. Mitigated by Option A (exclude) or an SST-owner
   LICENSE addition.
2. No substrate copyright owner is identifiable in-tree; the LICENSE file
   cannot be honestly filled without a human answer (M1/M2).
3. `runs/` and some docs embed the machine username (`anshu`) in absolute
   paths — a privacy/paper-cut issue for publication, not a license conflict.
4. No other conflicts found: no copyleft code, no pasted third-party
   snippets, no STC/ANIMA bytes, no conflicting license declarations.
```

Output path: `prototype/programme-20261004/LICENSE-AUDIT.md`.
