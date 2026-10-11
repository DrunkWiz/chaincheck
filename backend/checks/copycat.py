"""Copycat check (docs/BUILD_BRIEF.md §7).

Runs when a company name matches a MAS-licensed firm, exactly or fuzzily.
Red when a website, email or phone given doesn't match that firm's MAS record.
Amber when no contact details were given, because we can't tell who you're
really talking to.
"""

from backend import config, normalize
from backend.flags import AMBER, RED, Flag


def _skip(domain):
    return domain in config.SKIP_DOMAINS or any(domain.endswith("." + s) for s in config.SKIP_DOMAINS)


def _on_record(domain, firm):
    allowed = firm.websites | firm.email_domains
    return any(domain == d or domain.endswith("." + d) for d in allowed)


def check(name, firm, entities, snapshot, ctx):
    domains = [normalize.domain(d) for d in entities["domains"]]
    domains = [d for d in domains if d and not _skip(d)]
    emails = [normalize.domain(e) for e in entities["emails"]]
    phones = [normalize.phone(p) for p in entities["phones"]]
    phones = [p for p in phones if p]

    mismatches = []
    for d in domains:
        if _on_record(d, firm):
            ctx.on_record_domains.add(d)
        else:
            mismatches.append(f"the website {normalize.defang(d)}")
    for e in emails:
        if not _on_record(e, firm):
            mismatches.append(f"an email address at {normalize.defang(e)}")
    phone_mismatch = 0
    for p in phones:
        if p in firm.phones:
            ctx.on_record_phones.add(p)
        else:
            phone_mismatch += 1
    if phone_mismatch:
        mismatches.append("a phone number" if phone_mismatch == 1 else f"{phone_mismatch} phone numbers")

    if mismatches:
        ctx.copycat_of.add(firm.key)
        return [Flag(
            RED, "copycat.contact_mismatch", f"Copycat of {firm.name}",
            f"The name matches a MAS-licensed firm, but {_join(mismatches)} you were given "
            f"{'is' if len(mismatches) == 1 else 'are'} not on that firm's MAS record. "
            "Scammers copy real firms' names. Contact the firm only through the details on MAS's register.",
            snapshot.label, "company", name, snapshot.date,
        )]
    if not (domains or emails or phones):
        return [Flag(
            AMBER, "copycat.no_contact_details", f"Can't tell if this is really {firm.name}",
            "The name matches a MAS-licensed firm, but no website, email or phone number was given "
            "to compare with its MAS record. Contact the firm only through the details on MAS's register.",
            snapshot.label, "company", name, snapshot.date,
        )]
    ctx.matched_firms.add(firm.key)  # contacts were given and all are on the firm's MAS record
    return []


def _join(items):
    return items[0] if len(items) == 1 else ", ".join(items[:-1]) + " and " + items[-1]
