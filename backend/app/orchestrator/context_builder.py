"""Coordinates recent history, memory, profile, project, and task context."""

from __future__ import annotations

from dataclasses import dataclass, field
import logging
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.conversation import Conversation
from app.models.message import Message
from app.models.project import Project
from app.models.task import Task
from app.models.user import User
from app.orchestrator.conversation_intelligence import ConversationIntelligenceService
from app.orchestrator.intent_service import OrchestrationIntent, OrchestrationIntentCategory
from app.tasks.service import OPEN_STATUSES
from app.orchestrator.project_context_service import ProjectContextBundle, ProjectContextService
from app.retrieval.retrieval_service import RetrievalFilters, SemanticRetrievalService
from app.utils.text import truncate
from app.infrastructure.monitoring import monitor

logger = logging.getLogger(__name__)


@dataclass(slots=True)
class ContextBundle:
    user_profile: str = ""
    conversation_summary: str = ""
    recent_messages: list[dict[str, str]] = field(default_factory=list)
    memories: list[str] = field(default_factory=list)
    continuation_context: list[str] = field(default_factory=list)
    conversation_intelligence: list[str] = field(default_factory=list)
    personalization: list[str] = field(default_factory=list)
    project: ProjectContextBundle = field(default_factory=ProjectContextBundle)


class ContextBuilder:
    def __init__(
        self,
        session: AsyncSession,
        *,
        retrieval: SemanticRetrievalService | None = None,
        projects: ProjectContextService | None = None,
    ) -> None:
        self.session = session
        self.retrieval = retrieval or SemanticRetrievalService(session)
        self.projects = projects or ProjectContextService(session)
        self.conversation_intel = ConversationIntelligenceService(session)

    async def build(
        self,
        *,
        user_id: UUID,
        message: str,
        conversation: Conversation,
        intent: OrchestrationIntent,
        project_id: UUID | None,
    ) -> ContextBundle:
        user = await self.session.get(User, user_id)
        preferences = user.preferences or {} if user else {}
        memory_enabled = preferences.get("memory_enabled", True) and preferences.get("personalization_enabled", True)
        project_context = await self.projects.get_context(
            user_id=user_id,
            project_id=project_id,
            include_tasks=intent.strategy.include_tasks,
        )
        filters = RetrievalFilters(
            project_id=project_id,
            limit=intent.strategy.memory_limit,
            min_score=0.32,
        )
        ranked = []
        if memory_enabled:
            try:
                with monitor.timed("retrieval.context", project_id=str(project_id) if project_id else None):
                    ranked = await self.retrieval.retrieve(user_id=user_id, query=message, filters=filters)
            except Exception as exc:
                logger.warning(
                    "semantic retrieval failed; using lexical fallback",
                    extra={"operation": "retrieval", "error_code": exc.__class__.__name__},
                )
                with monitor.timed("retrieval.lexical_fallback", project_id=str(project_id) if project_id else None):
                    ranked = await self.retrieval.lexical_fallback(user_id=user_id, query=message, filters=filters)
        return ContextBundle(
            user_profile=await self._user_profile(user_id),
            conversation_summary=conversation.summary or "",
            recent_messages=await self._recent_messages(conversation.id, limit=intent.strategy.recent_message_limit),
            memories=[
                truncate(f"[{item.memory.memory_type}] {item.memory.summary or item.memory.content}", 320)
                for item in ranked
            ],
            continuation_context=await self._continuation_context(
                user_id=user_id,
                intent=intent,
                project_id=active_project_id(project_id, conversation.project_id),
            ),
            conversation_intelligence=await self.conversation_intel.related_context(
                user_id=user_id,
                query=message,
                current_conversation_id=conversation.id,
                project_id=active_project_id(project_id, conversation.project_id),
                limit=6,
            ),
            personalization=self._personalization_cues(user, ranked),
            project=project_context,
        )

    async def _user_profile(self, user_id: UUID) -> str:
        user = await self.session.get(User, user_id)
        if not user:
            return ""
        preferences = user.preferences or {}
        if preferences.get("personalization_enabled", True) is False:
            return ""
        return truncate(user.profile_summary or "", 700)

    async def _recent_messages(self, conversation_id: UUID, *, limit: int) -> list[dict[str, str]]:
        result = await self.session.execute(
            select(Message)
            .where(Message.conversation_id == conversation_id)
            .order_by(Message.created_at.desc())
            .limit(limit)
        )
        messages = list(result.scalars().all())
        messages.reverse()
        return [{"role": message.role, "content": truncate(message.content, 1200)} for message in messages]

    @staticmethod
    def _personalization_cues(user: User | None, ranked) -> list[str]:
        cues: list[str] = []
        preferences = user.preferences or {} if user else {}
        style = preferences.get("communication_style") or preferences.get("response_depth")
        if style:
            cues.append(f"Communication preference: {style}.")
        for item in ranked:
            memory = item.memory
            if memory.memory_type in {"preferences", "routines"}:
                cues.append(truncate(memory.summary or memory.content, 180))
            if len(cues) >= 4:
                break
        return cues

    async def _continuation_context(
        self,
        *,
        user_id: UUID,
        intent: OrchestrationIntent,
        project_id: UUID | None,
    ) -> list[str]:
        if intent.category not in {
            OrchestrationIntentCategory.PROJECT_CONTINUATION,
            OrchestrationIntentCategory.PLANNING,
            OrchestrationIntentCategory.ORGANIZATION,
            OrchestrationIntentCategory.TASK_ASSISTANCE,
        }:
            return []

        clauses = [Conversation.user_id == user_id, Conversation.deleted_at.is_(None), Conversation.archived_at.is_(None)]
        if project_id:
            clauses.append(Conversation.project_id == project_id)
        conversation_result = await self.session.execute(
            select(Conversation).where(*clauses).order_by(Conversation.updated_at.desc()).limit(3)
        )

        task_clauses = [Task.user_id == user_id, Task.deleted_at.is_(None), Task.status.in_(OPEN_STATUSES)]
        if project_id:
            task_clauses.append(Task.project_id == project_id)
        task_result = await self.session.execute(
            select(Task).where(*task_clauses).order_by(Task.updated_at.desc()).limit(5)
        )

        project_result = None
        if project_id:
            project_result = await self.session.execute(
                select(Project).where(Project.id == project_id, Project.user_id == user_id, Project.deleted_at.is_(None)).limit(1)
            )

        lines: list[str] = []
        if project_result:
            project = project_result.scalar_one_or_none()
            if project:
                detail = truncate(project.context_summary or project.description or "", 260)
                lines.append(f"Active project to restore: {project.name}. {detail}".strip())

        for conversation in conversation_result.scalars().all():
            detail = truncate(conversation.summary or conversation.active_intent or "", 260)
            if detail:
                lines.append(f"Recent discussion: {conversation.title or 'Untitled conversation'} - {detail}")

        for task in task_result.scalars().all():
            descriptor = f"{task.status.replace('_', ' ')}, {task.priority} priority"
            if task.description:
                descriptor += f": {truncate(task.description, 160)}"
            lines.append(f"Unfinished task: {task.title} ({descriptor})")

        return lines[:8]


def active_project_id(explicit_project_id: UUID | None, conversation_project_id: UUID | None) -> UUID | None:
    return explicit_project_id or conversation_project_id
