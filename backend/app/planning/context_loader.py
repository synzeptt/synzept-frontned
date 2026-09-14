from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.conversation import Conversation
from app.models.memory import Memory
from app.models.note import Note
from app.models.user import User
from app.models.user_understanding import UserUnderstanding
from app.tasks.service import TaskService


class ContextLoader:
    """Loads compact, real workspace signals for planning without exposing the intelligence layer."""

    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def load(self, user_id: UUID, project_id: UUID | None = None) -> dict:
        tasks = await TaskService(self.session).list_tasks(user_id, project_id=project_id)
        note_count = await self._count(Note, Note.user_id == user_id, Note.deleted_at.is_(None))
        conversation_count = await self._count(Conversation, Conversation.user_id == user_id, Conversation.archived_at.is_(None))
        user = await self._get_user(user_id)
        preferences = user.preferences if user and isinstance(user.preferences, dict) else {}
        open_tasks = [task.title for task in tasks if task.status not in {"completed", "archived", "done"}]
        memories = await self._load_memories(user_id, project_id)
        learning_context = await self._load_learning_context(user_id)
        return {
            "active_task_count": len(open_tasks),
            "active_tasks": open_tasks[:8],
            "file_count": int(note_count or 0),
            "conversation_count": int(conversation_count or 0),
            "has_preferences": bool(preferences),
            "project_id": str(project_id) if project_id else None,
            "memory_context": {
                "memory_count": len(memories),
                "memories": memories,
                "summary": self._memory_summary(memories),
            },
            "learning_context": {
                "items": learning_context,
                "summary": self._learning_summary(learning_context),
            },
        }

    async def _load_memories(self, user_id: UUID, project_id: UUID | None = None) -> list[dict]:
        if not hasattr(self.session, "execute"):
            return []
        statement = (
            select(Memory)
            .where(Memory.user_id == user_id, Memory.deleted_at.is_(None))
            .order_by(Memory.updated_at.desc())
            .limit(8)
        )
        if project_id is not None:
            statement = statement.where(Memory.project_id == project_id)
        result = await self.session.execute(statement)
        memories = result.scalars().all()
        return [
            {
                "summary": memory.summary or memory.content[:240],
                "content": memory.content[:280],
                "type": memory.memory_type,
                "confidence": round(float(memory.confidence or 0.0), 2),
            }
            for memory in memories
        ]

    async def _load_learning_context(self, user_id: UUID) -> list[dict]:
        if not hasattr(self.session, "execute"):
            return []
        result = await self.session.execute(
            select(UserUnderstanding)
            .where(UserUnderstanding.user_id == user_id, UserUnderstanding.source == "learned")
            .order_by(UserUnderstanding.learned_at.desc(), UserUnderstanding.updated_at.desc())
            .limit(8)
        )
        items = result.scalars().all()
        return [
            {
                "title": item.title,
                "description": item.value,
                "category": item.category,
                "confidence": round(float(item.confidence or 0.0), 2),
                "source": item.source,
            }
            for item in items
        ]

    @staticmethod
    def _memory_summary(memories: list[dict]) -> str:
        if not memories:
            return "No prior memory context is available."
        return " | ".join(item["summary"] for item in memories[:3])

    @staticmethod
    def _learning_summary(items: list[dict]) -> str:
        if not items:
            return "No learned preferences are available yet."
        return " | ".join(item["title"] for item in items[:3])

    async def _count(self, model, *filters):
        if not hasattr(self.session, "scalar"):
            return 0
        result = await self.session.scalar(select(func.count(model.id)).where(*filters))
        return int(result or 0)

    async def _get_user(self, user_id: UUID):
        if not hasattr(self.session, "get"):
            return None
        return await self.session.get(User, user_id)
