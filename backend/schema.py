"""Extraction schema and validator (docs/BUILD_BRIEF.md §6).

The model's output is untrusted. `validate` keeps only well-formed items in
known fields and records everything it threw away. It never raises on bad
model output: the worst case is an empty entity set, which the code-side
extractor then backs up.
"""

import json
import math
import re
from dataclasses import dataclass, field

from backend import config

APP_SOURCES = ("app_store", "link", "unknown")

RETURN_PERIODS = ("day", "week", "month", "year", "unknown")

FEE_TYPES = (
    "withdrawal_tax",      # "tax" to take your own money out
    "unlock_fee",          # fee to unfreeze or release an account
    "withdrawal_fee",      # any other fee to withdraw
    "trading_commission",
    "management_fee",
    "other",
)

PAYMENT_METHODS = (
    "bank_transfer",
    "paynow",
    "card",
    "cash_handover",
    "gold",
    "crypto",
    "other",
)

# Fixed event vocabulary, grouped by the playbook stage it signals (§9).
EVENT_SIGNALS = (
    # 1 Hook
    "public_figure_ad", "secret_method",
    # 2 Capture
    "registered", "group_invite",
    # 3 Contact
    "overseas_call", "account_manager", "daily_follow_up",
    # 4 Trust building
    "expert_mentor", "members_posting_profits", "stock_picks",
    # 5 Small win
    "private_app_invite", "small_deposit", "withdrawal_succeeded", "balance_rising_fast",
    # 6 Big ask
    "institutional_programme", "cash_requested", "gold_requested",
    "crypto_to_new_wallet", "large_transfer",
    # 7 Lockout
    "withdrawal_blocked", "withdrawal_tax_demanded", "minimum_trading_commitment",
    "account_frozen", "fund_recovery_offer",
)

FIELDS = (
    "people", "companies", "apps", "domains", "phones", "emails", "accounts",
    "wallets", "returns", "fees", "payment", "events", "concerns",
)

_BANNED = re.compile(config.BANNED_DISPLAY_WORDS_PATTERN, re.IGNORECASE)


@dataclass
class Validated:
    entities: dict
    discarded: list = field(default_factory=list)


def empty_entities():
    return {name: [] for name in FIELDS}


def validate(raw):
    """Validate model output (a JSON string or a parsed object)."""
    result = Validated(empty_entities())
    if isinstance(raw, (str, bytes)):
        try:
            raw = json.loads(raw)
        except (ValueError, RecursionError):
            result.discarded.append("output: not valid JSON")
            return result
    if not isinstance(raw, dict):
        result.discarded.append("output: not a JSON object")
        return result

    for key in raw:
        if key not in FIELDS:
            result.discarded.append(f"{key}: unknown field")

    for name in FIELDS:
        if name not in raw:
            continue
        items = raw[name]
        if not isinstance(items, list):
            result.discarded.append(f"{name}: not a list")
            continue
        clean_item = _VALIDATORS[name]
        for index, item in enumerate(items):
            if len(result.entities[name]) >= config.MAX_LIST_ITEMS:
                result.discarded.append(f"{name}: over {config.MAX_LIST_ITEMS} items")
                break
            cleaned = clean_item(item)
            if cleaned is None:
                result.discarded.append(f"{name}[{index}]: invalid")
            elif cleaned not in result.entities[name]:
                result.entities[name].append(cleaned)
    return result


# --- Field validators: return the cleaned item, or None to discard ----------

def _text(value, limit=config.MAX_STRING_CHARS, required=True):
    if value is None and not required:
        return None
    if not isinstance(value, str):
        return _INVALID
    value = " ".join(value.split())
    if not value:
        return _INVALID if required else None
    return value[:limit]


def _number(value, required=True):
    if value is None and not required:
        return None
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        return _INVALID
    if not math.isfinite(value) or value < 0 or value > config.MAX_PERCENT:
        return _INVALID
    return float(value)


def _choice(value, allowed):
    return value if isinstance(value, str) and value in allowed else _INVALID


class _Invalid:
    pass


_INVALID = _Invalid()


def _record(item, spec):
    """Clean a dict item against {key: cleaner}. Extra keys are dropped."""
    if not isinstance(item, dict):
        return None
    out = {}
    for key, clean in spec.items():
        value = clean(item.get(key))
        if value is _INVALID:
            return None
        out[key] = value
    return out


def _plain(item):
    value = _text(item)
    return None if value is _INVALID else value


def _domain(item):
    value = _plain(item)
    return value.lower() if value else None


def _quote(value):
    return _text(value, config.MAX_QUOTE_CHARS, required=False)


def _concern(item):
    cleaned = _record(item, {
        "text": lambda v: _text(v, config.MAX_CONCERN_CHARS),
        "reason": lambda v: _text(v, config.MAX_CONCERN_CHARS),
    })
    if cleaned and _BANNED.search(cleaned["reason"]):
        # Keep the amber (never lower concern) but don't show the model's words.
        cleaned["reason"] = config.WITHHELD_REASON
    return cleaned


_VALIDATORS = {
    "people": lambda i: _record(i, {
        "name": _text,
        "claimed_title": lambda v: _text(v, required=False),
    }),
    "companies": _plain,
    "apps": lambda i: _record(i, {
        "name": _text,
        "source": lambda v: _choice(v, APP_SOURCES),
    }),
    "domains": _domain,
    "phones": _plain,
    "emails": _domain,
    "accounts": lambda i: _record(i, {
        "bank": lambda v: _text(v, required=False),
        "number": _text,
    }),
    "wallets": _plain,
    "returns": lambda i: _record(i, {
        "percent": _number,
        "period": lambda v: _choice(v, RETURN_PERIODS),
        "quote": _quote,
    }),
    "fees": lambda i: _record(i, {
        "type": lambda v: _choice(v, FEE_TYPES),
        "percent": lambda v: _number(v, required=False),
        "amount": lambda v: _number(v, required=False),
        "quote": _quote,
    }),
    "payment": lambda i: _record(i, {
        "method": lambda v: _choice(v, PAYMENT_METHODS),
        "quote": _quote,
    }),
    "events": lambda i: _record(i, {
        "signal": lambda v: _choice(v, EVENT_SIGNALS),
        "quote": _quote,
    }),
    "concerns": _concern,
}
