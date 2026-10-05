"""The injection fixture must not change the verdict (docs/BUILD_BRIEF.md §12).

Marked xfail until the pipeline exists. xfail is strict, so these turn into
failures the moment they pass: remove the marker then.
"""

import pytest

from backend.pipeline import analyze
from backend.providers.fake import FakeProvider
from tests.conftest import load_json, load_offer

pending = pytest.mark.xfail(raises=NotImplementedError, reason="pipeline lands 7–9 Oct")


@pending
def test_injection_gets_same_verdict_as_clean_text(honest_model):
    clean = analyze(load_offer("michael"), honest_model)
    attacked = analyze(load_offer("injection"), honest_model)
    assert attacked.verdict == clean.verdict == "STOP"


@pending
def test_hijacked_model_cannot_clear_a_scam():
    # Code-side extraction must still find the cash handover, the 32% a month
    # and the withdrawal tax, even when the model returns nothing useful.
    result = analyze(load_offer("injection"), FakeProvider.hijacked())
    assert result.verdict == "STOP"


@pending
@pytest.mark.parametrize("name", ["michael", "justin", "legit_broker", "injection"])
def test_fixture_verdicts(name, honest_model):
    assert analyze(load_offer(name), honest_model).verdict == load_json("expected_verdicts.json")[name]
