"""MAS checks for each company (docs/BUILD_BRIEF.md §7).

- On the Investor Alert List snapshot (exact or fuzzy): red.
- Exactly a licensed name: copycat check.
- Close to a licensed name but not exact: red, possible copycat.
- Otherwise not in the Financial Institutions Directory snapshot: red.
Chat apps and exchanges are skipped: they aren't the firm offering the investment.
"""

from backend import normalize
from backend.checks import copycat, fuzzy
from backend.flags import RED, Flag


def check(entities, ctx):
    flags = []
    seen = set()
    for name in entities["companies"]:
        key = normalize.company(name)
        if not key or key in seen or fuzzy.is_platform(name):
            continue
        seen.add(key)

        alert, _, _ = fuzzy.best_match(name, ctx.ial.firms)
        if alert:
            flags.append(Flag(
                RED, "mas.alert_list", f"{name} is on MAS's Investor Alert List",
                f"MAS lists \"{alert.name}\" as an entity that may be wrongly taken to be licensed or regulated by MAS.",
                ctx.ial.label, "company", name, ctx.ial.date,
            ))

        firm, score, exact = fuzzy.best_match(name, ctx.fid.firms)
        if firm and exact:
            flags.extend(copycat.check(name, firm, entities, ctx.fid, ctx))
        elif firm:
            ctx.copycat_of.add(firm.key)
            flags.append(Flag(
                RED, "mas.lookalike_name", f"{name} looks like a copy of {firm.name}",
                f"\"{name}\" is not in MAS's directory, but it is {round(score * 100)}% similar to the "
                f"licensed firm \"{firm.name}\". Scammers use names close to real firms.",
                ctx.fid.label, "company", name, ctx.fid.date,
            ))
        elif not alert:
            flags.append(Flag(
                RED, "mas.not_licensed", f"{name} is not licensed by MAS",
                f"We couldn't find \"{name}\" in MAS's Financial Institutions Directory. Firms offering "
                "investments in Singapore must be licensed or exempt.",
                ctx.fid.label, "company", name, ctx.fid.date,
            ))
    ctx.company_flagged = bool(flags)
    return flags
