"""Every check in BUILD_BRIEF §7, including edge cases."""

from datetime import date

import pytest

from backend import config
from backend.checks import domain, fuzzy, mas, network, payment, people, returns
from tests.conftest import SECRET, entities, fixture_fid, make_ctx


def rules(flags):
    return [f.rule for f in flags]


def levels(flags):
    return {f.rule: f.level for f in flags}


# --- MAS, fuzzy, copycat --------------------------------------------------------

class TestMas:
    def test_unknown_company_is_red_not_licensed(self, ctx):
        flags = mas.check(entities(companies=["Golden Lotus Wealth"]), ctx)
        assert levels(flags) == {"mas.not_licensed": "red"}
        assert flags[0].snapshot_date == "2026-10-01"
        assert "2026-10-01" in flags[0].source

    def test_alert_list_company_is_red(self, ctx):
        flags = mas.check(entities(companies=["QuantEdge AI"]), ctx)
        assert rules(flags) == ["mas.alert_list"]

    def test_alert_list_fuzzy_match(self, ctx):
        assert "mas.alert_list" in rules(mas.check(entities(companies=["Quant Edge A.I."]), ctx))

    def test_platforms_are_never_flagged(self, ctx):
        assert mas.check(entities(companies=["WhatsApp", "Telegram", "Binance"]), ctx) == []

    def test_lookalike_name_is_red_copycat(self, ctx):
        flags = mas.check(entities(companies=["Merlion Krest Capital"]), ctx)
        assert rules(flags) == ["mas.lookalike_name"]
        assert "Merlion Crest Capital" in flags[0].title

    def test_below_fuzzy_threshold_is_just_not_licensed(self, ctx):
        assert rules(mas.check(entities(companies=["Merlion Capital Group"]), ctx)) == ["mas.not_licensed"]

    def test_suffix_and_punctuation_do_not_matter(self, ctx):
        e = entities(companies=["HARBOURVIEW SECURITIES PTE LTD"], domains=["harbourview-securities.example"])
        assert mas.check(e, ctx) == []

    def test_exact_name_with_wrong_phone_is_copycat(self, ctx):
        e = entities(companies=["Merlion Crest Capital Pte Ltd"], phones=["+65 8000 4321"])
        flags = mas.check(e, ctx)
        assert rules(flags) == ["copycat.contact_mismatch"]
        assert "8000" not in flags[0].detail  # phone numbers are never shown

    def test_exact_name_with_wrong_domain_is_copycat(self, ctx):
        e = entities(companies=["Merlion Crest Capital"], domains=["merlioncrest-capital.example"])
        flags = mas.check(e, ctx)
        assert rules(flags) == ["copycat.contact_mismatch"]
        assert "merlioncrest-capital[.]example" in flags[0].detail

    def test_exact_name_with_wrong_email_is_copycat(self, ctx):
        e = entities(companies=["Merlion Crest Capital"], emails=["desk@merlion-vip.example"])
        assert rules(mas.check(e, ctx)) == ["copycat.contact_mismatch"]

    def test_exact_name_with_matching_contacts_has_no_flag(self, ctx):
        e = entities(companies=["Merlion Crest Capital Pte. Ltd."], phones=["6000 0202"],
                     domains=["www.merlioncrestcapital.example"], emails=["help@merlioncrestcapital.example"])
        assert mas.check(e, ctx) == []
        assert "merlioncrestcapital.example" in ctx.on_record_domains

    def test_exact_name_without_contact_details_is_amber(self, ctx):
        assert levels(mas.check(entities(companies=["Merlion Crest Capital"]), ctx)) == {
            "copycat.no_contact_details": "amber"}

    def test_chat_links_are_not_contact_mismatches(self, ctx):
        e = entities(companies=["Merlion Crest Capital"], domains=["t.me", "harbourview-securities.example"],
                     phones=["+65 6000 0202"])
        # t.me is skipped; another licensed firm's site still doesn't match this firm's record.
        assert rules(mas.check(e, ctx)) == ["copycat.contact_mismatch"]

    def test_duplicate_company_names_flag_once(self, ctx):
        assert len(mas.check(entities(companies=["Golden Lotus", "GOLDEN LOTUS"]), ctx)) == 1


class TestFuzzy:
    def test_short_names_are_not_fuzzy_matched(self):
        firm, score, exact = fuzzy.best_match("Abc", fixture_fid().firms)
        assert firm is None

    def test_threshold_from_config(self, monkeypatch):
        monkeypatch.setattr(config, "FUZZY_MATCH_MIN", 0.99)
        assert fuzzy.best_match("Merlion Krest Capital", fixture_fid().firms)[0] is None


# --- Domain age -----------------------------------------------------------------

