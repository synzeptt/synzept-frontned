from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.message import Message
from app.services.conversation_service import ConversationService


class MessageService:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session
        self.conversations = ConversationService(session)

    async def create(
        self,
        user_id: UUID,
        conversation_id: UUID,
        role: str,
        content: str,
        token_count: int | None = None,
        provider_name: str | None = None,
        model_name: str | None = None,
        metadata: dict | None = None,
    ) -> Message | None:
        conversation = await self.conversations.get(user_id, conversation_id, include_archived=False)
        if not conversation:
            return None

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

    async def list(
        self,
        user_id: UUID,
        conversation_id: UUID,
        limit: int = 100,
        offset: int = 0,
    ) -> list[Message] | None:
        conversation = await self.conversations.get(user_id, conversation_id)
        if not conversation:
            return None

        result = await self.session.execute(
            select(Message)
            .where(Message.conversation_id == conversation_id)
            .order_by(Message.created_at.asc())
            .offset(offset)
            .limit(limit)
        )
        return list(result.scalars().all())

    async def create_assistant_placeholder(
        self,
        user_id: UUID,
        conversation_id: UUID,
        provider_name: str | None = None,
        model_name: str | None = None,
    ) -> Message | None:
        return await self.create(
            user_id=user_id,
            conversation_id=conversation_id,
            role="assistant",
            content="",
            provider_name=provider_name,
            model_name=model_name,
            metadata={"streaming": True, "status": "in_progress"},
        )

    async def finalize_streamed_message(
        self,
        user_id: UUID,
        message_id: UUID,
        content: str,
        token_count: int | None = None,
        metadata: dict | None = None,
    ) -> Message | None:
        message = await self.session.get(Message, message_id)
        if not message:
            return None
        conversation = await self.conversations.get(user_id, message.conversation_id, include_archived=False)
        if not conversation:
            return None

        message.content = content
        message.token_count = token_count
        message.metadata_ = {**(message.metadata_ or {}), **(metadata or {}), "streaming": False, "status": "complete"}
        await self.session.flush()
        return message
