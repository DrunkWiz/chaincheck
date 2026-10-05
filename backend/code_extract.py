"""Code-side extraction (docs/BUILD_BRIEF.md §4).

Pulls hard facts out of the text with fixed patterns: domains, phones, emails,
wallets, accounts, return claims, fees, payment methods, event signals,
claimed titles, firm names from the MAS snapshots, and text aimed at an AI.
Its entities are merged with the model's so the model can only add.

Phrases are denied-aware: a match is ignored when a negation word appears
earlier in the same sentence ("we will never ask you to pay cash").
"""

import re

from backend import config, normalize, schema

_I = re.IGNORECASE

TLDS = (
    "com|net|org|io|co|sg|app|xyz|top|vip|info|biz|cc|me|ai|online|site|club|pro|"
    "live|tech|store|shop|finance|money|trade|exchange|asia|hk|my|cn|uk|us|in|au|"
    "id|ph|th|vn|tw|jp|kr|ly|gl|gy|tk|ws|link|example|test|invalid"
)
DOMAIN = re.compile(
    r"(?<![@\w.-])(?:https?://)?((?:[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?\.)+(?:" + TLDS + r"))(?![\w-])", _I)
EMAIL = re.compile(r"[\w.+-]+@[\w-]+(?:\.[\w-]+)+")
SG_PHONE = re.compile(r"(?<![\d+])(?:\+65[\s-]?)?[3689]\d{3}[\s-]?\d{4}(?!\d)")
INTL_PHONE = re.compile(r"\+(?!65)\d{1,3}[\s-]?\d[\d\s-]{6,14}\d")
WALLETS = (
    re.compile(r"\b0x[a-fA-F0-9]{40}\b"),
    re.compile(r"\bbc1[a-z0-9]{25,59}\b"),
    re.compile(r"\bT[1-9A-HJ-NP-Za-km-z]{33}\b"),
)
ACCOUNT = re.compile(r"\b(?:account|a/c|acct)(?:\s+(?:no\.?|number))?\s*:?\s*(\d[\d -]{6,18}\d)\b", _I)

RETURN = re.compile(
    r"(\d+(?:\.\d+)?)\s?%\s*(?:returns?\s+)?(?:(?:a|an|per|each|every|/|in\s+(?:a|one))\s*)?"
    r"(day|week|month|year|annum|daily|weekly|monthly|yearly|annually|annual|p\.?\s?a\.?)(?![a-z])", _I)
PERIOD_WORDS = {
    "day": "day", "daily": "day", "week": "week", "weekly": "week",
    "month": "month", "monthly": "month", "year": "year", "yearly": "year",
    "annually": "year", "annual": "year", "annum": "year",
}

AMOUNT = re.compile(r"(?:S?\$|SGD\s?|USD\s?|USDT\s?)\s?(\d{1,3}(?:,\d{3})+|\d+)(?:\.\d+)?\s?(k\b)?", _I)
MONEY_MOVE = re.compile(r"\b(deposit\w*|top(?:ped)?[ -]?up|transferr?\w*|invested|put in|paid)\b", _I)
SMALL_DEPOSIT_MAX = 2_000
LARGE_TRANSFER_MIN = 20_000

