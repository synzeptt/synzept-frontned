from collections.abc import AsyncIterator
from typing import Any

import httpx

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


class GeminiProvider(BaseAIProvider):
    name = "gemini"
    _base_url = "https://generativelanguage.googleapis.com/v1beta/models"

    def __init__(self, client: httpx.AsyncClient | None = None) -> None:
        if not settings.gemini_api_key or settings.gemini_api_key.startswith("replace_with"):
            raise ValueError("GEMINI_API_KEY not configured")
        self._client = client or httpx.AsyncClient(timeout=settings.llm_timeout_seconds)

    @property
    def default_model(self) -> str:
        return settings.gemini_model

    async def complete(self, request: AIRequest) -> AIResponse:
        model = request.model or self.default_model
        response = await self._client.post(
            self._url(model, "generateContent"),
            headers=self._headers(),
            json=self._payload(request),
        )
        response.raise_for_status()
        data = response.json()
        content = self._extract_text(data).strip()
        usage = self._usage(data.get("usageMetadata"), request.messages, content)
        return AIResponse(
            content=content,
            usage=usage,
            metadata=ProviderMetadata(
                provider=self.name,
                model=model,
                finish_reason=self._finish_reason(data),
                raw={"prompt_feedback": data.get("promptFeedback")},
            ),
        )

    async def stream(self, request: AIRequest) -> AsyncIterator[AIStreamChunk]:
        model = request.model or self.default_model
        metadata = ProviderMetadata(provider=self.name, model=model)
        yield AIStreamChunk(event="meta", metadata=metadata)

        content_parts: list[str] = []
        usage: TokenUsage | None = None
        async with self._client.stream(
            "POST",
            f"{self._url(model, 'streamGenerateContent')}?alt=sse",
            headers=self._headers(),
            json=self._payload(request),
        ) as response:
            response.raise_for_status()
            async for line in response.aiter_lines():
                if not line.startswith("data: "):
                    continue
                data = line.removeprefix("data: ").strip()
                if not data or data == "[DONE]":
                    continue
                chunk = httpx.Response(200, content=data).json()
                text = self._extract_text(chunk)
                if text:
                    content_parts.append(text)
                    yield AIStreamChunk(event="token", content=text, metadata=metadata)
                if chunk.get("usageMetadata"):
                    usage = self._usage(chunk.get("usageMetadata"), request.messages, "".join(content_parts))
                finish_reason = self._finish_reason(chunk)
                if finish_reason:
                    metadata.finish_reason = finish_reason

        final_usage = usage or estimate_request_usage(request.messages, "".join(content_parts))
        yield AIStreamChunk(event="usage", usage=final_usage, metadata=metadata)
        yield AIStreamChunk(event="done", usage=final_usage, metadata=metadata)

    def _url(self, model: str, method: str) -> str:
        return f"{self._base_url}/{model}:{method}"

    def _headers(self) -> dict[str, str]:
        return {
            "Content-Type": "application/json",
            "x-goog-api-key": settings.gemini_api_key,
        }

    @staticmethod
    def _payload(request: AIRequest) -> dict[str, Any]:
        system_parts = [message.content for message in request.messages if message.role == "system"]
        contents = []
        for message in request.messages:
            if message.role == "system":
                continue
            contents.append(
                {
                    "role": "model" if message.role == "assistant" else "user",
                    "parts": [{"text": message.content}],
                }
            )
        payload: dict[str, Any] = {
            "contents": contents,
            "generationConfig": {
                "temperature": request.temperature,
                "maxOutputTokens": request.max_tokens,
                "thinkingConfig": {"thinkingBudget": 0},
            },
        }
        if system_parts:
            payload["systemInstruction"] = {
                "parts": [{"text": "\n\n".join(system_parts)}],
            }
        return payload

    @staticmethod
    def _extract_text(data: dict[str, Any]) -> str:
        texts: list[str] = []
        for candidate in data.get("candidates", []):
            for part in candidate.get("content", {}).get("parts", []):
                text = part.get("text")
                if text:
                    texts.append(text)
        return "".join(texts)

    @staticmethod
    def _finish_reason(data: dict[str, Any]) -> str | None:
        candidates = data.get("candidates") or []
        if not candidates:
            return None
        return candidates[0].get("finishReason")

    @staticmethod
    def _usage(raw_usage: dict[str, Any] | None, messages: list[AIMessage], completion: str) -> TokenUsage:
        if not raw_usage:
            return estimate_request_usage(messages, completion)
        return TokenUsage(
            prompt_tokens=int(raw_usage.get("promptTokenCount") or 0),
            completion_tokens=int(raw_usage.get("candidatesTokenCount") or 0),
            total_tokens=int(raw_usage.get("totalTokenCount") or 0),
        ).normalized()
