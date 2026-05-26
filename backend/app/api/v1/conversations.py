from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.dependencies import get_current_user, get_db
from app.models.user import User
from app.schemas.chat import (
    ConversationCreate,
    ConversationOut,
    ConversationRename,
    ConversationSummaryUpdate,
    MessageCreate,
    MessageOut,
)
from app.services.conversation_service import ConversationService
from app.services.message_service import MessageService

router = APIRouter(prefix="/conversations")


@router.get("", response_model=list[ConversationOut])
async def list_conversations(
    project_id: UUID | None = None,
    include_archived: bool = False,
    limit: int = Query(default=30, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
):
    return await ConversationService(session).list(
        user.id,
        project_id=project_id,
        include_archived=include_archived,
        limit=limit,
        offset=offset,
    )


@router.post("", response_model=ConversationOut)
async def create_conversation(
    body: ConversationCreate,
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
):
    conversation = await ConversationService(session).create(
        user_id=user.id,
        title=body.title,
        project_id=body.project_id,
        conversation_type=body.conversation_type,
        summary=body.summary,
    )
    if not conversation:
        raise HTTPException(status_code=404, detail="Project not found")
    return conversation


@router.get("/{conversation_id}", response_model=ConversationOut)
async def retrieve_conversation(
    conversation_id: UUID,
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
):
    conversation = await ConversationService(session).get(user.id, conversation_id)
    if not conversation:
        raise HTTPException(status_code=404, detail="Conversation not found")
    return conversation


@router.get("/{conversation_id}/messages", response_model=list[MessageOut])
async def get_messages(
    conversation_id: UUID,
    limit: int = Query(default=100, ge=1, le=500),
    offset: int = Query(default=0, ge=0),
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
):
    messages = await MessageService(session).list(user.id, conversation_id, limit=limit, offset=offset)
    if messages is None:
        raise HTTPException(status_code=404, detail="Conversation not found")
    return messages


@router.post("/{conversation_id}/messages", response_model=MessageOut)
async def create_message(
    conversation_id: UUID,
    body: MessageCreate,
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
):
    message = await MessageService(session).create(
        user_id=user.id,
        conversation_id=conversation_id,
        role=body.role,
        content=body.content,
        token_count=body.token_count,
        provider_name=body.provider_name,
        model_name=body.model_name,
        metadata=body.metadata,
    )
    if not message:
        raise HTTPException(status_code=404, detail="Conversation not found")
    return message


@router.patch("/{conversation_id}/archive", response_model=ConversationOut)
async def archive_conversation(
    conversation_id: UUID,
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
):
    conversation = await ConversationService(session).archive(user.id, conversation_id)
    if not conversation:
        raise HTTPException(status_code=404, detail="Conversation not found")
    return conversation


@router.patch("/{conversation_id}/rename", response_model=ConversationOut)
async def rename_conversation(
    conversation_id: UUID,
    body: ConversationRename,
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
):
    conversation = await ConversationService(session).rename(user.id, conversation_id, body.title)
    if not conversation:
        raise HTTPException(status_code=404, detail="Conversation not found")
    return conversation


@router.patch("/{conversation_id}/summary", response_model=ConversationOut)
async def update_conversation_summary(
    conversation_id: UUID,
    body: ConversationSummaryUpdate,
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
):
    conversation = await ConversationService(session).update_summary(user.id, conversation_id, body.summary)
    if not conversation:
        raise HTTPException(status_code=404, detail="Conversation not found")
    return conversation