class TestDomain:
    def check(self, *domains, **kwargs):
        return domain.check(entities(domains=list(domains)), make_ctx(**kwargs))

    def test_under_180_days_is_red(self):
        flags = self.check("merlioncrest-capital.example")
        assert levels(flags) == {"domain.very_new": "red"}
        assert "15 days ago" in flags[0].title

    def test_under_365_days_is_amber(self):
        assert levels(self.check("medium-site.example")) == {"domain.new": "amber"}

    def test_old_domain_has_no_flag(self):
        assert self.check("old-site.example") == []

    def test_boundaries(self):
        today = date(2026, 10, 5)
        exactly_180 = {"x.example": date.fromordinal(today.toordinal() - 180)}
        exactly_365 = {"x.example": date.fromordinal(today.toordinal() - 365)}
        assert levels(self.check("x.example", rdap=exactly_180.get)) == {"domain.new": "amber"}
        assert self.check("x.example", rdap=exactly_365.get) == []

    def test_failed_lookup_is_amber(self):
        assert levels(self.check("nobody-knows.example")) == {"domain.age_unknown": "amber"}

    def test_skip_list_and_subdomains(self):
        assert self.check("t.me", "chat.whatsapp.com", "apps.apple.com", "bit.ly") == []

    def test_on_record_domains_are_skipped(self):
        ctx = make_ctx()
        ctx.on_record_domains.add("brand-new.example")
        assert domain.check(entities(domains=["brand-new.example"]), ctx) == []

    def test_domain_is_shown_defanged(self):
        assert "[.]" in self.check("merlioncrest-capital.example")[0].title

    def test_registration_date_parsing(self):
        rdap = {"events": [{"eventAction": "last changed", "eventDate": "2026-01-01T00:00:00Z"},
                           {"eventAction": "registration", "eventDate": "2025-03-04T10:00:00Z"}]}
        assert domain.registration_date(rdap) == date(2025, 3, 4)
        assert domain.registration_date({}) is None

    def test_real_lookup_fails_closed_without_network(self):
        domain._cache.clear()
        assert domain.rdap_lookup("example.com") is None


# --- Returns --------------------------------------------------------------------

class TestReturns:
    @pytest.mark.parametrize("percent,period,expected", [
        (32, "month", 2_698.3), (2, "day", 137_640.5), (10, "year", 10.0), (1, "week", 67.8),
    ])
    def test_annualise(self, percent, period, expected):
        assert returns.annualise(percent, period) == pytest.approx(expected, rel=1e-3)

    def test_unknown_period_gives_none(self):
        assert returns.annualise(50, "unknown") is None

    def test_huge_returns_do_not_overflow(self):
        assert returns.annualise(1000, "day") == returns.CAP_PCT

    def claim(self, percent, period="year"):
        return returns.check(entities(returns=[{"percent": percent, "period": period, "quote": "q"}]))

    def test_above_30_is_red(self):
        assert levels(self.claim(30.1)) == {"returns.too_high": "red"}

    def test_exactly_30_is_amber(self):
        assert levels(self.claim(30)) == {"returns.high": "amber"}

    def test_exactly_15_is_amber(self):
        assert levels(self.claim(15)) == {"returns.high": "amber"}

    def test_under_15_has_no_flag(self):
        assert self.claim(14.9) == []

    def test_unknown_period_has_no_flag(self):
        assert self.claim(500, "unknown") == []

    def test_monthly_compounds(self):
        flags = self.claim(32, "month")
        assert "2,698%" in flags[0].title

    def test_format(self):
        assert returns.format_pct(2.5) == "2.5%"
        assert returns.format_pct(30.0) == "30%"
        assert returns.format_pct(2_697.6) == "2,698%"
        assert returns.format_pct(5e9) == "over 1,000,000%"


# --- Payment, fees, apps, lockout, recovery --------------------------------------

class TestPayment:
    def pay(self, method, **extra):
        return payment.check_payment(entities(payment=[{"method": method, "quote": "q"}], **extra))

    @pytest.mark.parametrize("method", ["cash_handover", "gold"])
    def test_cash_and_gold_are_red(self, method):
        assert levels(self.pay(method)) == {f"payment.{method}": "red"}

    def test_crypto_to_a_wallet_is_red(self):
        assert levels(self.pay("crypto", wallets=["0x" + "a" * 40])) == {"payment.crypto_wallet": "red"}

    def test_crypto_without_wallet_is_amber(self):
        assert levels(self.pay("crypto")) == {"payment.crypto": "amber"}

    @pytest.mark.parametrize("method", ["bank_transfer", "paynow", "card", "other"])
    def test_ordinary_methods_have_no_flag(self, method):
        assert self.pay(method) == []


class TestFees:
    def fee(self, kind, percent=None, amount=None):
        return payment.check_fees(entities(fees=[{"type": kind, "percent": percent, "amount": amount, "quote": "q"}]))

    @pytest.mark.parametrize("kind", ["withdrawal_tax", "unlock_fee"])
    def test_tax_and_unlock_are_red(self, kind):
        assert levels(self.fee(kind)) == {f"fees.{kind}": "red"}

    def test_percentage_withdrawal_fee_is_red(self):
        assert levels(self.fee("withdrawal_fee", percent=15)) == {"fees.withdrawal_fee": "red"}

    def test_small_flat_withdrawal_fee_is_not_red(self):
        assert self.fee("withdrawal_fee", amount=5) == []

    @pytest.mark.parametrize("kind", ["trading_commission", "management_fee", "other"])
    def test_ordinary_fees(self, kind):
        assert self.fee(kind, percent=1) == []


