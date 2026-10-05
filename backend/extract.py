"""Model call + schema validation (docs/BUILD_BRIEF.md §5 step 2).

Successful extractions are cached by input hash so the same text gives the
same entities, and so the same verdict.
"""

import hashlib
from collections import OrderedDict

from backend import config, schema
from backend.prompt import build_extraction_prompt

_cache = OrderedDict()


def extract(offer_text, provider):
    """Return a schema.Validated for one offer. Provider errors propagate."""
    system, user = build_extraction_prompt(offer_text)
    return schema.validate(provider.complete(system, user))


def cached_extract(offer_text, provider):
    key = (getattr(provider, "name", "?"), hashlib.sha256(offer_text.encode()).hexdigest())
    if key in _cache:
        _cache.move_to_end(key)
        return _cache[key]
    result = extract(offer_text, provider)
    _cache[key] = result
    if len(_cache) > config.EXTRACTION_CACHE_SIZE:
        _cache.popitem(last=False)
    return result


def clear_cache():
    _cache.clear()
