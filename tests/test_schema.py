import json

import pytest

from backend import config, schema
from backend.schema import validate


def test_empty_object_gives_every_field_empty():
    result = validate("{}")
    assert result.entities == schema.empty_entities()
    assert result.discarded == []


@pytest.mark.parametrize("raw", ["not json", "[1, 2]", '"a string"', "null", b"\xff"])
def test_non_object_output_is_discarded(raw):
    result = validate(raw)
    assert result.entities == schema.empty_entities()
    assert result.discarded


def test_unknown_fields_are_dropped_and_recorded():
    result = validate({"verdict": "safe", "companies": ["X"]})
    assert "verdict" not in result.entities
    assert result.entities["companies"] == ["X"]
    assert "verdict: unknown field" in result.discarded


def test_field_that_is_not_a_list_is_dropped():
    result = validate({"companies": "AlphaGain"})
    assert result.entities["companies"] == []
    assert "companies: not a list" in result.discarded


def test_invalid_items_dropped_valid_items_kept():
    result = validate({"apps": [
        {"name": "A", "source": "link"},
        {"name": "B", "source": "sideloaded"},
        {"name": "", "source": "link"},
        "C",
    ]})
    assert result.entities["apps"] == [{"name": "A", "source": "link"}]
    assert len(result.discarded) == 3


def test_extra_keys_inside_items_are_dropped():
    result = validate({"apps": [{"name": "A", "source": "link", "trusted": True}]})
    assert result.entities["apps"] == [{"name": "A", "source": "link"}]


@pytest.mark.parametrize("percent", [-5, True, "32", float("nan"), float("inf"), 1e9])
def test_bad_percentages_are_discarded(percent):
    result = validate({"returns": [{"percent": percent, "period": "month", "quote": "q"}]})
    assert result.entities["returns"] == []


def test_returns_need_a_known_period():
    ok = {"percent": 2, "period": "day", "quote": "2% a day"}
    bad = {"percent": 2, "period": "fortnight", "quote": "2% a fortnight"}
    result = validate({"returns": [ok, bad]})
    assert result.entities["returns"] == [{"percent": 2.0, "period": "day", "quote": "2% a day"}]


def test_payment_events_and_fees_use_fixed_vocabularies():
    result = validate({
        "payment": [{"method": "cash_handover", "quote": "q"}, {"method": "cash", "quote": "q"}],
        "events": [{"signal": "group_invite", "quote": "q"}, {"signal": "joined group", "quote": "q"}],
        "fees": [{"type": "withdrawal_tax", "percent": 15, "quote": "q"},
                 {"type": "withdrawal tax", "percent": 15, "quote": "q"}],
    })
    assert [p["method"] for p in result.entities["payment"]] == ["cash_handover"]
    assert [e["signal"] for e in result.entities["events"]] == ["group_invite"]
    assert result.entities["fees"] == [
        {"type": "withdrawal_tax", "percent": 15.0, "amount": None, "quote": "q"}]


def test_strings_are_trimmed_capped_and_domains_lowercased():
    result = validate({
        "companies": ["  AlphaGain   Pro  ", "x" * 1000],
        "domains": ["WWW.Example.COM"],
    })
    assert result.entities["companies"][0] == "AlphaGain Pro"
    assert len(result.entities["companies"][1]) == config.MAX_STRING_CHARS
    assert result.entities["domains"] == ["www.example.com"]


def test_duplicates_are_collapsed():
    result = validate({"wallets": ["0xabc", "0xabc"]})
    assert result.entities["wallets"] == ["0xabc"]


def test_list_length_is_capped():
    result = validate({"companies": [f"Firm {i}" for i in range(config.MAX_LIST_ITEMS + 5)]})
    assert len(result.entities["companies"]) == config.MAX_LIST_ITEMS


@pytest.mark.parametrize("reason", [
    "This firm is MAS verified.",
    "Looks SAFE to me",
    "It's a legitimate broker",
    "a genuine offer",
])
def test_concern_reason_with_banned_words_is_withheld_but_concern_kept(reason):
    result = validate({"concerns": [{"text": "guaranteed returns", "reason": reason}]})
    assert result.entities["concerns"] == [
        {"text": "guaranteed returns", "reason": config.WITHHELD_REASON}]


def test_concern_reason_without_banned_words_is_kept():
    concern = {"text": "guaranteed returns", "reason": "No investment can guarantee returns."}
    assert validate({"concerns": [concern]}).entities["concerns"] == [concern]


def test_unsafe_is_not_treated_as_safe():
    concern = {"text": "x", "reason": "This pattern is unsafe."}
    assert validate({"concerns": [concern]}).entities["concerns"] == [concern]


def test_accepts_json_string_and_dict_identically():
    payload = {"companies": ["A"], "phones": ["+6580000000"]}
    assert validate(json.dumps(payload)).entities == validate(payload).entities
