"""Gemini over its REST API, standard library only.

Not exercised by the test suite (no network). `transport` is injectable so
the request and response handling can be tested offline.
"""

import json
import os
import urllib.error
import urllib.request

from backend import config
from backend.providers.base import ProviderError

API = "https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent"


def _urllib_transport(url, headers, body, timeout):
    request = urllib.request.Request(url, data=body, headers=headers, method="POST")
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            return json.load(response)
    except urllib.error.HTTPError as exc:
        raise ProviderError(f"HTTP {exc.code}") from None
    except (urllib.error.URLError, TimeoutError, OSError, ValueError) as exc:
        raise ProviderError(type(exc).__name__) from None


class GeminiProvider:
    def __init__(self, model, api_key=None, transport=_urllib_transport):
        self.model = model
        self.name = f"gemini:{model}"
        self.api_key = api_key or os.environ.get("GEMINI_API_KEY", "")
        self.transport = transport

    def _call(self, payload):
        if not self.api_key:
            raise ProviderError("GEMINI_API_KEY not set")
        reply = self.transport(
            API.format(model=self.model),
            {"Content-Type": "application/json", "x-goog-api-key": self.api_key},
            json.dumps(payload).encode(),
            config.MODEL_TIMEOUT_SECONDS,
        )
        try:
            parts = reply["candidates"][0]["content"]["parts"]
            return "".join(p.get("text", "") for p in parts)
        except (KeyError, IndexError, TypeError):
            raise ProviderError("unexpected response shape") from None

    def complete(self, system, user):
        return self._call({
            "systemInstruction": {"parts": [{"text": system}]},
            "contents": [{"role": "user", "parts": [{"text": user}]}],
            "generationConfig": {"temperature": 0, "responseMimeType": "application/json"},
        })


def default_chain():
    """Primary model, then the fallback rung. Code-only extraction is the last resort."""
    from backend.providers.fallback import FallbackProvider
    return FallbackProvider([
        GeminiProvider(os.environ.get("GEMINI_MODEL", config.GEMINI_MODEL_DEFAULT)),
        GeminiProvider(os.environ.get("GEMINI_FALLBACK_MODEL", config.GEMINI_FALLBACK_MODEL_DEFAULT)),
    ])
