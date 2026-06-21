from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.dependencies import get_current_user, get_db
from app.models.user import User
from app.schemas.chat_intelligence import (
    ChatContextOut,
    ChatContextRequest,
    ChatContinueRequest,
    ChatHistorySummaryOut,
)
from app.schemas.continue_context import ContinueContextOut
from app.services.chat_intelligence_service import ChatIntelligenceService
from app.services.continue_context_service import ContinueContextService

router = APIRouter(prefix="/api/chat")


@router.post("/context", response_model=ChatContextOut)
async def get_chat_context(
    body: ChatContextRequest,
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
):
    return await ChatIntelligenceService(session).get_context(user, body.conversation_id, body.project_id)


@router.post("/continue", response_model=ContinueContextOut)
async def post_chat_continue(
    body: ChatContinueRequest,
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
):
    return await ContinueContextService(session).get_context(user)


@router.get("/history-summary", response_model=list[ChatHistorySummaryOut])
async def get_chat_history_summary(
    limit: int = Query(default=12, ge=1, le=50),
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
):
    return await ChatIntelligenceService(session).get_history_summary(user, limit=limit)
