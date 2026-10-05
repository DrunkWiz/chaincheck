"""Model call + schema validation (docs/BUILD_BRIEF.md §5 step 2).

TODO (6–7 Oct): code-side extraction of URLs, phones, emails, wallets,
percentages and fixed phrases, merged with the model's entities so the model
can only add, never drop. Plus screenshot text reading.
"""

from backend import schema
from backend.prompt import build_extraction_prompt


def extract(offer_text, provider):
    """Return a schema.Validated for one offer. Provider errors propagate."""
    system, user = build_extraction_prompt(offer_text)
    return schema.validate(provider.complete(system, user))
