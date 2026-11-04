#!/usr/bin/env python3
# Copyright 2026 Anshul48
# SPDX-License-Identifier: Apache-2.0
"""Speech to text with faster-whisper, on CPU.  One JSON line on stdout.

Run it with the Python that has faster-whisper installed (the author's machine:
/home/anshul/stt_venv/bin/python).  `anima voice` does that for you.

    python transcribe_worker.py CLIP.wav [--model base|small]

Output: {"text", "language", "audio_s", "model", "load_s", "transcribe_s"}
"""
import argparse
import json
import sys
import time

# No initial_prompt on purpose.  Measured on the six test clips with the base model: a long
# command-list prompt made one clip take about 17 s (temperature fallback loop), and a short
# vocabulary prompt turned "Pause" into "Paws".  With no prompt every clip took 1 to 2 s and
# came out right.  The fixed grammar in anima_voice.py absorbs small slips anyway.


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("audio")
    ap.add_argument("--model", default="base", choices=("base", "small"))
    ap.add_argument("--threads", type=int, default=4)
    a = ap.parse_args()
    from faster_whisper import WhisperModel  # imported late so --help works anywhere

    t = time.time()
    model = WhisperModel(a.model, device="cpu", compute_type="int8", cpu_threads=a.threads)
    load_s = time.time() - t
    t = time.time()
    segments, info = model.transcribe(
        a.audio, language="en", beam_size=5, vad_filter=True,
        vad_parameters={"min_silence_duration_ms": 400},
        condition_on_previous_text=False,
    )
    text = " ".join(s.text.strip() for s in segments).strip()
    print(json.dumps({"text": text, "language": info.language, "audio_s": round(info.duration, 2),
                      "model": a.model, "load_s": round(load_s, 2),
                      "transcribe_s": round(time.time() - t, 2)}))


if __name__ == "__main__":
    sys.exit(main())
