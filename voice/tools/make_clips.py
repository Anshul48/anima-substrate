#!/usr/bin/env python3
"""Make the test clips for `anima voice` with the local Kokoro TTS.

Run with the Python that has kokoro_onnx + soundfile installed (on the author's
machine: ~/trace-v5/venv/bin/python). Needs the two Kokoro model files
(kokoro-v1.0.int8.onnx, voices-v1.0.bin); pass their folder as --models.

    python make_clips.py --models ~/trace-v5/models --out ../clips

The clips are synthetic speech, not human recordings; they test the pipeline
(speech -> text -> fixed command), not accent robustness.
"""
import argparse
import json
from pathlib import Path

CLIPS = [
    # file, voice, text spoken
    ("show-status", "af_heart", "Show status."),
    ("pause-task-3", "af_heart", "Pause task three."),
    ("run-next-claude", "am_michael", "Run the next job with Claude."),
    ("run-next-muse", "af_heart", "Run the next job with Muse."),
    ("recall-similar", "am_michael", "Recall similar fixes."),
    ("not-a-command", "af_heart", "Delete everything in the repository."),
]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--models", required=True)
    ap.add_argument("--out", default=str(Path(__file__).resolve().parent.parent / "clips"))
    a = ap.parse_args()
    import numpy as np
    import soundfile as sf
    from kokoro_onnx import Kokoro

    models = Path(a.models).expanduser()
    k = Kokoro(str(models / "kokoro-v1.0.int8.onnx"), str(models / "voices-v1.0.bin"))
    out = Path(a.out)
    out.mkdir(parents=True, exist_ok=True)
    meta = {}
    for name, voice, text in CLIPS:
        s, sr = k.create(text, voice=voice, speed=1.0, lang="en-us")
        idx = np.where(np.abs(s) > 0.008)[0]
        if len(idx):
            s = s[max(0, idx[0] - int(0.15 * sr)): idx[-1] + int(0.30 * sr)]
        sf.write(out / f"{name}.wav", s, sr)
        meta[name] = {"voice": voice, "text": text, "seconds": round(len(s) / sr, 2), "sample_rate": sr}
        print(name, voice, meta[name]["seconds"], "s")
    (out / "clips.json").write_text(json.dumps(meta, indent=1) + "\n")


if __name__ == "__main__":
    main()
