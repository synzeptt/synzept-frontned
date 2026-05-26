from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.dependencies import get_current_user, get_db
from app.daily.constants import KIND_EVENING, KIND_MORNING
from app.daily.operating import DailyOperatingService
from app.models.user import User
from app.schemas.daily import DailyExperienceOut, DailyWrapUpIn

router = APIRouter(prefix="/daily")


@router.get("/today", response_model=DailyExperienceOut)
async def get_today(user: User = Depends(get_current_user), session: AsyncSession = Depends(get_db)):
    data = await DailyOperatingService(session).get_daily_experience(user, ensure_morning=True)
    return DailyExperienceOut(**data)


@router.post("/regenerate", response_model=DailyExperienceOut)
async def regenerate(
    kind: str = Query(default=KIND_MORNING, pattern="^(morning|evening)$"),
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
):
    svc = DailyOperatingService(session)
    if kind == KIND_EVENING:
        await svc.generate_evening(user)
    else:
        await svc.generate_morning(user)
    data = await svc.get_daily_experience(user, ensure_morning=False)
    return DailyExperienceOut(**data)


@router.post("/evening/close", response_model=DailyExperienceOut)
async def close_day(user: User = Depends(get_current_user), session: AsyncSession = Depends(get_db)):
    svc = DailyOperatingService(session)
    await svc.generate_evening(user)
    data = await svc.get_daily_experience(user, ensure_morning=False)
    return DailyExperienceOut(**data)


@router.post("/wrap-up", response_model=DailyExperienceOut)
async def save_wrap_up(
    body: DailyWrapUpIn,
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
):
    svc = DailyOperatingService(session)
    await svc.save_wrap_up(
        user,
        progress_summary=body.progress_summary,
        completed=body.completed,
        unfinished=body.unfinished,
        insights=body.insights,
        tomorrow_priorities=body.tomorrow_priorities,
        continuation_points=body.continuation_points,
    )
    data = await svc.get_daily_experience(user, ensure_morning=False)
    return DailyExperienceOut(**data)


@router.post("/consolidate")
async def consolidate_memories(user: User = Depends(get_current_user), session: AsyncSession = Depends(get_db)):
    from app.daily.consolidation import MemoryConsolidation

    result = await MemoryConsolidation(session).run(user.id)
    return {"ok": True, **result}
