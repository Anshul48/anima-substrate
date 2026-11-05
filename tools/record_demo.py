#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
"""Record the silent 60-second ANIMA recorded-replay tour at 1080p.

Serves docs/ on localhost, drives the demo page and the UI preview with
Playwright using the system Chrome (channel="chrome", no browser download),
records video with a fresh context (light colour scheme, empty storage), then
converts to a silent H.264 MP4 with ffmpeg. Six scenes of ten seconds each;
the scene list and caption text match docs/media/TOUR-STORYBOARD.md.

  python3 tools/record_demo.py                  write docs/media/replay-60s.mp4 + replay-60s.png
  python3 tools/record_demo.py --out /tmp/x.mp4 write elsewhere
Needs: playwright (Python), Google Chrome, ffmpeg. It does not change any page.
It only reads docs/; it never touches docs/evidence/ or the recorded run data.
"""

import argparse
import functools
import http.server
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import threading
import time

ROOT = Path(__file__).resolve().parent.parent
DOCS = ROOT / "docs"
MEDIA = DOCS / "media"
SCENE_SECONDS = 10
W, H = 1920, 1080

# Caption text; matches the ANIMA half of docs/media/TOUR-STORYBOARD.md
CAPTIONS = [
    "ANIMA: a prototype for one job type, fixing a bug.",
    "A recorded replay of nine bug-fixing jobs.",
    "The hidden checker catches a worker's wrong \u201cdone\u201d.",
    "Change one character and the record check fails.",
    "The state tree shows every task and attempt.",
    "UI preview: a recorded replay, not a live run.",
]

CAPTION_JS = """
(text) => {
  let el = document.getElementById('tour-caption');
  if (!el) {
    el = document.createElement('div');
    el.id = 'tour-caption';
    el.setAttribute('style', [
      'position:fixed', 'left:50%', 'bottom:36px', 'transform:translateX(-50%)',
      'max-width:1500px', 'padding:18px 32px', 'background:#ffffff',
      'color:#0b1220', 'border:1px solid #cfd6e4', 'border-left:6px solid #1a56db',
      'border-radius:10px', 'font:600 34px/1.3 system-ui,-apple-system,Segoe UI,sans-serif',
      'z-index:2147483647', 'box-shadow:none', 'pointer-events:none'
    ].join(';'));
    document.body.appendChild(el);
  }
  el.textContent = text;
}
"""

SMOOTH_JS = """
(y) => new Promise((resolve) => {
  const start = window.scrollY, dist = y - start, dur = 1400, t0 = performance.now();
  const ease = (t) => t < 0.5 ? 2*t*t : 1 - Math.pow(-2*t + 2, 2) / 2;
  const step = (now) => {
    const t = Math.min(1, (now - t0) / dur);
    window.scrollTo(0, start + dist * ease(t));
    if (t < 1) requestAnimationFrame(step); else resolve();
  };
  requestAnimationFrame(step);
})
"""


class QuietHandler(http.server.SimpleHTTPRequestHandler):
    def log_message(self, *args, **kwargs):
        pass


def serve(port):
    handler = functools.partial(QuietHandler, directory=str(DOCS))
    srv = http.server.ThreadingHTTPServer(("127.0.0.1", port), handler)
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    return srv


def caption(page, text):
    page.evaluate(CAPTION_JS, text)


def scroll_to(page, selector, offset=140):
    y = page.evaluate(
        "(s) => document.querySelector(s).getBoundingClientRect().top + window.scrollY",
        selector,
    )
    page.evaluate(SMOOTH_JS, max(0, y - offset))


def record(out_mp4, poster_png):
    from playwright.sync_api import sync_playwright

    srv = serve(0)
    base = "http://127.0.0.1:%d/" % srv.server_address[1]
    tmp = Path(tempfile.mkdtemp(prefix="anima-replay-"))
    try:
        with sync_playwright() as p:
            browser = p.chromium.launch(channel="chrome", headless=True)
            ctx = browser.new_context(
                viewport={"width": W, "height": H},
                record_video_dir=str(tmp),
                record_video_size={"width": W, "height": H},
                color_scheme="light",
                service_workers="block",
            )
            page = ctx.new_page()
            t0 = time.monotonic()

            def end_scene(n):
                left = t0 + SCENE_SECONDS * (n + 1) - time.monotonic()
                if left > 0:
                    time.sleep(left)

            # 1 demo opens
            page.goto(base + "demo/index.html", wait_until="load")
            page.wait_for_selector("#job-list li")
            time.sleep(1)
            caption(page, CAPTIONS[0])
            time.sleep(5)
            scroll_to(page, "#jobs", 40)
            end_scene(0)

            # 2 nine-job run replays (UI preview, 2x speed ~ 10 s)
            page.goto(base + "ui-preview/index.html", wait_until="load")
            page.wait_for_selector("#tree g")
            caption(page, CAPTIONS[1])
            page.select_option("#speed", "2")
            time.sleep(1)
            page.click("#playBtn")
            end_scene(1)
            page.screenshot(path=str(poster_png))

            # 3 checker catches a wrong "done"
            page.goto(base + "demo/index.html", wait_until="load")
            page.wait_for_selector("#job-list li")
            caption(page, CAPTIONS[2])
            scroll_to(page, "#tiles", 160)
            time.sleep(6)
            scroll_to(page, "#job-list", 120)
            end_scene(2)

            # 4 tamper check: check the record, change one character, check again
            caption(page, CAPTIONS[3])
            scroll_to(page, "#check", 60)
            time.sleep(1.5)
            page.click("#btn-check")
            time.sleep(3)
            page.click("#btn-tamper")
            time.sleep(1)
            end_scene(3)

            # 5 state tree
            page.goto(base + "ui-preview/index.html", wait_until="load")
            page.wait_for_selector("#tree g")
            caption(page, CAPTIONS[4])
            page.evaluate(
                "() => { const s = document.getElementById('scrubber');"
                " s.value = s.max; s.dispatchEvent(new Event('input', {bubbles: true})); }"
            )
            time.sleep(3)
            page.locator("#tree text", has_text="Claude Code").first.click()
            end_scene(4)

            # 6 UI-preview label card
            caption(page, CAPTIONS[5])
            page.locator(".preview-tag").scroll_into_view_if_needed()
            time.sleep(1)
            page.evaluate(
                "document.querySelector('.preview-tag').style.outline='4px solid #1a56db'"
            )
            end_scene(5)

            ctx.close()
            browser.close()
        webm = next(tmp.glob("*.webm"))
        out_mp4.parent.mkdir(parents=True, exist_ok=True)
        subprocess.run(
            [
                "ffmpeg",
                "-y",
                "-loglevel",
                "error",
                "-i",
                str(webm),
                "-t",
                "60",
                "-an",
                "-vf",
                "scale=%d:%d,fps=30" % (W, H),
                "-c:v",
                "libx264",
                "-pix_fmt",
                "yuv420p",
                "-preset",
                "medium",
                "-crf",
                "30",
                "-movflags",
                "+faststart",
                str(out_mp4),
            ],
            check=True,
        )
    finally:
        srv.shutdown()
        shutil.rmtree(tmp, ignore_errors=True)


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--out", default=str(MEDIA / "replay-60s.mp4"))
    ap.add_argument("--poster", default=None)
    a = ap.parse_args()
    out = Path(a.out)
    poster = Path(a.poster) if a.poster else out.with_suffix(".png")
    record(out, poster)
    print("wrote", out, "and", poster)
    return 0


if __name__ == "__main__":
    sys.exit(main())
