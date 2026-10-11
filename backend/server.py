"""Serve the API (and the built front end, if present) with the standard library.

Local: `python -m backend.server` then open http://localhost:8000
On Vercel, backend/wsgi.py serves the same App (see vercel.json "services").
"""

import json
import mimetypes
import os
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qsl, urlencode, urlsplit

from backend.api import App

DIST = Path(__file__).resolve().parent.parent / "frontend" / "dist"
_app = None


def app():
    global _app
    if _app is None:
        _app = App()
    return _app


def resolve(raw_path):
    """(path, query) for a request. Also accepts a `__route=<route>` query on
    /api or /api/index, a fallback for rewrites that don't keep the original path
    (Vercel Services do keep it)."""
    url = urlsplit(raw_path)
    params = [(k, v) for k, v in parse_qsl(url.query, keep_blank_values=True)]
    route = next((v for k, v in params if k == "__route"), None)
    query = urlencode([(k, v) for k, v in params if k != "__route"])
    if route is not None and url.path in ("/api", "/api/index"):
        return "/api/" + route.lstrip("/"), query
    return url.path, query


class Handler(BaseHTTPRequestHandler):
    server_version = "ChainCheck"

    def _api(self, method):
        path, query = resolve(self.path)
        length = int(self.headers.get("Content-Length") or 0)
        body = self.rfile.read(length) if length else b""
        status, payload = app().handle(method, path, query, body, dict(self.headers))
        data = json.dumps(payload).encode()
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(data)))
        self.send_header("Cache-Control", "no-store")
        self.send_header("X-Content-Type-Options", "nosniff")
        self.end_headers()
        self.wfile.write(data)

    def do_POST(self):
        self._api("POST")

    def do_GET(self):
        path = urlsplit(self.path).path
        if path.startswith("/api/"):
            return self._api("GET")
        self._static(path)

    def _static(self, path):
        target = (DIST / path.lstrip("/")).resolve()
        if not str(target).startswith(str(DIST)) or not target.is_file():
            target = DIST / "index.html"
        if not target.is_file():
            self.send_error(404, "Front end not built. Run `npm run build` in frontend/.")
            return
        data = target.read_bytes()
        self.send_response(200)
        self.send_header("Content-Type", mimetypes.guess_type(target.name)[0] or "application/octet-stream")
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def log_message(self, fmt, *args):  # no request bodies or query strings in logs
        pass


def main():
    port = int(os.environ.get("PORT", "8000"))
    # Hosts like Render route traffic in from outside the container; locally, stay private.
    host = os.environ.get("HOST") or ("0.0.0.0" if os.environ.get("RENDER") else "127.0.0.1")
    print(f"ChainCheck on http://{'localhost' if host == '127.0.0.1' else host}:{port}")
    ThreadingHTTPServer((host, port), Handler).serve_forever()


if __name__ == "__main__":
    main()
