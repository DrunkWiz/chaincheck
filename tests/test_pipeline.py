import re

import pytest

from backend import normalize, playbook, reality, verdict
from backend.flags import AMBER, RED, Flag
from backend.followups import apply, clean_answers, questions_for
from backend.pipeline import ScreenshotUnavailable, analyze
from backend.providers.fake import FakeProvider
from tests.conftest import entities, load_offer, make_ctx

PHONE_DIGITS = re.compile(r"8000\s?4321|6000\s?0101")


def flag(level):
    return Flag(level, "r", "t", "d", "s")


# --- Verdict --------------------------------------------------------------------

def test_any_red_is_stop():
    out = verdict.decide([flag(RED)])
    assert out["verdict"] == verdict.STOP and out["summary"] == "1 red flag"


def test_any_amber_is_stop():
    out = verdict.decide([flag(AMBER), flag(AMBER)])
    assert out["verdict"] == verdict.STOP and out["summary"] == "2 claims we couldn't verify"


def test_counts_wording():
    assert verdict.decide([flag(RED)] * 3 + [flag(AMBER)])["summary"] == "3 red flags, 1 claim we couldn't verify"


def test_no_flags_is_never_safe():
    out = verdict.decide([])
    assert out["verdict"] == verdict.NO_RED_FLAGS
    assert out["headline"] == "No red flags found. Verify these yourself before you pay."
    text = " ".join([out["headline"], out["summary"], *out["next_steps"]]).lower()
    for word in ("safe", "verified", "legit"):
        assert word not in text


# --- Playbook --------------------------------------------------------------------

def events(*signals):
    return [{"signal": s, "quote": s} for s in signals]


def test_stage_is_highest_present():
    s = playbook.stage(entities(events=events("group_invite", "withdrawal_succeeded", "expert_mentor")))
    assert (s["number"], s["name"]) == (5, "Small win")
    assert "bigger deposit" in s["next_move"]


def test_no_signals_no_stage():
    assert playbook.stage(entities()) is None


def test_payment_and_fees_imply_signals():
    e = entities(payment=[{"method": "cash_handover", "quote": None}])
    assert playbook.stage(e)["number"] == 6
    e = entities(fees=[{"type": "withdrawal_tax", "percent": 15, "amount": None, "quote": None}])
    assert playbook.stage(e)["number"] == 7


def test_every_schema_signal_has_a_stage():
    from backend.schema import EVENT_SIGNALS
    assert set(EVENT_SIGNALS) == set(playbook.SIGNAL_STAGE)


# --- Follow-up questions ---------------------------------------------------------------

def test_questions_for_missing_fields():
    assert [q["id"] for q in questions_for(entities(), {})] == ["payment", "withdrawal", "company"]


def test_answers_are_validated():
    assert clean_answers({"payment": "cash_handover", "withdrawal": "maybe", "evil": "x", "company": "  Acme  "}) == {
        "payment": "cash_handover", "company": "Acme"}
    assert clean_answers("nope") == {}


def test_answers_become_entities_and_questions_stop():
    answers = {"payment": "gold", "withdrawal": "blocked", "company": "Golden Lotus"}
    e = apply(entities(), answers)
    assert e["payment"][0]["method"] == "gold"
    assert e["events"][0]["signal"] == "withdrawal_blocked"
    assert e["companies"] == ["Golden Lotus"]
    assert questions_for(e, answers) == []


def test_answering_changes_the_verdict_only_toward_stop():
    text = "Hi, I have a great opportunity for you. Let me know if interested."
    before = analyze(text, None, make_ctx())
    after = analyze(text, None, make_ctx(), answers={"payment": "cash_handover"})
    assert before.verdict == verdict.NO_RED_FLAGS and before.incomplete
    assert after.verdict == verdict.STOP


# --- Reality Check -------------------------------------------------------------------

def test_reality_check():
    r = reality.reality_check(entities(returns=[{"percent": 32, "period": "month", "quote": "q"},
                                                {"percent": 9, "period": "unknown", "quote": "q"}]))
    assert len(r["claims"]) == 1
    assert r["claims"][0]["annual_text"] == "2,698%"
    assert r["claims"][0]["thousand_becomes"] == "$27,983"
    assert r["red_line_percent"] == 30.0
    assert reality.reality_check(entities()) is None


