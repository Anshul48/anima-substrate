# Docs index

Everything in `docs/`, grouped by what you are probably looking for. The project site is built from `docs/*.html`; those pages are generated from `docs/source/` by `tools/site.py` and should not be edited by hand. The same list is on the [Docs index page](https://anshul48.github.io/anima-substrate/docs.html).

## Receipts

- [Recorded run: nine jobs](evidence/flagship-run3/README.md): log, 69-record decision chain, checker output, and the chain checker. To check it yourself, run `python3 docs/evidence/flagship-run3/check_chain.py --tamper`.
- [Earlier run](evidence/flagship-run2/README.md): kept for the record (nine jobs, no escalation).
- [TRACE card, 100M test library](evidence/trace-card-100m/README.md): one small recorded TRACE test, 20 questions over the full test library, accepted by a hidden checker with 23 rules.
- [Evidence page](https://anshul48.github.io/anima-substrate/evidence.html): the same records, on the site.

## Reproduce

- [REPRODUCE-ALL.md](REPRODUCE-ALL.md): reproduce everything, on Linux or WSL, offline.
- [REVIEW.md](REVIEW.md): ten-minute reviewer entry point.
- [Verify page](https://anshul48.github.io/anima-substrate/verify.html): what each check proves, and what it does not.
- [HARNESSES.md](HARNESSES.md): use ANIMA with the coding agent you already have.
- [RECOVERY.md](RECOVERY.md): interruption boundaries and recovery procedures.

## Architecture

- [ROLES-AND-RULES.md](ROLES-AND-RULES.md): roles (architect, manager, worker) and the rules a program enforces; design, with what exists today marked.
- [ARCHITECTURE.md](ARCHITECTURE.md): the `anima-substrate` Python package: persistent project worlds and a crash-safe local host.
- [CONTRACTS.md](CONTRACTS.md): the pinned contracts the package tests enforce.
- [MEMORY.md](MEMORY.md): ANIMA memory on TRACE, a prototype link. See also the [memory page](https://anshul48.github.io/anima-substrate/memory.html) and the [TRACE repository](https://github.com/Anshul48/trace).
- [UI.md](UI.md): the state space tree screen, text mode, and voice.
- [TECHNICAL-REPORT.md](TECHNICAL-REPORT.md): citable guide to what the package measured and what it only proposes.
- [INTEGRATED-DEMO.md](INTEGRATED-DEMO.md): the one end-to-end run, what is tested today, with the record for each line.

### The earlier engine

The small offline engine in `src/` is the repository's earlier front page and is kept as it was.

- [README-technical.md](README-technical.md): the earlier front page.
- [CONSUMER.md](CONSUMER.md): consumer guide.
- [SST-STAGING.md](SST-STAGING.md): how the package stages a caller-provided checkout of an older search project that shares the abbreviation SST. It is not the State Space Tree screen described on the site.
- [RELEASE-NOTES-0.1.0.md](RELEASE-NOTES-0.1.0.md), [RELEASE-NOTES-0.1.1.md](RELEASE-NOTES-0.1.1.md): release notes.

## Research notes

Proposals, not results. Written during the programme's design phase; they record direction and open questions.

- [ROADMAP.md](ROADMAP.md): gap map of what is not done.
- [SUBSTRATE-DIRECTION.md](SUBSTRATE-DIRECTION.md)
- [WORLD-BOUNDARIES.md](WORLD-BOUNDARIES.md)
- [MEMORY-TIERS-AND-GRAPH-RETIREMENT.md](MEMORY-TIERS-AND-GRAPH-RETIREMENT.md)
- [PERSONAL-MODEL-AND-PROACTIVE-COLLABORATION.md](PERSONAL-MODEL-AND-PROACTIVE-COLLABORATION.md)
- [HARDWARE-AND-RESEARCH-ACCELERATION.md](HARDWARE-AND-RESEARCH-ACCELERATION.md)
- [ANIMA-ARCHITECTURE-CHANNEL-HANDOFF-2026-10-10.md](ANIMA-ARCHITECTURE-CHANNEL-HANDOFF-2026-10-10.md)
- [PENDING-B1-B2-REVIEW-2026-10-05.md](PENDING-B1-B2-REVIEW-2026-10-05.md)
- [RESEARCH-ARCHIVE.md](RESEARCH-ARCHIVE.md)

## Status

- [`status.json`](status.json): the one source for what is built and what is not.
- [Status page](https://anshul48.github.io/anima-substrate/status.html): the same record, on the site.
- [CHANGELOG.md](CHANGELOG.md): what changed.

## Contribute

- [CONTRIBUTING.md](../.github/CONTRIBUTING.md), section ["Changing the site"](../.github/CONTRIBUTING.md#changing-the-site): rebuild or change the site.

| Site source path | What it is |
|---|---|
| `docs/status.json` | Feature states. The only place a badge is decided |
| `docs/videos.json` | The list of films the Demos page shows; swap a film with one edit |
| `docs/source/` | Page templates, partials and the layout |
| `tools/site.py` | `build` (render pages), `sync-readme` (update the README tables), `check` (fail on stale pages, banned phrases, broken links, missing alt text, size, contrast) |
| `docs/assets/tokens.css` | Shared design tokens, the same file the TRACE site uses |

## Demos and films

- [Recorded demo](demo/index.html): check the record in a browser (open the file, or use the [Pages site](https://anshul48.github.io/anima-substrate/demo/)). Recorded replay.
- [Demos page](https://anshul48.github.io/anima-substrate/demos.html): the films.
- [`ui-preview/`](ui-preview/index.html): the dashboard screens. UI preview.
