"""Playbook stage and next move, fixed table (docs/BUILD_BRIEF.md §9).

Stage = the highest stage whose signals are present.
"""

STAGES = (
    (1, "Hook", ("public_figure_ad", "secret_method"),
     "They'll ask you to register or join a group."),
    (2, "Capture", ("registered", "group_invite"),
     "Expect a call or message from a \"personal manager\"."),
    (3, "Contact", ("overseas_call", "account_manager", "daily_follow_up"),
     "They'll introduce an \"expert\" and a group of members who seem to be winning."),
    (4, "Trust building", ("expert_mentor", "members_posting_profits", "stock_picks"),
     "They'll invite you to a private app or \"beta\" group and ask for a small deposit."),
    (5, "Small win", ("private_app_invite", "small_deposit", "withdrawal_succeeded", "balance_rising_fast"),
     "They'll ask for a much bigger deposit, often for an \"institutional programme\", paid in cash, gold or crypto."),
    (6, "Big ask", ("institutional_programme", "cash_requested", "gold_requested",
                    "crypto_to_new_wallet", "large_transfer"),
     "When you try to withdraw, it'll be blocked until you pay a \"tax\" or fee, or top up more."),
    (7, "Lockout", ("withdrawal_blocked", "withdrawal_tax_demanded", "minimum_trading_commitment",
                    "account_frozen", "fund_recovery_offer"),
     "More fees, then a \"fund recovery\" offer. Don't pay anything more: none of it comes back."),
)

SIGNAL_STAGE = {signal: number for number, _, signals, _ in STAGES for signal in signals}


def derive_signals(entities):
    """Signals implied by payment methods and fees, added to the events."""
    implied = []
    methods = {p["method"] for p in entities["payment"]}
    if "cash_handover" in methods:
        implied.append("cash_requested")
    if "gold" in methods:
        implied.append("gold_requested")
    if "crypto" in methods and entities["wallets"]:
        implied.append("crypto_to_new_wallet")
    if any(f["type"] in ("withdrawal_tax", "unlock_fee") for f in entities["fees"]):
        implied.append("withdrawal_tax_demanded")
    return implied


def stage(entities):
    """Return {number, name, next_move, evidence} or None."""
    found = {}
    for event in entities["events"]:
        found.setdefault(event["signal"], event.get("quote"))
    for signal in derive_signals(entities):
        found.setdefault(signal, None)
    present = [SIGNAL_STAGE[s] for s in found if s in SIGNAL_STAGE]
    if not present:
        return None
    number = max(present)
    _, name, signals, next_move = STAGES[number - 1]
    evidence = [found[s] for s in signals if s in found and found[s]]
    return {
        "number": number,
        "name": name,
        "next_move": next_move,
        "evidence": evidence[:3],
        "stages": [{"number": n, "name": nm} for n, nm, _, _ in STAGES],
    }
