"""Fuzzy firm-name matching (docs/BUILD_BRIEF.md §7)."""

from backend import config, normalize

MIN_KEY_CHARS = 4  # shorter names are too noisy to fuzzy-match


def is_platform(name):
    return name.strip().lower() in config.PLATFORM_NAMES or normalize.company(name) in {
        normalize.company(p) for p in config.PLATFORM_NAMES}


def best_match(name, firms):
    """Return (firm, score, exact) for the closest firm, or (None, 0.0, False)."""
    key = normalize.company(name)
    if not key:
        return None, 0.0, False
    best, best_score = None, 0.0
    for firm in firms:
        if firm.key == key:
            return firm, 1.0, True
        if len(key) < MIN_KEY_CHARS or len(firm.key) < MIN_KEY_CHARS:
            continue
        score = normalize.similarity(key, firm.key)
        if score > best_score:
            best, best_score = firm, score
    if best_score >= config.FUZZY_MATCH_MIN:
        return best, best_score, False
    return None, best_score, False
