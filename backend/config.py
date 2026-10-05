"""Every threshold and fixed list in one place (docs/BUILD_BRIEF.md §7).

These are starting values. Tune them on the accuracy set and copy the final
values back into the brief.
"""

# --- Company checks -------------------------------------------------------
# Similarity (0..1) to a licensed name, after normalising, that triggers the
# copycat check. Exact matches run the copycat check too.
FUZZY_MATCH_MIN = 0.85

# Suffixes stripped when normalising company names (after punctuation is
# removed), longest first.
COMPANY_SUFFIXES = (
    "private limited",
    "pte ltd",
    "pte",
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

# --- Payment / app ----------------------------------------------------------
# Words that, earlier in the same sentence, mean a phrase is being denied
# ("we will never ask you to pay cash"). Used by code-side extraction.
NEGATION_WORDS = ("never", "not", "no", "don't", "do not", "won't", "will not", "cannot")

# --- Community / network ----------------------------------------------------
# Script similarity (embeddings) is cut for now; see BUILD_BRIEF §13.
SCRIPT_SIMILARITY_MIN = 0.90
# Entity kinds that link reports into one network.
NETWORK_ENTITY_KINDS = ("domain", "app", "wallet", "account_hash", "phone_hash", "company", "email")
# A licensed firm needs this many independent reports *and* a copycat mismatch
# before reports can say anything about it (§10).
LICENSED_FIRM_MIN_REPORTS = 3

SCAM_TYPES = (
    "fake_trading_platform", "crypto", "romance_investment", "ai_trading_group",
    "copycat_firm", "fund_recovery", "other",
)
OUTCOMES = ("lost_money", "stopped_in_time", "still_happening", "recovered_some")
MAX_REPORT_CHARS = 8000

# --- Request limits -------------------------------------------------------------
MAX_TEXT_CHARS = 20_000
MAX_IMAGES = 4
MAX_IMAGE_BYTES = 4_000_000
MAX_BODY_BYTES = 24_000_000
MAX_ANSWER_CHARS = 120

# --- Model ------------------------------------------------------------------------
# Model IDs come from env (GEMINI_MODEL, GEMINI_FALLBACK_MODEL); these are
# defaults. Checked against Google's model list on 6 Oct 2026: 3.5 Flash is
# "legacy" but stable; 2.5 Flash is closed to new projects.
GEMINI_MODEL_DEFAULT = "gemini-3.5-flash"
GEMINI_FALLBACK_MODEL_DEFAULT = "gemini-3.5-flash-lite"
MODEL_TIMEOUT_SECONDS = 25
RDAP_TIMEOUT_SECONDS = 5
EXTRACTION_CACHE_SIZE = 256

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
