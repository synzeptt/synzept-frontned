"""Background job dispatch — Dramatiq when Redis is configured, asyncio otherwise."""

import asyncio
import logging
from enum import StrEnum
from typing import Any
from uuid import UUID

from app.core.config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()


class JobType(StrEnum):
    MEMORY_POST_RESPONSE = "memory_post_response"
    CONVERSATION_SUMMARIZE = "conversation_summarize"
    DAILY_SUMMARY = "daily_summary"
    EMBEDDING_GENERATE = "embedding_generate"
    MEMORY_CONSOLIDATION = "memory_consolidation"


def enqueue(job_type: JobType, **payload: Any) -> None:
    """
    Queue a background job without blocking the HTTP response.

    Uses Dramatiq + Redis when REDIS_URL is set; otherwise runs in-process asyncio.
    """
    if settings.redis_url:
        from app.workers import tasks as worker_tasks

        worker_tasks.dispatch(job_type.value, _serialize_payload(payload))
        logger.debug("Enqueued dramatiq job %s", job_type.value)
        return

    asyncio.create_task(_run_async(job_type, payload))
    logger.debug("Scheduled asyncio job %s", job_type.value)


def _serialize_payload(payload: dict[str, Any]) -> dict[str, Any]:
    out: dict[str, Any] = {}
    for key, value in payload.items():
        if isinstance(value, UUID):
            out[key] = str(value)
        else:
            out[key] = value
    return out


async def _run_async(job_type: JobType, payload: dict[str, Any]) -> None:
    from app.workers.runner import execute_job

    try:
        await execute_job(job_type, payload)
    except Exception:
        logger.exception("Background job failed: %s", job_type.value)
