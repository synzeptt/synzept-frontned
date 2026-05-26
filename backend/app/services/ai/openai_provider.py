from collections.abc import AsyncIterator
from typing import Any

from openai import AsyncOpenAI

from app.core.config import get_settings
from app.services.ai.base_provider import (
    AIMessage,
    AIRequest,
    AIResponse,
    AIStreamChunk,
    BaseAIProvider,
    ProviderMetadata,
    TokenUsage,
    estimate_request_usage,
)

settings = get_settings()


class OpenAIProvider(BaseAIProvider):
    name = "openai"

    def __init__(self, client: AsyncOpenAI | None = None) -> None:
        if client:
            self._client = client
            return
        if not settings.openai_api_key or settings.openai_api_key.startswith("replace_with"):
            raise ValueError("OPENAI_API_KEY not configured")
        self._client = AsyncOpenAI(api_key=settings.openai_api_key, timeout=settings.llm_timeout_seconds)

    @property
    def default_model(self) -> str:
        return settings.openai_model

    @staticmethod
    def _messages(messages: list[AIMessage]) -> list[dict[str, str]]:
        return [{"role": message.role, "content": message.content} for message in messages]

    @staticmethod
    def _usage(raw_usage: Any, fallback: TokenUsage) -> TokenUsage:
        if not raw_usage:
            return fallback
        return TokenUsage(
            prompt_tokens=getattr(raw_usage, "prompt_tokens", 0) or 0,
            completion_tokens=getattr(raw_usage, "completion_tokens", 0) or 0,
            total_tokens=getattr(raw_usage, "total_tokens", 0) or 0,
        ).normalized()

    async def complete(self, request: AIRequest) -> AIResponse:
        model = request.model or self.default_model
        response = await self._client.chat.completions.create(
            model=model,
            messages=self._messages(request.messages),
            temperature=request.temperature,
            max_tokens=request.max_tokens,
        )
        choice = response.choices[0]
        content = (choice.message.content or "").strip()
        fallback = estimate_request_usage(request.messages, content)
        return AIResponse(
            content=content,
            usage=self._usage(getattr(response, "usage", None), fallback),
            metadata=ProviderMetadata(
                provider=self.name,
                model=model,
                request_id=getattr(response, "id", None),
                finish_reason=getattr(choice, "finish_reason", None),
            ),
        )

    async def stream(self, request: AIRequest) -> AsyncIterator[AIStreamChunk]:
        model = request.model or self.default_model
        metadata = ProviderMetadata(provider=self.name, model=model)
        yield AIStreamChunk(event="meta", metadata=metadata)

        stream = await self._client.chat.completions.create(
            model=model,
            messages=self._messages(request.messages),
            temperature=request.temperature,
            max_tokens=request.max_tokens,
            stream=True,
            stream_options={"include_usage": True},
        )
        content_parts: list[str] = []
        usage: TokenUsage | None = None
        finish_reason: str | None = None

        async for event in stream:
            if getattr(event, "id", None):
                metadata.request_id = event.id
            if getattr(event, "usage", None):
                usage = self._usage(event.usage, estimate_request_usage(request.messages, "".join(content_parts)))
                continue
            if not event.choices:
                continue
            choice = event.choices[0]
            finish_reason = getattr(choice, "finish_reason", None) or finish_reason
            delta = getattr(choice.delta, "content", None)
            if delta:
                content_parts.append(delta)
                yield AIStreamChunk(event="token", content=delta, metadata=metadata)

        metadata.finish_reason = finish_reason
        final_usage = usage or estimate_request_usage(request.messages, "".join(content_parts))
        yield AIStreamChunk(event="usage", usage=final_usage, metadata=metadata)
        yield AIStreamChunk(event="done", usage=final_usage, metadata=metadata)
