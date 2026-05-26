from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.dependencies import get_current_user, get_db
from app.models.user import User
from app.schemas.onboarding import (
    OnboardingCompleteOut,
    OnboardingContextIn,
    OnboardingFirstChatIn,
    OnboardingFirstChatOut,
    OnboardingStatusOut,
    OnboardingWorkspaceIn,
)
from app.services.onboarding_service import OnboardingService

router = APIRouter(prefix="/onboarding")


@router.get("/status", response_model=OnboardingStatusOut)
async def onboarding_status(user: User = Depends(get_current_user), session: AsyncSession = Depends(get_db)):
    return await OnboardingService(session).get_status(user)


@router.post("/welcome", response_model=OnboardingStatusOut)
async def onboarding_welcome(user: User = Depends(get_current_user), session: AsyncSession = Depends(get_db)):
    return await OnboardingService(session).mark_welcome(user)


@router.post("/context", response_model=OnboardingStatusOut)
async def onboarding_context(
    body: OnboardingContextIn,
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
):
    return await OnboardingService(session).save_context(user, body)


@router.post("/initialize-memories", response_model=OnboardingStatusOut)
async def onboarding_memories(user: User = Depends(get_current_user), session: AsyncSession = Depends(get_db)):
    return await OnboardingService(session).initialize_memories(user)


@router.post("/workspace", response_model=OnboardingStatusOut)
async def onboarding_workspace(
    body: OnboardingWorkspaceIn,
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
):
    return await OnboardingService(session).save_workspace(user, body)


@router.post("/first-chat", response_model=OnboardingFirstChatOut)
async def onboarding_first_chat(
    body: OnboardingFirstChatIn,
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
):
    return await OnboardingService(session).first_interaction(user, body)


@router.post("/complete", response_model=OnboardingCompleteOut)
async def onboarding_complete(
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
):
    return await OnboardingService(session).complete(user)


@router.post("/skip", response_model=OnboardingCompleteOut)
async def onboarding_skip(
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
):
    return await OnboardingService(session).skip_to_complete(user)
