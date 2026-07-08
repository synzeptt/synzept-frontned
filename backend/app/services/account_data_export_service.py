from datetime import datetime, timezone
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.conversation import Conversation
from app.models.daily_brief_phase8 import DailyBriefSnapshot
from app.models.goal import Goal
from app.models.memory import Memory
from app.models.message import Message
from app.models.note import Note
from app.models.project import Project
from app.models.task import Task
from app.models.user import User
from app.models.user_understanding import UserUnderstanding


class AccountDataExportService:
    """Portable user-owned data export. Authentication secrets are never included."""

    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def export(self, user: User) -> dict:
        understanding = await self._rows(UserUnderstanding, UserUnderstanding.user_id == user.id)
        memories = await self._rows(Memory, Memory.user_id == user.id, Memory.deleted_at.is_(None))
        projects = await self._rows(Project, Project.user_id == user.id, Project.deleted_at.is_(None))
        goals = await self._rows(Goal, Goal.user_id == user.id)
        tasks = await self._rows(Task, Task.user_id == user.id, Task.deleted_at.is_(None))
        notes = await self._rows(Note, Note.user_id == user.id, Note.deleted_at.is_(None))
        conversations = await self._rows(Conversation, Conversation.user_id == user.id, Conversation.deleted_at.is_(None))
        conversation_ids = [item.id for item in conversations]
        messages = await self._rows(Message, Message.conversation_id.in_(conversation_ids)) if conversation_ids else []
        briefs = await self._rows(DailyBriefSnapshot, DailyBriefSnapshot.user_id == user.id)
        return {
            "format": "synzept-s1-export-v1",
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "account": {
                "id": str(user.id), "email": user.email, "display_name": user.display_name,
                "profile_summary": user.profile_summary, "timezone": user.timezone,
                "preferences": user.preferences or {}, "onboarding_state": user.onboarding_state,
                "created_at": self._value(user.created_at),
            },
            "understanding": [self._simple(item, ("id", "category", "title", "value", "source", "confidence", "learned_at", "created_at", "updated_at")) for item in understanding],
            "memories": [self._simple(item, ("id", "memory_type", "category", "content", "summary", "confidence", "importance_score", "source", "project_id", "conversation_id", "created_at", "updated_at")) for item in memories],
            "projects": [self._simple(item, ("id", "name", "description", "status", "current_focus", "recommended_next_step", "created_at", "updated_at")) for item in projects],
            "goals": [self._simple(item, ("id", "title", "description", "status", "progress", "target_date", "project_id", "created_at", "updated_at")) for item in goals],
            "tasks": [self._simple(item, ("id", "title", "description", "status", "priority", "due_at", "project_id", "created_at", "updated_at")) for item in tasks],
            "notes": [self._simple(item, ("id", "title", "content", "summary", "project_id", "created_at", "updated_at")) for item in notes],
            "conversations": [self._simple(item, ("id", "title", "summary", "active_intent", "project_id", "created_at", "updated_at")) for item in conversations],
            "messages": [self._simple(item, ("id", "conversation_id", "role", "content", "created_at")) for item in messages],
            "daily_briefs": [self._simple(item, ("id", "brief_date", "what_matters_today", "open_loops", "recommended_next_step", "recent_progress", "created_at", "updated_at")) for item in briefs],
        }

    async def _rows(self, model, *clauses):
        result = await self.session.execute(select(model).where(*clauses))
        return list(result.scalars())

    def _simple(self, item, fields: tuple[str, ...]) -> dict:
        return {field: self._value(getattr(item, field, None)) for field in fields}

    @staticmethod
    def _value(value):
        if isinstance(value, UUID):
            return str(value)
        if hasattr(value, "isoformat"):
            return value.isoformat()
        return value
