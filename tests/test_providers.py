import pytest

from backend.extract import extract
from backend.prompt import build_extraction_prompt
from backend.providers.base import ProviderError
from backend.providers.fake import FakeProvider
from backend.providers.fallback import AllProvidersFailed, FallbackProvider


def _ask(provider, text="offer"):
    return provider.complete(*build_extraction_prompt(text))


def test_fake_string_script():
    fake = FakeProvider('{"companies": []}')
    assert _ask(fake) == '{"companies": []}'
    assert fake.calls == ["offer"]


def test_fake_dict_script_is_keyed_by_offer_text():
    fake = FakeProvider({"a": "reply a", "b": "reply b"})
    assert _ask(fake, "b") == "reply b"
    with pytest.raises(ProviderError):
        _ask(fake, "c")


def test_fake_callable_script():
    fake = FakeProvider(lambda offer: offer.upper())
    assert _ask(fake, "abc") == "ABC"


def test_fake_failing_raises_provider_error():
    with pytest.raises(ProviderError):
        _ask(FakeProvider.failing())


def test_fallback_uses_first_working_provider():
    chain = FallbackProvider([FakeProvider.failing(), FakeProvider("ok", name="second")])
    assert _ask(chain) == "ok"
    assert chain.last_used == "second"


def test_fallback_raises_when_all_fail():
    chain = FallbackProvider([FakeProvider.failing("down"), FakeProvider.failing("quota")])
    with pytest.raises(AllProvidersFailed, match="down.*quota"):
        _ask(chain)
    assert chain.last_used is None


def test_fallback_does_not_swallow_programming_errors():
    chain = FallbackProvider([FakeProvider(ValueError("bug")), FakeProvider("ok")])
    with pytest.raises(ValueError):
        _ask(chain)


def test_fallback_needs_a_provider():
    with pytest.raises(ValueError):
        FallbackProvider([])


def test_hijacked_model_output_is_stripped_to_schema():
    result = extract("anything", FakeProvider.hijacked())
    assert "verdict" not in result.entities and "note" not in result.entities
    assert result.entities["companies"] == []
    # The reassuring reason never reaches the user.
    assert all("safe" not in c["reason"].lower() for c in result.entities["concerns"])
