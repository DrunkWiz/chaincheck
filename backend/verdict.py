"""Verdict from flags (docs/BUILD_BRIEF.md §8).

Any red or amber -> STOP. Otherwise "No red flags found". There is no green
verdict and the app never says safe, verified or legit.
"""

from backend.flags import AMBER, RED

STOP = "STOP"
NO_RED_FLAGS = "NO_RED_FLAGS"

STOP_HEADLINE = "STOP. Don't send money."
CLEAR_HEADLINE = "No red flags found. Verify these yourself before you pay."

VERIFY_YOURSELF = (
    "Search the firm's exact name on MAS's Financial Institutions Directory yourself.",
    "Contact the firm only through the phone number and website on MAS's register, not ones you were sent.",
    "Check the name on MAS's Investor Alert List.",
    "Never pay into a personal bank account, in cash, gold or crypto.",
    "Talk to someone you trust before you pay.",
)
AFTER_STOP = (
    "Don't send any more money, including any \"tax\" or fee to withdraw.",
    "If you've already paid, call your bank now and ask them to stop or recall the transfer.",
    "Report it on ScamShield and make a police report.",
    "Stop replying. Don't install anything else they send.",
)


def _plural(n, one, many):
    return f"{n} {one if n == 1 else many}"


def decide(flags):
    red = sum(1 for f in flags if f.level == RED)
    amber = sum(1 for f in flags if f.level == AMBER)
    if red or amber:
        parts = []
        if red:
            parts.append(_plural(red, "red flag", "red flags"))
        if amber:
            parts.append(_plural(amber, "claim we couldn't verify", "claims we couldn't verify"))
        return {
            "verdict": STOP, "headline": STOP_HEADLINE, "summary": ", ".join(parts),
            "counts": {"red": red, "amber": amber}, "next_steps": list(AFTER_STOP),
        }
    return {
        "verdict": NO_RED_FLAGS, "headline": CLEAR_HEADLINE,
        "summary": "Our checks found nothing, but they can't catch everything.",
        "counts": {"red": 0, "amber": 0}, "next_steps": list(VERIFY_YOURSELF),
    }
