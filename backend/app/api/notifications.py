from uuid import UUID

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.dependencies import get_current_user, get_db
from app.models.user import User
from app.schemas.notifications import NotificationDigestOut, NotificationSettingsOut, NotificationSettingsUpdate
from app.services.notification_service import NotificationService

router = APIRouter(prefix="/api/notifications")


@router.get("", response_model=NotificationDigestOut)
async def notifications_overview(
    generate: bool = False,
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
):
    return await NotificationService(session).overview(user, generate=generate)


@router.post("/generate", response_model=NotificationDigestOut)
async def generate_notifications(user: User = Depends(get_current_user), session: AsyncSession = Depends(get_db)):
    service = NotificationService(session)
    await service.generate_for_user(user)
    return await service.overview(user)


@router.patch("/settings", response_model=NotificationSettingsOut)
async def update_notification_settings(
    body: NotificationSettingsUpdate,
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
):
    return await NotificationService(session).update_settings(user, body)


@router.post("/{notification_id}/read", response_model=NotificationDigestOut)
async def mark_notification_read(
    notification_id: UUID,
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
):
    return await NotificationService(session).mark_read(user, notification_id)
