from contextlib import asynccontextmanager

import pytest

from app.core.exceptions import AIProviderError
from app.services.ai import AIMessage, AIRequest, AIResponse, AIService, AIStreamChunk
from app.services.ai.base_provider import BaseAIProvider, ProviderMetadata, TokenUsage
from app.services.ai.stream_service import StreamService


@asynccontextmanager
async def null_track(**_kwargs):
    ctx = {"prompt_tokens": None, "completion_tokens": None}
    yield ctx


class FakeRegistry:
    def __init__(self, providers: dict[str, BaseAIProvider], order: list[str]) -> None:
        self.providers = providers
        self.order = order

    def provider_order(self, requested: str | None = None) -> list[str]:
        if requested:
            return [requested] + [name for name in self.order if name != requested]
        return self.order

    def get(self, name: str) -> BaseAIProvider | None:
        return self.providers.get(name)


class FakeProvider(BaseAIProvider):
    def __init__(self, name: str, model: str, tokens: list[str] | None = None, fail: bool = False) -> None:
        self.name = name
        self._model = model
        self.tokens = tokens or ["hello"]
        self.fail = fail

    @property
    def default_model(self) -> str:
        return self._model

    async def complete(self, request: AIRequest) -> AIResponse:
        if self.fail:
            raise RuntimeError(f"{self.name} failed")
        content = " ".join(self.tokens)
        return AIResponse(
            content=content,
            usage=TokenUsage(prompt_tokens=3, completion_tokens=len(self.tokens)).normalized(),
            metadata=ProviderMetadata(provider=self.name, model=request.model or self._model),
        )

    async def stream(self, request: AIRequest):
        if self.fail:
            raise RuntimeError(f"{self.name} failed")
        metadata = ProviderMetadata(provider=self.name, model=request.model or self._model)
        yield AIStreamChunk(event="meta", metadata=metadata)
        for token in self.tokens:
            yield AIStreamChunk(event="token", content=token, metadata=metadata)
        usage = TokenUsage(prompt_tokens=3, completion_tokens=len(self.tokens)).normalized()
        yield AIStreamChunk(event="usage", usage=usage, metadata=metadata)
        yield AIStreamChunk(event="done", usage=usage, metadata=metadata)


@pytest.mark.asyncio
async def test_complete_uses_requested_provider_and_tracks_usage(monkeypatch):
    monkeypatch.setattr("app.services.ai.ai_service.AIInteractionLogger.track", null_track)
    service = AIService(
        FakeRegistry(
            {
                "openai": FakeProvider("openai", "gpt-test", ["openai"]),
                "anthropic": FakeProvider("anthropic", "claude-test", ["anthropic"]),
            },
            ["openai", "anthropic"],
        )
    )

    response = await service.complete(
        AIRequest(messages=[AIMessage(role="user", content="Hi")], provider="anthropic")
    )

    assert response.content == "anthropic"
    assert response.metadata.provider == "anthropic"
    assert response.usage.total_tokens == 4


@pytest.mark.asyncio
async def test_complete_falls_back_when_primary_fails(monkeypatch):
    monkeypatch.setattr("app.services.ai.ai_service.AIInteractionLogger.track", null_track)
    service = AIService(
        FakeRegistry(
            {
                "openai": FakeProvider("openai", "gpt-test", fail=True),
                "anthropic": FakeProvider("anthropic", "claude-test", ["fallback"]),
            },
            ["openai", "anthropic"],
        )
    )

    response = await service.complete(AIRequest(messages=[AIMessage(role="user", content="Hi")]))

    assert response.content == "fallback"
    assert response.metadata.provider == "anthropic"


@pytest.mark.asyncio
async def test_stream_emits_unified_events(monkeypatch):
    monkeypatch.setattr("app.services.ai.ai_service.AIInteractionLogger.track", null_track)
    service = AIService(
        FakeRegistry({"openai": FakeProvider("openai", "gpt-test", ["A", "B"])}, ["openai"])
    )

    chunks = [
        chunk
        async for chunk in service.stream(AIRequest(messages=[AIMessage(role="user", content="Hi")]))
    ]

    assert [chunk.event for chunk in chunks] == ["meta", "token", "token", "usage", "done"]
    assert "".join(chunk.content for chunk in chunks if chunk.event == "token") == "AB"
    assert chunks[-1].usage.total_tokens == 5


@pytest.mark.asyncio
async def test_stream_service_formats_sse(monkeypatch):
    monkeypatch.setattr("app.services.ai.ai_service.AIInteractionLogger.track", null_track)
    service = AIService(
        FakeRegistry({"openai": FakeProvider("openai", "gpt-test", ["A"])}, ["openai"])
    )

    events = [
        event
        async for event in StreamService.sse_from_chunks(
            service.stream(AIRequest(messages=[AIMessage(role="user", content="Hi")]))
        )
    ]

    assert events[0].startswith("event: meta")
    assert any("event: token" in event and '"content": "A"' in event for event in events)
    assert events[-1].startswith("event: done")


@pytest.mark.asyncio
async def test_request_validation_rejects_empty_messages(monkeypatch):
    monkeypatch.setattr("app.services.ai.ai_service.AIInteractionLogger.track", null_track)
    service = AIService(FakeRegistry({}, []))

    with pytest.raises(AIProviderError):
        await service.complete(AIRequest(messages=[]))
