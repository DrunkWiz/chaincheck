"""Reality Check: what the promised returns would mean over a year."""

import json
from functools import lru_cache

from backend import config
from backend.checks.returns import CAP_PCT, annualise, format_pct
from backend.snapshots import DATA_DIR


@lru_cache(maxsize=1)
def benchmarks():
    path = DATA_DIR / "benchmarks.json"
    return json.loads(path.read_text(encoding="utf-8")) if path.exists() else {"items": []}


def reality_check(entities):
    claims = []
    for claim in entities["returns"]:
        annual = annualise(claim["percent"], claim["period"])
        if annual is None:
            continue
        after = 1000 * (1 + annual / 100) if annual < CAP_PCT else None
        claims.append({
            "claimed": f"{format_pct(claim['percent'])} a {claim['period']}",
            "annual_percent": annual,
            "annual_text": format_pct(annual),
            "thousand_becomes": f"${after:,.0f}" if after is not None and after < 1e9 else "over $1 billion",
            "quote": claim["quote"],
        })
    if not claims:
        return None
    data = benchmarks()
    return {
        "claims": claims,
        "red_line_percent": config.RETURNS_RED_ANNUAL_PCT,
        "amber_line_percent": config.RETURNS_AMBER_ANNUAL_PCT,
        "benchmarks": data.get("items", []),
        "benchmarks_note": data.get("note", ""),
    }
