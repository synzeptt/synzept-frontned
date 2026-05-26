"""Persist AI provider calls for debugging and cost tracking."""

import asyncio
import logging
import time
from contextlib import asynccontextmanager
from collections.abc import AsyncIterator
from uuid import UUID

from app.database.session import SessionLocal
from app.infrastructure.tracing import get_request_id
from app.models.ai_interaction import AIInteraction

logger = logging.getLogger(__name__)


class AIInteractionLogger:
    @staticmethod
    @asynccontextmanager
    async def track(
        *,
        interaction_type: str,
        user_id: UUID | None = None,
        conversation_id: UUID | None = None,
        message_id: UUID | None = None,
        provider: str | None = None,
        model: str | None = None,
    ) -> AsyncIterator[dict]:
        """Context manager that records latency and outcome."""
        start = time.perf_counter()
        ctx: dict = {"prompt_tokens": None, "completion_tokens": None}
        status = "success"
        error_message: str | None = None
        try:
            yield ctx
        except Exception as exc:
            status = "error"
            error_message = str(exc)[:500]
            raise
        finally:
            latency_ms = int((time.perf_counter() - start) * 1000)
            asyncio.create_task(
                _persist(
                    interaction_type=interaction_type,
                    user_id=user_id,
                    conversation_id=conversation_id,
                    message_id=message_id,
                    provider=provider,
                    model=model,
                    prompt_tokens=ctx.get("prompt_tokens"),
                    completion_tokens=ctx.get("completion_tokens"),
                    latency_ms=latency_ms,
                    status=status,
                    error_message=error_message,
                )
            )


async def _persist(**fields) -> None:
    async with SessionLocal() as session:
        try:
            session.add(
                AIInteraction(
                    user_id=fields.get("user_id"),
                    conversation_id=fields.get("conversation_id"),
                    message_id=fields.get("message_id"),
                    interaction_type=fields["interaction_type"],
                    provider=fields.get("provider"),
                    model=fields.get("model"),
                    prompt_tokens=fields.get("prompt_tokens"),
                    completion_tokens=fields.get("completion_tokens"),
                    latency_ms=fields.get("latency_ms"),
                    status=fields.get("status", "success"),
                    error_message=fields.get("error_message"),
                    request_id=get_request_id(),
                    metadata_=fields.get("metadata") or {},
                )
            )
            await session.commit()
        except Exception:
            await session.rollback()
            logger.exception("Failed to persist AI interaction log")
