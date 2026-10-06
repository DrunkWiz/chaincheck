"""The interface every model provider implements (pattern from Voucher Kaki)."""

from typing import Protocol


class ProviderError(Exception):
    """A provider couldn't produce a reply (network, quota, timeout, refusal)."""


class Provider(Protocol):
    name: str

    def complete(self, system: str, user: str) -> str:
        """Return the model's raw text reply. Raise ProviderError on failure."""
        ...

