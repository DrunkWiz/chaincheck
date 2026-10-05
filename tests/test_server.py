import pytest

from backend.db import _arg
from backend.server import resolve


@pytest.mark.parametrize("raw,expected", [
    ("/api/meta", ("/api/meta", "")),
    ("/api/reports?q=x&type=crypto", ("/api/reports", "q=x&type=crypto")),
    # Vercel rewrite, original path lost
    ("/api/index?__route=reports&q=x", ("/api/reports", "q=x")),
    ("/api/index?__route=admin/reports/0123456789abcdef/approve", ("/api/admin/reports/0123456789abcdef/approve", "")),
    # Vercel rewrite, original path kept
    ("/api/reports?q=x&__route=reports", ("/api/reports", "q=x")),
])
def test_resolve(raw, expected):
    assert resolve(raw) == expected


def test_turso_numbers_are_strings():
    assert _arg(0.5) == {"type": "float", "value": "0.5"}
    assert _arg(7) == {"type": "integer", "value": "7"}
