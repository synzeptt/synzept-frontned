from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import AliasChoices, BaseModel, Field


PlanType = Literal["free", "pro"]
BillingCycle = Literal["monthly", "yearly"]
SubscriptionStatus = Literal["inactive", "active", "canceled", "past_due"]


class BillingPlanOut(BaseModel):
    planType: PlanType
    name: str
    priceInr: int
    interval: str = "month"
    billingCycle: BillingCycle = "monthly"
    savings: str | None = None
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
    planType: Literal["pro"] = Field(default="pro", validation_alias=AliasChoices("planType", "plan_type"))
    billingCycle: BillingCycle = Field(default="monthly", validation_alias=AliasChoices("billingCycle", "billing_cycle", "interval"))


class CheckoutCreateOut(BaseModel):
    checkoutId: UUID
    provider: Literal["razorpay"]
    keyId: str | None = None
    orderId: str
    amount: int
    currency: str = "INR"
    planType: Literal["pro"] = "pro"
    billingCycle: BillingCycle = "monthly"
    priceInr: int
    description: str


class PaymentVerifyIn(BaseModel):
    checkoutId: UUID = Field(validation_alias=AliasChoices("checkoutId", "checkout_id"))
    providerOrderId: str = Field(validation_alias=AliasChoices("providerOrderId", "razorpay_order_id", "order_id"))
    providerPaymentId: str = Field(validation_alias=AliasChoices("providerPaymentId", "razorpay_payment_id", "payment_id"))
    providerSignature: str = Field(validation_alias=AliasChoices("providerSignature", "razorpay_signature", "signature"))
