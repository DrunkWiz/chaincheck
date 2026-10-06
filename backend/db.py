"""Storage for community reports (docs/BUILD_BRIEF.md §10).

Decision (5 Oct): SQLite locally and in tests; Turso (hosted, SQLite-compatible)
in production, over its HTTP API with the standard library. Same SQL in both.
Set TURSO_DATABASE_URL and TURSO_AUTH_TOKEN to use Turso; otherwise the SQLite
file at DATABASE_PATH is used. On Vercel without Turso, storage is refused.
"""

import base64
import json
import os
import sqlite3
import threading
import urllib.error
import urllib.request

SCHEMA = (
    """CREATE TABLE IF NOT EXISTS reports (
        id TEXT PRIMARY KEY,
        story TEXT NOT NULL,
        outcome TEXT NOT NULL,
        scam_type TEXT NOT NULL,
        verdict TEXT NOT NULL,
        signals TEXT NOT NULL DEFAULT '[]',
        status TEXT NOT NULL DEFAULT 'pending',
        synthetic INTEGER NOT NULL DEFAULT 0,
        helped INTEGER NOT NULL DEFAULT 0,
        created_at TEXT NOT NULL,
        reviewed_at TEXT
    )""",
    """CREATE TABLE IF NOT EXISTS entities (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        kind TEXT NOT NULL,
        value TEXT NOT NULL,
        display TEXT NOT NULL,
        UNIQUE (kind, value)
    )""",
    """CREATE TABLE IF NOT EXISTS report_entities (
        report_id TEXT NOT NULL REFERENCES reports(id),
        entity_id INTEGER NOT NULL REFERENCES entities(id),
        PRIMARY KEY (report_id, entity_id)
    )""",
    """CREATE TABLE IF NOT EXISTS clusters (
        report_id TEXT PRIMARY KEY REFERENCES reports(id),
        cluster_id TEXT NOT NULL,
        size INTEGER NOT NULL
    )""",
    "CREATE INDEX IF NOT EXISTS reports_status ON reports(status)",
    "CREATE INDEX IF NOT EXISTS report_entities_entity ON report_entities(entity_id)",
)


class DatabaseError(Exception):
    pass


class SqliteDatabase:

    def __init__(self, path=":memory:"):
        self.path = path
        self._conn = sqlite3.connect(path, check_same_thread=False)
        self._conn.row_factory = sqlite3.Row
        self._lock = threading.Lock()

    def execute(self, sql, params=()):
        with self._lock:
            try:
                cur = self._conn.execute(sql, params)
                rows = [dict(r) for r in cur.fetchall()]
                self._conn.commit()
                return rows
            except sqlite3.Error as exc:
                self._conn.rollback()
                raise DatabaseError(str(exc)) from None

    def batch(self, statements):
        """Run [(sql, params)] atomically."""
        with self._lock:
            try:
                for sql, params in statements:
                    self._conn.execute(sql, params)
                self._conn.commit()
            except sqlite3.Error as exc:
                self._conn.rollback()
                raise DatabaseError(str(exc)) from None


def _http_transport(url, headers, body, timeout=10):
    request = urllib.request.Request(url, data=body, headers=headers, method="POST")
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            return json.load(response)
    except (urllib.error.URLError, OSError, ValueError) as exc:
        raise DatabaseError(f"Turso request failed: {type(exc).__name__}") from None


class TursoDatabase:
    """Turso over the Hrana-over-HTTP pipeline endpoint."""


    def __init__(self, url, token, transport=_http_transport):
        url = url.strip()
        if url.startswith("libsql://"):
            url = "https://" + url[len("libsql://"):]
        self.endpoint = url.rstrip("/") + "/v2/pipeline"
        self.token = token
        self.transport = transport

    def _pipeline(self, statements):
        requests = [{"type": "execute", "stmt": {"sql": sql, "args": [_arg(p) for p in params]}}
                    for sql, params in statements]
        requests.append({"type": "close"})
        reply = self.transport(
            self.endpoint,
            {"Authorization": f"Bearer {self.token}", "Content-Type": "application/json"},
            json.dumps({"requests": requests}).encode(),
        )
        results = reply.get("results", [])
        for result in results:
            if result.get("type") == "error":
                raise DatabaseError(result.get("error", {}).get("message", "Turso error"))
        return results

    def execute(self, sql, params=()):
        result = self._pipeline([(sql, params)])[0]["response"]["result"]
        cols = [c["name"] for c in result.get("cols", [])]
        return [dict(zip(cols, (_value(v) for v in row))) for row in result.get("rows", [])]

    def batch(self, statements):
        self._pipeline([("BEGIN", ())] + list(statements) + [("COMMIT", ())])


def _arg(value):
    if value is None:
        return {"type": "null"}
    if isinstance(value, bool):
        return {"type": "integer", "value": str(int(value))}
    if isinstance(value, int):
        return {"type": "integer", "value": str(value)}
    if isinstance(value, float):
        return {"type": "float", "value": repr(value)}  # Turso wants numbers as strings
    if isinstance(value, bytes):
        return {"type": "blob", "base64": base64.b64encode(value).decode()}
    return {"type": "text", "value": str(value)}


def _value(cell):
    kind = cell.get("type")
    if kind == "null":
        return None
    if kind == "integer":
        return int(cell["value"])
    if kind == "float":
        return float(cell["value"])
    if kind == "blob":
        return base64.b64decode(cell["base64"])
    return cell.get("value")


def init(db):
    for statement in SCHEMA:
        db.execute(statement)
    return db


def from_env():
    url = os.environ.get("TURSO_DATABASE_URL")
    if url:
        return init(TursoDatabase(url, os.environ.get("TURSO_AUTH_TOKEN", "")))
    if os.environ.get("VERCEL"):
        # Vercel's filesystem doesn't keep writes: refuse rather than lose reports.
        raise DatabaseError("TURSO_DATABASE_URL is not set")
    return init(SqliteDatabase(os.environ.get("DATABASE_PATH", "chaincheck.sqlite3")))
