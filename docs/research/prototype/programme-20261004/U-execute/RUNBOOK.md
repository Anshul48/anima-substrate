# U-execute leg runbook (filed pre-countersign; procedure, not prose)

Conventions: `U` = `prototype/programme-20261004/U-execute/`;
`S5` = `prototype/successor-005`; `PY` = `PYTHONDONTWRITEBYTECODE=1
python3`. Leg evidence lives under `U/runs/<arm>-<leg>/`
(command log `CMDS.log`, freeze pre/post, kill log, advertise
transcript, inspect JSON, LEG-VERDICT.json). One command log per leg
records every executing invocation (touch attestation, C2).

## Roots, worlds, keys (fixed)

- H-CC root (clean + change share ONE ledger for p_change_leg_shape):
  `U/runs/H-CC/` with worlds `U-clean`/`U-change`, keys
  `uclean-h1`/`uchange-h1`, procedure `relcheck` (all legs).
- H-K root (holdings fit 2 worlds/root; kill is separate):
  `U/runs/H-K/` with world `U-kill`, key `ukill-h1`.
- D work dirs (one leg each): `U/runs/D-clean/`, `U/runs/D-change/`,
  `U/runs/D-kill/`, run-ids `uclean-d1`/`uchange-d1`/`ukill-d1`
  (nonce = run-id; resume reuses the run-id).
- Order: clean (H+D) → kill (H+D) → reveal + derive → change (H+D)
  → blind-present ×3 → held-out rating → eval-u. Reveal sits after
  all base-bundle evidence is collected.

## Per-leg gates (all legs, both arms)

1. Launch gate: 1-min load ≤2.0 at leg start (record actual; P12/C8).
2. Freeze-pre: `PY U/u-harness.py freeze-check --upins U/frozen-pins.json
   --out <leg>/freeze-pre.json` → must exit 0 (else A-FROZEN ABORT).
3. Post-clean A-EXPENSE: honest clean-run wall <60 s ⇒ ABORT (I4).

## H leg commands

Inputs dir per H leg (`<leg>/inputs/`, assembled first):
`relcheck.py` + `pins.json` = byte copies from the leg bundle
(base: `S5/vehicle/relcheck/`; change: reveal out-bundle);
`params.json` = readiness template: `{"params_format": 1,
"mode": "host", "nonce": <run-id>, "run_id": <run-id>, "idem_key":
<key>, "run_root": <abs root>, "artifacts_dir": <abs
root>/artifacts/proc-<key>, "bundle_sha256": <leg bundle>,
"frozen": <UPINS frozen verbatim>}` (sorted keys, indent 2).

- Create (fresh root only; initializes adequate holdings):
  `PY S5/release.py ops create-proc-world --state-dir <root>
  --world <W> --bundle <bundle-dir> --reason u-execute-<leg>`
  → rc 0 + `proc-world` line (advertise ACCEPT; transcript kept).
  Second create on the same root ACCEPTS (proven); a third would
  refuse (holdings fit 2 — hence H-CC + H-K split, not 3-in-1).
- Run: `PY S5/release.py run-procedure --state-dir <root> --world
  <W> --procedure relcheck --key <K> --inputs <leg>/inputs/`.
- Kill leg: spawn the run under `setsid`, note its pgid; in parallel:
  `PY U/u-harness.py kill-watch --pgid <pgid> --signal
  ledger:<root>/ledger.jsonl:suite-r3:<K> --delay 55.4 --window
  27.7 83.0 --log <leg>/kill.json --poll 0.2`
  (P10: 0.5×110.7 host wall, ±0.25W; exit 2 ⇒ VOID per C1).
  Then `wait` (reap), then resume = run-procedure (same key). If it
  refuses with adopt-needed (0 touches): `PY S5/release.py ops
  recover --state-dir <root> --reason u-execute-kill-resume` (= 1
  touch) then run-procedure again (= 1 touch; adopt path totals 3
  ⇒ A-TOUCH VOID per C2, adopt-touch-cost recorded).
