# SEPARATION-PATHS.md — quarantine vs fission: when each applies

Two separation paths are implemented. They solve different problems;
neither is a special case of the other.

Successor-003 note: paths unchanged. Kill-during-fission now
recovers via `ops recover` (operator supplies the partition of
record); kill-during-quarantine-transfer is detected with explicit
operator steps (completion automation still out of scope, LIMITS-3).
See INTERRUPTION-BOUNDARIES.md.

## QUARANTINE (`fusion.quarantine_world`) — failure-driven isolation

- WHEN: one participant FAILED (or is untrusted) mid-task and its
  commitments must complete anyway. Asymmetric by design: a sick world
  and a healthy standby.
- WHAT: the failed world is SUSPENDED (not dissolved) with
  `pending_effects` naming each commitment's handoff; every commitment
  transfers to the standby (actor=`host`: the giver cannot act); the
  standby completes the work with its own capabilities. Invokes on the
  quarantined world are denied (not-active rule) with recorded denies.
- END STATE: failed world suspended (settleable later via
  reattach-then-dissolve), standby active and holding the commitments.
- USE: S5 drill (demo), `test_11`, `TestQuarantineConformance`.
- DO NOT USE to restructure a healthy composite: quarantine leaves a
  suspended world behind and concentrates custody on one standby — it
  does not produce two working peers.

## FISSION (`fusion.fission_worlds`) — planned decomposition of a fusion

- WHEN: a healthy FUSED COMPOSITE should become two working worlds
  again (planned restructure, reversal of a fusion, load split along a
  state-class boundary). Symmetric intent: both children are peers.
- WHAT: custody is partitioned back to two NEW worlds per the
  partition record (actor = the composite, O4); the composite
  settle-then-dissolves; the direct channel between the children is
  restored (cross-boundary coordination is explicit again); lineage
  entries name the fusion being split. Both children are live and can
  cooperate immediately (demonstrated: S6).
- PRECONDITIONS (all validated before any mutation): composite active
  AND a recorded fusion; partition covers exactly the composite's
  state classes across BOTH children.
- END STATE: composite dissolved, two active children holding the
  partitioned custody.
- USE: demo fission leg (S6), `test_fission.py`,
  `TestFissionConformance`.
- DO NOT USE on a failed participant: fission requires an ACTIVE
  recorded composite and produces peers, not a standby rescue — a
  world that cannot act cannot fission (use quarantine).

## Comparison

| | quarantine | fission |
|---|---|---|
| trigger | failure / distrust | planned restructure |
| input | 1 failed world + 1 standby | 1 healthy fused composite |
| custody | ALL commitments → standby | PARTITIONED across 2 children |
| input world after | suspended | dissolved |
| survivors | 1 (standby) | 2 (children, both active) |
| channel | untouched | restored between children |
| lineage written | `quarantine` entry | `fission` + `fission-of` entries naming the split fusion |
| reversibility | reattach possible | the children may fuse again (new fusion entry) |

What is NOT a separation path: revocation (flips capability usability,
moves nothing), revision (switches active representation, moves
nothing), and dissolve-without-successor (terminal; used only at
finish). Cross-host separation in any form is NOT implemented.
