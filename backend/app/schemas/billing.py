from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, Field


PlanType = Literal["free", "pro"]
SubscriptionStatus = Literal["inactive", "active", "canceled", "past_due"]


class BillingPlanOut(BaseModel):
    planType: PlanType
    name: str
    priceInr: int
    interval: str = "month"
    benefits: list[str] = Field(default_factory=list)


class SubscriptionStatusOut(BaseModel):
    userId: UUID
    planType: PlanType
    status: SubscriptionStatus
    paymentStatus: str
    isPro: bool
    renewalDate: datetime | None = None
    cancelAtPeriodEnd: bool = False
    provider: str = "manual"
    priceInr: int = 399


class PaymentTransactionOut(BaseModel):
    id: UUID
    provider: str
    providerOrderId: str | None = None
    providerPaymentId: str | None = None
    amount: float
    currency: str
    status: str
    planType: str
    createdAt: datetime
    updatedAt: datetime


class BillingOverviewOut(BaseModel):
    plan: SubscriptionStatusOut
    plans: list[BillingPlanOut]
    transactions: list[PaymentTransactionOut] = Field(default_factory=list)


class CheckoutCreateIn(BaseModel):
    planType: Literal["pro"] = "pro"


class CheckoutCreateOut(BaseModel):
    checkoutId: UUID
    provider: Literal["razorpay"]
    keyId: str | None = None
    orderId: str
    amount: int
    currency: str = "INR"
    planType: Literal["pro"] = "pro"
    priceInr: int
    description: str


class PaymentVerifyIn(BaseModel):
    checkoutId: UUID
    providerOrderId: str
    providerPaymentId: str
    providerSignature: str
