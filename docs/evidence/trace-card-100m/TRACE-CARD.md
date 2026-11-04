question: wikipedia/Louise_Hopkins # Louise Hopkins Louise Hopkins (born 1965) is a British contemporary artist and painter who lives and works in Glasgow, Scotland. == B
trace-source: FEDERATED-4 doc wikipedia:004a39dde9deafe0 "wikipedia/Louise_Hopkins" rank 1
scope: 99,891,846 tokens / 812,545 units / 4 shards via the thin query service; FEDERATED-4 merged answers; the 20k pilot is the comparison point, not equal evidence
trace-found: FEDERATED-4 guided source found 15/20 (handoff 10/10, s8 5/10)
trace-recall: guided-vs-f64 recall@10 mean 1.0 on 10 s8 probes x4 shards (quoted from service eval_recall.json); receipt 0.9975/0.9975/0.999/0.9975
baseline-flat: flat-exact control found 15/20 (handoff 10/10, s8 5/10); merged guided-vs-flat overlap@10 mean 1.0 on 20
baseline-keyword: keyword baseline UNVERIFIED (not run on this 100M store via the thin service; flat mode is the in-service control)
cost: model tokens spent by the hand: not measured
limits: two-level parents-to-atoms store; path leaf null; source-ordinal counts as measured: guided 15/20, flat 15/20 (s8: guided 5/10, flat 5/10); tailnet remote access not verified
models: TRACE sealed 100M engine did retrieval via the thin service (FEDERATED-4); subject hand wrote this card from retrieval.json; deterministic gate decided; architect lane designed the task
decision: accept guided matched the flat control at 15/20 with overlap 1.0 on the 100M store
evidence: retrieval.json
run: t100m-20261104T074333Z-5881 2026-11-04T07:43:33Z
