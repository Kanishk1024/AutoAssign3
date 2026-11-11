#!/usr/bin/env python3
"""
Capture screenshots of the live web demo for the report (dev tool).

    python report/screenshots.py            # all scenes -> report/figures/web_*.png
    python report/screenshots.py web_experiments

How it works: the web demo server (web_demo.Handler) is started in-process on
a free port. For each scene, index.html is served with
  * a scene script from report/scenes/ that clicks through the demo, and
  * a hidden image whose response is delayed, so the browser's `load` event --
    which is when `firefox --screenshot` captures -- waits for the scene.
Headless Firefox then writes the PNG. If Firefox is a snap package it can only
write inside ~/snap/firefox/common, so files are staged there and moved.
"""

from __future__ import annotations

import os
import shutil
import socket
import subprocess
import sys
import tempfile
import threading
import time
from http.server import ThreadingHTTPServer
from urllib.parse import parse_qs, urlparse

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, ROOT)
import web_demo  # noqa: E402

SCENES_DIR = os.path.join(HERE, "scenes")
OUT = os.path.join(HERE, "figures")

# name: (scene-length in ms, window width, window height, dark?)
SCENES = {
    "web_engine_grounded":        (3500, 1400, 1000, False),
    "web_engine_labellings":      (2800, 1400, 940, False),
    "web_strategic_manipulation": (6800, 1400, 1000, False),
    "web_strategic_ex511":        (5200, 1400, 1150, False),
    "web_strategic_random_q3":    (9000, 1400, 1150, False),
    "web_experiments":            (3200, 1400, 1100, False),
    "web_editor_dark":            (4800, 1400, 960, True),
}

PNG_1PX = bytes.fromhex("89504e470d0a1a0a0000000d4948445200000001000000010806000000"
                        "1f15c4890000000d4944415478da63f8ffff3f0005fe02fea7d6a4b6"
                        "0000000049454e44ae426082")


class SceneHandler(web_demo.Handler):
    def do_GET(self):
        u = urlparse(self.path)
        q = parse_qs(u.query)
        if u.path == "/__slow":
            time.sleep(int(q.get("ms", ["2000"])[0]) / 1000)
            return self._raw(PNG_1PX, "image/png")
        if u.path.startswith("/__scene/"):
            name = os.path.basename(u.path)
            js = open(os.path.join(SCENES_DIR, "_common.js"), "rb").read() + b"\n" + \
                open(os.path.join(SCENES_DIR, name), "rb").read()
            return self._raw(js, "text/javascript")
        if u.path in ("/", "/index.html") and "scene" in q:
            html = open(os.path.join(web_demo.WEB, "index.html"), encoding="utf-8").read()
            errs = ('<script>window.__errs=[];window.onerror=(m,s,l)=>{__errs.push(m+" @"+l)};'
                    'addEventListener("unhandledrejection",e=>__errs.push("rejection: "+e.reason));</script>')
            html = html.replace("<head>", "<head>" + errs)
            if q.get("dark"):
                html = html.replace("<html", '<html data-theme="dark"', 1)
            html = html.replace("</body>",
                                f'<img src="/__slow?ms={q["ms"][0]}" alt="" style="display:none">'
                                f'<script src="/__scene/{q["scene"][0]}.js"></script></body>')
            return self._raw(html.encode(), "text/html")
        return super().do_GET()

    def _raw(self, data, ctype):
        self.send_response(200)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(data)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(data)


def free_port() -> int:
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


def staging_dir() -> str:
    """Directory Firefox may write to (snap confinement aware)."""
    snap_common = os.path.expanduser("~/snap/firefox/common")
    if os.path.isdir(snap_common):
        return tempfile.mkdtemp(prefix="argshots-", dir=snap_common)
    return tempfile.mkdtemp(prefix="argshots-")


def main():
    if not shutil.which("firefox"):
        sys.exit("firefox not found -- screenshots need Firefox")
    names = sys.argv[1:] or list(SCENES)
    port = free_port()
    srv = ThreadingHTTPServer(("127.0.0.1", port), SceneHandler)
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    stage = staging_dir()
    os.makedirs(OUT, exist_ok=True)
    try:
        profile = os.path.join(stage, "profile")
        os.makedirs(profile)
        for name in names:
            ms, w, h, dark = SCENES[name]
            url = f"http://127.0.0.1:{port}/?scene={name}&ms={ms}" + ("&dark=1" if dark else "")
            target = os.path.join(stage, name + ".png")
            subprocess.run(["firefox", "--headless", "--no-remote", "--profile", profile,
                            f"--window-size={w},{h}", "--screenshot", target, url],
                           stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, timeout=120)
            if os.path.exists(target):
                shutil.move(target, os.path.join(OUT, name + ".png"))
                print("wrote", os.path.relpath(os.path.join(OUT, name + ".png"), ROOT))
            else:
                print("FAILED", name)
    finally:
        srv.shutdown()
        shutil.rmtree(stage, ignore_errors=True)


if __name__ == "__main__":
    main()
