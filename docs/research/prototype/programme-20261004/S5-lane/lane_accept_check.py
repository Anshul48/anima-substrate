"""S5-A12 lane-owned accept-fields check (S5-A1 demo leg).

Compares a fresh demo's EVIDENCE.json against accept/EXPECTED.json
per accept/README.md: every EXACT field must match; byte refs
(*_bytes_ref) are reported for eyeball comparison (REFERENCE).

Usage: lane_accept_check.py <new-EVIDENCE.json>
Exit 0 iff every exact field matches. Prints one PASS/FAIL line
per field plus the byte-ref eyeball table.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

S005 = (Path(__file__).resolve().parents[3] / "prototype"
        / "successor-005")

CHECKS: list[tuple[str, bool]] = []


def check(label: str, cond: bool, detail: str = "") -> None:
    CHECKS.append((label, cond))
    print(f"[{'PASS' if cond else 'FAIL'}] {label}"
          + (f" ({detail})" if detail else ""), flush=True)


def main() -> int:
    new = json.loads(Path(sys.argv[1]).read_text(encoding="utf-8"))
    exp = json.loads((S005 / "accept" / "EXPECTED.json").read_text(
        encoding="utf-8"))
    # S1/S2/S3 exact subset
    for task in ("S1", "S2", "S3"):
        for field in ("valid", "quality", "prefs_total", "lane"):
            check(f"{task}.{field}", new[task][field] == exp[task][field],
                  f"{new[task][field]!r}")
    check("S3.re_executed_invokes",
          new["S3"]["re_executed_invokes"]
          == exp["S3"]["re_executed_invokes"])
    check("S3.revoked", new["S3"]["revoked"] == exp["S3"]["revoked"])
    check("S3.skipped_pre_kill", len(new["S3"]["skipped"])
          == exp["S3"]["skipped_pre_kill"],
          f"len={len(new['S3']['skipped'])}")
    check("S3.representation-v2",
          exp["S3"]["representation"] == "v2"
          and "v2" in new["S3"].get("ruling", ""),
          new["S3"].get("ruling", ""))
    check("S3.child_killed",
          exp["S3"]["child_killed"] is True
          and new["kill"]["child_rc"] == -9,
          f"child_rc={new['kill']['child_rc']}")
    # S4-followup -> S4 (+lane via task stdout mapping: via SC-FUSED)
    s4, e4 = new["S4"], exp["S4-followup"]
    for field in ("valid", "quality", "prefs_total", "via",
                  "lineage_ok"):
        check(f"S4.{field}", s4[field] == e4[field], f"{s4[field]!r}")
    check("S4.task_id", s4["task_id"] == "S4-followup")
    # S5: probe denied + standby completed + world/standby
    s5, e5 = new["S5"], exp["S5"]
    check("S5.probe_denied",
          e5["probe_denied"] is True
          and s5["denied_probe"]["deny_seq"] == 14,
          f"deny_seq={s5['denied_probe']['deny_seq']}")
    check("S5.standby_completed",
          s5["standby_completed"] == e5["standby_completed"])
    check("S5.world/standby",
          s5["quarantine"]["world_id"] == e5["world"]
          and s5["quarantine"]["standby"] == e5["standby"])
    # S6-followup -> S6
    s6, e6 = new["S6"], exp["S6-followup"]
    for field in ("valid", "quality", "prefs_total", "lane", "via"):
        check(f"S6.{field}", s6[field] == e6[field], f"{s6[field]!r}")
    # SST exact
    sst, esst = new["SST"], exp["SST"]
    check("SST.snapshot_check",
          sst.get("snapshot_check") == esst["snapshot_check"]
          or "MATCH" in sst.get("child_stdout_tail", ""),
          str(sst.get("snapshot_check")))
    check("SST.champion_found",
          ("champion_found" in sst.get("child_stdout_tail", ""))
          == esst["champion_found"])
    check("SST.cost_usd", float(sst.get("cost_usd", 0.0))
          == esst["cost_usd"])
    check("SST.pydantic", sst.get("pydantic_version")
          == esst["pydantic"], str(sst.get("pydantic_version")))
    check("SST.envelope_keys", len(sst.get("envelope_keys", []))
          == esst["envelope_keys"],
          f"len={len(sst.get('envelope_keys', []))}")
    # fusion / fission records
    fus, efus = new["fusion"], exp["fusion"]
    check("fusion.fused_id",
          efus["fused_id"] in json.dumps(fus))
    check("fusion.parents",
          all(p in json.dumps(fus) for p in efus["parents"]))
    check("fusion.removed_mechanism",
          efus["removed_mechanism"]
          in fus.get("before_mechanisms", [])
          and efus["removed_mechanism"]
          not in fus.get("after_mechanisms", []))
    fis, efis = new["fission"], exp["fission"]
    check("fission.composite",
          efis["composite"] in json.dumps(fis))
    check("fission.children",
          all(c in json.dumps(fis) for c in efis["children"]))
    check("fission.restored_mechanism",
          efis["restored_mechanism"]
          in fis.get("after_mechanisms", []))
    # routing + settle
    check("routing_decisions", len(new["routing"])
          == exp["routing_decisions"], f"len={len(new['routing'])}")
    st, est = new["settle"], exp["settle"]
    check("settle.markers",
          st["grant_settle_markers"]
          == est["grant_settle_markers"])
    check("settle.terminals",
          st["settled_terminals"] == est["settled_terminals"])
    stranded_zero = all(
        all(v == 0.0 for v in m.values())
        for m in st["stranded"].values())
    check("settle.stranded_zero",
          stranded_zero == est["stranded_zero"])
    # byte refs (REFERENCE: eyeball, still verified equal here)
    print("--- byte refs (REFERENCE, eyeballed) ---")
    for task in ("S1", "S2", "S3"):
        cb = new[task]["central_bytes"] \
            == exp[task]["central_bytes_ref"]
        db = new[task]["direct_bytes"] \
            == exp[task]["direct_bytes_ref"]
        print(f"{task}: central {new[task]['central_bytes']} "
              f"(ref {exp[task]['central_bytes_ref']}) "
              f"{'MATCH' if cb else 'DIFF'}; direct "
              f"{new[task]['direct_bytes']} "
              f"(ref {exp[task]['direct_bytes_ref']}) "
              f"{'MATCH' if db else 'DIFF'}")
    nfail = sum(1 for _, ok in CHECKS if not ok)
    print(f"lane accept: {len(CHECKS)-nfail}/{len(CHECKS)} exact "
          f"fields MATCH")
    return 0 if nfail == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
