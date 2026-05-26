from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.conversation import Conversation
from app.models.message import Message
from app.services.conversation_service import ConversationService
from app.services.message_service import MessageService


class ChatService:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session
        self.conversations = ConversationService(session)
        self.messages = MessageService(session)

    async def create_conversation(self, user_id: UUID, title: str | None, project_id: UUID | None) -> Conversation:
        conversation = await self.conversations.create(user_id=user_id, title=title, project_id=project_id)
        if not conversation:
            raise ValueError("Project not found")
        return conversation

    async def get_conversation(self, user_id: UUID, conversation_id: UUID) -> Conversation | None:
        return await self.conversations.get(user_id, conversation_id)

    async def get_or_create(
        self, user_id: UUID, conversation_id: UUID | None, project_id: UUID | None
    ) -> Conversation:
        return await self.conversations.get_or_create(user_id, conversation_id, project_id)

    async def add_message(
        self,
        conversation_id: UUID,
        role: str,
        content: str,
        *,
        token_count: int | None = None,
        provider_name: str | None = None,
        model_name: str | None = None,
        metadata: dict | None = None,
    ) -> Message:
        message = Message(
            conversation_id=conversation_id,
            role=role,
            content=content,
            token_count=token_count,
            provider_name=provider_name,
            model_name=model_name,
            metadata_=metadata or {},
        )
        self.session.add(message)
        await self.session.flush()
        return message

    async def list_conversations(self, user_id: UUID, limit: int = 30) -> list[Conversation]:
        return await self.conversations.list(user_id, limit=limit)

    async def get_messages(self, conversation_id: UUID) -> list[Message]:
        result = await self.session.execute(
            select(Message).where(Message.conversation_id == conversation_id).order_by(Message.created_at.asc())
        )
        return list(result.scalars().all())

    async def update_summary(self, conversation_id: UUID, summary: str) -> None:
        conv = await self.session.get(Conversation, conversation_id)
        if conv:
            conv.summary = summary
