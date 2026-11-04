# SUBSTRATE SOFTWARE MANDATE — PROPOSAL (coordinator draft, needs agreement)

One agreed software realization with milestones inside the mandate.
Finish line = a genuinely usable substrate, not the full research vision
(§5 stays explicit and beyond the line). Coordinator owns routine
implementation, reconciliation, verification, release/banking across
milestones; user judgment reserved for consequential semantics,
architecture, and cost.

## §1. Scope (in)

1. Genuinely usable project-world journey: persistent project worlds
   doing real file-backed task work (beyond deterministic toy tasks),
   with an install path, examples, and actionable failures.
2. Substantial participants through pinned interfaces: at least two
   participant families behind versioned capability contracts,
   addable/upgradable without substrate edits.
3. Persistent organizational behavior: relationships, channels, and
   custody survive reopen; exported composites are portable and
   executable elsewhere, not evidence bundles only.
4. Evidence-grounded propose → assess → retain → reuse loop:
   proposals assessed mechanically + independently, retained with
   lineage + cost, reuse measured. NO invention/discovery claims
   (bounded by the Q4 negative and D-005 signal semantics).

Envelope carried throughout: single-host, local disk,
process-crash-only, $0/offline/stdlib-only (+ pinned SST snapshot
where qualified). Each milestone independently accepted through
consumer interfaces on fresh state; frozen predecessors untouched;
banking routine.

## §2. Milestones + concrete acceptance criteria

- M1 Usable journey. ACCEPT iff: fresh-state CLI journey creates a
  project world, does file-backed task work, closes cleanly, reopens
  with all state/relationships byte-verified, and finishes; install
  = documented commands on a clean checkout; 3 seeded failure cases
  produce actionable errors (named cause + fix); limits filed.
- M2 Pinned participants. ACCEPT iff: a second participant family
  (beyond the sched toy class) is added with zero substrate edits;
  advertise/run/recover/change all pass through the pinned contract;
  a mid-task version upgrade (v1→v2) completes with old pins
  still reproducible; contract delta filed for any §7 change.
- M3 Persistent organization. ACCEPT iff: channels + relationship
  evidence + custody persist across close/reopen (byte-verified
  inventories before/after); an exported composite executes
  UNMODIFIED on fresh state in a second task (VALID + lineage_ok);
  kill-during-persist converges via a supported repair path.
- M4 Experience loop. ACCEPT iff: a proposed recipe is assessed
  (mechanical predicates + independent check), retained with
  lineage + measured cost, and reused on a second task with
  cost-vs-from-scratch REPORTED (superiority unclaimed unless
  preregistered); D-005 signal classes kept distinct in every
  record; no discovery/invention verbiage in any verdict.

## §3. Execution order + rationale

M1 → M2 → M3 → M4. Rationale: usability first (it disciplines every
later interface), then participants (they need the stable journey),
then persistence (it needs real participants to persist), then the
loop (it needs retained behavior worth reusing). Each milestone is
independently shippable; later milestones must not weaken earlier
acceptance (regression suites carried).

## §4. Dependencies / ownership

- SST leg: re-carry requires the qualified snapshot path (M2
  participant candidate); no live-HEAD or venv-smuggling.
- STC execution: NOT in mandate (needs Ask 2B + a full-replay
  budgeting decision); experimental adapter stays unqualified-only
  per STC-CONSUMER-BOUNDARY.md.
- Q5 host: open, non-blocking; mandate is host-agnostic.
- Owner asks (Ask 1/2B): pursued in parallel; mandate never waits
  on them.

## §5. Beyond the finish line (explicit, retained)

Local policy invention; learned mappings/revisions; autonomous
adaptation discovery; recipe inheritance (descendant advantage);
cross-host / multi-writer / disk-loss; STC execution integration;
permanent host selection; HW/SW co-design and all V16/V18
machinery. Each needs its own mandate + discriminating protocol
before any claim. The ADAPT-EXPERIMENT-DESIGN (rev 2) covers
supplied-revision execution only and authorizes no runs by itself.

## §6. Decision requested

Approve / amend / reject this mandate scope + §2 criteria. On
approval, the coordinator proceeds M1→M4 with brief milestone
reports and escalates only consequential semantics, architecture,
or cost changes.
