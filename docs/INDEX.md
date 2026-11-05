# Docs index

Everything in `docs/`, grouped by what you are probably looking for, one line per document. The project site is built from `docs/*.html`; those pages are generated from `docs/source/` by `python3 tools/site.py build` and should not be edited by hand. The same list is on the [Docs index page](https://anshul48.github.io/anima-substrate/docs.html).

## Start here

Read these first, in this order.

- [Status](https://anshul48.github.io/anima-substrate/status.html): What is built, what is a prototype and what is only planned.
- [Install](https://anshul48.github.io/anima-substrate/install.html): What the one-line install puts on your machine today and what it does not.
- [Replay the nine-job run](https://anshul48.github.io/anima-substrate/demo/): The recorded run in your browser, with the record check.
- [Use ANIMA with your coding agent](HARNESSES.md): How ANIMA sits next to Muse Code, Claude Code or Codex.
- [The state tree screen, text mode and voice](UI.md): The one screen, the same tree as text, and the voice command.

## Receipts and reproduction

Everything here can be checked by running a command.

- [Recorded run, nine jobs](evidence/flagship-run3/README.md): Log, decision chain, checker output and the chain checker.
- [Earlier recorded run](evidence/flagship-run2/README.md): Kept for the record; nine jobs, no escalation.
- [One small recorded TRACE test](evidence/trace-card-100m/README.md): A hidden checker accepted a small set of questions over the full test library.
- [Reproduce everything](REPRODUCE-ALL.md): Offline steps for Linux and WSL, with what each one needs.
- [The integrated demo](INTEGRATED-DEMO.md): What is tested end to end today, with the record for each line.
- [ANIMA memory on TRACE](MEMORY.md): How finished jobs are written down and recalled for the next job.

## Design and architecture

How the parts are meant to fit. Planned parts are marked in the documents.

- [Roles and rules](ROLES-AND-RULES.md): Architect, manager and worker, and the rules a program would enforce.
- [Roadmap](ROADMAP.md): A gap map of what is not done.
- [Architecture of the package](ARCHITECTURE.md): Persistent project worlds and a crash-safe local host.
- [Contracts](CONTRACTS.md): The pinned contracts the package tests enforce.
- [Technical report](TECHNICAL-REPORT.md): What the package measured and what it only proposes.

## The earlier package in src/

The small offline engine that was the first front page. Kept as it was.

- [Earlier front page](README-technical.md): The toolkit in src/, written for researchers.
- [Consumer guide](CONSUMER.md): How to use the package as a library.
- [Reviewer entry point](REVIEW.md): A ten-minute path for a reviewer.
- [Recovery](RECOVERY.md): Interruption boundaries and recovery procedures.
- [SST staging](SST-STAGING.md): Staging a checkout of an older project that shares the abbreviation SST. It is not the state tree screen.
- [Release notes 0.1.0](RELEASE-NOTES-0.1.0.md): First package release.
- [Release notes 0.1.1](RELEASE-NOTES-0.1.1.md): Second package release.
- [Examples](examples/quickstart.py): A short quickstart script and an external-participant example.

## Research notes

Proposals written during design. They record direction and open questions, not measurements.

- [Substrate direction](SUBSTRATE-DIRECTION.md): Where the substrate idea was heading.
- [World boundaries](WORLD-BOUNDARIES.md): How project worlds are separated.
- [Memory tiers and graph retirement](MEMORY-TIERS-AND-GRAPH-RETIREMENT.md): Proposal for tiers of memory.
- [Personal model and proactive collaboration](PERSONAL-MODEL-AND-PROACTIVE-COLLABORATION.md): Proposal; nothing here is built.
- [Hardware and research acceleration](HARDWARE-AND-RESEARCH-ACCELERATION.md): Notes on hardware options.
- [Architecture channel handoff](ANIMA-ARCHITECTURE-CHANNEL-HANDOFF-2026-10-10.md): A dated handoff note.
- [Pending review, B1 and B2](PENDING-B1-B2-REVIEW-2026-10-05.md): A dated review note.
- [Research archive](RESEARCH-ARCHIVE.md): Index of older research material.

## Project and site

For people changing the repository or the pages.

- [Changelog](CHANGELOG.md): Notable changes to the package.
- [Cite it](CITATION.cff): Citation metadata.
- [Builder log, canonical record, provenance](records/CANONICAL-RECORD.md): Records of how the project was built.
- [Maintainer context](maintainer/ANIMA-CONTEXT.md): Orientation notes for maintainers.
- [status.json](status.json): The one source for every badge on the site.
- [videos.json](videos.json): The list of films the Demos page shows.
- [Changing the site](../.github/CONTRIBUTING.md): Rebuild and check the pages with tools/site.py.
