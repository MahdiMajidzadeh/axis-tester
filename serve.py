#!/usr/bin/env python3
"""Serve the app files and forward Moonraker API calls to the printer.

The browser talks only to this server (same origin), so the printer's
moonraker.conf needs no cors_domains change.

    python3 serve.py            # http://localhost:8000
    python3 serve.py 8080       # other port
"""
import json
import sys
import urllib.error
import urllib.request
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlparse

PORT = int(sys.argv[1]) if len(sys.argv) > 1 else 8000
ROOT = Path(__file__).resolve().parent
API_PREFIXES = ("/printer/", "/server/", "/machine/", "/access/")
STATIC = {"index.html": "text/html; charset=utf-8", "style.css": "text/css; charset=utf-8", "app.js": "text/javascript; charset=utf-8"}
ALLOWED_HOSTS = {f"localhost:{PORT}", f"127.0.0.1:{PORT}"}


class Handler(BaseHTTPRequestHandler):
    def log_message(self, fmt, *args):
        if not self.path.startswith("/printer/objects/query"):
            sys.stderr.write("%s %s\n" % (self.command, self.path))

    def reply(self, code, body, ctype="application/json"):
        if isinstance(body, (dict, list)):
            body = json.dumps(body).encode()
        self.send_response(code)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(body)

    def error(self, code, msg):
        self.reply(code, {"error": {"code": code, "message": msg}})

    def handle_any(self):
        # Reject DNS-rebinding and requests addressed to anything but this server.
        if self.headers.get("Host") not in ALLOWED_HOSTS:
            return self.error(403, "Open this app at http://localhost:%d" % PORT)
        path = urlparse(self.path).path
        if self.command == "GET" and (path == "/" or path.lstrip("/") in STATIC):
            name = "index.html" if path == "/" else path.lstrip("/")
            return self.reply(200, (ROOT / name).read_bytes(), STATIC[name])
        if path == "/__axis_proxy":
            return self.reply(200, {"proxy": True})
        if path.startswith(API_PREFIXES):
            return self.forward()
        return self.error(404, "Not found")

    def forward(self):
        # Required custom header: cross-site pages can't send it without a
        # CORS preflight, which this server never approves.
        target = self.headers.get("X-Moonraker-Target", "")
        u = urlparse(target)
        if u.scheme not in ("http", "https") or not u.netloc:
            return self.error(400, "Missing or invalid X-Moonraker-Target header")
        length = int(self.headers.get("Content-Length") or 0)
        data = self.rfile.read(length) if length else None
        headers = {k: self.headers[k] for k in ("Content-Type", "X-Api-Key") if self.headers.get(k)}
        req = urllib.request.Request(f"{u.scheme}://{u.netloc}{self.path}", data=data, headers=headers, method=self.command)
        # gcode/script blocks until Klipper has processed the moves, so no timeout there.
        timeout = None if self.path.startswith("/printer/gcode/script") else 10
        try:
            with urllib.request.urlopen(req, timeout=timeout) as r:
                self.reply(r.status, r.read(), r.headers.get("Content-Type", "application/json"))
        except urllib.error.HTTPError as e:
            self.reply(e.code, e.read(), e.headers.get("Content-Type", "application/json"))
        except Exception as e:
            self.error(502, f"Printer unreachable at {u.netloc}: {getattr(e, 'reason', e)}")

    do_GET = do_POST = handle_any


if __name__ == "__main__":
    try:
        server = ThreadingHTTPServer(("127.0.0.1", PORT), Handler)
    except OSError as e:
        if e.errno in (48, 98):  # EADDRINUSE on macOS / Linux
            sys.exit(f"Port {PORT} is already in use (is serve.py already running?). "
                     f"Try another port: python3 serve.py {PORT + 1}")
        raise
    print(f"Axis Tester: open http://localhost:{PORT}  (Ctrl+C to stop)")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
