from collections.abc import AsyncIterator
from typing import Any

from anthropic import AsyncAnthropic

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


class AnthropicProvider(BaseAIProvider):
    name = "anthropic"

    def __init__(self, client: AsyncAnthropic | None = None) -> None:
        if client:
            self._client = client
            return
        if not settings.anthropic_api_key or settings.anthropic_api_key.startswith("replace_with"):
            raise ValueError("ANTHROPIC_API_KEY not configured")
        self._client = AsyncAnthropic(api_key=settings.anthropic_api_key, timeout=settings.llm_timeout_seconds)

    @property
    def default_model(self) -> str:
        return settings.anthropic_model

    @staticmethod
    def _split_messages(messages: list[AIMessage]) -> tuple[str, list[dict[str, str]]]:
        system_parts: list[str] = []
        conversation: list[dict[str, str]] = []
        for message in messages:
            if message.role == "system":
                system_parts.append(message.content)
            else:
                conversation.append({"role": message.role, "content": message.content})
        return "\n\n".join(system_parts), conversation

    @staticmethod
    def _usage(raw_usage: Any, fallback: TokenUsage) -> TokenUsage:
        if not raw_usage:
            return fallback
        return TokenUsage(
            prompt_tokens=getattr(raw_usage, "input_tokens", 0) or 0,
            completion_tokens=getattr(raw_usage, "output_tokens", 0) or 0,
        ).normalized()

    async def complete(self, request: AIRequest) -> AIResponse:
        model = request.model or self.default_model
        system, messages = self._split_messages(request.messages)
        response = await self._client.messages.create(
            model=model,
            max_tokens=request.max_tokens,
            temperature=request.temperature,
            system=system,
            messages=messages,
        )
        content = "".join(block.text for block in response.content if block.type == "text").strip()
        fallback = estimate_request_usage(request.messages, content)
        return AIResponse(
            content=content,
            usage=self._usage(getattr(response, "usage", None), fallback),
            metadata=ProviderMetadata(
                provider=self.name,
                model=model,
                request_id=getattr(response, "id", None),
                finish_reason=getattr(response, "stop_reason", None),
            ),
        )

    async def stream(self, request: AIRequest) -> AsyncIterator[AIStreamChunk]:
        model = request.model or self.default_model
        system, messages = self._split_messages(request.messages)
        metadata = ProviderMetadata(provider=self.name, model=model)
        yield AIStreamChunk(event="meta", metadata=metadata)

        content_parts: list[str] = []
        usage: TokenUsage | None = None

        async with self._client.messages.stream(
            model=model,
            max_tokens=request.max_tokens,
            temperature=request.temperature,
            system=system,
            messages=messages,
        ) as stream:
            async for event in stream:
                event_type = getattr(event, "type", "")
                if event_type == "message_start":
                    message = getattr(event, "message", None)
                    metadata.request_id = getattr(message, "id", None)
                    usage = self._usage(getattr(message, "usage", None), estimate_request_usage(request.messages))
                elif event_type == "content_block_delta":
                    delta = getattr(getattr(event, "delta", None), "text", "")
                    if delta:
                        content_parts.append(delta)
                        yield AIStreamChunk(event="token", content=delta, metadata=metadata)
                elif event_type == "message_delta":
                    delta = getattr(event, "delta", None)
                    metadata.finish_reason = getattr(delta, "stop_reason", None) or metadata.finish_reason
                    raw_usage = getattr(event, "usage", None)
                    if raw_usage:
                        usage = TokenUsage(
                            prompt_tokens=usage.prompt_tokens if usage else 0,
                            completion_tokens=getattr(raw_usage, "output_tokens", 0) or 0,
                        ).normalized()

        final_usage = usage or estimate_request_usage(request.messages, "".join(content_parts))
        yield AIStreamChunk(event="usage", usage=final_usage, metadata=metadata)
        yield AIStreamChunk(event="done", usage=final_usage, metadata=metadata)