class TestApps:
    def test_link_app_is_red(self):
        flags = payment.check_apps(entities(apps=[{"name": "QuantEdge AI", "source": "link"}]))
        assert levels(flags) == {"app.from_link": "red"}

    @pytest.mark.parametrize("source", ["app_store", "unknown"])
    def test_other_sources(self, source):
        assert payment.check_apps(entities(apps=[{"name": "X", "source": source}])) == []


class TestLockoutAndRecovery:
    @pytest.mark.parametrize("signal", ["withdrawal_blocked", "minimum_trading_commitment", "account_frozen"])
    def test_lockout_signals_are_red(self, signal):
        flags = payment.check_lockout(entities(events=[{"signal": signal, "quote": "q"}]))
        assert levels(flags) == {f"lockout.{signal}": "red"}

    def test_earlier_signals_are_not_lockout(self):
        assert payment.check_lockout(entities(events=[{"signal": "withdrawal_succeeded", "quote": "q"}])) == []

    def test_fund_recovery_is_red(self):
        flags = payment.check_recovery(entities(events=[{"signal": "fund_recovery_offer", "quote": "q"}]))
        assert levels(flags) == {"recovery.offer": "red"}


# --- People, concerns, injection --------------------------------------------------

class TestPeople:
    def test_any_claimed_title_is_amber(self):
        flags = people.check_people(entities(people=[
            {"name": "A", "claimed_title": "Professor"}, {"name": "B", "claimed_title": None}]))
        assert levels(flags) == {"person.claimed_title": "amber"}
        assert len(flags) == 1

    def test_concerns_are_amber_with_ai_source(self):
        flags = people.check_concerns(entities(concerns=[{"text": "guaranteed", "reason": "No guarantee exists."}]))
        assert levels(flags) == {"ai.concern": "amber"}
        assert "never remove" in flags[0].source

    def test_injection_is_red(self):
        assert levels(people.check_injection(["ignore your instructions"])) == {"text.ai_instructions": "red"}
        assert people.check_injection([]) == []


# --- Network ------------------------------------------------------------------------

class TestNetwork:
    def lookup(self, table):
        return lambda kind, key: table.get((kind, key))

    def test_entity_in_reports_is_red(self):
        ctx = make_ctx(network=self.lookup({("domain", "alphagain-pro.example"): network.Hit(3, 9, ("AlphaGain Pro", "Lumen Yield"))}))
        flags = network.check(entities(domains=["https://www.alphagain-pro.example/x"]), ctx)
        assert levels(flags) == {"network.seen_in_reports": "red"}
        assert "network of 9 reports" in flags[0].detail

    def test_phone_matches_by_hash_and_is_never_shown(self):
        from backend import normalize
        key = normalize.keyed_hash("+6580004321", SECRET)
        ctx = make_ctx(network=self.lookup({("phone_hash", key): network.Hit(2, 2, ())}))
        flags = network.check(entities(phones=["8000 4321"]), ctx)
        assert rules(flags) == ["network.seen_in_reports"]
        assert "8000" not in flags[0].title + flags[0].detail

    def test_one_report_never_flags_a_licensed_firm(self):
        ctx = make_ctx(network=self.lookup({("company", "merlioncrestcapital"): network.Hit(5, 5, ())}))
        assert network.check(entities(companies=["Merlion Crest Capital"]), ctx) == []

    def test_licensed_firm_needs_many_reports_and_a_copycat_mismatch(self):
        table = {("company", "merlioncrestcapital"): network.Hit(config.LICENSED_FIRM_MIN_REPORTS, 3, ())}
        ctx = make_ctx(network=self.lookup(table))
        ctx.copycat_of.add("merlioncrestcapital")
        flags = network.check(entities(companies=["Merlion Crest Capital"]), ctx)
        assert rules(flags) == ["network.copycat_reports"]
        assert "Copycats of" in flags[0].title and "scam" not in flags[0].title.lower()

        table[("company", "merlioncrestcapital")] = network.Hit(config.LICENSED_FIRM_MIN_REPORTS - 1, 2, ())
        ctx = make_ctx(network=self.lookup(table))
        ctx.copycat_of.add("merlioncrestcapital")
        assert network.check(entities(companies=["Merlion Crest Capital"]), ctx) == []

    def test_licensed_phone_is_never_flagged(self):
        from backend import normalize
        key = normalize.keyed_hash("+6560000202", SECRET)
        ctx = make_ctx(network=self.lookup({("phone_hash", key): network.Hit(4, 4, ())}))
        assert network.check(entities(phones=["+65 6000 0202"]), ctx) == []

    def test_no_community_data_means_no_flags(self, ctx):
        assert network.check(entities(domains=["x.example"]), ctx) == []

    def test_platforms_and_link_placeholder_are_not_keys(self):
        keys = network.entity_keys(entities(companies=["Telegram"], apps=[{"name": "App installed from a link", "source": "link"}],
                                            domains=["t.me"]))
        assert keys == []
