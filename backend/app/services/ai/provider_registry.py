import logging

from app.core.config import get_settings
from app.services.ai.anthropic_provider import AnthropicProvider
from app.services.ai.base_provider import BaseAIProvider
from app.services.ai.gemini_provider import GeminiProvider
from app.services.ai.openai_provider import OpenAIProvider

logger = logging.getLogger(__name__)
settings = get_settings()


class ProviderRegistry:
    def __init__(self) -> None:
        self._providers: dict[str, BaseAIProvider] = {}

    def get(self, name: str) -> BaseAIProvider | None:
        provider_name = name.lower().strip()
        if provider_name in self._providers:
            return self._providers[provider_name]
        try:
            if provider_name == "gemini":
                provider = GeminiProvider()
            elif provider_name == "openai":
                provider = OpenAIProvider()
            elif provider_name == "anthropic":
                provider = AnthropicProvider()
            else:
                return None
        except ValueError as exc:
            logger.info("AI provider unavailable: %s", exc)
            return None
        self._providers[provider_name] = provider
        return provider

    def provider_order(self, requested: str | None = None) -> list[str]:
        preferred = (requested or settings.llm_provider or "gemini").lower().strip()
        fallback = (settings.llm_fallback_provider or "").lower().strip()
        order: list[str] = []
        for name in (preferred, fallback, "gemini", "openai", "anthropic"):
            if name and name not in order:
                order.append(name)
        return order

    def availability(self) -> dict[str, dict]:
        providers = {}
        for name in ("gemini", "openai", "anthropic"):
            provider = self.get(name)
            providers[name] = {
                "configured": provider is not None,
                "default_model": provider.default_model if provider else None,
            }
        return {
            "preferred": settings.llm_provider,
            "fallback": settings.llm_fallback_provider,
            "providers": providers,
            "available": any(item["configured"] for item in providers.values()),
        }
