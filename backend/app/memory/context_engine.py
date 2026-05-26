"""
Context Engine — assembles optimized context before every AI response.

Pipeline:
1. Analyze intent
2. Identify active project
3. Retrieve ranked memories
4. Load project memory
5. Trim short-term history
6. Select semantic snippets
7. Build ContextPayload
"""

import asyncio
import logging
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.memory.constants import MAX_SEMANTIC_HITS
from app.memory.pipeline import MemoryRetrievalPipeline
from app.memory.project_memory import ProjectMemory
from app.memory.short_term import ShortTermMemory
from app.memory.types import ContextPayload
from app.memory.validation import filter_scored_memories, filter_semantic_hits

try:
    from app.orchestrator.types import ClassifiedIntent
except ImportError:
    ClassifiedIntent = None  # type: ignore
from app.models.task import Task
from app.models.user import User
from app.daily.context import DailyContextService
from app.services.user_profile_service import UserProfileService
from app.core.reliability import timed_operation
from app.utils.text import truncate

logger = logging.getLogger(__name__)


class ContextEngine:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session
        self.pipeline = MemoryRetrievalPipeline(session)
        self.short_term = ShortTermMemory(session)
        self.project_memory = ProjectMemory(session)

    async def build(
        self,
        *,
        user_id: UUID,
        query: str,
        conversation_id: UUID,
        project_id: UUID | None = None,
        classified_intent: "ClassifiedIntent | None" = None,
    ) -> ContextPayload:
        with timed_operation("context_build"):
            return await self._build_inner(
                user_id=user_id,
                query=query,
                conversation_id=conversation_id,
                project_id=project_id,
                classified_intent=classified_intent,
            )

    async def _build_inner(
        self,
        *,
        user_id: UUID,
        query: str,
        conversation_id: UUID,
        project_id: UUID | None = None,
        classified_intent: "ClassifiedIntent | None" = None,
    ) -> ContextPayload:
        if classified_intent is not None:
            from app.memory.scoring import score_memory

            active_project = classified_intent.active_project_id or project_id
            semantic = self.pipeline.semantic
            semantic_hits = filter_semantic_hits(
                await semantic.search(user_id, query, limit=classified_intent.retrieval.semantic_limit),
                query=query,
                limit=classified_intent.retrieval.semantic_limit,
            )
            mem_project = active_project if classified_intent.retrieval.include_project else None
            memories = await self.pipeline.store.list_long_term(
                user_id, project_id=mem_project, limit=100
            )
            semantic_map = semantic.build_semantic_score_map(semantic_hits, [m.id for m in memories])
            scored = [
                score_memory(
                    m,
                    query,
                    semantic_score=semantic_map.get(str(m.id), 0.0),
                    project_id=str(active_project) if active_project else None,
                )
                for m in memories
            ]
            scored_memories, diagnostics = filter_scored_memories(
                scored,
                query=query,
                limit=classified_intent.retrieval.memory_limit,
            )
            await self.pipeline.store.touch_accessed([s.memory for s in scored_memories])
            logger.info(
                "context retrieval diagnostics",
                extra={
                    "hit_count": len(semantic_hits),
                    "selected": diagnostics.selected,
                    "filtered_low_score": diagnostics.filtered_low_score,
                    "filtered_untrusted": diagnostics.filtered_untrusted,
                },
            )
            intent = classified_intent.legacy_intent
        else:
            intent, scored_memories, semantic_hits = await self.pipeline.run(
                user_id, query, project_id=project_id
            )

        active_project_id = intent.active_project_id or project_id

        gather_tasks = [
            self.short_term.get_context(conversation_id, exclude_last_user=True),
            self._get_conversation(conversation_id),
            self.session.get(User, user_id),
            self._tasks_snapshot(user_id, active_project_id),
        ]
        if active_project_id:
            gather_tasks.append(self._load_project_context(user_id, active_project_id, query))

        results = await asyncio.gather(*gather_tasks)
        stm_result, conv, user, tasks_snapshot = results[:4]
        project_ctx = results[4] if active_project_id else None
        stm_messages, active_intent, trimmed = stm_result
        conversation_summary = conv.summary if conv else ""
        user_profile = await UserProfileService(self.session).get_or_create(user_id)
        profile = UserProfileService(self.session).format_for_context(user_profile, user)

        semantic_snippets = self._select_semantic_snippets(semantic_hits, scored_memories)
        long_term = [f"[{s.memory.category}] {s.memory.content}" for s in scored_memories]
        daily_context = await DailyContextService(self.session).get_for_prompt(user_id)

        return ContextPayload(
            intent=intent,
            user_profile=profile,
            conversation_summary=conversation_summary or "",
            active_intent=active_intent,
            short_term_messages=stm_messages,
            long_term_memories=long_term,
            project_context=project_ctx,
            semantic_snippets=semantic_snippets,
            tasks_snapshot=tasks_snapshot,
            daily_context=daily_context,
            trimmed_message_count=trimmed,
        )

    async def _get_conversation(self, conversation_id: UUID):
        from app.models.conversation import Conversation

        return await self.session.get(Conversation, conversation_id)

    async def _load_project_context(self, user_id: UUID, project_id: UUID, query: str):
        project_ctx = await self.project_memory.load(user_id, project_id)
        if not project_ctx:
            return None
        conv_summaries, semantic_extras = await asyncio.gather(
            self.project_memory.get_recent_conversation_summaries(project_id),
            self.project_memory.enrich_from_semantic(user_id, project_id, query),
        )
        if conv_summaries:
            project_ctx.summary = truncate(
                project_ctx.summary + "\nRecent threads:\n" + "\n".join(f"- {s}" for s in conv_summaries),
                1000,
            )
        if semantic_extras:
            project_ctx.notes = (semantic_extras + project_ctx.notes)[:8]
        return project_ctx

    async def _tasks_snapshot(self, user_id: UUID, project_id: UUID | None) -> str:
        query = select(Task).where(Task.user_id == user_id, Task.deleted_at.is_(None), Task.status != "done")
        if project_id:
            query = query.where(Task.project_id == project_id)
        result = await self.session.execute(query.order_by(Task.priority.desc()).limit(6))
        tasks = list(result.scalars().all())
        if not tasks:
            return ""
        return "\n".join(f"- [{t.priority}] {t.title}" for t in tasks)

    @staticmethod
    def _select_semantic_snippets(semantic_hits, scored_memories) -> list[str]:
        memory_contents = {s.memory.content for s in scored_memories}
        snippets: list[str] = []
        for hit in semantic_hits[:MAX_SEMANTIC_HITS]:
            if hit.content in memory_contents:
                continue
            snippets.append(f"[{hit.source_type}] {truncate(hit.content, 300)}")
        return snippets
