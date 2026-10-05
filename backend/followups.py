"""Follow-up questions from a fixed list (docs/BUILD_BRIEF.md §5 step 3).

Answers are structured: choice answers map to fixed entity values in code; the
company answer is a name, treated like any other untrusted company name.
"""

from backend import config

QUESTIONS = {
    "payment": {
        "text": "How are they asking you to pay? Bank transfer, cash, gold, crypto?",
        "choices": {
            "bank_transfer": "Bank transfer",
            "paynow": "PayNow",
            "cash_handover": "Cash, handed to someone",
            "gold": "Gold",
            "crypto": "Crypto",
            "card": "Card",
            "not_asked": "They haven't asked yet",
        },
    },
    "withdrawal": {
        "text": "Have you withdrawn any money yet?",
        "choices": {
            "worked": "Yes, and it worked",
            "blocked": "I tried, but it was blocked or they asked me to pay first",
            "not_yet": "No, not yet",
        },
    },
    "company": {
        "text": "What's the name of the company or app?",
        "choices": None,
    },
}

WITHDRAWAL_SIGNALS = {"withdrawal_succeeded", "withdrawal_blocked", "withdrawal_tax_demanded"}


def clean_answers(raw):
    """Keep only known questions with valid answers."""
    answers = {}
    if not isinstance(raw, dict):
        return answers
    for key, value in raw.items():
        if key not in QUESTIONS or not isinstance(value, str):
            continue
        choices = QUESTIONS[key]["choices"]
        if choices is None:
            value = " ".join(value.split())[: config.MAX_ANSWER_CHARS]
            if value:
                answers[key] = value
        elif value in choices:
            answers[key] = value
    return answers


def apply(entities, answers):
    """Add entities implied by answers. Returns the same dict."""
    if "payment" in answers and answers["payment"] != "not_asked":
        method = answers["payment"]
        if all(p["method"] != method for p in entities["payment"]):
            entities["payment"].append({"method": method, "quote": f"Your answer: {QUESTIONS['payment']['choices'][method]}"})
    withdrawal = answers.get("withdrawal")
    signal = {"worked": "withdrawal_succeeded", "blocked": "withdrawal_blocked"}.get(withdrawal)
    if signal and all(e["signal"] != signal for e in entities["events"]):
        entities["events"].append({"signal": signal, "quote": f"Your answer: {QUESTIONS['withdrawal']['choices'][withdrawal]}"})
    if "company" in answers and answers["company"] not in entities["companies"]:
        entities["companies"].append(answers["company"])
    return entities


def questions_for(entities, answers):
    asked = []
    if not entities["payment"] and "payment" not in answers:
        asked.append("payment")
    if not ({e["signal"] for e in entities["events"]} & WITHDRAWAL_SIGNALS) and "withdrawal" not in answers:
        asked.append("withdrawal")
    if not entities["companies"] and not entities["apps"] and "company" not in answers:
        asked.append("company")
    return [{
        "id": q,
        "text": QUESTIONS[q]["text"],
        "choices": [{"value": v, "label": l} for v, l in (QUESTIONS[q]["choices"] or {}).items()] or None,
    } for q in asked]
