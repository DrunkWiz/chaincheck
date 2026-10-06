"""Redaction before storing a report (docs/BUILD_BRIEF.md §10).

Regex for NRIC/FIN, phone numbers, bank account numbers and emails; then the
names the extractor found (people) plus honorific + name patterns. The reporter
sees and confirms the preview, and the server redacts again on submit.

`scrub_display` hides phone, account and NRIC numbers in anything we show.
"""

import re

NRIC = re.compile(r"\b[STFGM]\d{7}[A-Z]\b", re.IGNORECASE)
EMAIL = re.compile(r"[\w.+-]+@[\w-]+(?:\.[\w-]+)+")
# Singapore numbers (with or without +65) and any +country number. Plain
# dates like 2026-09-20 must not match.
PHONE = re.compile(
    r"(?<![\d+])(?:\+?65[\s-]?)?[3689]\d{3}[\s-]?\d{4}(?!\d)"
    r"|\+\d{1,3}[\s-]?\d[\d\s-]{6,14}\d")
ACCOUNT = re.compile(r"\b\d{3,4}[\s-]\d{3,6}[\s-]\d{1,6}(?:[\s-]\d{1,4})?\b|\b\d{9,16}\b")
HONORIFIC_NAME = re.compile(
    r"\b(Mr|Ms|Mrs|Mdm|Miss|Dr|Prof|Professor|Uncle|Auntie|Aunty)\.?\s+[A-Z][a-z]+(?:\s+[A-Z][a-z]+){0,2}")
SELF_NAME = re.compile(r"\b((?i:my name is|call me))\s+[A-Z][a-z]+(?:\s+[A-Z][a-z]+){0,2}")

WALLET = re.compile(r"\b0x[a-fA-F0-9]{40}\b|\bbc1[a-z0-9]{25,59}\b|\bT[1-9A-HJ-NP-Za-km-z]{33}\b")


def _protect(text, pattern):
    """Swap out matches (e.g. wallets) so number rules don't eat them."""
    saved = []

    def stash(match):
        saved.append(match.group(0))
        return f"\x00{len(saved) - 1}\x00"
    return pattern.sub(stash, text), saved


def _restore(text, saved):
    return re.sub(r"\x00(\d+)\x00", lambda m: saved[int(m.group(1))], text)


def redact(text, names=()):
    """Return (redacted_text, counts)."""
    counts = {}

    def sub(pattern, label, value):
        new, n = pattern.subn(label, value)
        if n:
            counts[label] = counts.get(label, 0) + n
        return new

    text, wallets = _protect(text, WALLET)
    text = sub(EMAIL, "[EMAIL]", text)
    text = sub(NRIC, "[NRIC]", text)
    text = sub(ACCOUNT, "[ACCOUNT]", text)
    text = sub(PHONE, "[PHONE]", text)
    for name in sorted({n for n in names if n and len(n) > 2}, key=len, reverse=True):
        text = sub(re.compile(re.escape(name), re.IGNORECASE), "[NAME]", text)
    text = sub(HONORIFIC_NAME, "[NAME]", text)
    new, n = SELF_NAME.subn(lambda m: f"{m.group(1)} [NAME]", text)
    if n:
        counts["[NAME]"] = counts.get("[NAME]", 0) + n
    return _restore(new, wallets), counts


def for_model(text):
    """What the model is allowed to see. Phones, emails, NRIC/FIN, account numbers and
    "my name is ..." are removed: code extracts those from the original text, so the
    model never needs them. Names with titles stay, because the model's job includes
    spotting claimed titles (and they're usually the scammer's alias)."""
    text, wallets = _protect(text, WALLET)
    text = EMAIL.sub("[EMAIL]", text)
    text = NRIC.sub("[NRIC]", text)
    text = ACCOUNT.sub("[ACCOUNT]", text)
    text = PHONE.sub("[PHONE]", text)
    text = SELF_NAME.sub(lambda m: f"{m.group(1)} [NAME]", text)
    return _restore(text, wallets)


def scrub_display(text):
    """Hide phone, account and NRIC numbers in text we show back."""
    text, wallets = _protect(text, WALLET)
    text = NRIC.sub("[NRIC]", text)
    text = ACCOUNT.sub("[ACCOUNT]", text)
    text = PHONE.sub("[PHONE]", text)
    return _restore(text, wallets)
