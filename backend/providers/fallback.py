"""Try providers in order; the first that replies wins."""

from backend.providers.base import ProviderError


class AllProvidersFailed(ProviderError):
    pass


class FallbackProvider:
    name = "fallback"

    def __init__(self, providers):
        if not providers:
            raise ValueError("FallbackProvider needs at least one provider")
        self.providers = list(providers)
        self.last_used = None

    def complete(self, system, user):
        return self._first(lambda provider: provider.complete(system, user))

    def _first(self, call):
        errors = []
        for provider in self.providers:
            try:
                reply = call(provider)
            except ProviderError as exc:
                errors.append(f"{provider.name}: {exc}")
                continue
            self.last_used = provider.name
            return reply
        self.last_used = None
        raise AllProvidersFailed("; ".join(errors))