- Inspect: `PY S5/release.py inspect --state-dir <root> --json >
  <leg>/inspect.json` (conservation guard input).
- Eval: `PY U/u-harness.py eval-leg --arm H --leg <leg> --out
  <leg>/LEG-VERDICT.json --pins <upins> --venv-py <P12 venv>
  --freeze-pre <leg>/freeze-pre.json --state-dir <root> --world
  <W> --procedure relcheck --key <K> [--key-new <K2> --worlds
  <Wold>,<Wnew> (change)] --touch-count <N> --touch-log
  <leg>/CMDS.log --inspect-json <leg>/inspect.json
  --rubric-scores null` (re-run with scores post-rating for final).

## D leg commands

Frozen flags (all six, from UPINS `frozen`, mechanical):
`--frozen r1=<abs> --frozen r2=<abs> --frozen r3=<abs> --frozen
s002=<abs> --frozen s003=<abs> --frozen s004=<abs>` (quote values).

- Run: `PY U/direct_run.py --bundle <bundle-dir> --work <leg-work>
  --frozen ... (×6) --pins <upins> --run-id <run-id> --nonce
  <run-id>` (change leg: `--bundle` = reveal out-bundle,
  `--pins` = derived pins).
- Kill leg: spawn under `setsid` + `kill-watch --pgid <pgid>
  --signal runlog:<work>/direct-ledger.jsonl:suite-r3 --delay 55.7
  --window 27.9 83.6 --log <leg>/kill.json` (P10 direct numbers);
  then resume with the SAME `--run-id` (attempt 2, touch 2).
- Eval: `PY U/u-harness.py eval-leg --arm D --leg <leg> --out
  <leg>/LEG-VERDICT.json --pins <upins> --venv-py <P12 venv>
  --freeze-pre <leg>/freeze-pre.json --work <leg-work> --bundle
  <bundle-dir> --rubric-scores null` (+ scores later).

## Reveal (after kill legs, before change legs)

`PY U/u-harness.py derive-revised-pins --sealed U/sealed/
--base-upins U/frozen-pins.json --base-bundle S5/vehicle/relcheck/
--out U/runs/reveal/revised-pins.json --transcript
U/runs/reveal/derive-transcript.json`
→ exit 0 (DERIVED) feeds change legs (`--bundle`
`<out-dir>/out-bundle` if flat-assembled else the envelope bundle
dir per the transcript's `bundle_dir`; `--pins` the derived file);
exit 2 ⇒ VOID change legs + investigate (C6/C1). Record the
envelope-vs-base diff + derived sha in the change-leg evidence.

## Blinding + rating + overall (per leg, post-legs)

`PY U/u-harness.py blind-present --leg <leg> --h-compat
<H-COMPAT.json> --d-compat <D-COMPAT.json> --h-report
<H-RELCHECK-REPORT.json> --d-report <D-RELCHECK-REPORT.json>
--upins <leg-upins> --run-roots <Hroot>,<Droot> --out-dir
U/runs/blind-<leg>/` (H live compat:
`<Hroot>/artifacts/proc-<key>/compat/COMPAT-REPORT.json`; D live
compat: `<Dwork>/artifacts/compat/COMPAT-REPORT.json`; same dirs
for the package reports; change leg uses derived upins).
A held-out rater (fresh agent: report bytes + rubric + PURPOSE.txt
only, no arm labels/ledger/logs) scores R1/R2/R3 per X/Y; mapping
opens after scores file; eval-leg re-runs with scores; then
`eval-u` over the six finals (+ `--allow-provisional` for the
pre-rating technical read).

## Voids and aborts (quick ref)

Out-of-window kill (watcher exit 2), over-cap touches, harness
defect, mistargeted kill, incomplete-envelope reveal ⇒ VOID + C1
(one identical re-run, void preserved; second void stands).
Frozen mismatch ⇒ ABORT + investigate (A-FROZEN). Network/key/cost
or non-stdlib outside SST confinement ⇒ ABORT (A-ENVELOPE).
Post-filing tool defect ⇒ note entry + fix + re-run (C11).
