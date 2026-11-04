"""P1 adapter self-test (stdlib-only, offline, $0).

Validates the scaffold against the CURRENT pins. Reads producer trees
(copy + hash + parse only); NEVER executes producer code, NEVER runs
producer test suites, NEVER writes to producer tracks.

Run from the substrate repo root:
    python3 prototype/programme-20261004/P1-adapters/selftest.py

Exit 0: all checks PASS. Exit 1: any FAIL (loud, named).
"""
from __future__ import annotations

import ast
import json
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

import pins as pins_mod  # noqa: E402
import sst_adapter  # noqa: E402
import stc_adapter  # noqa: E402

REPO = HERE.parents[2]  # .../substrate
R1_MANIFEST = (
    REPO / "prototype" / "successor-002" / "vendor" / "SNAPSHOT-MANIFEST.json"
)

PASS: list[str] = []
FAIL: list[str] = []


def check(name: str, fn) -> None:
    try:
        fn()
    except Exception as exc:  # noqa: BLE001 — self-test reports, not raises
        FAIL.append(f"{name}: {type(exc).__name__}: {exc}")
    else:
        PASS.append(name)


def expect_raise(name: str, exc_types, fn) -> None:
    try:
        fn()
    except exc_types as exc:
        PASS.append(f"{name} (raised {type(exc).__name__})")
    except Exception as exc:  # noqa: BLE001
        FAIL.append(f"{name}: wrong exception {type(exc).__name__}: {exc}")
    else:
        FAIL.append(f"{name}: expected {exc_types} but nothing raised")


def fresh_tmp() -> Path:
    return Path(tempfile.mkdtemp(prefix="p1-selftest-"))


# --- 1. vendor a fresh SST copy per VENDORING.md, verify MATCH ----------

def t_sst_fresh_vendor_match() -> None:
    tmp = fresh_tmp()
    src = REPO.parent / "sst" / "src"  # sibling read (copy FROM only)
    dst = tmp / "sst-copy"
    shutil.copytree(src, dst, ignore=shutil.ignore_patterns("__pycache__"))
    ev = sst_adapter.verify_snapshot_copy(dst)
    assert ev["verdict"] == "MATCH", ev
    assert ev["snapshot_hash"] == pins_mod.load_pins()["sst"]["snapshot_hash"]
    assert ev["file_count"] == 54, ev


def t_sst_matches_frozen_r1_manifest() -> None:
    """Independent oracle: fresh copy entries == frozen r1 manifest bytes."""
    tmp = fresh_tmp()
    src = REPO.parent / "sst" / "src"
    dst = tmp / "sst-copy"
    shutil.copytree(src, dst, ignore=shutil.ignore_patterns("__pycache__"))
    live = sst_adapter.file_entries(dst)
    frozen = json.loads(R1_MANIFEST.read_text(encoding="utf-8"))
    assert frozen["snapshot_hash"] == sst_adapter.snapshot_hash(live)
    assert frozen["files"] == [
        {"relpath": e["relpath"], "sha256": e["sha256"]} for e in live
    ]


def t_sst_tamper_refused() -> None:
    tmp = fresh_tmp()
    src = REPO.parent / "sst" / "src"
    dst = tmp / "sst-copy"
    shutil.copytree(src, dst, ignore=shutil.ignore_patterns("__pycache__"))
    target = dst / "sst" / "core" / "contracts.py"
    target.write_bytes(target.read_bytes() + b"# tamper\n")

    def run() -> None:
        sst_adapter.verify_snapshot_copy(dst)

    expect_raise("sst tampered copy refused", pins_mod.PinMismatch, run)


