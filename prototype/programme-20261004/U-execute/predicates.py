"""U-execute coded predicates (S5 design S5-DESIGN.md section 7.6).

DRAFT STATUS: NOT FROZEN. This file is the U-execute agent's pre-freeze
draft, prepared in parallel with the successor-005 build. It becomes the
frozen predicates.py ONLY at U-prereg freeze (sha256 pinned in PREREG.md
and PREREG-LOG); the verdict imports the frozen file verbatim, never
reimplements it.

Delta vs the section 7.6 printed text (both coordinator-directed):
- R-C: STEPS gains "package" (6th step: versioned artifact dir + single
  hash). Kill leg still targets suite-r3; p_kill_leg_shape is unchanged
  in logic (the STEPS loop covers "package" as begin-once).
- Docstring fix (coordinator note: "section 7.6 docstring overclaims
  counts (checker covers)"): p_ledger_report_agree claims rc/count
  agreement but the code checks rc only. Fixed docstring says rc; suite
  COUNT cross-check is verdict_relcheck.py section 2.3(b)'s job.

Reconciliation (at freeze, against built successor-005): ledger kind
spellings ("invoke"/"proc_begin"/"create"), payload field spellings
(capability/proc/result_ref/error/idem_key/step/bundle_sha256/exit_code/
artifacts/procedures), artifacts layout proc-<key>/<step>/<relpath>,
inspect "conservation"/"ok" shape. See DRAFT-NOTES.md.

Pre-freeze rebuild against BUILT bytes (NOT FROZEN; needs
RULES-AMENDMENT-2, a coordinator act — draft text in
PREREG-ENTRY-DRAFT.md):
- p_ledger_report_agree: compat shape. The packaged report nests the
  graded COMPAT-REPORT under report["compat"]; per-tag suites r1/r2/r3
  carry {ok, results[{file,rc,ran,skipped,ok}]} (relcheck.py
  step_compat/step_package). Agreement = ledger suite-step exits all
  0 AND every per-tag ok flag True AND every per-program rc 0/ok.
  Counts (ran/skipped) stay the checker's job (S5 section 2.3(b)).
- p_no_sst_leg RESCOPED to p_sst_snapshot_confined. The built vehicle
  EXECUTES SST inside suite children against the qualified vendored
  snapshot (relcheck.py run_child SST_VENV_PY forwarding lines
  ~100-110; run_suite_program scratch copies; sst_leg.py pre/post
  snapshot gates; manifest env_extra SST_VENV_PY on suite steps).
  "No SST leg" is FALSE of the built bytes; confinement (pinned venv
  interpreter, sst outputs only under scratch, zero network/key/cost
  evidence) is the checkable claim. S5-DESIGN section 8.2 ("asserted
  by p_no_sst_leg") and PREREG guards are updated to this name.
- A14 resolved WITHOUT a predicate change: built proc_begin payloads
  DO record world_id (closure ledger.jsonl lines 7,10,13,16,19,22);
  p_change_leg_shape keeps procedural key/world binding per
  DRAFT-NOTES.md A14 (no amendment needed for this item).

Coordinator pre-freeze deltas (need RULES-AMENDMENT-2 (d)(e), filed
with the entry — same built-bytes-correction class as (a)):
- (d) p_kill_leg_shape admits the adopt shape: built L3
  adopt-if-complete emits NO re-begin (success invoke with
  recovered:true on the single begin), so demanding exactly-two
  begins would INVALID honest optimal recovery.
- (e) Step-universe parameter: change legs run a revised manifest
  with more steps than STEPS, so p_steps_complete, p_kill_leg_shape,
  p_change_leg_shape and p_sst_snapshot_confined accept an optional
  steps list (default STEPS = base bundle). The verdict runner
  passes the leg's manifest steps mechanically.
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path

STEPS = ["identity", "suite-r1", "suite-r2", "suite-r3", "compat", "package"]


def _ledger_entries(ledger: Path) -> list[dict]:
    out = []
    for line in ledger.read_text(encoding="utf-8").splitlines():
        if line.strip():
            out.append(json.loads(line))
    return out


def _success_invokes(entries: list[dict], key: str) -> dict[str, dict]:
    """step -> success invoke payload for proc.exec under idem key."""
    found: dict[str, dict] = {}
    for e in entries:
        if e.get("kind") != "invoke":
            continue
        p = e.get("payload", {})
        if p.get("capability") != "proc.exec" or "error" in p:
            continue
        proc = p.get("proc", {})
        if proc.get("idem_key") != key or "result_ref" not in p:
            continue
        found[proc.get("step", "")] = p
    return found


def _begins(entries: list[dict], key: str, step: str) -> list[dict]:
    return [e.get("payload", {}) for e in entries
            if e.get("kind") == "proc_begin"
            and e["payload"].get("idem_key") == key
            and e["payload"].get("step") == step]


def p_report_valid(checker_line: str) -> bool:
    """Checker verdict line (verdict_relcheck.py stdout, first line)."""
    return checker_line.strip() == "RELCHECK-VALID"


def p_steps_complete(entries: list[dict], key: str,
                     steps: list[str] | None = None) -> bool:
    """Every step has exactly one success invoke under the key.

    steps defaults to STEPS (base bundle); change legs pass the
    revised manifest's step list (RULES-AMENDMENT-2(e)).
    """
    universe = STEPS if steps is None else steps
    ok = _success_invokes(entries, key)
    return sorted(ok) == sorted(universe)


def p_no_completed_rerun(entries: list[dict], key: str) -> bool:
    """No step succeeded twice (resume skipped every completed step)."""
    seen: dict[tuple, int] = {}
    for e in entries:
        if e.get("kind") != "invoke":
            continue
        p = e.get("payload", {})
        if p.get("capability") != "proc.exec" or "error" in p:
            continue
        proc = p.get("proc", {})
        if proc.get("idem_key") != key or "result_ref" not in p:
            continue
        k = (proc.get("bundle_sha256"), proc.get("step"))
        seen[k] = seen.get(k, 0) + 1
    return all(v == 1 for v in seen.values())


def p_kill_leg_shape(entries: list[dict], key: str,
                     steps: list[str] | None = None) -> bool:
    """Kill leg: suite-r3 interrupted + recovered; rest began once.

    Rerun shape: suite-r3 began twice, succeeded once. Adopt shape
    (built L3 adopt-if-complete; RULES-AMENDMENT-2(d)): suite-r3 began
    once but its success invoke carries recovered:true — the kill
    landed between DONE and the invoke row, so resume adopted without
    re-running. steps defaults to STEPS (kill legs run the base
    bundle); accepted for signature uniformity.
    """
    universe = STEPS if steps is None else steps
    for s in universe:
        n_beg = len(_begins(entries, key, s))
        if s == "suite-r3":
            if n_beg == 2:
                continue  # rerun shape
            if n_beg == 1:
                ok = _success_invokes(entries, key)
                if ok.get("suite-r3", {}).get("proc", {}).get(
                        "recovered") is not True:
                    return False
                continue  # adopt shape
            return False
        elif n_beg != 1:
            return False
    return p_steps_complete(entries, key, universe) and \
        p_no_completed_rerun(entries, key)


def p_ledger_report_agree(entries: list[dict], key: str,
                          report: dict) -> bool:
    """Suite ok-flags in the compat section agree with ledger exits.

    Compat shape (built bytes): the packaged RELCHECK-REPORT nests the
    graded COMPAT-REPORT under report["compat"]; per-tag suites r1/r2/r3
    carry {ok, results[{file, rc, ran, skipped, ok}]}. Agreement holds
    iff every ledger suite-step exit is 0 AND every per-tag ok flag is
    True AND every per-program rc is 0 with ok True (results must be
    non-empty — an ok flag over zero programs agrees with nothing).

    rc/ok ONLY: count cross-check (ran/skipped vs pins) is the
    checker's job (S5 section 2.3(b)), not this predicate's.
    """
    ok = _success_invokes(entries, key)
    suites = report.get("compat", {}).get("suites", {})
    for tag, step in (("r1", "suite-r1"), ("r2", "suite-r2"),
                      ("r3", "suite-r3")):
        if step not in ok:
            return False
        if ok[step].get("proc", {}).get("exit_code", -1) != 0:
            return False
        claim = suites.get(tag, {})
        if claim.get("ok") is not True:
            return False
        results = claim.get("results", [])
        if not results:
            return False
        for r in results:
            if r.get("rc", -1) != 0 or r.get("ok") is not True:
                return False
    return True


def p_hashes_recompute(entries: list[dict], key: str,
                       artifacts_root: Path) -> bool:
    """Every ledger artifact hash recomputes from artifact bytes."""
    ok = _success_invokes(entries, key)
    for step, p in ok.items():
        for a in p.get("proc", {}).get("artifacts", []):
            fp = artifacts_root / f"proc-{key}" / step / a["relpath"]
            if not fp.exists():
                return False
            if hashlib.sha256(fp.read_bytes()).hexdigest() != a["sha256"]:
                return False
    return True


def p_change_leg_shape(entries: list[dict], key_new: str,
                       worlds: tuple[str, str],
                       steps: list[str] | None = None) -> bool:
    """Change leg ran under a NEW world with a distinct bundle pin.

    steps: the leg's manifest step list — change legs pass the
    revised manifest steps (RULES-AMENDMENT-2(e)); default STEPS."""
    creates = {e["payload"]["world_id"]: e["payload"]
               for e in entries if e.get("kind") == "create"}
    old_w, new_w = worlds
    if old_w not in creates or new_w not in creates:
        return False
    old_pins = {t["bundle_sha256"]
                for t in creates[old_w].get("procedures", [])}
    new_pins = {t["bundle_sha256"]
                for t in creates[new_w].get("procedures", [])}
    if not new_pins or new_pins & old_pins:
        return False
    universe = STEPS if steps is None else steps
    return p_steps_complete(entries, key_new, universe)


def p_conservation_ok(inspect_json: dict) -> bool:
    return inspect_json.get("conservation", {}).get("ok") is True


def p_rubric_bar(scores: dict) -> bool:
    """Blind rubric (section 7.3): total>=4 and R2>=1."""
    return (scores.get("R1", 0) + scores.get("R2", 0)
            + scores.get("R3", 0)) >= 4 and scores.get("R2", 0) >= 1


def p_touch_cap(touches_used: int, cap: int = 2) -> bool:
    return touches_used <= cap


NET_KIND_PREFIXES = ("net_", "network", "socket", "http")

KEY_FRAGMENTS = ("KEY", "SECRET", "TOKEN", "CREDENTIAL", "PASSWORD",
                 "PRIVATE")


def p_sst_snapshot_confined(entries: list[dict], key: str,
                            run_dir: Path, manifest: dict,
                            pinned_venv_py: str,
                            steps: list[str] | None = None) -> bool:
    """SST executes ONLY inside the qualified snapshot on scratch copies.

    Rescoped from p_no_sst_leg (which is FALSE of the built bytes: SST
    runs in suite children). Three checkable slots, all must hold:

    (a) venv interpreter == pinned abspath: every manifest step
        env_extra SST_VENV_PY equals pinned_venv_py, and that path
        is an existing file.
    (b) sst-leg outputs exist ONLY under scratch copies: every
        "sst-leg" dir under run_dir sits under a proc_begin-recorded
        scratch root for this key.
    (c) no network/key/cost evidence: every success invoke under the
        key has capability proc.exec with cost_usd 0.0; no ledger kind
        starts with a NET_KIND_PREFIXES prefix; no proc_begin env key
        under the key contains a KEY_FRAGMENTS fragment
        (case-insensitive). (Denylist, not allowlist: legit minihost
        kinds beyond the closure-observed eight must not false-fail.)

    steps defaults to STEPS (base bundle); change legs pass the
    revised manifest's step list (RULES-AMENDMENT-2(e)).
    """
    ok = _success_invokes(entries, key)
    universe = STEPS if steps is None else steps
    begins = [b for s in universe for b in _begins(entries, key, s)]
    # (a) venv interpreter pin.
    for spec in manifest.get("steps", []):
        extra = spec.get("env_extra", {})
        if "SST_VENV_PY" in extra \
                and extra["SST_VENV_PY"] != pinned_venv_py:
            return False
    if not Path(pinned_venv_py).is_file():
        return False
    # (b) sst-leg outputs confined to scratch copies.
    scratches = [Path(b["scratch"]) for b in begins
                 if b.get("scratch")]
    for p in run_dir.rglob("sst-leg"):
        if not any(str(p).startswith(str(s)) for s in scratches):
            return False
    # (c) no network/key/cost evidence.
    for e in entries:
        kind = str(e.get("kind", "")).lower()
        if kind.startswith(NET_KIND_PREFIXES):
            return False
    for step, p in ok.items():
        if p.get("capability") != "proc.exec":
            return False
        if p.get("cost", {}).get("cost_usd", -1) != 0.0:
            return False
    for b in begins:
        for name in b.get("env_keys", []):
            if any(f in str(name).upper() for f in KEY_FRAGMENTS):
                return False
    return True


def d_confinement_slots(run_dir: Path, manifest: dict,
                        pinned_venv_py: str,
                        steps: list[str] | None = None) -> bool:
    """D-arm SST confinement (PREREG §8 C3; no ledger analogue).

    Same three questions as p_sst_snapshot_confined, answered over
    the direct-runner layout (mechanical; filed under this file's P14
    sha per PREREG §8 C3 — not a §7.6 change):
    (a) venv interpreter == pinned abspath (same loop);
    (b) every "sst-leg" dir under run_dir sits under a step scratch
        dir (run_dir/scratch/<step> — children run with cwd set
        there, and sst-leg dirs are never declared outputs, so they
        are never collected elsewhere);
    (scan) no network/key evidence in direct-ledger rows: no row
        "event" starts with a NET_KIND_PREFIXES prefix; no
        env_extra_keys entry contains a KEY_FRAGMENTS fragment
        (case-insensitive). Direct rows carry no ledger kinds and no
        cost field — nothing further to scan; argv/bundle binding is
        the checker's job. Missing or malformed log ⇒ False
        (fail closed: confinement unprovable).
    """
    universe = STEPS if steps is None else steps
    # (a) venv interpreter pin.
    for spec in manifest.get("steps", []):
        extra = spec.get("env_extra", {})
        if "SST_VENV_PY" in extra \
                and extra["SST_VENV_PY"] != pinned_venv_py:
            return False
    if not Path(pinned_venv_py).is_file():
        return False
    # (b) sst-leg outputs confined to step scratch dirs.
    scratches = [run_dir / "scratch" / s for s in universe]
    for p in run_dir.rglob("sst-leg"):
        if not any(str(p).startswith(str(s)) for s in scratches):
            return False
    # (scan) direct-ledger rows.
    log = run_dir / "direct-ledger.jsonl"
    if not log.is_file():
        return False
    try:
        lines = log.read_text(encoding="utf-8").splitlines()
    except OSError:
        return False
    for line in lines:
        if not line.strip():
            continue
        try:
            row = json.loads(line)
        except ValueError:
            return False
        if not isinstance(row, dict):
            return False
        ev = row.get("event")
        if isinstance(ev, str) and ev.lower().startswith(
                NET_KIND_PREFIXES):
            return False
        for name in row.get("env_extra_keys", []):
            if any(f in str(name).upper() for f in KEY_FRAGMENTS):
                return False
    return True
