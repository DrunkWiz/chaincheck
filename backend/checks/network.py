"""Community network check (docs/BUILD_BRIEF.md §7, §10).

Red "seen in N reports" when an entity appears in approved community reports.
A MAS-licensed firm's name, website or phone is never flagged from reports,
unless several reports name it *and* this offer is already a copycat of it.

Script similarity (embeddings) is cut for now (BUILD_BRIEF §13 cut order).
"""

from dataclasses import dataclass

from backend import config, normalize
from backend.checks.copycat import _skip
from backend.checks.fuzzy import is_platform
from backend.flags import RED, Flag

SOURCE = "ChainCheck community reports (reviewed before publishing)"
LINK_APP = "App installed from a link"


@dataclass(frozen=True)
class Hit:
    reports: int          # approved reports containing this entity
    cluster_reports: int  # reports in its network
    names: tuple          # names seen across that network


def entity_keys(entities, secret=None):
    """[(kind, key, display)] for linking and lookups. Phones and accounts are hashed."""
    keys = []
    for name in entities["companies"]:
        if not is_platform(name) and normalize.company(name):
            keys.append(("company", normalize.company(name), name))
    for app in entities["apps"]:
        if app["name"] != LINK_APP and not is_platform(app["name"]) and normalize.company(app["name"]):
            keys.append(("app", normalize.company(app["name"]), app["name"]))
    for raw in entities["domains"]:
        d = normalize.domain(raw)
        if d and not _skip(d):
            keys.append(("domain", d, normalize.defang(d)))
    for raw in entities["emails"]:
        keys.append(("email", raw.lower(), normalize.defang(raw.lower())))
    for raw in entities["wallets"]:
        w = normalize.wallet(raw)
        keys.append(("wallet", w, normalize.short_wallet(w)))
    for raw in entities["phones"]:
        p = normalize.phone(raw)
        if p:
            keys.append(("phone_hash", normalize.keyed_hash(p, secret), "A phone number"))
    for acc in entities["accounts"]:
        a = normalize.account(acc["number"])
        if a:
            keys.append(("account_hash", normalize.keyed_hash(a, secret), "A bank account"))
    seen, unique = set(), []
    for k in keys:
        if k[:2] not in seen:
            seen.add(k[:2])
            unique.append(k)
    return unique


def licensed_keys(fid):
    """Keys that belong to MAS-licensed firms; reports alone never flag these."""
    keys = set()
    for firm in fid.firms:
        keys.add(("company", firm.key))
        keys.add(("app", firm.key))
        keys.update(("domain", d) for d in firm.websites)
    return keys


def check(entities, ctx):
    if ctx.network is None:
        return []
    licensed = licensed_keys(ctx.fid)
    licensed_phones = {normalize.keyed_hash(p, ctx.secret) for f in ctx.fid.firms for p in f.phones}
    flags = []
    for kind, key, display in entity_keys(entities, ctx.secret):
        hit = ctx.network(kind, key)
        if not hit or hit.reports < 1:
            continue
        if (kind, key) in licensed or (kind == "phone_hash" and key in licensed_phones):
            if not (kind == "company" and key in ctx.copycat_of
                    and hit.reports >= config.LICENSED_FIRM_MIN_REPORTS):
                continue
            flags.append(Flag(
                RED, "network.copycat_reports", f"Copycats of {display} were reported {hit.reports} times",
                "People have reported scams using this licensed firm's name with different contact details. "
                "This doesn't mean the real firm is a scam.",
                SOURCE, "company", display))
            continue
        plural = "report" if hit.reports == 1 else "reports"
        detail = f"{display} appears in {hit.reports} community {plural} of investment scams."
        if hit.cluster_reports > hit.reports and len(hit.names) > 1:
            detail += (f" It's linked to a network of {hit.cluster_reports} reports under names like "
                       f"{', '.join(hit.names[:4])}, likely one group using several names.")
        flags.append(Flag(RED, "network.seen_in_reports", f"Seen in {hit.reports} scam {plural}: {display}",
                          detail, SOURCE, _node_kind(kind), display))
    return flags


def _node_kind(kind):
    return {"phone_hash": "phone", "account_hash": "account"}.get(kind, kind)
