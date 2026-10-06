import json
import socket
from datetime import date
from pathlib import Path

import pytest

from backend import extract, schema, snapshots
from backend.checks import Context
from backend.prompt import neutralise
from backend.redact import for_model
from backend.providers.fake import FakeProvider

FIXTURES = Path(__file__).parent / "fixtures"
OFFER_NAMES = ("michael", "justin", "legit_broker", "injection")
TODAY = date(2026, 10, 5)
SECRET = "test-secret"

# Fixture RDAP answers. Anything missing means "lookup failed".
RDAP = {
    "merlioncrest-capital.example": date(2026, 9, 20),
    "quantedge-ai.example": date(2026, 8, 1),
    "harbourview-securities.example": date(2015, 1, 1),
    "old-site.example": date(2018, 1, 1),
    "medium-site.example": date(2026, 1, 1),
}


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


@pytest.fixture(autouse=True)
def fresh_cache():
    extract.clear_cache()
    yield
    extract.clear_cache()


def load_offer(name):
    return (FIXTURES / "offers" / f"{name}.txt").read_text(encoding="utf-8")


def load_model_output(name):
    return (FIXTURES / "model_outputs" / f"{name}.json").read_text(encoding="utf-8")


def load_json(relative):
    return json.loads((FIXTURES / relative).read_text(encoding="utf-8"))


def fixture_fid():
    return snapshots.load_file(FIXTURES / "mas" / "mas_fid_2026-10-01.json", "fid")


def fixture_ial():
    return snapshots.load_file(FIXTURES / "mas" / "mas_ial_2026-10-01.json", "ial")


def make_ctx(network=None, rdap=None, today=TODAY):
    return Context(fid=fixture_fid(), ial=fixture_ial(), today=today,
                   rdap=rdap or RDAP.get, network=network, secret=SECRET)


def context_factory(**overrides):
    """Drop-in for pipeline.make_context, using fixture data."""
    def factory(network_lookup=None, secret=None, **_):
        return make_ctx(network=network_lookup)
    return factory


def entities(**fields):
    e = schema.empty_entities()
    e.update(fields)
    return e


@pytest.fixture
def ctx():
    return make_ctx()


@pytest.fixture
def honest_model():
    """Fake gateway that replays the expected model output for each fixture offer."""
    script = {
        # The model only ever sees redacted text (redact.for_model).
        neutralise(for_model(load_offer(name))).strip("\n"): load_model_output(name)
        for name in OFFER_NAMES
    }
    return FakeProvider(script, name="fake-honest")