def t_sst_wrong_pin_refused() -> None:
    tmp = fresh_tmp()
    src = REPO.parent / "sst" / "src"
    dst = tmp / "sst-copy"
    shutil.copytree(src, dst, ignore=shutil.ignore_patterns("__pycache__"))
    bad_pins = tmp / "PINS.json"
    doc = json.loads((HERE / "PINS.json").read_text(encoding="utf-8"))
    doc["sst"]["snapshot_hash"] = "0" * 64
    bad_pins.write_text(json.dumps(doc), encoding="utf-8")

    def run() -> None:
        sst_adapter.verify_snapshot_copy(dst, pins_path=bad_pins)

    expect_raise("sst wrong pin refused", pins_mod.PinMismatch, run)


# --- 2. envelope validator ------------------------------------------------

VALID_ENVELOPE = {
    "tree_id": "t1",
    "termination_reason": "champion_found",
    "champion": {"proposal_id": "c1"},
    "alternatives": [],
    "budget_consumed": {"tokens": 100},
    "provider_errors": [],
    "gateway_bindings": [],
    "event_log_ref": "sqlite:run1",
}


def t_envelope_accepts_valid() -> None:
    ev = sst_adapter.validate_envelope(dict(VALID_ENVELOPE))
    assert ev["verdict"] == "VALID", ev


def t_envelope_accepts_real_observed_shape() -> None:
    """Independent oracle: parse (never execute) SST's live-qual envelope."""
    raw = (REPO.parent / "sst" / "docs" / "evidence" / "live-qual-2026-10-04"
           / "run2-envelope.json").read_text(encoding="utf-8")
    ev = sst_adapter.validate_envelope(json.loads(raw))
    assert ev["verdict"] == "VALID", ev


def t_envelope_rejects() -> None:
    missing = dict(VALID_ENVELOPE)
    del missing["champion"]
    extra = dict(VALID_ENVELOPE)
    extra["surprise"] = 1
    wrongtype = dict(VALID_ENVELOPE)
    wrongtype["alternatives"] = {}
    for name, obj in (
        ("missing key", missing),
        ("extra key", extra),
        ("wrong type", wrongtype),
        ("non-mapping", [1, 2]),
    ):
        expect_raise(
            f"envelope rejects {name}",
            sst_adapter.EnvelopeViolation,
            lambda o=obj: sst_adapter.validate_envelope(o),
        )


# --- 3. STC doc copy ------------------------------------------------------

STC_HEAD_FILES = {
    "STC-LIVE-READINESS-PACKET.md": "docs/STC-LIVE-READINESS-PACKET.md",
    "STC-DSH-RELEASE.md": "docs/STC-DSH-RELEASE.md",
    "STC-DSH-RECORD.md": "docs/STC-DSH-RECORD.md",
    "STC-SST-CALLER-CONTRACT.md": "docs/STC-SST-CALLER-CONTRACT.md",
    "DSH_PIN": "dsh-plugin-stc/DSH_PIN",
    "lease_git.py": "src/stc/integration/lease_git.py",
}


def vendor_stc_docs(tmp: Path) -> Path:
    """Extract HEAD bytes (frozen) via `git show` — read-only, no worktree."""
    dst = tmp / "stc-docs"
    dst.mkdir()
    for local, repo_path in STC_HEAD_FILES.items():
        out = subprocess.run(
            ["git", "-C", str(REPO.parent / "stc"), "show",
             f"HEAD:{repo_path}"],
            capture_output=True,
            check=True,
            timeout=60,
        )
        (dst / local).write_bytes(out.stdout)
    return dst


def t_stc_doc_copy_match() -> None:
    dst = vendor_stc_docs(fresh_tmp())
    ev = stc_adapter.verify_doc_copy(dst)
    assert ev["verdict"] == "MATCH", ev
    assert ev["external_pins"]["sst"] == "079f4de6fd43881c2f1b529f0612f1df64a62f32"


def t_stc_dirty_worktree_refused() -> None:
    """The dirty worktree's caller contract must NOT pass the HEAD pin."""
    tmp = fresh_tmp()
    dst = vendor_stc_docs(tmp)
    live = (REPO.parent / "stc" / "docs" / "STC-SST-CALLER-CONTRACT.md"
            ).read_bytes()
    (dst / "STC-SST-CALLER-CONTRACT.md").write_bytes(live)

    def run() -> None:
        stc_adapter.verify_doc_copy(dst)

    expect_raise("stc dirty-worktree doc refused",
                 pins_mod.PinMismatch, run)


