# INTEGRATED-DEMO

The one checkable end-to-end run of ANIMA. This file says what is tested,
where the records are, and what is planned. The integrator's final text
(the exact commands a stranger runs, what each prints, and what each needs)
lands in "What the integrator delivers" below.

## What the integrator delivers

- `READY/anima-build/integrate/RUN-LOG.md`: every command, its output and its
  exit code, from a fresh clone.
- `READY/anima-build/integrate/patches/`: the merged worker commits.
- `READY/anima-build/integrate/CHANGES.md`: what the merge changed.
- This file, filled in: the exact commands a stranger runs, what each prints,
  and what each needs.

## What is tested today (each line names its record)

- One-line install from a `file://` remote, twice, and `anima init` finding
  the CLIs with Muse Code first: PASS.
  Record: `READY/anima-build/harness/RUN-LOG.md`, sections A, A2, A3, B.
- `anima doctor` and `anima doctor --live`: muse PASS, claude PASS,
  codex2 PASS; primary codex NOT RUN (its login is expired).
  Record: `READY/anima-build/harness/RUN-LOG.md`, sections C, D, N.
- One small bug task (`tiny-bug`) against hidden tests: muse PASS,
  claude PASS, codex2 PASS.
  Record: `READY/anima-build/harness/RUN-LOG.md`, section F.
- Plan-first (claude plans, muse edits): PASS.
  Record: `READY/anima-build/harness/RUN-LOG.md`, section H.
- Escalation (rung 0 helper fails on purpose, rung 1 passes): PASS, marked
  CUSTOM on every record.
  Record: `READY/anima-build/harness/RUN-LOG.md`, sections I, I3.
- Process watch stopping a forbidden push in a Muse run: PASS in enforce mode.
  Record: `READY/anima-build/harness/RUN-LOG.md`, section J2.
- The real one-line address (`curl ... | sh` from GitHub): NOT RUN. The
  address exists only after the project's first push.
- Memory plug-in, state-tree screen, voice control: planned. The memory
  worker's store/recall commands and the integrator's merged run have no
  PASS record yet. Their pages stay marked **Planned** until they do.

## What flips at integrate

When the merged tree is re-run from a fresh clone and its RUN-LOG says PASS,
one edit to `docs/status.json` flips each part, then
`python3 tools/site.py build` redraws every badge, table and planned command.
Nothing on the site is flipped by hand.
