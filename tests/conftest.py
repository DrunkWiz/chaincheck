import json
import socket
from pathlib import Path

import pytest

from backend.prompt import neutralise
from backend.providers.fake import FakeProvider

FIXTURES = Path(__file__).parent / "fixtures"
OFFER_NAMES = ("michael", "justin", "legit_broker", "injection")


class NetworkBlocked(RuntimeError):
    pass


def _blocked(*args, **kwargs):
    raise NetworkBlocked("network access is not allowed in tests")


@pytest.fixture(autouse=True)
def no_network(monkeypatch):
    """Any attempt to open a connection or resolve a name fails the test."""
    monkeypatch.setattr(socket.socket, "connect", _blocked)
    monkeypatch.setattr(socket.socket, "connect_ex", _blocked)
    monkeypatch.setattr(socket, "create_connection", _blocked)
    monkeypatch.setattr(socket, "getaddrinfo", _blocked)


def load_offer(name):
    return (FIXTURES / "offers" / f"{name}.txt").read_text(encoding="utf-8")


def load_model_output(name):
    return (FIXTURES / "model_outputs" / f"{name}.json").read_text(encoding="utf-8")


def load_json(relative):
    return json.loads((FIXTURES / relative).read_text(encoding="utf-8"))


@pytest.fixture
def honest_model():
    """Fake gateway that replays the expected model output for each fixture offer."""
    script = {
        neutralise(load_offer(name)).strip("\n"): load_model_output(name)
        for name in OFFER_NAMES
    }
    return FakeProvider(script, name="fake-honest")
