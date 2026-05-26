"""Shared async job execution (used by Dramatiq actors and asyncio fallback)."""

import logging
from uuid import UUID

from app.database.session import SessionLocal
from app.infrastructure.jobs import JobType
logger = logging.getLogger(__name__)


async def execute_job(job_type: JobType, payload: dict) -> None:
    if job_type == JobType.MEMORY_POST_RESPONSE:
        await _memory_post_response(payload)
    elif job_type == JobType.DAILY_SUMMARY:
        await _daily_summary(payload)
    elif job_type == JobType.CONVERSATION_SUMMARIZE:
        await _conversation_summarize(payload)
    elif job_type == JobType.MEMORY_CONSOLIDATION:
        await _memory_consolidation(payload)
    else:
        logger.warning("Unknown job type: %s", job_type)


async def _memory_post_response(payload: dict) -> None:
    async with SessionLocal() as session:
        try:
            from app.memory.embedding_service import EmbeddingGenerationService
            from app.memory.extraction_service import ConversationTurn
            from app.memory.memory_service import MemoryService

            try:
                embeddings = EmbeddingGenerationService()
            except ValueError:
                embeddings = None

            service = MemoryService(session, embeddings=embeddings)
            await service.process_conversation(
                user_id=UUID(payload["user_id"]),
                turns=[
                    ConversationTurn(role="user", content=payload["user_message"]),
                    ConversationTurn(role="assistant", content=payload["assistant_reply"]),
                ],
                conversation_id=UUID(payload["conversation_id"]),
                project_id=UUID(payload["project_id"]) if payload.get("project_id") else None,
            )
            await session.commit()
        except Exception:
            await session.rollback()
            raise


async def _daily_summary(payload: dict) -> None:
    from app.daily.constants import KIND_EVENING, KIND_MORNING
    from app.daily.operating import DailyOperatingService
    from app.models.user import User

    async with SessionLocal() as session:
        try:
            user = await session.get(User, UUID(payload["user_id"]))
            if not user:
                return
            svc = DailyOperatingService(session)
            kind = payload.get("kind", KIND_MORNING)
            if kind == KIND_EVENING:
                await svc.generate_evening(user)
            else:
                await svc.generate_morning(user)
            await session.commit()
        except Exception:
            await session.rollback()
            raise


async def _memory_consolidation(payload: dict) -> None:
    from app.daily.consolidation import MemoryConsolidation

    async with SessionLocal() as session:
        try:
            await MemoryConsolidation(session).run(UUID(payload["user_id"]))
            await session.commit()
        except Exception:
            await session.rollback()
            raise


async def _conversation_summarize(payload: dict) -> None:
    from app.memory.engine import MemoryEngine

    async with SessionLocal() as session:
        try:
            engine = MemoryEngine(session)
            await engine.summarize_conversation_if_needed(UUID(payload["conversation_id"]))
            await session.commit()
        except Exception:
            await session.rollback()
            raise