# (pattern, field, value, negatable)
PHRASES = [
    # payment
    (r"\b(collect|hand ?over|pass|meet)\w*\b[^.\n]{0,40}\bcash\b|\bcash\b[^.\n]{0,40}\b(collect\w*|courier|hand ?over|in person)\b|\bcourier\b[^.\n]{0,40}\bcollect", "payment", "cash_handover", True),
    (r"\b(gold bars?|buy(?:ing)? gold|purchase gold|gold bullion)\b|\b(pay|hand|deliver|courier)\w*\b[^.\n]{0,30}\bgold\b", "payment", "gold", True),
    (r"\b(deposit|transfer|top ?up|send|pay|fund)\w*\b[^.\n]{0,40}\b(usdt|usdc|tether|bitcoin|btc|eth|ethereum|crypto\w*)\b|\b(usdt|usdc|bitcoin|btc|eth|crypto\w*)\b[^.\n]{0,30}\b(wallet|address)\b", "payment", "crypto", True),
    (r"\bbank transfer\b", "payment", "bank_transfer", True),
    (r"\bpaynow\b", "payment", "paynow", True),
    # fees
    (r"\bwithdrawal tax\b|\btax\w*\b[^.\n]{0,40}\bbefore\b[^.\n]{0,30}\bwithdraw", "fees", "withdrawal_tax", False),
    (r"\b(unlock|unfreeze|release|activation|verification|anti-money laundering|aml)\s+(fee|deposit|charge)\b", "fees", "unlock_fee", False),
    # events, stage 1-7
    (r"\b(ad|advert\w*|article|video|post)\b[^.\n]{0,60}\b(famous|celebrity|minister|billionaire|public figure)\b|\b(famous|celebrity)\b[^.\n]{0,40}\b(ad|advert\w*|endors\w*)\b", "events", "public_figure_ad", True),
    (r"\bsecret\b[^.\n]{0,20}\b(method|strategy|formula|system|technique)\b", "events", "secret_method", True),
    (r"\b(registered|signed up)\b", "events", "registered", True),
    (r"\b(whatsapp|telegram|wechat|line|signal)\b[^.\n]{0,15}\b(group|channel|chat)\b|\b(group|channel)\b[^.\n]{0,20}\b(whatsapp|telegram)\b", "events", "group_invite", True),
    (r"\b(overseas|foreign|international)\s+(call|number)\b|\bcall\w*\s+from\s+(overseas|abroad)\b", "events", "overseas_call", True),
    (r"\b(personal|account|investment|client)\s+(manager|assistant)\b", "events", "account_manager", True),
    (r"\b(every day|daily)\b[^.\n]{0,30}\b(follow|check|remind|messag)\w*", "events", "daily_follow_up", True),
    (r"\b(professor|prof\.|mentor|teacher|guru|trading master)\b", "events", "expert_mentor", True),
    (r"\bmembers?\b[^.\n]{0,40}\b(profit|gain|earning|screenshot)\w*", "events", "members_posting_profits", True),
    (r"\b(shares?|posts?|sends?|gives?)\b[^.\n]{0,25}\b(stock picks?|trading signals?|signals|stock tips)\b", "events", "stock_picks", True),
    (r"\b(private|beta|exclusive)\b[^.\n]{0,30}\b(app|platform|group|tier|programme|program)\b", "events", "private_app_invite", True),
    (r"\b(withdrew|withdrawn|cashed out)\b|\bwithdrawal\b[^.\n]{0,20}\b(success\w*|worked|went through|received|reached)\b", "events", "withdrawal_succeeded", True),
    (r"\b(balance|account|portfolio)\b[^.\n]{0,30}\b(doubled|tripled|grew|rising|rose|jumped)\b", "events", "balance_rising_fast", True),
    (r"\binstitutional\b|\b(vip|premium)\s+(tier|programme|program|account)\b", "events", "institutional_programme", True),
    (r"\b(cannot|can't|cant|unable to|not able to|blocked|won't let me)\b[^.\n]{0,20}\bwithdraw", "events", "withdrawal_blocked", False),
    (r"\bwithdrawal tax\b|\b(tax|fee)\w*\b[^.\n]{0,40}\bbefore\b[^.\n]{0,30}\bwithdraw|\bpay\b[^.\n]{0,40}\bbefore\b[^.\n]{0,30}\bwithdraw", "events", "withdrawal_tax_demanded", False),
    (r"\bminimum\s+(trading|turnover|volume)\b|\btrading\s+(volume|turnover)\s+requirement\b", "events", "minimum_trading_commitment", True),
    (r"\b(account|funds?)\b[^.\n]{0,20}\b(frozen|freeze|locked|suspended)\b", "events", "account_frozen", False),
    (r"\b(recover|recovery|get back)\b[^.\n]{0,30}\b(funds?|money|losses|lost)\b", "events", "fund_recovery_offer", False),
]
PHRASES = [(re.compile(p, _I), f, v, n) for p, f, v, n in PHRASES]

