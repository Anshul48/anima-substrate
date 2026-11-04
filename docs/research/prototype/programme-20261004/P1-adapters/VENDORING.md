# VENDORING.md — how adapter input copies are made (P1)

Adapters consume COPIES ONLY. No adapter module references a live
producer tree at runtime (asserted by selftest `no runtime refs into
producers`). This file is the normative copy procedure. Every step is
read-only toward the producer: copy FROM, never write TO.

## SST snapshot copy (for `sst_adapter.verify_snapshot_copy`)

Source: the SST sibling tree at the pinned commit
`df78f42894a65c48f524337a498032617689a013` (must be clean —
`git -C ../sst status --porcelain` empty — else the copy is not the
pinned commit and verification SHOULD fail).

```sh
# from the substrate repo root:
rm -rf /tmp/p1-sst-copy
cp -r ../sst/src /tmp/p1-sst-copy
find /tmp/p1-sst-copy -name __pycache__ -type d -prune -exec rm -rf {} +
PYTHONDONTWRITEBYTECODE=1 python3 - <<'EOF'
import sys
sys.path.insert(0, "prototype/programme-20261004/P1-adapters")
from sst_adapter import verify_snapshot_copy
print(verify_snapshot_copy("/tmp/p1-sst-copy"))
EOF
# expect: verdict MATCH, snapshot_hash 5f1f3789… (see PINS.json)
```

Equivalence anchor: the same bytes are pinned by r1's frozen
`prototype/successor-002/vendor/SNAPSHOT-MANIFEST.json` (54 files,
`substrate-snapshot-v1`, hash `5f1f3789…`). The self-test asserts
fresh-copy entries == frozen manifest entries, so this procedure
reproduces r1's snapshot exactly. Do NOT copy `../sst` wholesale
(tests/docs/evidence are out of scope); do NOT run anything inside
the copy.

## STC doc copy (for `stc_adapter.verify_doc_copy`)

Source: STC HEAD bytes (`8fa8ac3…`), extracted via `git show` so the
dirty worktree can never leak in. Never copy worktree files for the
two paths that differ from HEAD (`docs/STC-SST-CALLER-CONTRACT.md`,
`src/stc/integration/lease_git.py`).

```sh
# from the substrate repo root:
rm -rf /tmp/p1-stc-docs && mkdir -p /tmp/p1-stc-docs
cd /tmp/p1-stc-docs
for spec in \
  "STC-LIVE-READINESS-PACKET.md:docs/STC-LIVE-READINESS-PACKET.md" \
  "STC-DSH-RELEASE.md:docs/STC-DSH-RELEASE.md" \
  "STC-DSH-RECORD.md:docs/STC-DSH-RECORD.md" \
  "STC-SST-CALLER-CONTRACT.md:docs/STC-SST-CALLER-CONTRACT.md" \
  "DSH_PIN:dsh-plugin-stc/DSH_PIN" \
  "lease_git.py:src/stc/integration/lease_git.py" ; do
  local="${spec%%:*}"; repo_path="${spec#*:}"
  git -C <substrate-root>/../stc show "HEAD:${repo_path}" > "${local}"
done
```

Verify with `stc_adapter.verify_doc_copy("/tmp/p1-stc-docs")`
(expect MATCH + EXTERNAL_PINS == pinned HEAD set). `lease_git.py`
is parsed with `ast` (never imported/executed).

## Deliberate-pin upgrade (both producers)

1. Survey the new producer state (read-only; record HEAD/porcelain/tags).
2. Edit `PINS.json` (new hashes + `pinned_at_utc` + reason in SURVEY.md).
3. Re-vendor per this file; run `selftest.py` — must be all-PASS.
4. Never point an adapter at a live tree to "pick up" HEAD silently.

## Prohibited

- Runtime `sys.path` / import / subprocess of anything under a
  producer tree (SST leg execution stays r1's `sst_leg.py` + venv job).
- Writing into `../sst`, `../stc`, `../trace`, or any frozen substrate
  artifact (r1 = successor-002 + release-20261004; R1 = successor-003).
- Running producer test suites (`pytest` under `../sst`/`../stc`).
