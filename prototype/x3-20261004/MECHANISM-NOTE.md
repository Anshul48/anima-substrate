# Mechanism investigation note (2026-10-04, pre-X3)

Question: should X3 build on DSH extension, a Cordis seam, a distinct
host, or the Python pilot lineage?

Inspected (read-only): DSH pin 639ed01 tree (`/tmp/dsh-upstream`:
~45 packages incl. session, workflow, subagent, storage, jobs;
Cordis vendored at `vendor/cordis`, docs at `docs/cordis-*`);
STC `stc-bundle` loader (`stc/dsh-plugin-stc/src/index.ts:19`, composes
hello/tools/run/policy as Cordis fibers); STC mechanical `substrate/`
package (runner + receipt only — naming boundary preserved).

Assessment:

- DSH/Cordis supply composition, contexts, dependency resolution, typed
  events, effect lifecycle. They do NOT supply ledger-shaped crash
  recovery, grant conservation, custody transfer, or settle semantics.
  Adopting them as the substrate host would mean IMPLEMENTING world/host
  semantics as TS Cordis services — a port + migration, not a seam reuse.
- Cost asymmetry: a DSH/Cordis build pays migration + cross-language
  adapter costs with zero evidence it changes any X1/X2/X1H outcome,
  since those outcomes turned on orchestration topology, not runtime.
- Reversibility: staying in the Python pilot lineage for X3 keeps the
  experiment a reversible probe. A Cordis-seam pilot stays a candidate
  for later, AFTER X3 shows which mechanism actually matters.

Decision (PROPOSAL, coordinator-owned, reversible): run X3 in the
Python lineage with the retained recovery machinery held constant
across arms. Revisit DSH/Cordis/distinct-host only with X3 evidence
in hand. No migration, no semantic commitment.
