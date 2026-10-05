"""Every threshold and fixed list in one place (docs/BUILD_BRIEF.md §7).

These are starting values. Tune them on the accuracy set and copy the final
values back into the brief.
"""

# --- Company checks -------------------------------------------------------
# Similarity (0..1) to a licensed name, after normalising, that triggers the
# copycat check. Exact matches run the copycat check too.
FUZZY_MATCH_MIN = 0.85

# Suffixes stripped when normalising company names, longest first.
COMPANY_SUFFIXES = (
    "private limited",
    "pte. ltd.",
    "pte ltd",
    "limited",
    "ltd",
)

# Names the model may extract as "companies" that are platforms, not the firm
# offering the investment. Never flagged "not licensed".
PLATFORM_NAMES = frozenset({
    "whatsapp", "telegram", "facebook", "instagram", "tiktok", "youtube",
    "wechat", "line", "signal", "google", "apple", "app store", "google play",
    "binance", "coinbase", "metamask", "usdt", "tether", "bitcoin", "ethereum",
})

# --- Domain checks --------------------------------------------------------
DOMAIN_AGE_RED_DAYS = 180    # registered fewer than this many days ago: red
DOMAIN_AGE_AMBER_DAYS = 365  # fewer than this: amber

# Messaging, app-store and link-shortener domains: no domain-age check.
SKIP_DOMAINS = frozenset({
    "t.me", "wa.me", "chat.whatsapp.com", "whatsapp.com", "telegram.org",
    "apps.apple.com", "play.google.com", "facebook.com", "instagram.com",
    "youtube.com", "youtu.be", "tiktok.com",
    "bit.ly", "tinyurl.com", "t.co", "goo.gl", "rb.gy", "cutt.ly",
})

# --- Returns --------------------------------------------------------------
RETURNS_RED_ANNUAL_PCT = 30.0    # strictly above: red
RETURNS_AMBER_ANNUAL_PCT = 15.0  # at or above (up to and including 30): amber
PERIODS_PER_YEAR = {"day": 365, "week": 52, "month": 12, "year": 1}
# period "unknown" -> no returns flag.

# --- Community / similarity -------------------------------------------------
SCRIPT_SIMILARITY_MIN = 0.90

# --- Model output limits (schema validation) --------------------------------
MAX_LIST_ITEMS = 50
MAX_STRING_CHARS = 200
MAX_QUOTE_CHARS = 300
MAX_CONCERN_CHARS = 300
MAX_PERCENT = 1_000_000.0

# Model-written text shown to users must never contain these. A concern whose
# reason uses one keeps its amber but shows WITHHELD_REASON instead.
BANNED_DISPLAY_WORDS_PATTERN = r"\b(safe|safely|verified|legit\w*|genuine)\b"
WITHHELD_REASON = "The AI flagged this wording. Its explanation was withheld."
