"""P1 STC adapter: pinned release-doc reader + qualification gate (stdlib-only).

STC exposes NO substrate-facing runtime envelope (survey 2026-10-04:
STC's contracts target its own DSH/SST consumption). This adapter
therefore consumes ONLY vendored copies of STC release documents
(see VENDORING.md) and answers one question: does the pinned STC
material satisfy 'qualified for substrate consumption'?

Two gates:
  1. verify_doc_copy(copy_dir): every vendored doc must hash-match
     PINS.json (HEAD bytes, not the dirty worktree). Parses
     EXTERNAL_PINS out of the vendored lease_git.py via `ast`
     (read + parse only; the module is never imported or executed).
     ANY drift -> PinMismatch.
  2. qualification_report(copy_dir, owner_release=None): evaluates the
     four qualification criteria (frozen identity, owner statement,
     envelope stability, test evidence). With no owner-minted release
     (current state) the verdict is always UNQUALIFIED with an explicit
     gap list. The `owner_release` parameter is the FUTURE gate: a
     parsed OWNER-RELEASE.json (see PRODUCER-ASK.md) that flips the
     verdict only when every field validates.

Both gates are exact-match; there is no warn-and-proceed.
"""
from __future__ import annotations

import ast
import hashlib
import sys
from pathlib import Path
from typing import Any

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

from pins import DEFAULT_PINS, PinMismatch, load_pins, require_equal  # noqa: E402

__all__ = [
    "PinMismatch",
    "DocViolation",
    "verify_doc_copy",
    "parse_external_pins",
    "qualification_report",
    "QUALIFICATION_CRITERIA",
]

# Vendored filename -> PINS.json key holding its pinned sha256.
PINNED_DOCS = {
    "STC-LIVE-READINESS-PACKET.md": "readiness_packet_sha256",
    "STC-DSH-RELEASE.md": "release_doc_sha256",
    "STC-DSH-RECORD.md": "release_record_sha256",
    "STC-SST-CALLER-CONTRACT.md": "caller_contract_head_sha256",
    "DSH_PIN": "dsh_pin_sha256",
    "lease_git.py": "lease_git_head_sha256",
}

QUALIFICATION_CRITERIA = (
    "frozen_identity",
    "owner_statement",
    "envelope_stability",
    "test_evidence",
)


class DocViolation(Exception):
    """Vendored STC doc fails to parse as the expected shape."""


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def parse_external_pins(lease_git_source: str) -> dict[str, str]:
    """Extract EXTERNAL_PINS from lease_git.py source via ast (no exec)."""
    try:
        tree = ast.parse(lease_git_source)
    except SyntaxError as exc:
        raise DocViolation(f"vendored lease_git.py does not parse: {exc}")
    for node in ast.walk(tree):
        if (
            isinstance(node, ast.AnnAssign)
            and isinstance(node.target, ast.Name)
            and node.target.id == "EXTERNAL_PINS"
            and node.value is not None
        ):
            try:
                pins = ast.literal_eval(node.value)
            except ValueError as exc:
                raise DocViolation(
                    f"EXTERNAL_PINS is not a literal dict: {exc}"
                )
            if not isinstance(pins, dict) or not all(
                isinstance(k, str) and isinstance(v, str)
                for k, v in pins.items()
            ):
                raise DocViolation("EXTERNAL_PINS is not a str->str dict")
            return dict(pins)
    raise DocViolation("EXTERNAL_PINS assignment not found in lease_git.py")


def verify_doc_copy(
    copy_dir: Path | str,
    pins_path: Path = DEFAULT_PINS,
) -> dict[str, Any]:
    """Verify a vendored STC doc copy against PINS.json. Returns evidence."""
    copy_dir = Path(copy_dir)
    pins = load_pins(pins_path)["stc"]
    for filename, pin_key in PINNED_DOCS.items():
        path = copy_dir / filename
        if not path.is_file():
            raise PinMismatch(f"vendored STC doc missing: {filename}")
        require_equal(f"stc doc {filename}", _sha256(path), pins[pin_key])
    external = parse_external_pins((copy_dir / "lease_git.py").read_text())
    if external != pins["external_pins_at_head"]:
        raise PinMismatch(
            f"EXTERNAL_PINS drift: vendored {external!r} != pinned "
            f"{pins['external_pins_at_head']!r}"
        )
    return {
        "copy_dir": str(copy_dir),
        "docs_verified": sorted(PINNED_DOCS),
        "head_commit": pins["head_commit"],
        "external_pins": external,
        "verdict": "MATCH",
    }


def qualification_report(
    copy_dir: Path | str,
    owner_release: dict[str, Any] | None = None,
    pins_path: Path = DEFAULT_PINS,
) -> dict[str, Any]:
    """Evaluate 'qualified for substrate consumption' for pinned STC docs.

    `owner_release` is a parsed OWNER-RELEASE.json (the producer ask).
    Required shape when present:
      {"tag": str, "commit": 40-hex, "statement_sha256": hex,
       "envelope": {"name": str, "keys": [str...], "frozen": true},
       "tests": {"command": str, "passed": int, "failed": 0}}
    """
    evidence = verify_doc_copy(copy_dir, pins_path)
    gaps: dict[str, str] = {}
    if owner_release is None:
        gaps = {
            "frozen_identity": "no owner-minted tag/release commit; HEAD "
            "8fa8ac3 is a docs packet, worktree dirty (28 porcelain lines)",
            "owner_statement": "no owner statement naming a substrate-"
            "consumable version (readiness packet gates STC's own spend)",
            "envelope_stability": "no STC surface targets substrate "
            "consumption; no frozen envelope exists to pin",
            "test_evidence": "no owner-attested gate record bound to a "
            "frozen identity for substrate use",
        }
        return {
            **evidence,
            "criteria": {c: "GAP" for c in QUALIFICATION_CRITERIA},
            "gaps": gaps,
            "qualified": False,
            "verdict": "UNQUALIFIED",
        }
    criteria: dict[str, str] = {}
    if not isinstance(owner_release.get("tag"), str) or not owner_release["tag"]:
        gaps["frozen_identity"] = "owner_release.tag missing/empty"
    if not isinstance(owner_release.get("commit"), str) or len(
        owner_release.get("commit", "")
    ) != 40:
        gaps.setdefault(
            "frozen_identity", "owner_release.commit is not a 40-hex id"
        )
    if not isinstance(owner_release.get("statement_sha256"), str):
        gaps["owner_statement"] = "owner_release.statement_sha256 missing"
    env = owner_release.get("envelope")
    if (
        not isinstance(env, dict)
        or not isinstance(env.get("keys"), list)
        or env.get("frozen") is not True
    ):
        gaps["envelope_stability"] = (
            "owner_release.envelope must be {name, keys[], frozen:true}"
        )
    tests = owner_release.get("tests")
    if (
        not isinstance(tests, dict)
        or tests.get("failed") != 0
        or not isinstance(tests.get("passed"), int)
    ):
        gaps["test_evidence"] = (
            "owner_release.tests must be {command, passed:int, failed:0}"
        )
    for criterion in QUALIFICATION_CRITERIA:
        criteria[criterion] = "GAP" if criterion in gaps else "SATISFIED"
    qualified = not gaps
    return {
        **evidence,
        "criteria": criteria,
        "gaps": gaps,
        "qualified": qualified,
        "verdict": "QUALIFIED" if qualified else "UNQUALIFIED",
    }
