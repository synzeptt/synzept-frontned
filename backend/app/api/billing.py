from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.dependencies import get_current_user, get_db
from app.models.user import User
from app.schemas.billing import (
    BillingOverviewOut,
    CheckoutCreateIn,
    CheckoutCreateOut,
    PaymentVerifyIn,
    SubscriptionStatusOut,
)
from app.services.billing_service import BillingService

router = APIRouter(prefix="/api/billing")


@router.get("", response_model=BillingOverviewOut)
async def billing_overview(user: User = Depends(get_current_user), session: AsyncSession = Depends(get_db)):
    return await BillingService(session).overview(user)


@router.post("/checkout", response_model=CheckoutCreateOut)
async def create_checkout(
    body: CheckoutCreateIn,
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
):
    return await BillingService(session).create_checkout(user, body)


@router.post("/verify", response_model=SubscriptionStatusOut)
async def verify_payment(
    body: PaymentVerifyIn,
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
):
    return await BillingService(session).verify_payment(user, body)


@router.post("/cancel", response_model=SubscriptionStatusOut)
async def cancel_subscription(user: User = Depends(get_current_user), session: AsyncSession = Depends(get_db)):
    return await BillingService(session).cancel(user)
