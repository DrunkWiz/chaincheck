"""Promised returns (docs/BUILD_BRIEF.md §7).

Annualise with (1 + p)^periods_per_year - 1. Red above RETURNS_RED_ANNUAL_PCT,
amber from RETURNS_AMBER_ANNUAL_PCT. Period "unknown" gives no flag.
"""

from backend import config
from backend.flags import AMBER, RED, RULE_SOURCE, Flag

CAP_PCT = 1e12


def annualise(percent, period):
    """Annual % for a per-period %, or None when the period is unknown."""
    n = config.PERIODS_PER_YEAR.get(period)
    if n is None:
        return None
    try:
        value = ((1 + percent / 100) ** n - 1) * 100
    except OverflowError:
        return CAP_PCT
    # Round away float noise so 30% a year is exactly 30, not 30.000000000000004.
    return min(round(value, 6), CAP_PCT)


def format_pct(value):
    if value >= 1e6:
        return "over 1,000,000%"
    return f"{value:,.0f}%" if value >= 100 else f"{value:,.1f}%".replace(".0%", "%")


def check(entities, _ctx=None):
    flags = []
    for claim in entities["returns"]:
        annual = annualise(claim["percent"], claim["period"])
        if annual is None:
            continue
        claimed = f"{format_pct(claim['percent'])} a {claim['period']}"
        source = f"{RULE_SOURCE}: returns above {config.RETURNS_RED_ANNUAL_PCT:g}% a year"
        if annual > config.RETURNS_RED_ANNUAL_PCT:
            flags.append(Flag(
                RED, "returns.too_high", f"{claimed} is {format_pct(annual)} a year",
                f"Compounded, that's {format_pct(annual)} a year. Anything above "
                f"{config.RETURNS_RED_ANNUAL_PCT:g}% a year is a red flag: no real investment pays that reliably.",
                source, "returns", claimed,
            ))
        elif annual >= config.RETURNS_AMBER_ANNUAL_PCT:
            flags.append(Flag(
                AMBER, "returns.high", f"{claimed} is {format_pct(annual)} a year",
                "That's well above what regulated investments usually return. Ask how, and get it in writing.",
                source, "returns", claimed,
            ))
    return flags
