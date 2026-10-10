"""Clearly labelled SYNTHETIC community reports (docs/BUILD_BRIEF.md §10).

Every story is invented, modelled on patterns in reported cases. Nine of them
form one network under three names, linked by shared wallets, phones, a bank
account and websites. The deployed app seeds these itself on first start when
SEED_DEMO_REPORTS=1; `python -m scripts.seed_reports` does the same locally.
"""

import hashlib

from backend import community, pipeline

W1 = "0x4b2e9f1a7c3d5e8b0a6f2c4d9e1b3a5c7d8e0f2a"
W2 = "0x9c1d3e5f7a2b4c6d8e0f1a3b5c7d9e2f4a6b8c0d"

SYNTHETIC_REPORTS = [
    # --- One network, three names -----------------------------------------------
    ("ai_trading_group", "lost_money",
     "SYNTHETIC. Joined a Telegram group after an ad with a famous investor. The mentor pushed AlphaGain Pro, "
     f"site alphagain-pro.example. I deposited $800 and later sent 15,000 USDT to wallet {W1}. "
     "They promised 3% per day."),
    ("fake_trading_platform", "lost_money",
     "SYNTHETIC. An account manager from AlphaGain Pro called me every day from +65 8000 7777. "
     "The platform alphagain-pro.example showed my balance doubled. When I tried to withdraw they asked for a 20% withdrawal tax."),
    ("crypto", "stopped_in_time",
     "SYNTHETIC. A WhatsApp group shared an app you install from a link, not the App Store. "
     f"They wanted me to top up in USDT to {W1}. A family member stopped me before I paid."),
    ("fake_trading_platform", "lost_money",
     "SYNTHETIC. Nova Apex Trading Pte Ltd contacted me from +65 8000 7777 about an institutional programme. "
     "Their site novaapex.example promised 25% per month. I withdrew a small profit, then lost $40,000."),
    ("fake_trading_platform", "lost_money",
     "SYNTHETIC. Nova Apex Trading Pte Ltd asked me to transfer $30,000 to account 123-456789-0 for a VIP tier. "
     "Website novaapex.example. My account was then frozen until I paid an unlock fee."),
    ("crypto", "still_happening",
     f"SYNTHETIC. The professor in the group said Nova Apex Trading Pte Ltd was moving to crypto. Send USDT to {W2}. "
     "Site novaapex.example. They say my account is frozen."),
    ("romance_investment", "lost_money",
     "SYNTHETIC. Someone I met on a dating app introduced Lumen Yield Pte Ltd, lumenyield.example. "
     "I transferred $25,000 to account 123-456789-0. They said 2% per day was normal."),
    ("romance_investment", "lost_money",
     f"SYNTHETIC. My online partner's uncle ran Lumen Yield Pte Ltd. I sent crypto to {W2} after the site "
     "lumenyield.example showed huge profits. Withdrawal blocked until I paid tax."),
    ("ai_trading_group", "recovered_some",
     "SYNTHETIC. Lumen Yield Pte Ltd ran an AI trading group. Call +65 8000 8888, site lumenyield.example. "
     "My bank recalled part of my transfer."),
    # --- Unrelated reports --------------------------------------------------------
    ("copycat_firm", "stopped_in_time",
     "SYNTHETIC. Someone claimed to be from Merlion Crest Capital Pte Ltd and called from +65 8000 4321. "
     "Their site was merlioncrest-capital.example. I checked MAS's register and the real number was different."),
    ("fund_recovery", "lost_money",
     "SYNTHETIC. After losing money, Asset Recovery Bureau Pte Ltd said they could recover my lost funds for an "
     "upfront fee. Site recoverfunds.example. It was another scam."),
    ("romance_investment", "stopped_in_time",
     "SYNTHETIC. A man online told me to buy gold bars for Orchid Prime Markets and a courier would collect them. "
     "Site orchidprime.example. My daughter checked and stopped me."),
]


def seed(db, ctx=None, secret=None):
    """Add the synthetic reports. Safe to run twice or concurrently: each report's id
    comes from its story, so a second run inserts nothing new."""
    ctx = ctx or pipeline.make_context(rdap=lambda _domain: None)
    ids = []
    for scam_type, outcome, story in SYNTHETIC_REPORTS:
        report_id = hashlib.sha256(story.encode()).hexdigest()[:16]
        ids.append(community.submit(db, story, outcome, scam_type, {}, None, ctx, secret=secret,
                                    synthetic=True, status="approved", report_id=report_id))
    community.recompute_clusters(db)
    return ids


def seed_if_empty(db, ctx=None, secret=None):
    """Seed only when no synthetic reports exist yet. Returns how many were added."""
    if db.execute("SELECT COUNT(*) AS n FROM reports WHERE synthetic = 1")[0]["n"]:
        return 0
    return len(seed(db, ctx, secret))
