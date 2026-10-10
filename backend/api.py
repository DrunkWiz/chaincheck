"""HTTP routes (docs/BUILD_BRIEF.md §11), framework-free.

`App.handle(method, path, query, body, headers)` returns (status, payload).
`backend/server.py` serves it locally; `backend/wsgi.py` serves it on Vercel.
"""

import hmac
import json
import os
import re
import sys
from urllib.parse import parse_qs

from backend import community, config, db as database, normalize, pipeline, snapshots
from backend.providers.base import ProviderError


class HttpError(Exception):
    def __init__(self, status, message):
        super().__init__(message)
        self.status = status
        self.message = message


class App:
    def __init__(self, db=None, provider_factory=None, context_factory=None, admin_token=None, secret=None):
        self._db = db
        self.provider_factory = provider_factory or _default_provider
        self.context_factory = context_factory or pipeline.make_context
        self.admin_token = admin_token if admin_token is not None else os.environ.get("ADMIN_TOKEN", "")
        self.secret = secret

    @property
    def db(self):
        if self._db is None:
            db = database.from_env()
            if os.environ.get("SEED_DEMO_REPORTS") == "1":
                # First start on a fresh database: add the labelled synthetic reports.
                from backend.demo_seed import seed_if_empty
                seed_if_empty(db, pipeline.make_context(rdap=lambda _domain: None), self.secret)
            self._db = db
        return self._db

    def context(self, with_network=True):
        lookup = None
        if with_network:
            try:
                lookup = community.network_index(self.db).lookup
            except database.DatabaseError:
                lookup = None  # community data unavailable: checks still run
        return self.context_factory(network_lookup=lookup, secret=self.secret)

    # --- dispatch ---------------------------------------------------------

    def handle(self, method, path, query="", body=b"", headers=None):
        headers = {k.lower(): v for k, v in (headers or {}).items()}
        try:
            if len(body or b"") > config.MAX_BODY_BYTES:
                raise HttpError(413, "That's too much to check at once.")
            params = {k: v[0] for k, v in parse_qs(query or "").items()}
            data = _json(body) if method == "POST" else {}
            for pattern, route_method, handler in ROUTES:
                match = re.fullmatch(pattern, path.rstrip("/") or "/")
                if match and route_method == method:
                    return 200, handler(self, data=data, params=params, headers=headers, **match.groupdict())
            raise HttpError(404, "Not found.")
        except HttpError as exc:
            return exc.status, {"error": exc.message}
        except community.ReportError as exc:
            return 400, {"error": str(exc)}
        except database.DatabaseError:
            return 503, {"error": "Community reports are unavailable right now. Checks still work."}
        except normalize.ConfigError as exc:
            print(f"ChainCheck config error: {exc}", file=sys.stderr)  # names the variable, never its value
            return 503, {"error": "ChainCheck isn't fully set up yet, so we can't check this right now. "
                                  "Please try again later."}

    # --- routes -------------------------------------------------------------

    def meta(self, **_):
        fid, ial = snapshots.load_latest("fid"), snapshots.load_latest("ial")
        return {
            "fid": fid.label, "ial": ial.label, "demo": fid.demo or ial.demo,
            "scam_types": list(config.SCAM_TYPES), "outcomes": list(config.OUTCOMES),
            "scamshield_url": "https://www.scamshield.gov.sg/",
        }

    def analyze(self, data, **_):
        text = data.get("text") or ""
        if not isinstance(text, str):
            raise HttpError(400, "Text must be a string.")
        if len(text) > config.MAX_TEXT_CHARS:
            raise HttpError(400, f"Please paste under {config.MAX_TEXT_CHARS:,} characters.")
        if data.get("images"):
            # Screenshots are read on the user's device; images never reach the server.
            raise HttpError(400, "Send the text only. Screenshots are read in your browser.")
        if not text.strip():
            raise HttpError(400, "Paste the offer or add a screenshot first.")
        result = pipeline.analyze(text, self.provider_factory(), self.context(),
                                  answers=data.get("answers") or {})
        return result.to_dict()

    def reports(self, params, **_):
        return {"reports": community.list_reports(self.db, params.get("q", ""), params.get("type", "")),
                "alerts": community.network_alerts(self.db)}

    def network(self, **_):
        return {"alerts": community.network_alerts(self.db)}

    def preview(self, data, **_):
        return community.preview(data.get("story"), self.provider_factory(), self.context(False), self.secret)

    def submit(self, data, **_):
        report_id = community.submit(
            self.db, data.get("story"), data.get("outcome"), data.get("scam_type"),
            data.get("confirmations") or {}, self.provider_factory(), self.context(False), self.secret)
        return {"id": report_id, "status": "pending"}

    def helped(self, report_id, **_):
        community.mark_helped(self.db, report_id)
        return {"ok": True}

    def admin_pending(self, headers, **_):
        self._require_admin(headers)
        return {"reports": community.pending(self.db)}

    def admin_review(self, headers, report_id, action, **_):
        self._require_admin(headers)
        community.review(self.db, report_id, approve=(action == "approve"))
        return {"ok": True}

    def _require_admin(self, headers):
        token = headers.get("x-admin-token", "")
        if not self.admin_token or not hmac.compare_digest(token.encode(), self.admin_token.encode()):
            raise HttpError(403, "Admin token required.")


ROUTES = (
    (r"/api/meta", "GET", App.meta),
    (r"/api/analyze", "POST", App.analyze),
    (r"/api/reports", "GET", App.reports),
    (r"/api/search", "GET", App.reports),
    (r"/api/network", "GET", App.network),
    (r"/api/reports/preview", "POST", App.preview),
    (r"/api/reports", "POST", App.submit),
    (r"/api/reports/(?P<report_id>[0-9a-f]{16})/helped", "POST", App.helped),
    (r"/api/admin/reports", "GET", App.admin_pending),
    (r"/api/admin/reports/(?P<report_id>[0-9a-f]{16})/(?P<action>approve|reject)", "POST", App.admin_review),
)


def _json(body):
    if not body:
        return {}
    try:
        data = json.loads(body)
    except (ValueError, UnicodeDecodeError):
        raise HttpError(400, "Body must be JSON.") from None
    if not isinstance(data, dict):
        raise HttpError(400, "Body must be a JSON object.")
    return data


def _default_provider():
    """Real model chain when a key is set; otherwise code-only extraction."""
    if not os.environ.get("GEMINI_API_KEY"):
        return None
    from backend.providers.gemini import default_chain
    return default_chain()


__all__ = ["App", "HttpError", "ProviderError"]
