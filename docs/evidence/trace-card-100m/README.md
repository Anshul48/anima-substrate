# TRACE card at 100M tokens — evidence (2026-11-04)

What this is: the recorded TRACE card, rebuilt on the 100M-token store, with the same gate-and-harness structure as the 20k card. Retrieval was done by the TRACE query service on the VM (127.0.0.1:8495); a Muse hand on the VM wrote the card text from retrieval.json; a deterministic gate decided; the ANIMA architect (Claude) designed the task and checked it.

## Roles (who did what)
- Retrieval: TRACE sealed 100M engine through the thin query service (FEDERATED-4: four shards merged; not global-exact).
- Card text: subject hand (Muse, VM), run id `t100m-20261104T074333Z-5881`, 42 harness requests.
- Decision: deterministic gate `gate/gate_trace100m_card.py` (sha256 a1124cdf1748ff6465c309563e28c66d3667aa87284555a16c9b72197a7bafe3), harness pinned at 2c28c2ac3b83409e345e26df1e4abaa5370aac19bc3f89893c2f9a94642a8371 (`gate/gate.pins`).
- Architect: designed the task, ran hostile mutants, re-ran the gate live, recorded the chain.

## Result
- Gate: PASS, 23 rules, 0 failed, both modes — `gate-replay.txt` (offline from responses.jsonl) and `gate-live.txt` (re-queried the live service on the VM at 2026-11-04T07:52:27Z; R2live retrieval == live re-query).
- Store: 99,891,846 tokens / 812,545 units / 4 shards.
- Source found, guided: 15/20 (handoff 10/10, s8 5/10). Flat exact control: 15/20 (same split). So guided == flat on this store; the card does NOT claim TRACE beats flat.
- Recall@10 vs the f64 ground truth: mean 1.0 on 10 s8 probes x 4 shards (quoted from the service eval; receipt 0.9975/0.9975/0.999/0.9975).
- Model-token cost: not measured. Keyword baseline on 100M: UNVERIFIED (not run).

## Gate hardening (round 2)
Round 1 let four of my twelve hostile mutants through (A "outperforming", C "globally exact", H zero-width space in "global-exact", K "state of the art" in prose). Round 2 (builder hand, VM) normalises text before the lint, adds a comparative-claim rule and a hidden-character rule. My re-run: `my12-mutants-fixed-gate.txt` — 11 of 12 now fail on the intended rule; mutant I (non-breaking hyphen inside the label FEDERATED-4) still passes by design, because the label text is intact after normalisation. Mutant L (a key-shaped test string) is not stored here; it failed rule R5f3 as intended. The builder's own 22-mutant table and receipts are in its workspace (anima-trace100m-gate-fix).

## Chain
`chain.jsonl`: 9 projlog events (card.created, hand.assigned, harness.pinned, retrieval.recorded, hand.done, gate.run, decision.needed, decision.made accept, task.done). `python3 -I tools/record_chain.py --verify --log chain.jsonl` prints `chain ok 9`. HONEST NOTE: I recorded this chain from the run artifacts after the fact; the dispatcher did not emit it live.

## Limits and UNVERIFIED
- FEDERATED-4: answers merge four shard results; not a global-exact index.
- Two-level parents-to-atoms store; path leaf is null.
- Source-ordinal on s8 is 5/10 for both guided and flat (prefix-query property).
- Tailnet remote access to the service: not verified.
- 20 questions (10 handoff, 10 s8); small sample; no confidence interval claimed.
- The 100M number is a TRACE store size, not an ANIMA scale claim.
