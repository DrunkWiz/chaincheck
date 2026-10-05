"""Domain age from RDAP (docs/BUILD_BRIEF.md §7).

Red if registered under DOMAIN_AGE_RED_DAYS ago, amber under
DOMAIN_AGE_AMBER_DAYS, amber if the lookup fails. Messaging, app-store and
shortener domains are skipped, and so are domains on a licensed firm's MAS
record. The clock and the lookup are injected through Context.
"""

import json
import urllib.request
from datetime import date

from backend import config, normalize
from backend.checks.copycat import _skip
from backend.flags import AMBER, RED, RULE_SOURCE, Flag

RDAP_SOURCE = "RDAP domain registration record"
_cache = {}


def check(entities, ctx):
    flags = []
    for raw in entities["domains"]:
        domain = normalize.domain(raw)
        if not domain or _skip(domain) or domain in ctx.on_record_domains:
            continue
        shown = normalize.defang(domain)
        created = ctx.rdap(domain)
        if created is None:
            flags.append(Flag(
                AMBER, "domain.age_unknown", f"Couldn't check when {shown} was created",
                "The domain registry didn't answer, so we can't tell how new this website is.",
                f"{RULE_SOURCE}: domain age", "domain", shown,
            ))
            continue
        age = (ctx.today - created).days
        when = f"{age} days ago ({created.isoformat()})"
        if age < config.DOMAIN_AGE_RED_DAYS:
            flags.append(Flag(
                RED, "domain.very_new", f"{shown} was created {when}",
                f"Websites under {config.DOMAIN_AGE_RED_DAYS} days old are a common sign of a scam platform. "
                "Real investment firms have been online for years.",
                RDAP_SOURCE, "domain", shown,
            ))
        elif age < config.DOMAIN_AGE_AMBER_DAYS:
            flags.append(Flag(
                AMBER, "domain.new", f"{shown} was created {when}",
                "This website is less than a year old.",
                RDAP_SOURCE, "domain", shown,
            ))
    return flags


def rdap_lookup(domain):
    """Creation date from rdap.org, or None. Cached per process."""
    if domain in _cache:
        return _cache[domain]
    created = None
    try:
        request = urllib.request.Request(
            f"https://rdap.org/domain/{domain}", headers={"Accept": "application/rdap+json"})
        with urllib.request.urlopen(request, timeout=config.RDAP_TIMEOUT_SECONDS) as response:
            created = registration_date(json.load(response))
    except Exception:  # any failure means "couldn't check"
        created = None
    _cache[domain] = created
    return created


def registration_date(rdap):
    for event in rdap.get("events", []):
        if event.get("eventAction") == "registration":
            return date.fromisoformat(event["eventDate"][:10])
    return None
