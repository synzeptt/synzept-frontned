from uuid import UUID

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.dependencies import get_current_user, get_db
from app.models.user import User
from app.schemas.learning import (
    LearningEngineOut,
    LearningSettingsOut,
    LearningSettingsUpdate,
    LearningSuggestionOut,
    LearningSuggestionUpdate,
)
from app.schemas.user_understanding import UserUnderstandingOut
from app.services.learning_engine_service import LearningEngineService

router = APIRouter(prefix="/learning-engine")


@router.get("", response_model=LearningEngineOut)
async def get_learning_engine(user: User = Depends(get_current_user), session: AsyncSession = Depends(get_db)):
    return await LearningEngineService(session).get_engine(user)


@router.post("/analyze", response_model=LearningEngineOut)
async def analyze_learning(user: User = Depends(get_current_user), session: AsyncSession = Depends(get_db)):
    return await LearningEngineService(session).analyze(user)


@router.patch("/settings", response_model=LearningSettingsOut)
async def update_learning_settings(
    body: LearningSettingsUpdate,
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
):
    return await LearningEngineService(session).update_settings(user, body)


@router.delete("/history")
async def delete_learning_history(user: User = Depends(get_current_user), session: AsyncSession = Depends(get_db)):
    await LearningEngineService(session).clear_history(user.id)
    return {"ok": True}


@router.patch("/suggestions/{suggestion_id}", response_model=LearningSuggestionOut)
async def edit_suggestion(
    suggestion_id: UUID,
    body: LearningSuggestionUpdate,
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
):
    return await LearningEngineService(session).edit_suggestion(user.id, suggestion_id, body)


@router.post("/suggestions/{suggestion_id}/accept", response_model=UserUnderstandingOut)
async def accept_suggestion(
    suggestion_id: UUID,
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
):
    return await LearningEngineService(session).accept_suggestion(user.id, suggestion_id)


@router.post("/suggestions/{suggestion_id}/ignore", response_model=LearningSuggestionOut)
async def ignore_suggestion(
    suggestion_id: UUID,
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
):
    return await LearningEngineService(session).ignore_suggestion(user.id, suggestion_id)
