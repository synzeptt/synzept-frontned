from uuid import UUID

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.dependencies import get_current_user, get_db
from app.models.user import User
from app.schemas.knows_you import (
    LearningSuggestionCreate,
    LearningSuggestionEdit,
    LearningSuggestionOut,
    UserUnderstandingBody,
    UserUnderstandingProfileOut,
)
from app.services.knows_you_service import KnowsYouService

router = APIRouter(prefix="/api")


@router.get("/user-understanding", response_model=UserUnderstandingProfileOut)
async def get_user_understanding(user: User = Depends(get_current_user), session: AsyncSession = Depends(get_db)):
    return await KnowsYouService(session).get_understanding(user.id)


@router.post("/user-understanding", response_model=UserUnderstandingProfileOut)
async def create_user_understanding(
    body: UserUnderstandingBody,
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
):
    return await KnowsYouService(session).create_understanding(user.id, body)


@router.put("/user-understanding", response_model=UserUnderstandingProfileOut)
async def update_user_understanding(
    body: UserUnderstandingBody,
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
):
    return await KnowsYouService(session).update_understanding(user.id, body)


@router.get("/learning-suggestions", response_model=list[LearningSuggestionOut])
async def list_learning_suggestions(user: User = Depends(get_current_user), session: AsyncSession = Depends(get_db)):
    return await KnowsYouService(session).list_suggestions(user.id)


@router.post("/learning-suggestions", response_model=LearningSuggestionOut)
async def create_learning_suggestion(
    body: LearningSuggestionCreate,
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
):
    return await KnowsYouService(session).create_suggestion(user.id, body)


@router.put("/learning-suggestions/{suggestion_id}/accept", response_model=LearningSuggestionOut)
async def accept_learning_suggestion(
    suggestion_id: UUID,
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
):
    return await KnowsYouService(session).accept_suggestion(user.id, suggestion_id)


@router.put("/learning-suggestions/{suggestion_id}/ignore", response_model=LearningSuggestionOut)
async def ignore_learning_suggestion(
    suggestion_id: UUID,
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
):
    return await KnowsYouService(session).ignore_suggestion(user.id, suggestion_id)


@router.put("/learning-suggestions/{suggestion_id}/edit", response_model=LearningSuggestionOut)
async def edit_learning_suggestion(
    suggestion_id: UUID,
    body: LearningSuggestionEdit,
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
):
    return await KnowsYouService(session).edit_suggestion(user.id, suggestion_id, body)
