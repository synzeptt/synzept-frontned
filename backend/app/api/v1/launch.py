import secrets

from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.core.dependencies import get_current_user, get_db
from app.models.launch import InviteCode, WaitlistEntry
from app.models.user import User
from app.schemas.launch import AccessStatus, InviteCreate, InviteOut, WaitlistJoin, WaitlistOut

router = APIRouter(prefix="/launch")


@router.get("/access", response_model=AccessStatus)
async def access_status():
    settings = get_settings()
    return AccessStatus(
        early_access_enabled=settings.early_access_enabled,
        invite_required=settings.invite_required,
    )


@router.post("/waitlist", response_model=WaitlistOut)
async def join_waitlist(body: WaitlistJoin, session: AsyncSession = Depends(get_db)):
    email = body.email.lower()
    result = await session.execute(select(WaitlistEntry).where(WaitlistEntry.email == email))
    entry = result.scalar_one_or_none()
    if entry:
        entry.name = body.name or entry.name
        entry.role = body.role or entry.role
        entry.intended_use = body.intended_use or entry.intended_use
        entry.source = body.source or entry.source
        return entry

    entry = WaitlistEntry(
        email=email,
        name=body.name,
        role=body.role,
        intended_use=body.intended_use,
        source=body.source,
    )
    session.add(entry)
    await session.flush()
    return entry


@router.post("/invites", response_model=InviteOut)
async def create_invite(
    body: InviteCreate,
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
):
    invite = InviteCode(
        code=secrets.token_urlsafe(12),
        email=body.email.lower() if body.email else None,
        max_uses=body.max_uses,
        notes=body.notes,
        created_by_user_id=user.id,
    )
    session.add(invite)
    await session.flush()
    return invite

