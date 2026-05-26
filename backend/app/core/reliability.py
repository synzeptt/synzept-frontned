"""Production-readiness helpers for safe UX and diagnostics."""

import logging
import re
import time
from contextlib import contextmanager
from dataclasses import dataclass
from typing import Iterator

from app.infrastructure.monitoring import monitor

logger = logging.getLogger("synzept.reliability")

SAFE_ERROR_MESSAGES = {
    "ai_provider_error": "Synzept had trouble reaching the AI service. Your message is saved and you can retry.",
    "timeout": "Synzept took longer than expected. Your message is saved and you can retry.",
    "retrieval_error": "Synzept could not load every piece of context, so it answered with the context it could trust.",
    "unauthorized": "Please sign in again to continue.",
    "invalid_credentials": "Invalid email or password.",
    "forbidden": "You do not have access to that workspace item.",
    "not_found": "That item could not be found or is no longer available.",
    "app_error": "Synzept could not complete that action. Please try again.",
    "rate_limit": "Synzept is receiving too many requests. Please wait a moment and try again.",
    "internal_error": "Something went wrong, but your workspace is still safe. Please try again.",
    "database_error": "Synzept could not reach the workspace database. Please try again in a moment.",
    "invalid_request": "That request was not valid. Please check the details and try again.",
    "stream_interrupted": "The response stream was interrupted. You can retry or continue from here.",
}

PROMPT_INJECTION_PATTERNS = (
    re.compile(r"\bignore (all )?(previous|prior|above) (instructions|rules)\b", re.I),
    re.compile(r"\breveal (the )?(system|developer) (prompt|message|instructions)\b", re.I),
    re.compile(r"\byou are now\b", re.I),
    re.compile(r"\bdisregard (the )?(rules|instructions)\b", re.I),
)


@dataclass(frozen=True)
class OperationMetric:
    name: str
    duration_ms: int
    status: str


def safe_error_message(code: str | None) -> str:
    return SAFE_ERROR_MESSAGES.get(code or "internal_error", SAFE_ERROR_MESSAGES["internal_error"])


def sanitize_user_input(text: str, max_chars: int = 16000) -> str:
    """Normalize user-provided text while preserving meaning."""
    cleaned = text.replace("\x00", "").strip()
    cleaned = re.sub(r"[\u202a-\u202e\u2066-\u2069]", "", cleaned)
    return cleaned[:max_chars]


def sanitize_log_value(value, max_chars: int = 500):
    if isinstance(value, str):
        cleaned = re.sub(r"(sk-[A-Za-z0-9_\-]+|Bearer\s+[A-Za-z0-9._\-]+)", "[redacted]", value)
        return cleaned[:max_chars]
    if isinstance(value, dict):
        return {k: sanitize_log_value(v, max_chars=max_chars) for k, v in value.items() if "secret" not in k.lower() and "key" not in k.lower()}
    if isinstance(value, list):
        return [sanitize_log_value(item, max_chars=max_chars) for item in value[:20]]
    return value


def has_prompt_injection_signal(text: str) -> bool:
    return any(pattern.search(text) for pattern in PROMPT_INJECTION_PATTERNS)


def validate_ai_response(text: str) -> str:
    """Guard against empty, malformed, or obviously degraded model output."""
    cleaned = text.replace("\x00", "").strip()
    if not cleaned:
        return "I could not produce a reliable answer that time. Your message is saved, so please retry."

    words = cleaned.split()
    if len(words) > 24:
        window = words[:12]
        repeated = sum(1 for i in range(12, min(len(words), 60), 12) if words[i : i + 12] == window)
        if repeated >= 2:
            return "I started repeating myself, so I stopped that response. Please retry and I will answer cleanly."

    return cleaned[:12000]


@contextmanager
def timed_operation(name: str, **extra) -> Iterator[None]:
    start = time.perf_counter()
    status = "success"
    try:
        yield
    except Exception:
        status = "error"
        raise
    finally:
        duration_ms = int((time.perf_counter() - start) * 1000)
        monitor.record(name, duration_ms, status, **extra)
        logger.info(
            "operation completed",
            extra={"operation": name, "duration_ms": duration_ms, "status": status, **extra},
        )