def t_stc_unqualified_without_owner_release() -> None:
    dst = vendor_stc_docs(fresh_tmp())
    rep = stc_adapter.qualification_report(dst, owner_release=None)
    assert rep["qualified"] is False and rep["verdict"] == "UNQUALIFIED", rep
    assert set(rep["gaps"]) == set(stc_adapter.QUALIFICATION_CRITERIA), rep


def t_stc_future_gate_logic() -> None:
    dst = vendor_stc_docs(fresh_tmp())
    good = {
        "tag": "stc-substrate-qual-1",
        "commit": "a" * 40,
        "statement_sha256": "b" * 64,
        "envelope": {"name": "x", "keys": ["a"], "frozen": True},
        "tests": {"command": "y", "passed": 10, "failed": 0},
    }
    rep = stc_adapter.qualification_report(dst, owner_release=dict(good))
    assert rep["qualified"] is True and rep["verdict"] == "QUALIFIED", rep
    bad = dict(good)
    bad["tests"] = {"command": "y", "passed": 9, "failed": 1}
    rep2 = stc_adapter.qualification_report(dst, owner_release=bad)
    assert rep2["qualified"] is False, rep2
    assert "test_evidence" in rep2["gaps"], rep2


# --- 4. hygiene: no runtime refs, stdlib-only ------------------------------

def t_no_runtime_refs_into_producers() -> None:
    banned = ("../sst", "../stc", "import sst", "import stc",
              "from sst", "from stc")
    for mod in ("pins.py", "sst_adapter.py", "stc_adapter.py"):
        text = (HERE / mod).read_text(encoding="utf-8")
        for token in banned:
            assert token not in text, f"{mod} contains {token!r}"


def t_stdlib_only() -> None:
    stdlib = set(sys.stdlib_module_names)
    stdlib |= {"pins", "sst_adapter", "stc_adapter"}  # sibling modules
    for mod in ("pins.py", "sst_adapter.py", "stc_adapter.py",
                "selftest.py"):
        tree = ast.parse((HERE / mod).read_text(encoding="utf-8"))
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    top = alias.name.split(".")[0]
                    assert top in stdlib, f"{mod} imports {top!r}"
            elif isinstance(node, ast.ImportFrom):
                if node.module:
                    top = node.module.split(".")[0]
                    assert top in stdlib, f"{mod} imports {top!r}"


def main() -> int:
    check("sst fresh-vendor MATCH", t_sst_fresh_vendor_match)
    check("sst matches frozen r1 manifest", t_sst_matches_frozen_r1_manifest)
    check("sst tamper refused", t_sst_tamper_refused)
    check("sst wrong-pin refused", t_sst_wrong_pin_refused)
    check("envelope accepts valid", t_envelope_accepts_valid)
    check("envelope accepts real observed shape",
          t_envelope_accepts_real_observed_shape)
    check("envelope rejects bad shapes", t_envelope_rejects)
    check("stc doc-copy MATCH", t_stc_doc_copy_match)
    check("stc dirty-worktree refused", t_stc_dirty_worktree_refused)
    check("stc unqualified w/o owner release",
          t_stc_unqualified_without_owner_release)
    check("stc future-gate logic", t_stc_future_gate_logic)
    check("no runtime refs into producers", t_no_runtime_refs_into_producers)
    check("stdlib-only", t_stdlib_only)
    print(f"P1 self-test: {len(PASS)} PASS, {len(FAIL)} FAIL")
    for line in PASS:
        print(f"  PASS {line}")
    for line in FAIL:
        print(f"  FAIL {line}")
    return 1 if FAIL else 0


if __name__ == "__main__":
    raise SystemExit(main())
