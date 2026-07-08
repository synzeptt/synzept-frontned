from uuid import UUID

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.dependencies import get_current_user, get_db
from app.models.user import User
from app.schemas.user_understanding import (
    UserUnderstandingCreate,
    UserUnderstandingCoverageOut,
    UserUnderstandingProfileOut,
    UserUnderstandingOut,
    UserUnderstandingSyncOut,
    UserUnderstandingUpdate,
)
from app.services.user_understanding_service import UserUnderstandingService

router = APIRouter(prefix="/user-understanding")


@router.get("", response_model=list[UserUnderstandingOut])
async def list_understanding(user: User = Depends(get_current_user), session: AsyncSession = Depends(get_db)):
    return await UserUnderstandingService(session).list_for_user(user)


@router.get("/profile", response_model=UserUnderstandingProfileOut)
async def understanding_profile(user: User = Depends(get_current_user), session: AsyncSession = Depends(get_db)):
    return await UserUnderstandingService(session).profile_for_user(user)


@router.get("/coverage", response_model=UserUnderstandingCoverageOut)
async def understanding_coverage(user: User = Depends(get_current_user), session: AsyncSession = Depends(get_db)):
    return await UserUnderstandingService(session).coverage_for_user(user)


@router.post("/sync", response_model=UserUnderstandingSyncOut)
async def sync_understanding(user: User = Depends(get_current_user), session: AsyncSession = Depends(get_db)):
    created, coverage = await UserUnderstandingService(session).sync_from_memories(user.id)
    return UserUnderstandingSyncOut(created=created, coverage=coverage)


@router.post("", response_model=UserUnderstandingOut)
async def create_understanding(
    body: UserUnderstandingCreate,
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
):
    return await UserUnderstandingService(session).create(user.id, body)


@router.patch("/{item_id}", response_model=UserUnderstandingOut)
async def update_understanding(
    item_id: UUID,
    body: UserUnderstandingUpdate,
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
):
    return await UserUnderstandingService(session).update(user.id, item_id, body)


@router.delete("/{item_id}")
async def delete_understanding(
    item_id: UUID,
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
):
    await UserUnderstandingService(session).delete(user.id, item_id)
    return {"ok": True}
