import pytest

from backend.db import _arg
from backend.server import resolve


@pytest.mark.parametrize("raw,expected", [
    ("/api/meta", ("/api/meta", "")),
    ("/api/reports?q=x&type=crypto", ("/api/reports", "q=x&type=crypto")),
    # Vercel rewrite, original path lost
    ("/api/index?__route=reports&q=x", ("/api/reports", "q=x")),
    ("/api/index?__route=admin/reports/0123456789abcdef/approve", ("/api/admin/reports/0123456789abcdef/approve", "")),
    # Vercel rewrite, original path kept
    ("/api/reports?q=x&__route=reports", ("/api/reports", "q=x")),
])
def test_resolve(raw, expected):
    assert resolve(raw) == expected


def test_turso_numbers_are_strings():
    assert _arg(0.5) == {"type": "float", "value": "0.5"}
    assert _arg(7) == {"type": "integer", "value": "7"}


def test_wsgi_app_serves_the_api():
    import io
    import json
    from wsgiref.util import setup_testing_defaults

    from backend import server
    from backend.api import App
    from backend.wsgi import app
    from tests.conftest import context_factory

    server._app = App(provider_factory=lambda: None, context_factory=context_factory(), secret="s")

    def call(method, path, body=b"", query=""):
        env = {}
        setup_testing_defaults(env)
        env.update(REQUEST_METHOD=method, PATH_INFO=path, QUERY_STRING=query,
                   CONTENT_LENGTH=str(len(body)), **{"wsgi.input": io.BytesIO(body)})
        seen = {}
        data = b"".join(app(env, lambda status, headers: seen.update(status=status, headers=dict(headers))))
        return seen["status"], seen["headers"], json.loads(data)

    try:
        status, headers, body = call("POST", "/api/analyze", json.dumps({"text": "earn 32% per month"}).encode())
        assert status == "200 OK" and body["verdict"] == "STOP"
        assert headers["Content-Type"] == "application/json"
        assert call("GET", "/api/nope")[0] == "404 Not Found"
        assert call("PUT", "/api/meta")[0] == "405 Method Not Allowed"
    finally:
        server._app = None
