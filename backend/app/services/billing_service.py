from __future__ import annotations

import base64
import hashlib
import hmac
from datetime import datetime, timedelta, timezone
from uuid import UUID

import httpx
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.core.exceptions import AppError, NotFoundError
from app.models.subscription import PaymentTransaction, Subscription
from app.models.user import User
from app.schemas.billing import CheckoutCreateIn, PaymentVerifyIn
from app.services.usage_event_service import UsageEventService

PRO_BENEFITS = [
    "Synzept Agent",
    "Synzept Knows You",
    "Advanced Memory",
    "Unlimited Projects",
    "Priority Features",
]


class BillingService:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session
        self.settings = get_settings()

    async def overview(self, user: User) -> dict:
        subscription = await self._subscription(user.id)
        return {
            "plan": self._status_out(user.id, subscription),
            "plans": self.plans(),
            "transactions": [self._transaction_out(item) for item in await self._transactions(user.id)],
        }

    def plans(self) -> list[dict]:
        return [
            {
                "planType": "free",
                "name": "Free",
                "priceInr": 0,
                "interval": "month",
                "benefits": ["Synzept Agent", "Basic Projects", "Basic AI", "Mobile Access", "Basic Memory"],
            },
            {
                "planType": "pro",
                "name": "Synzept Pro",
                "priceInr": self.settings.pro_monthly_price_inr,
                "interval": "month",
                "benefits": PRO_BENEFITS,
            },
        ]

    async def create_checkout(self, user: User, body: CheckoutCreateIn) -> dict:
        if body.planType != "pro":
            raise AppError("Unsupported plan", status_code=400, code="unsupported_plan", user_message="Only Synzept Pro is available right now.")
        existing = await self._subscription(user.id)
        if self.is_pro(existing):
            raise AppError("Already subscribed", status_code=409, code="already_pro", user_message="You already have Synzept Pro.")

        amount_paise = int(self.settings.pro_monthly_price_inr * 100)
        if not self._razorpay_ready:
            raise AppError(
                "Payment provider is not configured",
                status_code=503,
                code="payment_not_configured",
                user_message="Payments are not configured yet. Please try again later.",
            )
        order_id = await self._create_razorpay_order(amount_paise)

        transaction = PaymentTransaction(
            user_id=user.id,
            provider="razorpay",
            provider_order_id=order_id,
            amount=self.settings.pro_monthly_price_inr,
            currency="INR",
            status="created",
            plan_type="pro",
            metadata_={"email": user.email},
        )
        self.session.add(transaction)
        await self.session.flush()
        await UsageEventService(self.session).track(
            user_id=user.id,
            event_type="checkout_started",
            surface="billing",
            metadata={"provider": "razorpay", "planType": "pro", "amount": self.settings.pro_monthly_price_inr},
        )
        return {
            "checkoutId": transaction.id,
            "provider": "razorpay",
            "keyId": self.settings.razorpay_key_id,
            "orderId": order_id,
            "amount": amount_paise,
            "currency": "INR",
            "planType": "pro",
            "priceInr": self.settings.pro_monthly_price_inr,
            "description": "Synzept Pro monthly subscription",
        }

    async def verify_payment(self, user: User, body: PaymentVerifyIn) -> dict:
        transaction = await self._owned_transaction(user.id, body.checkoutId)
        if transaction.provider != "razorpay":
            raise AppError("Invalid provider", status_code=400, code="invalid_payment_provider")
        if not self._razorpay_ready:
            raise AppError("Payment provider is not configured", status_code=503, code="payment_not_configured")
        if transaction.provider_order_id != body.providerOrderId:
            transaction.status = "failed"
            await self.session.flush()
            raise AppError("Payment order mismatch", status_code=400, code="payment_order_mismatch", user_message="Payment verification failed. Please try again.")
        if not self._verify_signature(body.providerOrderId, body.providerPaymentId, body.providerSignature):
            transaction.status = "failed"
            await self.session.flush()
            raise AppError("Payment verification failed", status_code=400, code="payment_verification_failed", user_message="Payment verification failed. Please try again.")
        transaction.provider_order_id = body.providerOrderId
        transaction.provider_payment_id = body.providerPaymentId
        transaction.provider_signature = body.providerSignature
        payment = await self._fetch_razorpay_payment(body.providerPaymentId)
        try:
            self._validate_razorpay_payment(payment, transaction)
        except AppError:
            await self.session.flush()
            raise
        transaction.status = "paid"
        subscription = await self._activate(user.id, transaction, provider="razorpay")
        await UsageEventService(self.session).track(
            user_id=user.id,
            event_type="payment_successful",
            surface="billing",
            metadata={"provider": "razorpay", "planType": "pro", "transactionId": str(transaction.id), "amount": transaction.amount},
        )
        return self._status_out(user.id, subscription)

    async def cancel(self, user: User) -> dict:
        subscription = await self._subscription(user.id)
        if not subscription or not self.is_pro(subscription):
            raise NotFoundError("Active Pro subscription not found")
        subscription.status = "canceled"
        subscription.plan_type = "free"
        subscription.payment_status = "canceled"
        subscription.cancel_at_period_end = False
        subscription.updated_at = datetime.now(timezone.utc)
        self.session.add(
            PaymentTransaction(
                user_id=user.id,
                subscription_id=subscription.id,
                provider=subscription.provider,
                amount=0,
                currency="INR",
                status="canceled",
                plan_type="pro",
            )
        )
        await self.session.flush()
        return self._status_out(user.id, subscription)

    async def cancel_checkout(self, user: User, checkout_id: UUID) -> dict:
        transaction = await self._owned_transaction(user.id, checkout_id)
        if transaction.status == "created":
            transaction.status = "canceled"
            transaction.metadata_ = {
                **(transaction.metadata_ or {}),
                "canceled_at": datetime.now(timezone.utc).isoformat(),
            }
            await self.session.flush()
        return self._status_out(user.id, await self._subscription(user.id))

    async def _activate(self, user_id: UUID, transaction: PaymentTransaction, provider: str) -> Subscription:
        now = datetime.now(timezone.utc)
        renewal = now + timedelta(days=30)
        subscription = await self._subscription(user_id)
        if not subscription:
            subscription = Subscription(user_id=user_id)
            self.session.add(subscription)
            await self.session.flush()
        subscription.plan_type = "pro"
        subscription.status = "active"
        subscription.payment_status = "paid"
        subscription.provider = provider
        subscription.provider_subscription_id = transaction.provider_payment_id
        subscription.current_period_start = now
        subscription.current_period_end = renewal
        subscription.cancel_at_period_end = False
        subscription.updated_at = now
        transaction.subscription_id = subscription.id
        await self.session.flush()
        return subscription

    async def _subscription(self, user_id: UUID) -> Subscription | None:
        result = await self.session.execute(select(Subscription).where(Subscription.user_id == user_id))
        return result.scalar_one_or_none()

    async def _transactions(self, user_id: UUID) -> list[PaymentTransaction]:
        result = await self.session.execute(
            select(PaymentTransaction).where(PaymentTransaction.user_id == user_id).order_by(PaymentTransaction.created_at.desc()).limit(20)
        )
        return list(result.scalars())

    async def _owned_transaction(self, user_id: UUID, transaction_id: UUID) -> PaymentTransaction:
        result = await self.session.execute(
            select(PaymentTransaction).where(PaymentTransaction.id == transaction_id, PaymentTransaction.user_id == user_id)
        )
        transaction = result.scalar_one_or_none()
        if not transaction:
            raise NotFoundError("Checkout not found")
        return transaction

    async def _create_razorpay_order(self, amount_paise: int) -> str:
        auth = base64.b64encode(f"{self.settings.razorpay_key_id}:{self.settings.razorpay_key_secret}".encode()).decode()
        async with httpx.AsyncClient(timeout=20) as client:
            response = await client.post(
                "https://api.razorpay.com/v1/orders",
                headers={"Authorization": f"Basic {auth}"},
                json={
                    "amount": amount_paise,
                    "currency": "INR",
                    "receipt": f"synzept_{int(datetime.now(timezone.utc).timestamp())}",
                    "payment_capture": 1,
                    "notes": {"plan_type": "pro", "product": "Synzept Pro"},
                },
            )
        if response.status_code >= 400:
            raise AppError("Payment provider unavailable", status_code=502, code="payment_provider_error", user_message="Payment could not start. Please try again.")
        return response.json()["id"]

    async def _fetch_razorpay_payment(self, payment_id: str) -> dict:
        auth = base64.b64encode(f"{self.settings.razorpay_key_id}:{self.settings.razorpay_key_secret}".encode()).decode()
        async with httpx.AsyncClient(timeout=20) as client:
            response = await client.get(
                f"https://api.razorpay.com/v1/payments/{payment_id}",
                headers={"Authorization": f"Basic {auth}"},
            )
        if response.status_code >= 400:
            raise AppError(
                "Payment provider verification failed",
                status_code=502,
                code="payment_provider_error",
                user_message="Payment verification could not be completed. Please try again.",
            )
        return response.json()

    def _validate_razorpay_payment(self, payment: dict, transaction: PaymentTransaction) -> None:
        expected_amount = int(transaction.amount * 100)
        if payment.get("order_id") != transaction.provider_order_id:
            transaction.status = "failed"
            raise AppError(
                "Payment order mismatch",
                status_code=400,
                code="payment_order_mismatch",
                user_message="Payment verification failed. Please try again.",
            )
        if payment.get("id") != transaction.provider_payment_id and transaction.provider_payment_id:
            transaction.status = "failed"
            raise AppError(
                "Payment ID mismatch",
                status_code=400,
                code="payment_id_mismatch",
                user_message="Payment verification failed. Please try again.",
            )
        if int(payment.get("amount") or 0) != expected_amount or payment.get("currency") != "INR":
            transaction.status = "failed"
            raise AppError(
                "Payment amount mismatch",
                status_code=400,
                code="payment_amount_mismatch",
                user_message="Payment verification failed. Please try again.",
            )
        if payment.get("status") != "captured":
            transaction.status = "failed"
            raise AppError(
                "Payment is not captured",
                status_code=400,
                code="payment_not_captured",
                user_message="Payment was not completed. No Pro access was activated.",
            )

    @property
    def _razorpay_ready(self) -> bool:
        return bool(
            self.settings.razorpay_key_id
            and self.settings.razorpay_key_secret
            and self.settings.razorpay_key_id.startswith("rzp_live_")
        )

    def _verify_signature(self, order_id: str, payment_id: str, signature: str) -> bool:
        digest = hmac.new(
            self.settings.razorpay_key_secret.encode(),
            f"{order_id}|{payment_id}".encode(),
            hashlib.sha256,
        ).hexdigest()
        return hmac.compare_digest(digest, signature)

    def _status_out(self, user_id: UUID, subscription: Subscription | None) -> dict:
        is_pro = self.is_pro(subscription)
        return {
            "userId": user_id,
            "planType": "pro" if is_pro else "free",
            "status": subscription.status if subscription else "inactive",
            "paymentStatus": subscription.payment_status if subscription else "none",
            "isPro": is_pro,
            "renewalDate": subscription.current_period_end if is_pro and subscription else None,
            "cancelAtPeriodEnd": subscription.cancel_at_period_end if subscription else False,
            "provider": subscription.provider if subscription else "manual",
            "priceInr": self.settings.pro_monthly_price_inr,
        }

    @staticmethod
    def is_pro(subscription: Subscription | None) -> bool:
        if not subscription:
            return False
        if subscription.plan_type != "pro" or subscription.status != "active" or subscription.payment_status != "paid":
            return False
        if subscription.current_period_end:
            period_end = subscription.current_period_end
            if period_end.tzinfo is None:
                period_end = period_end.replace(tzinfo=timezone.utc)
            if period_end < datetime.now(timezone.utc):
                return False
        return True

    @staticmethod
    def _transaction_out(transaction: PaymentTransaction) -> dict:
        return {
            "id": transaction.id,
            "provider": transaction.provider,
            "providerOrderId": transaction.provider_order_id,
            "providerPaymentId": transaction.provider_payment_id,
            "amount": transaction.amount,
            "currency": transaction.currency,
            "status": transaction.status,
            "planType": transaction.plan_type,
            "createdAt": transaction.created_at,
            "updatedAt": transaction.updated_at,
        }
