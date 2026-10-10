import pytest

from backend import community, db as database
from backend.pipeline import analyze
from backend.verdict import STOP
from backend import demo_seed as seed_reports
from tests.conftest import SECRET, make_ctx

STORY = ("A man called Mr Daniel Koh added me to a Telegram group. He said AlphaGain Pro paid 3% per day. "
         "I sent USDT to 0x4b2e9f1a7c3d5e8b0a6f2c4d9e1b3a5c7d8e0f2a and called him on +65 8000 7777. "
         "My NRIC S1234567D was asked for. Site alphagain-pro.example.")
CONFIRM = {"redaction": True, "truthful": True}


@pytest.fixture
def db():
    return database.init(database.SqliteDatabase())


def submit(db, story=STORY, **kw):
    return community.submit(db, story, kw.pop("outcome", "lost_money"), kw.pop("scam_type", "crypto"),
                            kw.pop("confirmations", CONFIRM), None, make_ctx(), secret=SECRET, **kw)


def test_preview_redacts_and_lists_entities():
    out = community.preview(STORY, None, make_ctx(), secret=SECRET)
    assert "Daniel Koh" not in out["redacted"] and "S1234567D" not in out["redacted"]
    assert "8000 7777" not in out["redacted"]
    assert "alphagain-pro.example" in out["redacted"]
    kinds = {e["kind"] for e in out["entities"]}
    assert {"domain", "wallet", "phone_hash"} <= kinds
    assert all("8000" not in e["display"] for e in out["entities"])
    assert out["verdict"] == STOP


def test_submit_requires_confirmations_and_valid_choices(db):
    with pytest.raises(community.ReportError):
        submit(db, confirmations={"redaction": True})
    with pytest.raises(community.ReportError):
        submit(db, outcome="won")
    with pytest.raises(community.ReportError):
        submit(db, story="too short")


def test_submitted_reports_wait_for_review(db):
    report_id = submit(db)
    assert community.list_reports(db) == []
    pending = community.pending(db)
    assert [r["id"] for r in pending] == [report_id]
    stored = db.execute("SELECT story FROM reports")[0]["story"]
    assert "Daniel Koh" not in stored and "S1234567D" not in stored and "8000 7777" not in stored


def test_phone_stored_only_as_hash(db):
    submit(db)
    values = [r["value"] for r in db.execute("SELECT value FROM entities WHERE kind = 'phone_hash'")]
    assert values and all("8000" not in v and len(v) == 64 for v in values)


def test_approve_publishes_and_reject_hides(db):
    a, b = submit(db), submit(db)
    community.review(db, a, approve=True)
    community.review(db, b, approve=False)
    assert [r["id"] for r in community.list_reports(db)] == [a]
    with pytest.raises(community.ReportError):
        community.review(db, "0" * 16, approve=True)


def test_public_view_hides_phones_and_defangs(db):
    community.review(db, submit(db), approve=True)
    report = community.list_reports(db)[0]
    displays = [e["display"] for e in report["entities"]]
    assert "alphagain-pro[.]example" in displays
    assert "A phone number (hidden)" in displays


def test_helped_counter(db):
    rid = submit(db)
    community.mark_helped(db, rid)  # pending: ignored
    community.review(db, rid, approve=True)
    community.mark_helped(db, rid)
    assert community.list_reports(db)[0]["helped"] == 1


def test_licensed_firm_details_are_never_linked(db):
    story = ("Someone said they were from Merlion Crest Capital and gave the real number +65 6000 0202 "
             "but wanted cash. Their other site was merlioncrestcapital.example.")
    submit(db, story=story)
    kinds = {(r["kind"], r["value"]) for r in db.execute("SELECT kind, value FROM entities")}
    assert ("company", "merlioncrestcapital") not in kinds
    assert ("domain", "merlioncrestcapital.example") not in kinds
    assert not any(k == "phone_hash" for k, _ in kinds)


def test_seed_builds_one_network_of_nine(db):
    ids = seed_reports.seed(db, make_ctx(), secret=SECRET)
    assert len(ids) == 12
    alerts = community.network_alerts(db)
    assert alerts[0]["reports"] == 9
    names = " ".join(alerts[0]["names"]).lower()
    assert "alphagain" in names and "nova apex" in names and "lumen yield" in names
    assert all(r["synthetic"] for r in community.list_reports(db))


def test_search(db):
    seed_reports.seed(db, make_ctx(), secret=SECRET)
    assert len(community.list_reports(db, "novaapex.example")) == 3
    assert len(community.list_reports(db, "https://www.lumenyield.example/")) == 3
    assert len(community.list_reports(db, "Nova Apex Trading Pte. Ltd.")) == 3
    assert len(community.list_reports(db, "0x9c1d3e5f7a2b4c6d8e0f1a3b5c7d9e2f4a6b8c0d")) == 2
    assert len(community.list_reports(db, scam_type="fund_recovery")) == 1
    assert community.list_reports(db, "nothing-like-this") == []


def test_network_feeds_the_checker(db):
    seed_reports.seed(db, make_ctx(), secret=SECRET)
    index = community.NetworkIndex(db)
    offer = "New platform Zeta Prime, send USDT to 0x4b2e9f1a7c3d5e8b0a6f2c4d9e1b3a5c7d8e0f2a. WhatsApp +65 8000 7777."
    result = analyze(offer, None, make_ctx(network=index.lookup))
    network_flags = [f for f in result.flags if f.rule == "network.seen_in_reports"]
    assert len(network_flags) == 2
    assert any("network of 9 reports" in f.detail for f in network_flags)
    assert not any("8000" in f.title + f.detail for f in result.flags)


def test_copycat_reports_never_say_scam_about_the_real_firm(db):
    seed_reports.seed(db, make_ctx(), secret=SECRET)
    result = analyze("Merlion Crest Capital here, call +65 8000 4321", None,
                     make_ctx(network=community.NetworkIndex(db).lookup))
    assert "copycat.contact_mismatch" in {f.rule for f in result.flags}
    # The copycat's phone was reported once; the licensed name itself is never a network flag.
    assert "network.copycat_reports" not in {f.rule for f in result.flags}


def test_seeding_twice_adds_nothing(db):
    seed_reports.seed(db, make_ctx(), secret=SECRET)
    seed_reports.seed(db, make_ctx(), secret=SECRET)
    assert len(community.list_reports(db)) == 12
    assert seed_reports.seed_if_empty(db, make_ctx(), secret=SECRET) == 0
