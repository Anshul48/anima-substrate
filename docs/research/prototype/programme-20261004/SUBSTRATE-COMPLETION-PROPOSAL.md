# SUBSTRATE-COMPLETION-PROPOSAL.md — concise completion proposal

Sources: COMPLETION-MAP.md (R1–R12, Q1–Q5, S5-proc, U-exec, P1-prod, deferreds), U-OVERALL-FINAL.md, SUBSTRATE-DIRECTION.md, ANIMA packet (OPERATIVE-BRIEF, IDEA-MAP, REQUIREMENTS-AND-EVIDENCE). No new scope invented.

## 1. Remaining capabilities (map-derived only)

1. **Persistent worlds** — nested worlds w/ own state, policy, lifecycle, resource delegation (R1 PARTIAL, R10 toy-only).
2. **Local responsibility** — child invents local policy within outer limits; reduces central load (R1/R8 CONDITIONAL; policy invention missing).
3. **Reorganization** — versioned relationships + fusion/fission/assimilation w/ real state/ownership change (R3–R5 single-host only; cross-host/multi-writer DEFERRED).
4. **Reuse** — composite + lineage reuse elsewhere w/ costs (R6 PARTIAL; recipe inheritance missing).
5. **Adaptation** — recover useful behaviour under unfamiliar change, measured cost (R7 authorized-only; autonomous discovery DEFERRED; U-exec change legs VOID).
6. **Inheritance** — descendant advantage on unfamiliar work from retained recipe (R6/Q4 negative; DEFERRED, needs learning loop).

## 2. User journeys (3)

- **J1 Builder:** nest experiment world in construction world, delegate budget, interrupt/kill, resume byte-identical, export composite for next task.
- **J2 Integrator:** introduce participant w/o substrate edit; discover capability; negotiate versioned adapter; revise after representation change; dissolve coalition keeping records.
- **J3 Maintainer:** face unfamiliar fault; world quarantines, recovers limited mode, proposes assessed repair, retains recipe; descendant shows advantage on new fault.

## 3. Acceptance criteria (observable, per capability)

| Cap | Pass iff |
|---|---|
| Worlds | create/nest/run/interrupt/resume; pre/post mechanism inventory shows real ownership change; receipts verify |
| Local resp. | policy invented locally (not hand-written); central bytes/dialogue lower vs central baseline at scale; calibration reported |
| Reorg | fusion lineage + reuse ≥4/4; fission partition; quarantine separation; all survive reopen (single-host envelope) |
| Reuse | composite consumed unmodified by second consumer; derived_from lineage VALID; cost recorded |
| Adaptation | unfamiliar-change probe: recovery TRUE, task quality + cost + human effort vs baseline; no prepared-repair leak |
| Inheritance | descendant-from-recipe beats from-scratch on held-out work; diversity/transfer/cost assessed |

## 4. Dependencies / ownership

- SST/STC: qualified-exports-only (P1-prod byte-identity OK; owner contracts missing — producer owners owe). No HEAD-following; re-pin only to consume.
- TRACE: presence-only; TL absent — no dependency.
- Owners: host/worlds = substrate owner (undecided host — Q5 standing); learning/inheritance = future-learning owner under D-005 signal semantics; quarantine-transfer repair = owned (R11).
- Envelopes preserved: single-host, toy scale, TEST-only SST, process-crash-only, no fsync. Cross-host/multi-writer/disk-loss stay DEFERRED.

## 5. Execution order + rationale

1. **Repair + harden envelope** (quarantine-transfer operator, R11; resume-coupling list → R9) — owed, unblocks trust.
2. **J1 persistent-worlds path** — extends SATISFIED R10/R11; cheapest demonstrated-value increment.
3. **J2 revisable cooperation** — R3 learned-revision probe only on live uncertainty (Q4 negative binds; bounded probe).
4. **J3 adaptation probe** — discriminating unfamiliar-change protocol (V10/E3-E4 obligation); must precede any inheritance claim.
5. **Inheritance last** — needs J3 instrument + learning loop; ARC-negative history means high bar.
- Rationale: bank what is near (1–2), instrument before claiming (3–4), gate the RSI-adjacent (5). B1/B2 review stays PAUSED.

## 6. Alternatives considered

- **Extend DSH/Cordis vs new host:** undecided (Q5); proposal is host-agnostic — pick provisional host per W0, keep composite semantics identical.
- **More benchmarks now:** rejected — R8/Q1-Q2 rules hold (no runs without new hypothesis); only discriminating probes.
- **Evolution machinery now:** rejected — V16/D-004 conditions unmet; local adaptation first.

## 7. Demonstrated vs unfinished ambition

| Demonstrated (in envelope) | Unfinished ambition (honest negative) |
|---|---|
| Single-host fusion/fission + reuse, durable revocation (R4/R5) | Cross-host, multi-writer, disk-loss |
| Nested self-solve, versioned relations, kill-resume byte-identical (R1/R3/R11) | Local policy invention; learned mapping/revision |
| Bounded procedure participant 57/57, tamper 5/5 (S5-proc) | Autonomous discovery; recipe inheritance; descendant advantage |
| U-exec: recovery TRUE, clean bar-met, H-vs-D TIED | U-exec overall HOST-VALUE-NOT-DEMONSTRATED; adaptation VOID; r5 NOT banked |
| Producer byte identity; no overclaim (P1-prod) | Owner contracts/evidence genuinely missing; Q5 host undecided |

**Recommendation:** do 1→2 now; gate 3–5 on discriminating probes; keep deferreds deferred.
