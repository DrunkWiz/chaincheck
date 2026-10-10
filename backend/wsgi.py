"""WSGI entry point for Vercel (Services). Standard library only.

vercel.json routes /api/* here with the original path. `app` is a plain WSGI
callable around the same App.handle the local server uses.
"""

import json

from backend.server import app as get_app
from backend.server import resolve


def app(environ, start_response):
    method = environ.get("REQUEST_METHOD", "GET")
    raw_path = environ.get("PATH_INFO", "/") or "/"
    query = environ.get("QUERY_STRING", "")
    path, query = resolve(f"{raw_path}?{query}" if query else raw_path)
    try:
        length = int(environ.get("CONTENT_LENGTH") or 0)
    except ValueError:
        length = 0
    body = environ["wsgi.input"].read(length) if length > 0 else b""
    headers = {key[5:].replace("_", "-").title(): value
               for key, value in environ.items() if key.startswith("HTTP_")}

    if method not in ("GET", "POST"):
        status, payload = 405, {"error": "Method not allowed."}
    else:
        status, payload = get_app().handle(method, path, query, body, headers)

    data = json.dumps(payload).encode()
    start_response(f"{status} {_REASONS.get(status, 'OK')}", [
        ("Content-Type", "application/json"),
        ("Content-Length", str(len(data))),
        ("Cache-Control", "no-store"),
        ("X-Content-Type-Options", "nosniff"),
    ])
    return [data]


_REASONS = {200: "OK", 400: "Bad Request", 403: "Forbidden", 404: "Not Found", 405: "Method Not Allowed",
            413: "Payload Too Large", 503: "Service Unavailable"}
