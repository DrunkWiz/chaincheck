import base64
import json

import pytest

from backend import db as database
from backend.api import App
from backend.providers.fake import FakeProvider
from scripts import seed_reports
from tests.conftest import SECRET, context_factory, load_offer, make_ctx


@pytest.fixture
def app():
    db = database.init(database.SqliteDatabase())
    seed_reports.seed(db, make_ctx(), secret=SECRET)
    return App(db=db, provider_factory=lambda: None, context_factory=context_factory(),
               admin_token="admin-test", secret=SECRET)


def post(app, path, payload, headers=None):
    return app.handle("POST", path, "", json.dumps(payload).encode(), headers or {})


def test_analyze(app):
    status, body = post(app, "/api/analyze", {"text": load_offer("michael")})
    assert status == 200
    assert body["verdict"] == "STOP"
    assert body["flags"] and body["chain"] and body["stage"]["number"] == 7
    assert body["data"]["demo"] is True


def test_analyze_uses_the_network(app):
    status, body = post(app, "/api/analyze", {"text": "Join AlphaGain Pro at alphagain-pro.example"})
    assert "network.seen_in_reports" in {f["rule"] for f in body["flags"]}


def test_analyze_with_answers(app):
    _, body = post(app, "/api/analyze", {"text": "Great chance to invest with us.", "answers": {"payment": "gold"}})
    assert body["verdict"] == "STOP"


@pytest.mark.parametrize("payload,status", [
    ({}, 400),
    ({"text": 5}, 400),
    ({"text": "x" * 20_001}, 400),
    ({"images": [{"mime": "image/gif", "data": "AAAA"}]}, 400),
    ({"images": [{"mime": "image/png", "data": "not base64!"}]}, 400),
    ({"images": [{"mime": "image/png", "data": base64.b64encode(b"png").decode()}]}, 503),
])
def test_analyze_rejects_bad_input(app, payload, status):
    assert post(app, "/api/analyze", payload)[0] == status


def test_screenshot_flow():
    provider = FakeProvider(lambda offer: "{}", transcript="Earn 5% per day, pay the withdrawal tax.")
    app = App(db=database.init(database.SqliteDatabase()), provider_factory=lambda: provider,
              context_factory=context_factory())
    status, body = post(app, "/api/analyze", {"images": [{"mime": "image/png", "data": base64.b64encode(b"x").decode()}]})
    assert status == 200 and body["verdict"] == "STOP" and body["transcript"]


def test_bad_json_and_unknown_route(app):
    assert app.handle("POST", "/api/analyze", "", b"{nope", {})[0] == 400
    assert app.handle("POST", "/api/analyze", "", b"[1]", {})[0] == 400
    assert app.handle("GET", "/api/nothing", "", b"", {})[0] == 404
    assert app.handle("GET", "/api/analyze", "", b"", {})[0] == 404


def test_reports_listing_and_search(app):
    status, body = app.handle("GET", "/api/reports", "q=novaapex.example", b"", {})
    assert status == 200 and len(body["reports"]) == 3
    assert body["alerts"][0]["reports"] == 9


def test_share_flow_with_review(app):
    story = "They promised 4% per day on Kopi Gains, then wanted a 20% withdrawal tax before I could withdraw."
    status, preview = post(app, "/api/reports/preview", {"story": story})
    assert status == 200 and "redacted" in preview
    status, body = post(app, "/api/reports", {"story": story, "outcome": "lost_money", "scam_type": "crypto",
                                               "confirmations": {"redaction": True, "truthful": True}})
    assert status == 200 and body["status"] == "pending"
    report_id = body["id"]

    assert app.handle("GET", "/api/admin/reports", "", b"", {})[0] == 403
    assert app.handle("GET", "/api/admin/reports", "", b"", {"X-Admin-Token": "wrong"})[0] == 403
    status, queue = app.handle("GET", "/api/admin/reports", "", b"", {"X-Admin-Token": "admin-test"})
    assert [r["id"] for r in queue["reports"]] == [report_id]

    status, _ = post(app, f"/api/admin/reports/{report_id}/approve", {}, {"X-Admin-Token": "admin-test"})
    assert status == 200
    _, listing = app.handle("GET", "/api/reports", "q=Kopi", b"", {})
    assert [r["id"] for r in listing["reports"]] == [report_id]
    assert post(app, f"/api/reports/{report_id}/helped", {})[0] == 200


def test_submit_validation_error(app):
    status, body = post(app, "/api/reports", {"story": "short"})
    assert status == 400 and "error" in body


def test_admin_disabled_without_token():
    app = App(db=database.init(database.SqliteDatabase()), admin_token="", context_factory=context_factory())
    assert app.handle("GET", "/api/admin/reports", "", b"", {"X-Admin-Token": ""})[0] == 403


def test_database_outage_does_not_break_checks():
    class Broken:
        def execute(self, *a, **k):
            raise database.DatabaseError("down")
        batch = execute
    app = App(db=Broken(), provider_factory=lambda: None, context_factory=context_factory())
    assert post(app, "/api/analyze", {"text": load_offer("michael")})[0] == 200
    assert app.handle("GET", "/api/reports", "", b"", {})[0] == 503


def test_meta(app):
    status, body = app.handle("GET", "/api/meta", "", b"", {})
    assert status == 200 and "snapshot" in body["fid"] and body["demo"] is True


def test_missing_hmac_secret_on_vercel_is_a_clear_503(monkeypatch, capsys):
    monkeypatch.setenv("VERCEL", "1")
    monkeypatch.delenv("PHONE_HMAC_SECRET", raising=False)

    def factory(network_lookup=None, secret=None, **_):
        ctx = make_ctx(network=network_lookup)
        ctx.secret = secret  # use the app's (missing) secret, not the test one
        return ctx

    app = App(db=database.init(database.SqliteDatabase()), provider_factory=lambda: None,
              context_factory=factory, secret=None)
    status, body = post(app, "/api/analyze", {"text": "Call me on +65 8000 4321, earn 3% per day"})
    assert status == 503 and "isn't fully set up" in body["error"]
    assert "PHONE_HMAC_SECRET" in capsys.readouterr().err
    # Offers without phone numbers still get checked.
    assert post(app, "/api/analyze", {"text": "Earn 3% per day"})[0] == 200
