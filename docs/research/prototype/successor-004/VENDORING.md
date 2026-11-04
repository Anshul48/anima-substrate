# Vendoring note: minihost.py (successor-004 extends the vendored host)

Successor-002 note: `minihost.py` remains the byte-identical vendored
host (sha `d01049a93b0e068e9e0384379cb26f509726f6a7ee659ff71dd0f0ec7bd4b206`,
still pinned by `test_14_no_frozen_imports_vendor_pinned`). Zero lines
changed since successor-001 (see PROVENANCE.md).

Successor-003 note: the R1 fork EXTENDS the vendored host
(`check_settleable`, settle pre-validation, test-only crash hooks;
new pin `a2b7ed5925b5a2bb9fedfc81d7ab7ae14bb0bdccd896fc9d95d3aa182ead05d3`
— base pin above is the before record). Imports remain stdlib-only
(asserted); clean-path ledger bytes unchanged (demo EVIDENCE
structurally identical to r1). The base bytes are NOT vendored
elsewhere: successor-002 keeps the original pin intact.

Successor-004 note: R3 extends the fork again (`atomic_write_text`
+ the two write-interior crash hooks + classified refusal on an
unreadable checkpoint; new pin
`8551ed92346d55a1624cfca815ce3cce7c43acdf3bcc190fadf2096c233d5757`
— R1 pin above is the before record). Imports remain stdlib-only
(asserted by the same test); clean-path bytes unchanged (demo
EVIDENCE structurally identical to r2 — see EVIDENCE.md).

`successor-001/minihost.py` is a byte-identical vendor copy of
`prototype/reuse-demo-001/minihost.py`:

- sha256 (both files): `d01049a93b0e068e9e0384379cb26f509726f6a7ee659ff71dd0f0ec7bd4b206`
- Copied with `cp` (no edits); verified with `sha256sum` after copy.
- Delta: NONE. Zero lines changed, zero lines added.

Why vendoring instead of importing: the frozen directories are never
imported at runtime (asserted by `test_14_no_frozen_imports_vendor_pinned`,
which pins the sha above and scans every successor-001 module for frozen-dir
references and non-stdlib imports of the vendored host). This follows the
X3 precedent (byte-copy with pinned sha in FREEZE.json).

What the vendored host provides toward WORLD-CONTRACT-v1: C1 (invoke
success/error split, consume-on-success-only), C4 (worlds mapping with
`.lifecycle` strings), C5 (`deny`/`suspend`/`reattach` shapes), C7
(checkpoint schema + identity rule, grant_settle + unsettled-terminal
replay check, host_reopen, descriptor re-supply + fail-closed
withholding). C2/C3/C6 are pipeline-side conventions implemented by
`resume.py` + `pipeline.py` (`SchedWorld` artifact shapes, args keys,
result schemas, file-name conventions) and asserted by tests 01–05.
