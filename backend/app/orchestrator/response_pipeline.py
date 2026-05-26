"""AI request orchestration and response post-processing."""

from __future__ import annotations

from collections.abc import AsyncIterator
from uuid import UUID

from app.core.reliability import validate_ai_response
from app.services.ai import AIMessage, AIRequest, AIResponse, AIService, AIStreamChunk


class ResponsePipeline:
    def __init__(self, ai: AIService | None = None) -> None:
        self.ai = ai or AIService()

    async def complete(
        self,
        *,
        messages: list[AIMessage],
        user_id: UUID,
        conversation_id: UUID,
        provider: str | None,
        model: str | None,
        temperature: float,
        max_tokens: int,
    ) -> AIResponse:
        response = await self.ai.complete(
            AIRequest(
                messages=messages,
                provider=provider,
                model=model,
                temperature=temperature,
                max_tokens=max_tokens,
                metadata={
                    "interaction_type": "chat",
                    "user_id": user_id,
                    "conversation_id": conversation_id,
                },
            )
        )
        response.content = validate_ai_response(response.content)
        return response

    async def stream(
        self,
        *,
        messages: list[AIMessage],
        user_id: UUID,
        conversation_id: UUID,
        provider: str | None,
        model: str | None,
        temperature: float,
        max_tokens: int,
    ) -> AsyncIterator[AIStreamChunk]:
        async for chunk in self.ai.stream(
            AIRequest(
                messages=messages,
                provider=provider,
                model=model,
                temperature=temperature,
                max_tokens=max_tokens,
                metadata={
                    "interaction_type": "chat_stream",
                    "user_id": user_id,
                    "conversation_id": conversation_id,
                },
            )
        ):
            yield chunk
