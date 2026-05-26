from collections.abc import AsyncIterator

from app.services.ai.ai_service import AIService
from app.services.ai.base_provider import AIRequest, AIMessage


class LLMRouter:
    """Compatibility facade for legacy imports."""

    def __init__(self, service: AIService | None = None) -> None:
        self._service = service or AIService()

    async def complete(
        self,
        messages: list[AIMessage],
        temperature: float = 0.3,
        provider: str | None = None,
        metadata: dict | None = None,
    ) -> str:
        response = await self._service.complete(
            AIRequest(messages=messages, temperature=temperature, provider=provider, metadata=metadata or {})
        )
        return response.content

    async def stream(
        self,
        messages: list[AIMessage],
        temperature: float = 0.3,
        provider: str | None = None,
        metadata: dict | None = None,
    ) -> AsyncIterator[str]:
        async for chunk in self._service.stream(
            AIRequest(messages=messages, temperature=temperature, provider=provider, metadata=metadata or {})
        ):
            if chunk.event == "token":
                yield chunk.content
