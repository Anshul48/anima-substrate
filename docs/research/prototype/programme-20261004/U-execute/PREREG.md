# U-execute PREREG (FILED — FROZEN AT COUNTERSIGN)

Status: FILED. Prepared by the U-execute rebuild agent as draft; Holes below are FILLED
against the BUILT successor-005 + built relcheck bundle (pins
`2dbb0439…`, bundle `1fee2241…`) plus NOTE-1 closure evidence
(READINESS-PASS 183.2 s); nothing here is frozen until the coordinator
countersigns (S5-DESIGN.md §7.8; coordinator filed the PREREG-LOG entry at U-prereg time (text was
DRAFTED in PREREG-ENTRY-DRAFT.md; the filed entry + RULES-AMENDMENT-2
(a)–(f) are in PREREG-LOG.md). Values marked [COORDINATOR-ACT] (envelope seal, amendment
issue, final sha countersigns) cannot be completed by this agent.

Gating: this prereg may be frozen + filed iff S5-A1–S5-A12 all PASS
(§6 gating rule). Any FAIL ⇒ fix-the-successor or escalate; never
proceed-to-U on a failed gate.

Conventions: all holes are filled below (a pin value, hash, path, or
byte-blob reference, each with built-bytes provenance in
PREREG-ENTRY-DRAFT.md). Frozen prose (rubric, aborts, verdict rules,
analysis rules) is final text below, transcribed from S5-DESIGN.md
§7.3/§7.4/§7.5/§7.7 as amended by the RULES-AMENDMENT-2 draft (compat
shape, SST confinement, A-ENVELOPE wording). `[Proposal]` marks the two
values the spec + bytes do not fix (P10 numbers, P12 load rule) and the
coordinator adopted in §8 C8 (see DRAFT-NOTES.md for alternatives).

---

## 1. Task pins (§7.1 — filed)

| # | Pin | Value (filled vs built bytes; provenance in PREREG-ENTRY-DRAFT.md) |
|---|---|------|
| P1 | `relcheck` bundle sha256 (canonical-manifest bytes, §1.3) | `1fee2241d1fd2d482ab90ac2a3aa63b8d3f4e56dd44427a89c3aa6ce5161c91d` |
| P2 | REDEFINED: inline-JSON identity maps, r1 lane pair `{r1: 76 files, s002: 96 files}` (concept change: no separate IDENTITY.sha256 bytes exist; maps live inline in frozen-pins.json `identity`) | maps verbatim in `frozen-pins.json` `identity.r1` + `identity.s002`; covered by pins sha `2dbb0439…` |
| P3 | REDEFINED: inline-JSON identity maps, r2 lane pair `{r2: 27 files, s003: 100 files}` | maps verbatim in `frozen-pins.json` `identity.r2` + `identity.s003`; covered by pins sha `2dbb0439…` |
| P4 | REDEFINED: inline-JSON identity maps, r3 lane pair `{r3: 24 files, s004: 100 files}` | maps verbatim in `frozen-pins.json` `identity.r3` + `identity.s004`; covered by pins sha `2dbb0439…` |
| P5 | Release root paths (r1/r2/r3, checker input) | r1 `…/prototype/release-20261004`, r2 `…/prototype/release-r2`, r3 `…/prototype/release-r3` (full abspaths in frozen-pins.json `frozen`; s002/s003/s004 likewise) |
| P6 | Suite file lists + expected counts per release | r1→s002: `test_conformance.py` unittest 9/0 + `successor_demo.py` demo marker; r2→s003: conformance 9/0 + `test_atomicity.py` 27/0; r3→s004: conformance 9/0 + atomicity 39/0 (all `expect_skipped: 0`; verbatim in frozen-pins.json `suites`) |
| P7 | Minimum surface sets (CLI verbs + api functions) | PER-RELEASE minima (built shape; supersedes the A12 global proposal): r1 14 verbs/19 funcs, r2 15/21, r3 15/21 — full lists verbatim in frozen-pins.json `surface_min`; ACCEPT rule is per-release superset (P20) |
| P8 | Sealed change envelope: sha256 of revised bundle + reveal point | `{author: held-out-revision-agent, revised_bundle_sha256: 5c3d1bbdd9a74dc00436983a72f743072af79ea5bd647e1184d4a1cd9790ce60, manifest_sha256: d2e6dcd48c2dc947173225c5c66d0037213424de1c8a46bc220137b4fe94008b, reveal: post-countersign identical bytes to both arms, validation: throwaway disclosed (3 runs, own state dir, keys sealed-val-1/2/3)}` (slot filled in frozen-pins.json `u_execute.envelope_seal_slot`; tree roll-up recorded in the entry, not relied upon) |
| P9 | Change shape (frozen): the §3 (1+1+1) delta budget (RULES-AMENDMENT-2(f)) — exactly one added step carrying exactly one added declared output (base steps' declared sets byte-equal) + exactly one added suite target in the existing tags + a program delta present (relcheck.py bytes changed XOR one added bin/ program argv-referenced by the new step); no removals (files/steps/programs). Bundle files = base set + ≤1 added bin/ file. CONTENT held out (in the envelope, never here pre-reveal). Mechanical conformance in derive-revised-pins (P9-conformance). | shape fixed (left); content sealed per P8 |
| P10 | Kill spec: step `suite-r3`, fractional point, delay-scaling rule | step fixed `suite-r3`; fraction `0.5` of the arm's own closure suite-r3 wall; delays host `55.4 s` (0.5×110.7) / direct `55.7 s` (0.5×111.483); tolerance `±0.25` of wall (in-window `[0.25W, 0.75W]`); out-of-window ⇒ leg VOID (confirm: H `p_kill_leg_shape` + attempt record; D stamps+RUN-LOG). [Proposal per DRAFT-NOTES A7; coordinator adopts] |
| P11 | Touch cap | fixed `2` per leg per arm (§5.2(d)) |
| P12 | Pinned machine + interpreter | machine: this box, `/tmp` on ext4, quiet-load rule (1-min load ≤2.0 at launch, recorded; [Proposal]); interpreters: proc `/usr/bin/python3` 3.12.3 + SST venv `…/prototype/w1/.venv/bin/python` 3.12.3 (abspaths pinned; versions recorded in proc_begin) |
| P13 | `verdict_relcheck.py` sha256 (frozen bytes) | `3ea4868d485d04ffa5b4d152217a7c54baa3bfabbead0ceb91fc1351fbe38de5` (rev4: base 6 + pins universe + direct log binding + non-base input subset (f) + freeze_verify_roots; 29-case battery checker-negatives.log; supersedes 388-line draft `fc54f2e0…`; built vehicle reference `776924c56e30ef4d51673a9e0f600f32979526d18e759d2465a3d9c0f9738e6f` untouched; battery `checker-battery.py` `f95e8a3693c9732b1ff4e105181198ecd2d20f9c8ba3a1ba8c24accdece7fee3`) |
| P14 | `predicates.py` sha256 (frozen bytes: §7.6 + R-C + docstring fix + RULES-AMENDMENT-2 (a)(c)(d)(e) + d_confinement_slots (C3)) | `d12adfa2229c326de6567e0f00cdba50c7ce6be8f51498913aebe548676e3d47` (amended functions quoted verbatim in §5) |
| P15 | Direct baseline form (make-vs-stdlib, §5.1/§10.1 Q4) + its sha256 | form `direct_run.py` (stdlib runner, STAMP_SCHEMA 3, builder evidence shape steps/*-RESULT.json + direct-ledger.jsonl end rows; Makefile.template discarded from freeze, kept in drafts); sha `44ced7ddffb9a45ddd2384eaad48267d52db89165e17e674582f26bcb559333e` (supersedes 281-line `f161615d…`) |
| P16 | Frozen pins file for the checker (`frozen-pins.json`: P1–P7 verbatim + U-chapter + provenance) + its sha256 | `U-execute/frozen-pins.json` (56036 bytes); sha `1e3a3a6a587e6eee5d2de57bce9738417c24eb4114d4ba24ceaea2937fe04884` (slot filled at freeze) |
| P17 | Step list (R-C): fixed `["identity","suite-r1","suite-r2","suite-r3","compat","package"]`; manifest steps must match exactly (R1 parity) | fixed (left); matches built manifest + pins `steps` |
| P18 | Run identity fields the report must carry (checker binds ledger rows to the run) | fixed: packaged report carries `{nonce, run_id, mode}` + `{bundle_sha256, pins_sha256}`; `world_id`/`idem_key` live LEDGER-SIDE ONLY (proc_begin/invoke payloads). Supersedes the world_id/idem_key-in-report proposal — built compat bytes carry no run identity (witness: redact-guess.log) |
| P19 | Counts grammar (checker §2.3(b) parses counts from hash-verified logs) | fixed: unittest grammar (`Ran N …` / exact `OK` / `FAILED` marker / `skipped=N`, parsed from combined child output) + demo marker `integrated demo: OK` + 2-log layout per suite step (conformance+demo / conformance+atomicity). `RELCHECK-COUNTS` line DELETED (never existed in built bytes) |
| P20 | Verdict mapping PARTIAL/FAIL (frozen text, §2.3(d)) | fixed (`verdict_rule`, checker-duplicated): ACCEPT iff ident_ok ∧ suites_ok ∧ surface_ok; PARTIAL iff ident_ok ∧ suites_ok ∧ surface shortfall; else FAIL. Inputs are bools/per-tag (`identities.{tag}.match`, `suites.{tag}.ok`, `surface.{tag}.minimum_ok`) — same logic as the draft text, built input shape |

Additional freeze records (not pins, disclosed with the filing):
S5-A10 readiness runs (throwaway state dirs, disclosed, no verdict
implications); honest-expense measurement (A-EXPENSE input); bundle
byte review (no sleep/burn loops); `make` presence/absence on the
pinned machine.

## 2. Design freeze (§7.2 — fixed)

Arms: H = successor-005 procedure worlds (`create-proc-world` +
`run-procedure` + `recover`); D = §5.1 baseline (P15 frozen form).
Legs (both arms): clean + change + kill. Step lists identical (P17).
Metrics §6 below. Rubric §3. Abort criteria §4. Analysis rules §7.
No runs before PREREG-LOG countersign except S5-A10 readiness
(throwaway state dirs, disclosed).

Matched resources (§5.2): (a) identical bundle bytes both arms (same
sha256; host stages a copy, direct uses the original — copy verified by
hash); (b) identical change content + reveal point (P8/P9); (c) same
kill class (process-crash/SIGKILL) + plan-phase (mid-`suite-r3`, same
fractional point ± P10 tolerance); process-group kill by the harness
(P15); kill-during-quarantine-transfer excluded (pre-registered);
(d) touch cap 2 per leg per arm (H: recover+re-invoke = 2; D: resume =
1 + 1 spare; over-cap ⇒ guard FAIL, leg verdict VOID); (e) $0/offline/
stdlib-only-except-qualified-SST-snapshot (suite steps run the frozen
trees' own suites, whose SST legs execute ONLY against the vendored
qualified snapshot on scratch copies — confinement asserted by
`p_sst_snapshot_confined`; the "no SST leg" wording is corrected by
RULES-AMENDMENT-2, drafted in PREREG-ENTRY-DRAFT.md). R1 granularity
parity (step boundaries both arms; step lists match exactly). R2 honest
re-work counting (completed-step re-runs: 0 asserted on H, counted
exactly on D; current-step re-runs counted on both). NOT held equal
(measured outcomes): ledger/artifact byte counts, invoke/step counts,
re-executed work, wall-clock (guard-only). No wall-clock primaries.

## 3. Blind usefulness rubric (§7.3 — frozen text, scored blind to arm)

Lane scores each arm's final `COMPAT-REPORT.json` + purpose statement
("release-lane pre-flight: would you file this with a cut record?")
on: R1 actionability (verdict + per-release evidence traceable to
pins/logs — 0/1/2); R2 trustworthiness (every claim independently
recomputable from attached evidence — 0/1/2); R3 completeness
(identities + suites + surface, no silent gaps — 0/1/2). Bar: total
≥4 AND R2 ≥1 (coded: `p_rubric_bar`). The lane sees report bytes only
(no arm labels, no ledger — ledger cross-check is the checker's job,
§2.3, not the rubric's).

Blinding procedure: the coordinator applies the frozen redaction
field list (`frozen-pins.json` `u_execute.redaction_field_list` —
strip-if-present run-identity keys, path prefixes, timing keys; keep
pins/identities/suites/surface/verdict) to both arms' COMPAT-REPORT.json,
presents the two redacted reports in random order labeled X/Y, and
records the mapping sealed until scores are filed. Empirical witness
(redact-guess.log): on NOTE-1 VALID bytes the two compat reports are
byte-identical (5065 B, sha `099f4e33…`), redaction removes nothing, and
nothing identifies the arm — blinding holds with margin. See
DRAFT-NOTES.md §C for leak analysis (leak classes 1–4 absent by
construction; §C3(b) near-identity caveat confirmed and accepted).

## 4. Abort criteria (§7.4 — frozen, incl. executability re-gate)

- G-RE (executability re-gate, applied to BUILT successor-005 before
  first non-throwaway run — G1..G5 re-applied with the vehicle):
  G1 real artifact+consumer (relcheck + release lane — PASS by §2.2
  unless pins fail); G2 not a grid re-skin (PASS — no scheduling
  content); G3 every step through honest consumer interfaces
  (PASS iff S5-A2/A3 green); G4 competent direct baseline exists
  (PASS iff S5-A10 direct VALID); G5 host load-bearing in ≥1 leg
  (PASS iff S5-A6/A8 green). Any re-gate FAIL ⇒ STEP0-ABORT-2
  (complete negative; no U runs; re-scope, do not execute).
- A-EXPENSE: honest clean-run wall <60 s on the pinned machine ⇒
  ABORT (I4 fails; padding forbidden).
- A-FROZEN: any frozen IDENTITY mismatch pre/post any leg ⇒ ABORT +
  investigate (frozen discipline breach).
- A-ENVELOPE (wording corrected by RULES-AMENDMENT-2, drafted in
  PREREG-ENTRY-DRAFT.md — the design's "SST-uninvolved" parenthetical is
  FALSE vs built bytes): any network/key/cost evidence, or any non-stdlib
  execution OUTSIDE the qualified SST snapshot confinement
  (`p_sst_snapshot_confined` slots), ⇒ ABORT. SST execution inside the
  confinement is expected, not abortable.
- A-TOUCH: touches over cap on either arm ⇒ guard FAIL for that leg
  (leg verdict VOID, not silently kept).

## 5. Coded predicates (§7.6 + R-C — frozen bytes by hash)

The verdict imports `predicates.py` (sha256 P14) verbatim, never
reimplements. At freeze, the exact coded predicates are quoted in this
section verbatim (M1-redux pattern, L1 lesson B) OR pinned by hash with
the file filed alongside — coordinator's call at filing.

File ref: `U-execute/predicates.py` sha256 P14 (final).
The five amended functions are quoted verbatim below in file order
(RULES-AMENDMENT-2 (a) p_ledger_report_agree, (c)
p_sst_snapshot_confined, (d) p_kill_leg_shape, (e) p_steps_complete +
p_change_leg_shape + p_sst steps parameter; all other functions are
§7.6 verbatim + R-C `package` step + the docstring fix). A
verification script asserts each quote equals its file span exactly.

```python
def p_steps_complete(entries: list[dict], key: str,
                     steps: list[str] | None = None) -> bool:
    """Every step has exactly one success invoke under the key.

    steps defaults to STEPS (base bundle); change legs pass the
    revised manifest's step list (RULES-AMENDMENT-2(e)).
    """
    universe = STEPS if steps is None else steps
    ok = _success_invokes(entries, key)
    return sorted(ok) == sorted(universe)


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
```

Predicate list (names fixed): `p_report_valid`, `p_steps_complete`,
`p_no_completed_rerun`, `p_kill_leg_shape`, `p_ledger_report_agree`
(rc/ok only, compat shape; counts are the checker's job),
`p_hashes_recompute`, `p_change_leg_shape`, `p_conservation_ok`,
`p_rubric_bar`, `p_touch_cap`, `p_sst_snapshot_confined`
(rescoped from `p_no_sst_leg` by RULES-AMENDMENT-2). STEPS fixed per P17.

## 6. Verdict rules (§7.7 — frozen; arm comparison per value cell)

- CELL-VALIDITY (per arm, per leg): `p_report_valid` AND
  `p_ledger_report_agree` (H only; D has no ledger — D's agreement is
  stamps-vs-report, audited by the same checker with `--no-ledger`
  mode, frozen) AND `p_hashes_recompute` (H). FAIL ⇒ arm-leg INVALID.
- CELL-RECOVERY (kill leg): H DEMONSTRATED iff `p_kill_leg_shape`
  AND `p_no_completed_rerun` AND VALID; D re-work counted from
  stamps+log (exact); comparison REPORTED (counts), with the
  preregistered directional claim: H re-executes 0 completed steps
  (predicate) while D's honest stamp-resume re-executes 0 completed
  steps too — EXPECTED TIE on counts; the discriminating H value is
  ledger accountability (`p_ledger_report_agree` +
  `p_hashes_recompute` have no D analogue — stated as the
  accountability cell, not as a recovery win).
- CELL-ADAPT (change leg): both arms must reach VALID under the
  revised bundle; cost-to-adapt counts REPORTED; preregistered claim:
  H's advertise-time validation refuses malformed revisions pre-work
  (demonstrated in S5-A8; in U-execute the revision is well-formed,
  so this cell measures parity honestly — no rigged defect).
- CELL-USEFUL (all legs): `p_rubric_bar` per arm, blind. Joint
  primary: arm must be VALID + meet the bar.
- Overall U verdict: HOST-VALUE-DEMONSTRATED iff H VALID + bar met
  on all legs AND guards hold AND ≥1 of (recovery accountability,
  adapt accountability) has its preregistered H-exclusive evidence
  present; else HOST-VALUE-NOT-DEMONSTRATED (with the failing cell
  named — a clean negative is complete). NO verdict claims H
  superiority on cost or speed — unclaimed by design.

Guards (§5.3): conservation holds on H; `re_executed_steps == 0` on H;
frozen trees byte-intact (IDENTITY re-check pre/post every leg); bundle
post-hashes MATCH; no wall-clock primaries; no TEST-stub content scored
and SST confined to the qualified snapshot (`p_sst_snapshot_confined`
all three slots); touch cap respected.

Cost metrics: cost-to-adapt (§3 leg) = invokes/steps to first VALID
revised report. Recovery cost (§4 leg) = re-executed completed steps
(H: 0 asserted; D: counted) + current-step re-runs (both counted) +
touches used.

## 7. Analysis rules (§7.5 + §7.8 — frozen)

Primaries are count/byte/validity predicates (§5) + rubric (§3);
wall-clock is guard-only (reported as observed durations, never a
superiority claim). Arm comparison is per value cell (§6), never a
single-race winner. Verdict code imports `predicates.py` verbatim;
any predicate edit after filing ⇒ new PREREG-LOG entry + re-freeze
(RULES-AMENDMENT-1 procedure).

Filing: standard PREREG-LOG entry (UTC stamp, this file's sha,
predicates.py sha, task pins P1–P20, generator/harness shas,
prev_hash chain, rule line) per PREREG-LOG.md format; coordinator
appends/countersigns BEFORE first non-throwaway run (L1 lessons A+B;
RULES-AMENDMENT-1). S5-A10 readiness runs are throwaway (own state
dirs, disclosed, no verdict implications). §8 clarifications are part
of this filed prereg (this file's sha covers them).

---

*End of filed prereg. Holes P1–P20 filled vs built bytes; frozen at
countersign (PREREG-LOG U-EXECUTE entry + RULES-AMENDMENT-2(a)–(f)).*

---

## 8. Coordinator pre-freeze clarifications (filed with this prereg)

These items fix points the design transcription left open. All are
mechanical (no judgment at run time); all were fixed before countersign;
none alter a §7 rule — they state how the filed bytes execute it.

- C1 void handling. A VOID leg (P10 out-of-window, A-TOUCH over-cap,
  harness-defect, mistargeted kill, incomplete-envelope reveal — see
  C6) is re-runnable ONCE with identical preregistered parameters;
  the void, its cause and its evidence are preserved. A second void
  stands as VOID (reported; neither VALID nor INVALID). A VOID is
  never silently re-run and never scored.
- C2 touches (P11 mechanics). One touch = one CLI invocation that
  executes leg work (H: run-procedure, ops-recover; D: direct_run
  run/resume). Setup (init/create-proc-world/mkdir/freeze-check) and
  inspection (inspect/audit/dry-run/eval/blind-present) cost 0.
  Refusals cost 0 (D touch-cap refusal; H adopt-needed refusal).
  Killed/failed invocations that executed work DO count (both arms).
  Envelope: clean/change = 1 per arm; kill via rerun path = 2 per
  arm; H kill via adopt path = 3 (run + recover + re-invoke) ⇒
  A-TOUCH VOID with the adopt-touch-cost recorded in the void note.
- C3 D-arm application. D CELL-VALIDITY = p_report_valid on the
  --no-ledger checker verdict; p_steps_complete, p_ledger_report_agree,
  p_hashes_recompute and p_conservation_ok are H-only (no D analogue).
  D guards = A-FROZEN + bundle post-hash + p_sst_snapshot_confined
  slots (a)+(b) plus the ledger-kind scan over direct-ledger rows
  (slot (c) invoke/cost checks are H-only) + touch cap. D re-work
  counts from direct-ledger.jsonl: completed-step re-runs = steps
  with a prior rc-0 attempt_end plus a later attempt; current-step
  re-runs = attempts beyond the first minus completed re-runs;
  touches from touches.json. H current-step re-runs = begins beyond
  the first per step (ledger count); completed re-runs asserted 0
  by p_no_completed_rerun.
- C4 rubric mechanics. The rubric (§3) is scored PER LEG on the two
  arms' redacted COMPAT-REPORTs (X/Y shuffled per leg by
  u-harness.py blind-present; mappings sealed separately until that
  leg's scores are filed). The bar (total ≥4 AND R2 ≥1) applies per
  arm per leg; CELL-USEFUL requires the bar on all legs. The purpose
  statement is FIXED boilerplate, identical for X/Y (no arm
  authorship, no leak surface): "release-lane pre-flight: would you
  file this with a cut record?" The rater is a held-out agent seeing
  report bytes + rubric only (no arm labels, no ledger, no logs).
- C5 kill leg bundle. Kill legs run the BASE bundle (P17 6 steps);
  only change legs run revised bytes. p_kill_leg_shape's universe is
  therefore STEPS (its steps parameter stays default).
- C6 reveal + revised-pins derivation (change leg). At reveal (after
  countersign), the coordinator opens sealed/ and runs u-harness.py
  derive-revised-pins, which (i) checks envelope completeness
  (revised bundle dir + REVISION-MANIFEST.json required; revised
  15-key vehicle pins used when present and schema-valid); missing
  manifest or bundle ⇒ VOID change leg + investigate; (ii) verifies
  the manifest's recorded shas against the revealed bytes;
  (iii) takes revised vehicle pins from the envelope when present
  and schema-valid, else grafts mechanically (base
  identity/frozen/trees/surface_min/surface_trees/ignore_top/
  demo_marker/pins_format chapters + revised steps/argv from the
  revised MANIFEST + revised suites/artifacts from the revised
  in-bundle pins.json + recomputed bundle_sha256
  (procedure.canonical_manifest_bytes rule), bin_relcheck_sha256 and
  pins_sha256); (iv) verifies schema (15 keys), base-superset steps,
  argv/artifacts coverage, suites internal consistency and bundle
  binding; (v) appends the carried u_execute chapter + fresh
  provenance and writes the derived file. Any verification failure ⇒
  VOID change leg + investigate (never silent repair). The derivation
  transcript + derived-file sha are leg evidence (the sha cannot be
  preregistered — the content is sealed — but the derivation is).
  Reveal shape check: the mechanical envelope-vs-base diff is
  recorded; shape outside P9 ⇒ VOID + re-seal under amendment, never
  silent keep.
- C7 overall computation. u-harness.py eval-u reads the six
  LEG-VERDICT.json files and applies the §6 overall rule
  mechanically (HOST-VALUE-DEMONSTRATED iff H VALID + bar met on
  all legs AND guards hold AND ≥1 preregistered H-exclusive
  accountability cell present; else HOST-VALUE-NOT-DEMONSTRATED
  with the failing cell named). No cost/speed superiority verbiage.
- C8 proposals adopted. P10 numbers (55.4 s host / 55.7 s direct,
  ±0.25W, void-if-out-of-window) and the P12 quiet-load rule
  (launch iff 1-min load ≤2.0; per-leg launch load recorded; no
  mid-leg void on load) are ADOPTED as written (coordinator
  pre-freeze act).
- C9 adapt cell. H CELL-ADAPT = VALID ∧ p_change_leg_shape (new world
  + disjoint bundle pin); D CELL-ADAPT = VALID. Rationale:
  p_change_leg_shape's only consumer is CELL-ADAPT; without it H
  could pass the change leg without versioning.
- C10 overall + comparison voids. Overall DEMONSTRATED requires
  per-leg H demonstration (clean validity, kill recovery cell,
  change adapt cell) + bar met per arm per leg + all guards on both
  arms + the explicit ≥1 H-exclusive cell + no standing void. A D
  INVALID voids that leg's comparison (baseline failure,
  investigated); a voided comparison ⇒ NOT-DEMONSTRATED with the
  voided cell named — the claim needs its control. (Re-runnable
  once per C1 after a note-entry fix; see C11.)
- C11 post-filing defects. Baseline/checker/harness defect found
  live: leg VOID + PREREG-LOG note entry (defect + fix + new sha +
  void ref) + re-run once (C1). Predicate edits still need a new
  entry + re-freeze (RULES-AMENDMENT-1 procedure, §7).