PERCENT_TAX = re.compile(r"(\d+(?:\.\d+)?)\s?%[^.\n]{0,20}\btax\b", _I)
PERCENT_WITHDRAWAL_FEE = re.compile(r"(\d+(?:\.\d+)?)\s?%\s+(?:withdrawal|processing|handling)\s+fee", _I)

APP_FROM_LINK = re.compile(
    r"\.apk\b|testflight|\b(?:not|isn't|isnt|is not)\s+(?:on|in|available\s+(?:on|in))\s+(?:the\s+)?(?:app store|google play|play store)"
    r"|\b(?:install|download)\w*\b[^.\n]{0,30}\bfrom\s+(?:this|the|our|a)\s+(?:link|website|site)\b", _I)

TITLED_PEOPLE = (
    (re.compile(r"\b(Prof(?:essor)?\.?|Dr\.?)\s+([A-Z][a-z]+(?:\s+[A-Z][a-z]+){0,2})"), None),
    (re.compile(r"\b((?i:(?:senior |chief |head )?(?:analyst|fund manager|portfolio manager|strategist|trading mentor)))\s+"
                r"(?:Mr|Ms|Mrs|Mdm|Dr)\.?\s+([A-Z][a-z]+(?:\s+[A-Z][a-z]+)?)"), "title_first"),
)
COMPANY_SUFFIXED = re.compile(
    r"\b((?:[A-Z][\w&'-]*[ \t]+){0,4}[A-Z][\w&'-]*)[ \t]+(Pte\.?[ \t]*Ltd\.?|Private Limited)")
# Capitalised words that start a sentence, not a firm name ("Our Acme Pte Ltd").
COMPANY_LEAD_WORDS = frozenset({
    "our", "the", "at", "from", "with", "by", "join", "contact", "dear", "hi", "hello",
    "welcome", "this", "your", "i", "we", "a", "an", "call", "visit", "about", "and",
    "also", "then", "but", "so", "please", "thanks", "my", "is", "was",
})
_SUFFIX_WORDS = frozenset({"pte", "ltd", "private", "limited"})

INJECTION = [re.compile(p, _I) for p in (
    r"\bignore\b[^.\n]{0,40}\b(instructions?|prompts?|rules|previous|above)\b",
    r"\b(mark|classify|label|rate|treat|flag)\b[^.\n]{0,20}\b(this|it|as)\b[^.\n]{0,20}\b(safe|legit\w*|genuine|not a scam)\b",
    r"\b(system|admin(?:istrator)?|developer)\s*(notice|prompt|message|override|instruction)",
    r"untrusted[\s_-]*text",
    r"\byou are (?:now )?(?:an? )?(?:ai|assistant|language model|chatbot)\b",
    r"\b(return|output|respond with)\b[^.\n]{0,20}\b(empty|json)\b",
)]

_NEGATION = re.compile(r"\b(" + "|".join(re.escape(w) for w in config.NEGATION_WORDS) + r")\b", _I)
# Break after . ! ? only when whitespace follows, so "3.1% p.a." stays whole.
_SENTENCE_BREAK = re.compile(r"(?<=[.!?])\s+|\n+")


def sentences(text):
    return [s for s in _SENTENCE_BREAK.split(text) if s.strip()]


def _negated(sentence, start):
    return bool(_NEGATION.search(sentence[:start]))


def _quote(sentence):
    return " ".join(sentence.split())[: config.MAX_QUOTE_CHARS]


