import json

import pytest

from backend import db as database


def test_sqlite_schema_and_queries():
    db = database.init(database.SqliteDatabase())
    db.execute("INSERT INTO entities (kind, value, display) VALUES (?, ?, ?)", ("domain", "x.example", "x[.]example"))
    assert db.execute("SELECT kind, value FROM entities") == [{"kind": "domain", "value": "x.example"}]


def test_sqlite_batch_is_atomic():
    db = database.init(database.SqliteDatabase())
    with pytest.raises(database.DatabaseError):
        db.batch([
            ("INSERT INTO entities (kind, value, display) VALUES (?, ?, ?)", ("a", "1", "1")),
            ("INSERT INTO nope VALUES (1)", ()),
        ])
    assert db.execute("SELECT COUNT(*) AS n FROM entities") == [{"n": 0}]


class FakeTurso:
    """Records Hrana pipeline requests and answers like Turso would."""

    def __init__(self, reply=None):
        self.requests = []
        self.reply = reply

    def __call__(self, url, headers, body, timeout=10):
        payload = json.loads(body)
        self.requests.append((url, headers, payload))
        if self.reply:
            return self.reply
        return {"results": [{"type": "ok", "response": {"type": "execute", "result": {
            "cols": [{"name": "id"}, {"name": "kind"}, {"name": "score"}, {"name": "gone"}],
            "rows": [[{"type": "integer", "value": "7"}, {"type": "text", "value": "domain"},
                      {"type": "float", "value": 0.5}, {"type": "null"}]],
        }}} for r in payload["requests"] if r["type"] == "execute"] + [{"type": "ok", "response": {"type": "close"}}]}


def test_turso_execute_request_and_rows():
    transport = FakeTurso()
    db = database.TursoDatabase("libsql://chaincheck-demo.turso.io", "tok", transport)
    rows = db.execute("SELECT * FROM entities WHERE kind = ? AND id = ?", ("domain", 7))
    assert rows == [{"id": 7, "kind": "domain", "score": 0.5, "gone": None}]
    url, headers, payload = transport.requests[0]
    assert url == "https://chaincheck-demo.turso.io/v2/pipeline"
    assert headers["Authorization"] == "Bearer tok"
    stmt = payload["requests"][0]["stmt"]
    assert stmt["args"] == [{"type": "text", "value": "domain"}, {"type": "integer", "value": "7"}]
    assert payload["requests"][-1] == {"type": "close"}


def test_turso_batch_wraps_in_a_transaction():
    transport = FakeTurso()
    database.TursoDatabase("https://x.turso.io", "t", transport).batch([("DELETE FROM clusters", ())])
    sqls = [r["stmt"]["sql"] for r in transport.requests[0][2]["requests"] if r["type"] == "execute"]
    assert sqls == ["BEGIN", "DELETE FROM clusters", "COMMIT"]


def test_turso_errors_raise():
    transport = FakeTurso(reply={"results": [{"type": "error", "error": {"message": "no such table"}}]})
    with pytest.raises(database.DatabaseError, match="no such table"):
        database.TursoDatabase("https://x.turso.io", "t", transport).execute("SELECT 1")


def test_from_env_prefers_turso(monkeypatch):
    monkeypatch.setenv("TURSO_DATABASE_URL", "libsql://x.turso.io")
    monkeypatch.setattr(database, "init", lambda db: db)
    assert isinstance(database.from_env(), database.TursoDatabase)


def test_from_env_refuses_sqlite_on_vercel(monkeypatch):
    monkeypatch.delenv("TURSO_DATABASE_URL", raising=False)
    monkeypatch.setenv("VERCEL", "1")
    with pytest.raises(database.DatabaseError, match="TURSO_DATABASE_URL"):
        database.from_env()


def test_api_without_turso_on_vercel_still_checks(monkeypatch):
    from backend.api import App
    from tests.conftest import context_factory
    monkeypatch.delenv("TURSO_DATABASE_URL", raising=False)
    monkeypatch.setenv("VERCEL", "1")
    app = App(provider_factory=lambda: None, context_factory=context_factory(), secret="s")
    assert app.handle("POST", "/api/analyze", "", b'{"text": "Earn 3% per day"}', {})[0] == 200
    assert app.handle("GET", "/api/reports", "", b"", {})[0] == 503
