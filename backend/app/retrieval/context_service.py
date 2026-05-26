"""Context assembly foundation for future orchestration."""

from __future__ import annotations

from dataclasses import dataclass, field
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.conversation import Conversation
from app.models.message import Message
from app.models.project import Project
from app.models.user import User
from app.retrieval.retrieval_service import RetrievalFilters, SemanticRetrievalService


@dataclass(slots=True)
class AssembledContext:
    memories: list[str] = field(default_factory=list)
    recent_messages: list[dict[str, str]] = field(default_factory=list)
    project_context: str = ""
    user_profile_context: str = ""
    conversation_summary: str = ""


class ContextAssemblyService:
    def __init__(self, session: AsyncSession, retrieval: SemanticRetrievalService | None = None) -> None:
        self.session = session
        self.retrieval = retrieval or SemanticRetrievalService(session)

    async def assemble(
        self,
        *,
        user_id: UUID,
        query: str,
        conversation_id: UUID,
        project_id: UUID | None = None,
        memory_limit: int = 6,
        recent_message_limit: int = 12,
    ) -> AssembledContext:
        ranked = await self.retrieval.retrieve(
            user_id=user_id,
            query=query,
            filters=RetrievalFilters(project_id=project_id, limit=memory_limit),
        )
        return AssembledContext(
            memories=[f"[{item.memory.memory_type}] {item.memory.summary or item.memory.content}" for item in ranked],
            recent_messages=await self._recent_messages(conversation_id, limit=recent_message_limit),
            project_context=await self._project_context(project_id) if project_id else "",
            user_profile_context=await self._user_profile(user_id),
            conversation_summary=await self._conversation_summary(conversation_id),
        )

    async def _recent_messages(self, conversation_id: UUID, *, limit: int) -> list[dict[str, str]]:
        result = await self.session.execute(
            select(Message).where(Message.conversation_id == conversation_id).order_by(Message.created_at.desc()).limit(limit)
        )
        messages = list(result.scalars().all())
        messages.reverse()
        return [{"role": message.role, "content": message.content} for message in messages]

    async def _project_context(self, project_id: UUID) -> str:
        project = await self.session.get(Project, project_id)
        if not project:
            return ""
        parts = [project.name]
        if project.description:
            parts.append(project.description)
        if project.context_summary:
            parts.append(project.context_summary)
        return "\n".join(parts)

    async def _user_profile(self, user_id: UUID) -> str:
        user = await self.session.get(User, user_id)
        if not user:
            return ""
        return user.profile_summary or ""

    async def _conversation_summary(self, conversation_id: UUID) -> str:
        conversation = await self.session.get(Conversation, conversation_id)
        return conversation.summary if conversation and conversation.summary else ""
