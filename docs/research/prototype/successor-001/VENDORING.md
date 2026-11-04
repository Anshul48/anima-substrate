# Vendoring note: minihost.py

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
