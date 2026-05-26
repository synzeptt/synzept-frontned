from datetime import datetime, timezone
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.conversation import Conversation
from app.models.project import Project


class ConversationService:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def create(
        self,
        user_id: UUID,
        title: str | None = None,
        project_id: UUID | None = None,
        conversation_type: str = "general",
        summary: str | None = None,
    ) -> Conversation | None:
        if project_id and not await self._user_owns_project(user_id, project_id):
            return None

        conversation = Conversation(
            user_id=user_id,
            project_id=project_id,
            title=title or "New conversation",
            summary=summary,
            conversation_type=conversation_type,
        )
        self.session.add(conversation)
        await self.session.flush()
        return conversation

    async def get(self, user_id: UUID, conversation_id: UUID, include_archived: bool = True) -> Conversation | None:
        conversation = await self.session.get(Conversation, conversation_id)
        if (
            not conversation
            or conversation.user_id != user_id
            or conversation.deleted_at
            or (not include_archived and conversation.archived_at)
        ):
            return None
        return conversation

    async def get_or_create(
        self,
        user_id: UUID,
        conversation_id: UUID | None,
        project_id: UUID | None,
    ) -> Conversation:
        if conversation_id:
            conversation = await self.get(user_id, conversation_id, include_archived=False)
            if conversation:
                return conversation

        conversation = await self.create(user_id=user_id, project_id=project_id)
        if not conversation:
            conversation = await self.create(user_id=user_id)
        return conversation

    async def list(
        self,
        user_id: UUID,
        project_id: UUID | None = None,
        include_archived: bool = False,
        limit: int = 30,
        offset: int = 0,
    ) -> list[Conversation]:
        query = select(Conversation).where(Conversation.user_id == user_id, Conversation.deleted_at.is_(None))
        if project_id:
            query = query.where(Conversation.project_id == project_id)
        if not include_archived:
            query = query.where(Conversation.archived_at.is_(None))

        result = await self.session.execute(
            query.order_by(Conversation.updated_at.desc()).offset(offset).limit(limit)
        )
        return list(result.scalars().all())

    async def rename(self, user_id: UUID, conversation_id: UUID, title: str) -> Conversation | None:
        conversation = await self.get(user_id, conversation_id)
        if not conversation:
            return None
        conversation.title = title
        await self.session.flush()
        return conversation

    async def archive(self, user_id: UUID, conversation_id: UUID) -> Conversation | None:
        conversation = await self.get(user_id, conversation_id)
        if not conversation:
            return None
        conversation.archived_at = datetime.now(timezone.utc)
        conversation.is_active = False
        await self.session.flush()
        return conversation

    async def update_summary(self, user_id: UUID, conversation_id: UUID, summary: str | None) -> Conversation | None:
        conversation = await self.get(user_id, conversation_id)
        if not conversation:
            return None
        conversation.summary = summary
        await self.session.flush()
        return conversation

    async def _user_owns_project(self, user_id: UUID, project_id: UUID) -> bool:
        project = await self.session.get(Project, project_id)
        return bool(project and project.user_id == user_id and not project.deleted_at)
