# RUNBOOK.md — successor-006 J1 persistent-worlds journey

One-command demo (from the repo root; exits 0/1 with per-stage
PASS/FAIL, fresh state under `successor-006/runs/`):

```
export PYTHONDONTWRITEBYTECODE=1
python3 prototype/successor-006/j1_demo.py
```

The same journey step by step through the CLI (copy-paste; uses a
scratch dir you delete afterwards):

```
export PYTHONDONTWRITEBYTECODE=1
S6=prototype/successor-006
D=$S6/runs/j1-manual   # keep inside successor-006/

# 1. persistent project world on FRESH state
python3 $S6/release.py j1-init --state-dir $D --project PROJ \
    --reason "manual J1"

# 2. nest an experiment world + delegate budget (sub-grant + custody)
python3 $S6/release.py ops nest --state-dir $D --project PROJ \
    --child EXP1 --delegate 0.5,30,50 --custody j1.budget \
    --reason "manual J1"

# 3. run work through the experiment world (project cross-verifies)
python3 $S6/release.py ops j1-work --state-dir $D --world EXP1 \
    --task J1-T1 --verifier PROJ
# expect: valid=True re_executed=0

# 4. interrupt (real kill) + reopen byte-identical
python3 $S6/release.py ops j1-kill-resume --state-dir $D --world EXP1 \
    --task J1-T2 --verifier PROJ
# expect: child_rc=-9 (rc != 0), valid=True, re_executed=0

# 5. inspect responsibilities + evidence
python3 $S6/release.py ops j1-status --state-dir $D
python3 $S6/release.py ops j1-status --state-dir $D --json | head -40

# 6. fuse into one composite (real ownership change)
python3 $S6/release.py ops fuse --state-dir $D --a PROJ --b EXP1 \
    --fused PROJ-FUSED --reason "manual J1"

# 7. reuse the composite in a first task, then UNMODIFIED in a second
python3 $S6/release.py ops reuse --state-dir $D --composite PROJ-FUSED \
    --followup S4
python3 $S6/release.py ops reuse --state-dir $D --composite PROJ-FUSED \
    --followup S6
# expect: valid=True both; identical derived_from lineage

# 8. export the verifiable evidence bundle
python3 $S6/release.py ops j1-export --state-dir $D --composite PROJ-FUSED
cat $D/artifacts/j1-export-PROJ-FUSED.json

# 9. settle: 0 stranded
python3 $S6/release.py ops settle --state-dir $D --worlds PROJ-FUSED \
    --reason "manual J1 done"
```

## Quarantine repair drill (R11)

```
D2=$S6/runs/q-manual
python3 $S6/release.py init --state-dir $D2
# Clean quarantine (both worlds ship with init):
python3 $S6/release.py ops quarantine --state-dir $D2 --world SC-L \
    --standby SC-S --reason drill
# ... or, after a kill during quarantine-transfer:
python3 $S6/release.py ops recover --state-dir $D2   # detects + steps
python3 $S6/release.py ops quarantine-complete --state-dir $D2 \
    --world SC-L --standby SC-S --reason "operator decision: complete"
# or:
python3 $S6/release.py ops quarantine-rollback --state-dir $D2 \
    --world SC-L --standby SC-S --reason "operator decision: rollback"
```

To reproduce an interrupted transfer deterministically (test-only
hook; the hook's ledger effect is identical to a SIGKILL at the same
boundary):

```
D3=$S6/runs/q-kill
python3 $S6/release.py init --state-dir $D3
SUBSTRATE_CRASH_AFTER_APPENDS=4 python3 $S6/release.py ops quarantine \
    --state-dir $D3 --world SC-L --standby SC-S --reason drill
echo "rc=$? (expect 42 = simulated kill)"
python3 $S6/release.py ops quarantine-complete --state-dir $D3 \
    --world SC-L --standby SC-S --reason drill
```

## Pass/fail criteria

- Demo: `J1 journey: OK (10/10 PASS)` on stdout, exit 0.
- Manual: every command exits 0; the `expect:` lines above hold;
  `j1-status` shows conservation ok; `settle` reports stranded=0.
- Any deviation is a FAIL: keep the state dir and file the exact
  command + output (see LIMITS.md for the envelope — outside it,
  behavior is explicitly unpromised).
