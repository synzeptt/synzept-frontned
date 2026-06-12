from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.core.dependencies import get_current_user, get_db
from app.core.exceptions import UnauthorizedError
from app.models.user import User
from app.schemas.product_analytics import ProductAnalyticsOut
from app.services.product_analytics_service import ProductAnalyticsService

router = APIRouter(prefix="/api/internal/analytics")


async def require_founder(user: User = Depends(get_current_user)) -> User:
    settings = get_settings()
    allowed = settings.founder_analytics_email_list
    if settings.environment == "production" and user.email.lower() not in allowed:
        raise UnauthorizedError("Founder analytics access required")
    if allowed and user.email.lower() not in allowed:
        raise UnauthorizedError("Founder analytics access required")
    return user


@router.get("", response_model=ProductAnalyticsOut)
async def product_analytics(
    window_days: int = 30,
    _founder: User = Depends(require_founder),
    session: AsyncSession = Depends(get_db),
):
    days = min(max(window_days, 7), 90)
    return await ProductAnalyticsService(session).overview(window_days=days)
