import csv
import json

import pytest

from backend import snapshots
from backend.providers.base import ProviderError
from backend.providers.gemini import GeminiProvider
from scripts import run_accuracy, snapshot_mas


class Transport:
    def __init__(self, reply):
        self.reply = reply
        self.calls = []

    def __call__(self, url, headers, body, timeout):
        self.calls.append((url, headers, json.loads(body)))
        if isinstance(self.reply, Exception):
            raise self.reply
        return self.reply


OK = {"candidates": [{"content": {"parts": [{"text": '{"companies": []}'}]}}]}


def test_gemini_request_shape():
    transport = Transport(OK)
    provider = GeminiProvider("gemini-test", api_key="k", transport=transport)
    assert provider.complete("sys", "user") == '{"companies": []}'
    url, headers, body = transport.calls[0]
    assert "models/gemini-test:generateContent" in url
    assert headers["x-goog-api-key"] == "k" and "k" not in url
    assert body["generationConfig"]["temperature"] == 0
    assert body["systemInstruction"]["parts"][0]["text"] == "sys"


@pytest.mark.parametrize("reply", [{}, {"candidates": []}, ProviderError("HTTP 429")])
def test_gemini_failures_are_provider_errors(reply):
    with pytest.raises(ProviderError):
        GeminiProvider("m", api_key="k", transport=Transport(reply)).complete("s", "u")


def test_gemini_without_key(monkeypatch):
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)
    with pytest.raises(ProviderError, match="not set"):
        GeminiProvider("m").complete("s", "u")


def test_real_snapshot_beats_demo(tmp_path):
    (tmp_path / "demo_mas_fid_2026-10-05.json").write_text(json.dumps({"snapshot_date": "2026-10-05", "institutions": []}))
    assert snapshots.latest_path("fid", tmp_path).name.startswith("demo_")
    (tmp_path / "mas_fid_2026-09-01.json").write_text(json.dumps({"snapshot_date": "2026-09-01", "institutions": []}))
    assert snapshots.latest_path("fid", tmp_path).name == "mas_fid_2026-09-01.json"


def test_demo_snapshot_is_labelled():
    snap = snapshots.load_latest("fid")
    assert snap.demo and snap.label.startswith("DEMO data")


def test_snapshot_converter(tmp_path):
    path = tmp_path / "fid.csv"
    with open(path, "w", newline="", encoding="utf-8") as handle:
        writer = csv.writer(handle)
        writer.writerow(["Organisation Name", "Website", "Phone", "Licence Type"])
        writer.writerow(["Acme Securities Pte. Ltd.", "www.acme.example", "6000 1234", "CMS"])
        writer.writerow(["", "", "", ""])
    with open(path, newline="", encoding="utf-8") as handle:
        reader = csv.DictReader(handle)
        out = snapshot_mas.convert("fid", list(reader), reader.fieldnames, "2026-10-06", {})
    assert out["snapshot_date"] == "2026-10-06"
    assert out["institutions"] == [{"name": "Acme Securities Pte. Ltd.", "websites": ["www.acme.example"],
                                    "licence": "CMS", "phones": ["6000 1234"], "email_domains": []}]
    snap = snapshots.parse(out, "fid")
    assert snap.firms[0].websites == {"acme.example"} and not snap.demo


def test_accuracy_set_runs_offline():
    report = run_accuracy.run()
    assert (report["scams"], report["legit"]) == (20, 20)
    # Regression floor for code-only mode, not a claim. Update when rules change.
    assert report["hits"] >= 19
    assert report["false_alarms"] <= 2