def extract(text, firms=()):
    """Return (entities, injection_quotes). `firms` are snapshot Firms to look for by name."""
    entities = schema.empty_entities()
    injection = []

    for match in EMAIL.finditer(text):
        entities["emails"].append(match.group(0).lower())
    for match in DOMAIN.finditer(text):
        entities["domains"].append(normalize.domain(match.group(1)))
    for pattern in (SG_PHONE, INTL_PHONE):
        for match in pattern.finditer(text):
            entities["phones"].append(match.group(0).strip())
    for pattern in WALLETS:
        entities["wallets"].extend(m.group(0) for m in pattern.finditer(text))
    for match in ACCOUNT.finditer(text):
        entities["accounts"].append({"bank": None, "number": match.group(1).strip()})

    for firm in firms:
        words = [w for w in firm.name.split() if w.strip(".,").lower() not in _SUFFIX_WORDS]
        if words and re.search(r"\b" + r"\W*".join(re.escape(w) for w in words) + r"\b", text, _I):
            entities["companies"].append(firm.name)
    for match in COMPANY_SUFFIXED.finditer(text):
        words = match.group(1).split()
        while words and words[0].lower() in COMPANY_LEAD_WORDS:
            words.pop(0)
        if words:
            entities["companies"].append(" ".join(words + match.group(2).split()))

    for pattern, mode in TITLED_PEOPLE:
        for match in pattern.finditer(text):
            title, name = match.group(1), match.group(2)
            if mode is None:
                title = "Professor" if title.lower().startswith("prof") else "Doctor"
            entities["people"].append({"name": name, "claimed_title": title.strip()})

    if APP_FROM_LINK.search(text):
        entities["apps"].append({"name": "App installed from a link", "source": "link"})

    for sentence in sentences(text):
        quote = _quote(sentence)
        for match in RETURN.finditer(sentence):
            if _negated(sentence, match.start()):
                continue
            word = match.group(2).lower().replace(" ", "")
            period = PERIOD_WORDS.get(word, "year" if word.startswith("p") else "unknown")
            entities["returns"].append({"percent": float(match.group(1)), "period": period, "quote": quote})

        for pattern, field, value, negatable in PHRASES:
            match = pattern.search(sentence)
            if not match or (negatable and _negated(sentence, match.start())):
                continue
            if field == "payment":
                entities["payment"].append({"method": value, "quote": quote})
            elif field == "events":
                entities["events"].append({"signal": value, "quote": quote})
            elif field == "fees":
                pct = PERCENT_TAX.search(sentence) if value == "withdrawal_tax" else None
                entities["fees"].append({
                    "type": value, "percent": float(pct.group(1)) if pct else None,
                    "amount": None, "quote": quote,
                })
        for match in PERCENT_WITHDRAWAL_FEE.finditer(sentence if "withdraw" in sentence.lower() else ""):
            entities["fees"].append({"type": "withdrawal_fee", "percent": float(match.group(1)),
                                     "amount": None, "quote": quote})

        move = MONEY_MOVE.search(sentence)
        if move and not _negated(sentence, move.start()):
            for amount in _amounts(sentence):
                if 0 < amount <= SMALL_DEPOSIT_MAX:
                    entities["events"].append({"signal": "small_deposit", "quote": quote})
                elif amount >= LARGE_TRANSFER_MIN:
                    entities["events"].append({"signal": "large_transfer", "quote": quote})

        if any(p.search(sentence) for p in INJECTION):
            injection.append(quote)

    return merge(schema.validate(entities).entities, schema.empty_entities()), injection


def _amounts(sentence):
    for match in AMOUNT.finditer(sentence):
        value = float(match.group(1).replace(",", ""))
        yield value * 1000 if match.group(2) else value


# --- Merging -------------------------------------------------------------------

_HONORIFIC = re.compile(r"^(mr|ms|mrs|mdm|dr|prof|professor)\.?\s+", _I)

_KEYS = {
    "people": lambda p: _HONORIFIC.sub("", p["name"]).lower(),
    "companies": normalize.company,
    "apps": lambda a: (a["name"].lower(), a["source"]),
    "domains": normalize.domain,
    "phones": normalize.phone,
    "emails": str.lower,
    "accounts": lambda a: normalize.account(a["number"]),
    "wallets": normalize.wallet,
    "returns": lambda r: (r["percent"], r["period"]),
    "fees": lambda f: f["type"],
    "payment": lambda p: p["method"],
    "events": lambda e: e["signal"],
    "concerns": lambda c: (c["text"], c["reason"]),
}


def merge(model, code):
    """Union of two entity sets, model first. Code can only add."""
    merged = {}
    for field in schema.FIELDS:
        key = _KEYS[field]
        seen, items = set(), []
        for item in model.get(field, []) + code.get(field, []):
            k = key(item)
            if k in seen:
                continue
            if field == "apps" and item["name"] == "App installed from a link" and any(
                    a["source"] == "link" for a in items):
                continue
            seen.add(k)
            items.append(item)
        merged[field] = items
    return merged
