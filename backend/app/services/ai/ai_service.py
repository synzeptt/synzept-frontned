import asyncio
import logging
import time
from collections.abc import AsyncIterator
from dataclasses import replace

from app.core.config import get_settings
from app.core.exceptions import AIProviderError
from app.core.reliability import validate_ai_response
from app.infrastructure.monitoring import monitor
from app.services.ai.base_provider import AIRequest, AIResponse, AIStreamChunk, TokenUsage, estimate_request_usage
from app.services.ai.provider_registry import ProviderRegistry
from app.services.ai_interaction_logger import AIInteractionLogger

logger = logging.getLogger(__name__)
settings = get_settings()


class AIService:
    def __init__(self, registry: ProviderRegistry | None = None) -> None:
        self.registry = registry or ProviderRegistry()

    async def complete(self, request: AIRequest) -> AIResponse:
        self._validate_request(request)
        errors: list[str] = []

        for provider_name in self.registry.provider_order(request.provider):
            provider = self.registry.get(provider_name)
            if not provider:
                continue
            provider_request = replace(request, model=request.model or provider.default_model)
            for attempt in range(1, settings.llm_max_retries + 1):
                start = time.perf_counter()
                try:
                    async with AIInteractionLogger.track(
                        interaction_type=request.metadata.get("interaction_type", "chat"),
                        user_id=request.metadata.get("user_id"),
                        conversation_id=request.metadata.get("conversation_id"),
                        provider=provider.name,
                        model=provider_request.model,
                    ) as ctx:
                        response = await asyncio.wait_for(
                            provider.complete(provider_request),
                            timeout=request.timeout_seconds or settings.llm_timeout_seconds,
                        )
                        response.content = validate_ai_response(response.content)
                        ctx["prompt_tokens"] = response.usage.prompt_tokens
                        ctx["completion_tokens"] = response.usage.completion_tokens
                        monitor.record(
                            "ai.complete",
                            int((time.perf_counter() - start) * 1000),
                            "success",
                            provider=provider.name,
                            model=provider_request.model,
                        )
                        if provider_name != self.registry.provider_order(request.provider)[0]:
                            logger.info(
                                "AI fallback provider succeeded",
                                extra={"provider": provider.name, "fallback_provider": provider.name},
                            )
                        return response
                except Exception as exc:
                    monitor.record(
                        "ai.complete",
                        int((time.perf_counter() - start) * 1000),
                        "error",
                        provider=provider_name,
                        retry_attempt=attempt,
                    )
                    logger.warning(
                        "AI provider failed",
                        extra={"provider": provider_name, "retry_attempt": attempt, "error_code": self._failure_code(exc)},
                    )
                    errors.append(f"{provider_name}: {self._failure_code(exc)}")
                    if attempt < settings.llm_max_retries and self._is_retryable(exc):
                        await asyncio.sleep(min(2 ** (attempt - 1) * 0.4, 2.5))
                        continue
                    break

        raise AIProviderError("; ".join(errors) or "No AI provider available")

    async def stream(self, request: AIRequest) -> AsyncIterator[AIStreamChunk]:
        self._validate_request(request)
        errors: list[str] = []

        for provider_name in self.registry.provider_order(request.provider):
            provider = self.registry.get(provider_name)
            if not provider:
                continue
            provider_request = replace(request, model=request.model or provider.default_model)
            emitted = False
            usage = TokenUsage()
            try:
                start = time.perf_counter()
                async with AIInteractionLogger.track(
                    interaction_type=request.metadata.get("interaction_type", "chat_stream"),
                    user_id=request.metadata.get("user_id"),
                    conversation_id=request.metadata.get("conversation_id"),
                    provider=provider.name,
                    model=provider_request.model,
                ) as ctx:
                    stream = provider.stream(provider_request)
                    first = await asyncio.wait_for(
                        anext(stream),
                        timeout=request.timeout_seconds or settings.llm_stream_start_timeout_seconds,
                    )
                    monitor.record(
                        "ai.stream_start",
                        int((time.perf_counter() - start) * 1000),
                        "success",
                        provider=provider.name,
                        model=provider_request.model,
                    )
                    for chunk in [first]:
                        if chunk.event == "token":
                            emitted = True
                        if chunk.usage:
                            usage = chunk.usage
                        yield chunk
                    async for chunk in stream:
                        if chunk.event == "token":
                            emitted = True
                        if chunk.usage:
                            usage = chunk.usage
                        yield chunk
                    if not usage.total_tokens:
                        usage = estimate_request_usage(request.messages)
                    ctx["prompt_tokens"] = usage.prompt_tokens
                    ctx["completion_tokens"] = usage.completion_tokens
                return
            except asyncio.CancelledError:
                logger.info("AI stream cancelled", extra={"provider": provider_name})
                raise
            except Exception as exc:
                monitor.record("ai.stream", 0, "error", provider=provider_name, error_code=self._failure_code(exc))
                logger.warning(
                    "AI stream provider failed",
                    extra={"provider": provider_name, "error_code": self._failure_code(exc)},
                )
                errors.append(f"{provider_name}: {self._failure_code(exc)}")
                if emitted:
                    raise AIProviderError("Streaming interrupted after response started") from exc

        raise AIProviderError("; ".join(errors) or "No AI provider available")

    @staticmethod
    def _validate_request(request: AIRequest) -> None:
        if not request.messages:
            raise AIProviderError("AI request requires at least one message")
        for message in request.messages:
            if message.role not in ("system", "user", "assistant"):
                raise AIProviderError(f"Unsupported AI message role: {message.role}")
            if not message.content.strip():
                raise AIProviderError("AI request contains an empty message")
        if request.max_tokens < 1 or request.max_tokens > 8000:
            raise AIProviderError("AI request max_tokens is out of range")
        if request.temperature < 0 or request.temperature > 2:
            raise AIProviderError("AI request temperature is out of range")

    @staticmethod
    def _failure_code(exc: Exception) -> str:
        name = exc.__class__.__name__.lower()
        text = str(exc).lower()
        if isinstance(exc, asyncio.TimeoutError) or "timeout" in text:
            return "timeout"
        if "rate" in text or "429" in text:
            return "rate_limit"
        if "auth" in text or "401" in text or "403" in text:
            return "provider_auth"
        if "connection" in text or "network" in text:
            return "network"
        return name or "provider_error"

    @classmethod
    def _is_retryable(cls, exc: Exception) -> bool:
        return cls._failure_code(exc) in {"timeout", "rate_limit", "network", "runtimeerror"}
