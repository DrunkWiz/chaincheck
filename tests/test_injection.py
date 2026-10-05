"""The injection fixture must not change the verdict (docs/BUILD_BRIEF.md §12)."""

import pytest

from backend.pipeline import analyze
from backend.providers.fake import FakeProvider
from backend.verdict import STOP
from tests.conftest import load_json, load_offer, make_ctx


def test_injection_gets_same_verdict_as_clean_text(honest_model):
    clean = analyze(load_offer("michael"), honest_model, make_ctx())
    attacked = analyze(load_offer("injection"), honest_model, make_ctx())
    assert attacked.verdict == clean.verdict == STOP
    # Every red in the clean text is still red under attack.
    assert {f.rule for f in clean.flags if f.level == "red"} <= {f.rule for f in attacked.flags}


def test_hijacked_model_cannot_clear_a_scam():
    clean = analyze(load_offer("michael"), None, make_ctx())
    hijacked = analyze(load_offer("injection"), FakeProvider.hijacked(), make_ctx())
    assert hijacked.verdict == STOP
    assert {f.rule for f in clean.flags if f.level == "red"} <= {f.rule for f in hijacked.flags}


def test_injection_text_is_its_own_red_flag():
    result = analyze(load_offer("injection"), FakeProvider.hijacked(), make_ctx())
    assert "text.ai_instructions" in {f.rule for f in result.flags}


def test_hijacked_model_never_puts_reassurance_on_screen():
    result = analyze(load_offer("injection"), FakeProvider.hijacked(), make_ctx())
    shown = " ".join(f"{f.title} {f.detail}" for f in result.flags if f.rule == "ai.concern").lower()
    assert "verified" not in shown and "safe." not in shown


@pytest.mark.parametrize("name", ["michael", "justin", "legit_broker", "injection"])
def test_fixture_verdicts(name, honest_model):
    assert analyze(load_offer(name), honest_model, make_ctx()).verdict == load_json("expected_verdicts.json")[name]


@pytest.mark.parametrize("name", ["michael", "justin", "injection"])
def test_scam_fixtures_stop_even_with_no_model(name):
    assert analyze(load_offer(name), None, make_ctx()).verdict == STOP
