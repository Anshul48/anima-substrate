# Docs index

Everything in `docs/`, by what you are probably looking for. The project site is built from `docs/*.html`; those pages are generated from `site/` by `tools/site.py` and should not be edited by hand.

## Start here

| I want to | Go to |
|---|---|
| See what is built and what is not | [`status.json`](status.json) (the one source), or the [Status page](https://anshul48.github.io/anima-substrate/status.html) |
| Check the recorded nine-job run myself | [Recorded run: nine jobs](evidence/flagship-run3/README.md), then `python3 docs/evidence/flagship-run3/check_chain.py --tamper` |
| Check the record in a browser | [`demo/`](demo/index.html) (open the file, or use the Pages site) |
| Understand roles and enforced rules | [ROLES-AND-RULES.md](ROLES-AND-RULES.md) |
| Read about the memory (TRACE) | [TRACE repository](https://github.com/Anshul48/trace) and the [memory page](https://anshul48.github.io/anima-substrate/memory.html) |
| See the one end-to-end run | [INTEGRATED-DEMO.md](INTEGRATED-DEMO.md): what is tested today, with the record for each line |
| Rebuild or change the site | [CONTRIBUTING.md](../.github/CONTRIBUTING.md), section "Changing the site" |

## Evidence

| Document | What it is |
|---|---|
| [evidence/flagship-run3/](evidence/flagship-run3/README.md) | The recorded nine-job run: log, 69-record decision chain, checker output, and the chain checker |
| [evidence/flagship-run2/](evidence/flagship-run2/README.md) | The earlier run, kept for the record (nine jobs, no escalation) |
| [evidence/trace-card-100m/](evidence/trace-card-100m/README.md) | One small recorded TRACE test: 20 questions over the full test library, accepted by a hidden checker with 23 rules |

## Design and roadmap

| Document | What it is |
|---|---|
| [ROLES-AND-RULES.md](ROLES-AND-RULES.md) | Roles (architect, manager, worker) and the rules a program enforces; design, with what exists today marked |
| [ROADMAP.md](ROADMAP.md) | Gap map of what is not done |
| [ARCHITECTURE.md](ARCHITECTURE.md) | The `anima-substrate` Python package: persistent project worlds and a crash-safe local host |
| [CONTRACTS.md](CONTRACTS.md) | The pinned contracts the package tests enforce |
| [TECHNICAL-REPORT.md](TECHNICAL-REPORT.md) | Citable guide to what the package measured and what it only proposes |

## The `anima-substrate` package (the earlier engine)

The small offline engine in `src/`. It is the repository's earlier front page and is kept as it was.

| Document | What it is |
|---|---|
| [README-technical.md](README-technical.md) | The earlier front page |
| [CONSUMER.md](CONSUMER.md) | Consumer guide |
| [REVIEW.md](REVIEW.md) | Ten-minute reviewer entry point |
| [RECOVERY.md](RECOVERY.md) | Interruption boundaries and recovery procedures |
| [SST-STAGING.md](SST-STAGING.md) | How the package stages a caller-provided checkout of an older search project that shares the abbreviation SST. It is not the State Space Tree screen described on the site |
| [RELEASE-NOTES-0.1.0.md](RELEASE-NOTES-0.1.0.md), [RELEASE-NOTES-0.1.1.md](RELEASE-NOTES-0.1.1.md) | Release notes |

## Research notes (proposals, not results)

Written during the programme's design phase. They record direction and open questions; they are not measurements.

[SUBSTRATE-DIRECTION.md](SUBSTRATE-DIRECTION.md), [WORLD-BOUNDARIES.md](WORLD-BOUNDARIES.md), [MEMORY-TIERS-AND-GRAPH-RETIREMENT.md](MEMORY-TIERS-AND-GRAPH-RETIREMENT.md), [PERSONAL-MODEL-AND-PROACTIVE-COLLABORATION.md](PERSONAL-MODEL-AND-PROACTIVE-COLLABORATION.md), [HARDWARE-AND-RESEARCH-ACCELERATION.md](HARDWARE-AND-RESEARCH-ACCELERATION.md), [ANIMA-ARCHITECTURE-CHANNEL-HANDOFF-2026-10-10.md](ANIMA-ARCHITECTURE-CHANNEL-HANDOFF-2026-10-10.md), [PENDING-B1-B2-REVIEW-2026-10-05.md](PENDING-B1-B2-REVIEW-2026-10-05.md), [RESEARCH-ARCHIVE.md](RESEARCH-ARCHIVE.md).

## Site source (for people changing the pages)

| Path | What it is |
|---|---|
| `docs/status.json` | Feature states. The only place a badge is decided |
| `docs/videos.json` | The list of films the Demos page shows; swap a film with one edit |
| `site/` | Page templates, partials and the layout |
| `tools/site.py` | `build` (render pages), `sync-readme` (update the README tables), `check` (fail on stale pages, banned phrases, broken links, missing alt text, size, contrast) |
| `docs/assets/tokens.css` | Shared design tokens, the same file the TRACE site uses |
