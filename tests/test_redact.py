import pytest

from backend.redact import redact, scrub_display


@pytest.mark.parametrize("text,label", [
    ("My IC is S1234567D.", "[NRIC]"),
    ("FIN G7654321K here", "[NRIC]"),
    ("Call +65 8000 4321 now", "[PHONE]"),
    ("Call 9123-4567 now", "[PHONE]"),
    ("UK line +44 20 7946 0000", "[PHONE]"),
    ("Pay into 123-456789-0 today", "[ACCOUNT]"),
    ("Account 0123456789012 please", "[ACCOUNT]"),
    ("Email me at tan.ah.kow@mail.example", "[EMAIL]"),
    ("Mr Victor Hale said so", "[NAME]"),
    ("my name is Mei Ling Tan and", "[NAME]"),
])
def test_redacts(text, label):
    out, counts = redact(text)
    assert label in out and counts[label] >= 1


def test_extracted_names_are_redacted_case_insensitively():
    out, _ = redact("Serene Lau told me. Later SERENE LAU called.", names=["Serene Lau"])
    assert "Serene" not in out and "SERENE" not in out


def test_entities_needed_for_the_network_survive():
    text = "Site alphagain-pro.example, wallet 0x7a3f9c2e4b1d8a6f0e5c7b9d2a4f6e8c1b3dc91e, firm AlphaGain Pro."
    out, counts = redact(text)
    assert out == text and counts == {}


def test_dates_and_money_survive():
    text = "On 2026-09-20 I paid $50,000 and then $1,200."
    assert redact(text)[0] == text


def test_scrub_display_hides_numbers_only():
    out = scrub_display("Call Ms Lau at +65 8000 4321, IC S1234567D, acct 123-456789-0, on 2026-09-20")
    assert "8000" not in out and "S1234567D" not in out and "456789" not in out
    assert "Ms Lau" in out and "2026-09-20" in out
