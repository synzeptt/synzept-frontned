"""Dramatiq task actors — run when REDIS_URL is configured."""

import asyncio
import logging

import dramatiq

from app.infrastructure.jobs import JobType
import app.workers.broker  # noqa: F401 — configures Dramatiq broker when Redis is set
from app.workers.runner import execute_job

logger = logging.getLogger(__name__)


def dispatch(job_name: str, payload: dict) -> None:
    """Route job name to the appropriate actor."""
    actors = {
        JobType.MEMORY_POST_RESPONSE.value: process_memory_post_response,
        JobType.DAILY_SUMMARY.value: generate_daily_summary,
        JobType.CONVERSATION_SUMMARIZE.value: summarize_conversation,
        JobType.MEMORY_CONSOLIDATION.value: consolidate_memories,
    }
    actor = actors.get(job_name)
    if actor:
        actor.send(payload)
    else:
        logger.warning("No dramatiq actor for job: %s", job_name)


@dramatiq.actor(max_retries=3, time_limit=120_000)
def process_memory_post_response(payload: dict) -> None:
    asyncio.run(execute_job(JobType.MEMORY_POST_RESPONSE, payload))


@dramatiq.actor(max_retries=3, time_limit=180_000)
def generate_daily_summary(payload: dict) -> None:
    asyncio.run(execute_job(JobType.DAILY_SUMMARY, payload))


@dramatiq.actor(max_retries=3, time_limit=120_000)
def summarize_conversation(payload: dict) -> None:
    asyncio.run(execute_job(JobType.CONVERSATION_SUMMARIZE, payload))


@dramatiq.actor(max_retries=2, time_limit=180_000)
def consolidate_memories(payload: dict) -> None:
    asyncio.run(execute_job(JobType.MEMORY_CONSOLIDATION, payload))
