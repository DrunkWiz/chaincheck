"""Claimed titles, model concerns, and text aimed at an AI (docs/BUILD_BRIEF.md §7)."""

from backend.flags import AMBER, RED, RULE_SOURCE, Flag

AI_SOURCE = "AI reader (can add a warning, never remove one)"


def check_people(entities, ctx=None):
    """Claimed titles are amber: we can't check them. The exception is an offer from a
    licensed firm whose contact details all match its MAS record, with no company flag:
    there the authority trick doesn't apply, so the title becomes a check-it-yourself
    item instead of a flag."""
    titled = [p for p in entities["people"] if p["claimed_title"]]
    firm_checks_out = ctx is not None and ctx.matched_firms and not ctx.company_flagged
    if firm_checks_out:
        for p in titled:
            ctx.verify_yourself.append(
                f"{p['name']} is described as \"{p['claimed_title']}\". Look them up on MAS's Register of "
                "Representatives before acting on their advice.")
        return []
    return [Flag(
        AMBER, "person.claimed_title", f"{p['name']} claims to be: {p['claimed_title']}",
        "We can't check titles like professor, analyst or fund manager automatically. "
        "Look the person up on MAS's Register of Representatives yourself.",
        f"{RULE_SOURCE}: claimed titles", "person", p["name"],
    ) for p in titled]


def check_concerns(entities, _ctx=None):
    return [Flag(
        AMBER, "ai.concern", f"Wording to question: \"{c['text']}\""[:200], c["reason"],
        AI_SOURCE, "concern", c["text"][:80],
    ) for c in entities["concerns"]]


def check_injection(quotes):
    if not quotes:
        return []
    return [Flag(
        RED, "text.ai_instructions", "The message contains instructions aimed at AI checkers",
        f"It says: \"{quotes[0][:120]}\". Real offers don't try to instruct software. "
        "This was ignored, and it's a sign someone expects their message to be checked.",
        f"{RULE_SOURCE}: instructions aimed at AI", "concern", "Instructions aimed at AI",
    )]