# --- Pipeline -----------------------------------------------------------------------

def test_michael_result_end_to_end(honest_model):
    result = analyze(load_offer("michael"), honest_model, make_ctx())
    rules = {f.rule for f in result.flags}
    assert {"copycat.contact_mismatch", "domain.very_new", "returns.too_high", "fees.withdrawal_tax",
            "payment.cash_handover", "person.claimed_title"} <= rules
    assert result.stage["number"] == 7
    assert result.flags[0].level == RED  # reds first
    assert not result.degraded


def test_same_input_same_result(honest_model):
    a = analyze(load_offer("justin"), honest_model, make_ctx()).to_dict()
    b = analyze(load_offer("justin"), honest_model, make_ctx()).to_dict()
    assert a == b


def test_extraction_is_cached(honest_model):
    analyze(load_offer("justin"), honest_model, make_ctx())
    analyze(load_offer("justin"), honest_model, make_ctx())
    assert len(honest_model.calls) == 1


def test_provider_failure_degrades_to_code_only():
    result = analyze(load_offer("michael"), FakeProvider.failing(), make_ctx())
    assert result.degraded and result.verdict == verdict.STOP


def test_no_stage_shown_without_stop(honest_model):
    assert analyze(load_offer("legit_broker"), honest_model, make_ctx()).stage is None


def test_phone_numbers_never_appear_in_output(honest_model):
    for name in ("michael", "legit_broker", "injection"):
        out = analyze(load_offer(name), honest_model, make_ctx()).to_dict()
        assert not PHONE_DIGITS.search(str(out)), name


def test_output_never_says_safe_verified_or_legit(honest_model):
    for name in ("michael", "justin", "legit_broker", "injection"):
        out = analyze(load_offer(name), honest_model, make_ctx()).to_dict()
        ours = " ".join([out["headline"], out["summary"], *out["next_steps"]] +
                        [f["title"] + " " + f["detail"] for f in out["flags"] if f["rule"] != "ai.concern"])
        assert not re.search(r"\b(safe|verified|legit)\b", ours, re.I), name


def test_every_flag_names_rule_and_source(honest_model):
    for name in ("michael", "justin", "injection"):
        for f in analyze(load_offer(name), honest_model, make_ctx()).flags:
            assert f.rule and f.source
            if f.rule.startswith(("mas.", "copycat.")):
                assert f.snapshot_date and f.snapshot_date in f.source


def test_chain_map(honest_model):
    chain = analyze(load_offer("michael"), honest_model, make_ctx()).chain
    by_kind = {n["kind"]: n for n in chain}
    assert by_kind["company"]["status"] == "red"
    assert by_kind["domain"]["label"] == "merlioncrest-capital[.]example"
    assert by_kind["phone"]["label"] == "1 phone number (hidden)"
    assert all(n["status_text"] for n in chain)


def test_screenshots_are_transcribed_then_checked():
    provider = FakeProvider(lambda offer: "{}", transcript="Earn 3% per day. Courier will collect cash.")
    result = analyze("", provider, make_ctx(), images=[("image/png", b"png")])
    assert result.verdict == verdict.STOP
    assert result.transcript.startswith("Earn")


def test_screenshots_without_model_raise():
    with pytest.raises(ScreenshotUnavailable):
        analyze("", None, make_ctx(), images=[("image/png", b"png")])
    with pytest.raises(ScreenshotUnavailable):
        analyze("", FakeProvider.failing(), make_ctx(), images=[("image/png", b"png")])


def test_evidence_summary(honest_model):
    out = analyze(load_offer("michael"), honest_model, make_ctx()).to_dict()
    assert out["evidence_summary"].startswith("ChainCheck result (2026-10-05): STOP")
    assert "Source:" in out["evidence_summary"]
    assert "DEMO data" in out["evidence_summary"]  # fixture snapshots are invented
    assert out["scamshield_url"] == "https://www.scamshield.gov.sg/"


def test_normalise_phone():
    assert normalize.phone("8000 4321") == "+6580004321"
    assert normalize.phone("+65-8000-4321") == "+6580004321"
    assert normalize.phone("6580004321") == "+6580004321"
    assert normalize.phone("+44 20 7946 0000") == "+442079460000"
