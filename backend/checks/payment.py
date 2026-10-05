"""How they want you to pay, fees to withdraw, and where the app comes from
(docs/BUILD_BRIEF.md §7)."""

from backend import normalize
from backend.flags import AMBER, RED, RULE_SOURCE, Flag

PAYMENT_TEXT = {
    "cash_handover": ("Cash handed to a person", "Real investment firms never collect cash in person."),
    "gold": ("Payment in gold", "Real investment firms never ask you to buy or hand over gold."),
}
UNREVERSABLE = "Crypto payments can't be reversed or traced back to a firm."


def check_payment(entities, _ctx=None):
    flags = []
    for item in entities["payment"]:
        method = item["method"]
        if method in PAYMENT_TEXT:
            title, why = PAYMENT_TEXT[method]
            said = f" They said: \"{item['quote']}\"" if item["quote"] else ""
            flags.append(Flag(RED, f"payment.{method}", title, why + said,
                              f"{RULE_SOURCE}: payment method", "payment", title))
        elif method == "crypto":
            wallets = entities["wallets"]
            if wallets:
                flags.append(Flag(
                    RED, "payment.crypto_wallet", "Crypto sent to a wallet they gave you",
                    f"{UNREVERSABLE} A licensed firm won't ask you to send crypto to a wallet address "
                    f"in a chat ({normalize.short_wallet(wallets[0])}).",
                    f"{RULE_SOURCE}: payment method", "payment", "Crypto"))
            else:
                flags.append(Flag(
                    AMBER, "payment.crypto", "They want payment in crypto",
                    UNREVERSABLE, f"{RULE_SOURCE}: payment method", "payment", "Crypto"))
    return flags


def check_fees(entities, _ctx=None):
    flags = []
    for fee in entities["fees"]:
        kind = fee["type"]
        if kind == "withdrawal_tax" or kind == "unlock_fee" or (kind == "withdrawal_fee" and fee["percent"]):
            if kind == "withdrawal_tax":
                what = "A \"tax\" to withdraw your money"
            elif kind == "unlock_fee":
                what = "A fee to unlock your account"
            else:
                what = f"A {fee['percent']:g}% fee to withdraw"
            flags.append(Flag(
                RED, f"fees.{kind}", what,
                "Paying to get your own money out is how investment scams take a last payment. "
                "Real platforms deduct any fees from your balance; they don't ask you to pay first.",
                f"{RULE_SOURCE}: fees to withdraw", "fees", what))
    return flags


def check_apps(entities, _ctx=None):
    return [Flag(
        RED, "app.from_link", f"{app['name']} is installed from a link, not an app store",
        "Scam platforms are often installed from a download link because the app stores removed them "
        "or never approved them. The numbers inside a fake app can be anything.",
        f"{RULE_SOURCE}: app source", "app", app["name"],
    ) for app in entities["apps"] if app["source"] == "link"]


LOCKOUT_SIGNALS = {
    "withdrawal_blocked": "Your withdrawal is being blocked",
    "minimum_trading_commitment": "A trading target before you can withdraw",
    "account_frozen": "Your account is \"frozen\"",
}


def check_lockout(entities, _ctx=None):
    """Lockout-stage signals (§9 stage 7) are red on their own."""
    flags = []
    for event in entities["events"]:
        title = LOCKOUT_SIGNALS.get(event["signal"])
        if title and all(f.title != title for f in flags):
            flags.append(Flag(
                RED, f"lockout.{event['signal']}", title,
                "Holding your money back until you pay, trade more or top up is how these scams take more. "
                "Paying won't release it.",
                f"{RULE_SOURCE}: withdrawal held back", "event", title))
    return flags


def check_recovery(entities, _ctx=None):
    for event in entities["events"]:
        if event["signal"] == "fund_recovery_offer":
            return [Flag(
                RED, "recovery.offer", "An offer to recover lost money",
                "\"Fund recovery\" services that contact you after a scam are usually the same scammers. "
                "Police and banks don't charge to recover scam losses.",
                f"{RULE_SOURCE}: fund recovery", "event", "Fund recovery offer")]
    return []
