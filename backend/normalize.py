"""Normalising and hashing entity values (docs/BUILD_BRIEF.md §7, §10)."""

import hashlib
import hmac
import os
import re
from difflib import SequenceMatcher

from backend import config

_DEV_SECRET = "dev-only-secret-do-not-deploy"


def company(name):
    """Lower-case, strip legal suffixes, punctuation and spaces."""
    value = " ".join(re.sub(r"[\W_]+", " ", name.lower()).split())
    for suffix in config.COMPANY_SUFFIXES:
        if value.endswith(" " + suffix):
            value = value[: -len(suffix)]
            break
    return value.replace(" ", "")


def similarity(a, b):
    """Similarity of two already-normalised company names, 0..1."""
    return SequenceMatcher(None, a, b).ratio()


def domain(value):
    """`https://WWW.Example.com:443/path` -> `example.com`. Email -> its domain."""
    value = value.strip().lower()
    if "@" in value and "/" not in value:
        value = value.rsplit("@", 1)[1]
    value = re.sub(r"^[a-z][a-z0-9+.-]*://", "", value)
    value = re.split(r"[/?#]", value, maxsplit=1)[0]
    value = value.split(":", 1)[0].rstrip(".")
    if value.startswith("www."):
        value = value[4:]
    return value


def phone(value):
    """Normalise to +<digits>. Bare 8-digit Singapore numbers get +65."""
    digits = re.sub(r"\D", "", value)
    if len(digits) == 8 and digits[0] in "3689":
        return "+65" + digits
    if len(digits) == 10 and digits.startswith("65") and digits[2] in "3689":
        return "+" + digits
    return "+" + digits if digits else ""


def account(value):
    return re.sub(r"\D", "", value)


def wallet(value):
    value = value.strip()
    return value.lower() if value.lower().startswith("0x") else value


class ConfigError(RuntimeError):
    """A required server setting is missing. Never fall back silently in production."""


def secret():
    value = os.environ.get("PHONE_HMAC_SECRET")
    if value:
        return value
    if is_hosted():
        raise ConfigError("PHONE_HMAC_SECRET must be set in the hosting dashboard")
    return _DEV_SECRET


def is_hosted():
    """True on a hosting platform, where dev fallbacks must never be used."""
    return bool(os.environ.get("VERCEL") or os.environ.get("RENDER"))


def keyed_hash(value, key=None):
    """HMAC so phones and accounts match across reports but can't be read back."""
    key = (key or secret()).encode()
    return hmac.new(key, value.encode(), hashlib.sha256).hexdigest()


def defang(domain_value):
    """`alphagain-pro.com` -> `alphagain-pro[.]com`."""
    return domain_value.replace(".", "[.]")


def short_wallet(value):
    return value if len(value) <= 14 else f"{value[:6]}…{value[-4:]}"
