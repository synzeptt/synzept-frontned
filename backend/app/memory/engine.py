"""
Memory Engine — coordinates all 4 memory layers and post-conversation updates.
"""

import logging
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.memory.long_term import LongTermMemory
from app.memory.project_memory import ProjectMemory
from app.memory.short_term import ShortTermMemory
from app.memory.retrieve import MemoryRetriever
from app.memory.store import MemoryStore
from app.memory.summarize import MemorySummarizer
from app.memory.user_context import UserContextGraph
from app.services.chat_service import ChatService
from app.services.embedding_service import EmbeddingService
from app.services.providers.router import LLMRouter

logger = logging.getLogger(__name__)


class MemoryEngine:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session
        embeddings = None
        try:
            embeddings = EmbeddingService()
        except ValueError:
            pass
        self.store = MemoryStore(session, embeddings)
        self.retrieve = MemoryRetriever(session, embeddings)
        self.user_context = UserContextGraph(session)
        self.short_term = ShortTermMemory(session)
        self.long_term = LongTermMemory(session, embeddings)
        self.project_memory = ProjectMemory(session)
        self.summarizer = MemorySummarizer(LLMRouter())
        self.chat = ChatService(session)

    async def process_exchange(
        self,
        *,
        user_id: UUID,
        conversation_id: UUID,
        user_message: str,
        assistant_reply: str,
        project_id: UUID | None,
    ) -> None:
        """Post-conversation: extract long-term memory, update intent, summarize if needed."""
        # Update active session intent (short-term layer)
        intent_snippet = user_message[:200] if len(user_message) > 20 else ""
        if intent_snippet:
            await self.short_term.update_active_intent(conversation_id, intent_snippet)

        # Long-term extraction (meaningful only — dedup inside)
        memory = await self.long_term.process_exchange(
            user_id=user_id,
            user_message=user_message,
            assistant_reply=assistant_reply,
            conversation_id=conversation_id,
            project_id=project_id,
        )

        if memory and project_id:
            await self.project_memory.update_summary(user_id, project_id, memory.content)

        if memory:
            await self.user_context.refresh(user_id)

        await self._maybe_summarize_conversation(conversation_id)
        if project_id:
            await self._maybe_summarize_project(user_id, project_id)

    async def summarize_conversation_if_needed(self, conversation_id: UUID) -> None:
        await self._maybe_summarize_conversation(conversation_id)

    async def _maybe_summarize_conversation(self, conversation_id: UUID) -> None:
        messages = await self.chat.get_messages(conversation_id)
        if len(messages) < 10:
            return
        recent = [{"role": m.role, "content": m.content} for m in messages]
        summary = await self.summarizer.summarize_conversation(recent)
        if summary:
            await self.chat.update_summary(conversation_id, summary)
        if len(messages) > 24:
            compact = await self.summarizer.compact_old_messages(recent)
            if compact:
                from app.models.conversation import Conversation

                conv = await self.session.get(Conversation, conversation_id)
                if conv and conv.summary:
                    await self.chat.update_summary(conversation_id, f"{conv.summary}\n{compact}")

    async def _maybe_summarize_project(self, user_id: UUID, project_id: UUID) -> None:
        from app.models.project import Project

        project = await self.session.get(Project, project_id)
        if not project:
            return
        ctx = await self.project_memory.load(user_id, project_id)
        if not ctx:
            return
        summary = await self.summarizer.summarize_project(
            project.name, ctx.notes, ctx.tasks, ctx.decisions
        )
        if summary:
            project.context_summary = summary
