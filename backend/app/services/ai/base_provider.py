from abc import ABC, abstractmethod
from collections.abc import AsyncIterator
from dataclasses import dataclass, field
from typing import Any, Literal


ProviderName = Literal["gemini", "openai", "anthropic"]
MessageRole = Literal["system", "user", "assistant"]
StreamEvent = Literal["meta", "token", "usage", "done", "error"]


@dataclass(slots=True)
class AIMessage:
    role: MessageRole
    content: str


@dataclass(slots=True)
class TokenUsage:
    prompt_tokens: int = 0
    completion_tokens: int = 0
    total_tokens: int = 0
    estimated: bool = False

    def normalized(self) -> "TokenUsage":
        if not self.total_tokens:
            self.total_tokens = self.prompt_tokens + self.completion_tokens
        return self

    def to_dict(self) -> dict[str, Any]:
        self.normalized()
        return {
            "prompt_tokens": self.prompt_tokens,
            "completion_tokens": self.completion_tokens,
            "total_tokens": self.total_tokens,
            "estimated": self.estimated,
        }


@dataclass(slots=True)
class ProviderMetadata:
    provider: str
    model: str
    request_id: str | None = None
    finish_reason: str | None = None
    raw: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "provider": self.provider,
            "model": self.model,
            "request_id": self.request_id,
            "finish_reason": self.finish_reason,
            "raw": self.raw,
        }


@dataclass(slots=True)
class AIRequest:
    messages: list[AIMessage]
    provider: str | None = None
    model: str | None = None
    temperature: float = 0.3
    max_tokens: int = 1200
    timeout_seconds: float | None = None
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(slots=True)
class AIResponse:
    content: str
    usage: TokenUsage
    metadata: ProviderMetadata

    def to_dict(self) -> dict[str, Any]:
        return {
            "content": self.content,
            "usage": self.usage.to_dict(),
            "metadata": self.metadata.to_dict(),
        }


@dataclass(slots=True)
class AIStreamChunk:
    event: StreamEvent
    content: str = ""
    usage: TokenUsage | None = None
    metadata: ProviderMetadata | None = None
    error: dict[str, Any] | None = None

    def to_sse_data(self) -> dict[str, Any]:
        data: dict[str, Any] = {}
        if self.content:
            data["content"] = self.content
        if self.usage:
            data["usage"] = self.usage.to_dict()
        if self.metadata:
            data["metadata"] = self.metadata.to_dict()
            data["provider"] = self.metadata.provider
            data["model"] = self.metadata.model
        if self.error:
            data["error"] = self.error
            data["message"] = self.error.get("message")
        return data


class BaseAIProvider(ABC):
    name: str

    @property
    @abstractmethod
    def default_model(self) -> str:
        raise NotImplementedError

    @abstractmethod
    async def complete(self, request: AIRequest) -> AIResponse:
        raise NotImplementedError

    @abstractmethod
    async def stream(self, request: AIRequest) -> AsyncIterator[AIStreamChunk]:
        raise NotImplementedError


def estimate_tokens(text: str) -> int:
    if not text:
        return 0
    return max(1, len(text) // 4)


def estimate_request_usage(messages: list[AIMessage], completion: str = "") -> TokenUsage:
    prompt = sum(estimate_tokens(message.content) for message in messages)
    output = estimate_tokens(completion)
    return TokenUsage(prompt_tokens=prompt, completion_tokens=output, estimated=True).normalized()
