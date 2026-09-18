from __future__ import annotations

import base64
import hashlib
import hmac
from datetime import datetime, timedelta, timezone
from typing import Any
from uuid import UUID

import httpx
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.core.exceptions import AppError, NotFoundError
from app.models.subscription import BillingWebhookEvent, PaymentTransaction, Subscription
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
    RAZORPAY_API = "https://api.razorpay.com/v1"
    MONTHLY_AMOUNT_PAISE = 49_900

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
        yearly_savings = max((self.settings.pro_monthly_price_inr * 12) - self.settings.pro_yearly_price_inr, 0)
        return [
            {
                "planType": "free",
                "name": "Free",
                "priceInr": 0,
                "interval": "month",
                "billingCycle": "monthly",
                "benefits": ["Synzept Agent", "Basic Projects", "Basic AI", "Mobile Access", "Basic Memory"],
            },
            {
                "planType": "pro",
                "name": "Synzept Pro Monthly",
                "priceInr": self.settings.pro_monthly_price_inr,
                "interval": "month",
                "billingCycle": "monthly",
                "savings": None,
                "benefits": PRO_BENEFITS,
            },
            {
                "planType": "pro",
                "name": "Synzept Pro Yearly",
                "priceInr": self.settings.pro_yearly_price_inr,
                "interval": "year",
                "billingCycle": "yearly",
                "savings": f"Save ₹{yearly_savings}" if yearly_savings else None,
                "benefits": PRO_BENEFITS,
            },
        ]

    async def create_checkout(self, user: User, body: CheckoutCreateIn) -> dict:
        if body.planType != "pro":
            raise AppError("Unsupported plan", status_code=400, code="unsupported_plan", user_message="Only Synzept Pro is available right now.")
        existing = await self._subscription(user.id)
        if self.is_pro(existing):
            raise AppError("Already subscribed", status_code=409, code="already_pro", user_message="You already have Synzept Pro.")

        if body.billingCycle != "monthly":
            raise AppError("Unsupported billing cycle", status_code=400, code="unsupported_billing_cycle", user_message="Only monthly Pro billing is available right now.")
        plan = self._plan_for_cycle("monthly")
        amount_paise = self.MONTHLY_AMOUNT_PAISE
        if plan["priceInr"] != 499:
            raise AppError("Invalid Pro price configuration", status_code=500, code="invalid_price_configuration")
        if not self._razorpay_ready:
            raise AppError(
                "Payment provider is not configured",
                status_code=503,
                code="payment_not_configured",
                user_message="Payments are not configured yet. Please try again later.",
            )
        subscription_id = await self._create_razorpay_subscription(user, amount_paise)

        transaction = PaymentTransaction(
            user_id=user.id,
            provider="razorpay",
            provider_subscription_id=subscription_id,
            amount=plan["priceInr"],
            currency="INR",
            status="created",
            plan_type="pro",
            metadata_={"email": user.email, "billingCycle": body.billingCycle, "interval": plan["interval"]},
        )
        self.session.add(transaction)
        await self.session.flush()
        await UsageEventService(self.session).track(
            user_id=user.id,
            event_type="checkout_started",
            surface="billing",
            metadata={"provider": "razorpay", "planType": "pro", "billingCycle": body.billingCycle, "amount": plan["priceInr"]},
        )
        return {
            "checkoutId": transaction.id,
            "provider": "razorpay",
            "keyId": self.settings.razorpay_key_id,
            "subscriptionId": subscription_id,
            "amount": amount_paise,
            "currency": "INR",
            "planType": "pro",
            "billingCycle": body.billingCycle,
            "priceInr": plan["priceInr"],
            "description": f"Synzept Pro {plan['interval']} subscription",
        }

    async def verify_payment(self, user: User, body: PaymentVerifyIn) -> dict:
        transaction = await self._owned_transaction(user.id, body.checkoutId)
        if transaction.provider != "razorpay":
            raise AppError("Invalid provider", status_code=400, code="invalid_payment_provider")
        if transaction.status == "paid":
            if transaction.provider_payment_id == body.providerPaymentId:
                return self._status_out(user.id, await self._subscription(user.id))
            raise AppError("Payment was already verified", status_code=409, code="payment_already_verified")
        if not self._razorpay_ready:
            raise AppError("Payment provider is not configured", status_code=503, code="payment_not_configured")
        if transaction.provider_subscription_id != body.providerSubscriptionId:
            transaction.status = "failed"
            await self.session.flush()
            raise AppError("Payment subscription mismatch", status_code=400, code="payment_subscription_mismatch", user_message="Payment verification failed. Please try again.")
        existing_payment = await self._transaction_by_payment_id(body.providerPaymentId)
        if existing_payment and existing_payment.id != transaction.id:
            raise AppError("Payment was already associated", status_code=409, code="payment_already_associated")
        if not self._verify_subscription_signature(body.providerSubscriptionId, body.providerPaymentId, body.providerSignature):
            transaction.status = "failed"
            await self.session.flush()
            raise AppError("Payment verification failed", status_code=400, code="payment_verification_failed", user_message="Payment verification failed. Please try again.")
        transaction.provider_subscription_id = body.providerSubscriptionId
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
            metadata={
                "provider": "razorpay",
                "planType": "pro",
                "billingCycle": (transaction.metadata_ or {}).get("billingCycle", "monthly"),
                "transactionId": str(transaction.id),
                "amount": transaction.amount,
            },
        )
        return self._status_out(user.id, subscription)

    async def cancel(self, user: User) -> dict:
        subscription = await self._subscription(user.id)
        if not subscription or not self.is_pro(subscription):
            raise NotFoundError("Active Pro subscription not found")
        if subscription.provider == "razorpay" and subscription.provider_subscription_id:
            await self._cancel_razorpay_subscription(subscription.provider_subscription_id)
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
            if transaction.provider_subscription_id:
                await self._cancel_razorpay_subscription(transaction.provider_subscription_id)
            transaction.status = "canceled"
            transaction.metadata_ = {
                **(transaction.metadata_ or {}),
                "canceled_at": datetime.now(timezone.utc).isoformat(),
            }
            await self.session.flush()
        return self._status_out(user.id, await self._subscription(user.id))

    async def _activate(self, user_id: UUID, transaction: PaymentTransaction, provider: str) -> Subscription:
        now = datetime.now(timezone.utc)
        billing_cycle = (transaction.metadata_ or {}).get("billingCycle", "monthly")
        renewal = now + timedelta(days=365 if billing_cycle == "yearly" else 30)
        subscription = await self._subscription(user_id)
        if not subscription:
            subscription = Subscription(user_id=user_id)
            self.session.add(subscription)
            await self.session.flush()
        subscription.plan_type = "pro"
        subscription.status = "active"
        subscription.payment_status = "paid"
        subscription.provider = provider
        subscription.provider_subscription_id = transaction.provider_subscription_id
        subscription.current_period_start = now
        subscription.current_period_end = renewal
        subscription.cancel_at_period_end = False
        subscription.metadata_ = {**(subscription.metadata_ or {}), "billingCycle": billing_cycle}
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

    async def _create_razorpay_subscription(self, user: User, amount_paise: int) -> str:
        plan = await self._fetch_razorpay_plan()
        item = plan.get("item") or {}
        if int(item.get("amount") or 0) != amount_paise or item.get("currency") != "INR" or plan.get("period") != "monthly":
            raise AppError("Razorpay plan does not match Synzept Pro", status_code=503, code="invalid_payment_plan")
        async with httpx.AsyncClient(timeout=20) as client:
            response = await client.post(
                f"{self.RAZORPAY_API}/subscriptions",
                headers=self._razorpay_headers(),
                json={
                    "plan_id": self.settings.razorpay_pro_plan_id,
                    "total_count": 120,
                    "customer_notify": 1,
                    "notes": {
                        "synzept_user_id": str(user.id),
                        "plan_type": "pro",
                        "amount_inr": "499",
                        "currency": "INR",
                    },
                },
            )
        if response.status_code >= 400:
            raise AppError("Payment provider unavailable", status_code=502, code="payment_provider_error", user_message="Payment could not start. Please try again.")
        return str(response.json()["id"])

    async def _fetch_razorpay_plan(self) -> dict[str, Any]:
        async with httpx.AsyncClient(timeout=20) as client:
            response = await client.get(
                f"{self.RAZORPAY_API}/plans/{self.settings.razorpay_pro_plan_id}",
                headers=self._razorpay_headers(),
            )
        if response.status_code >= 400:
            raise AppError("Payment plan verification failed", status_code=502, code="payment_provider_error", user_message="Payment could not start. Please try again.")
        return response.json()

    async def _fetch_razorpay_payment(self, payment_id: str) -> dict:
        async with httpx.AsyncClient(timeout=20) as client:
            response = await client.get(
                f"{self.RAZORPAY_API}/payments/{payment_id}",
                headers=self._razorpay_headers(),
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
        if payment.get("subscription_id") != transaction.provider_subscription_id:
            transaction.status = "failed"
            raise AppError(
            "Payment subscription mismatch",
                status_code=400,
            code="payment_subscription_mismatch",
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
            and getattr(self.settings, "razorpay_pro_plan_id", "")
            and self.settings.razorpay_key_id.startswith("rzp_live_")
        )

    def _razorpay_headers(self) -> dict[str, str]:
        auth = base64.b64encode(f"{self.settings.razorpay_key_id}:{self.settings.razorpay_key_secret}".encode()).decode()
        return {"Authorization": f"Basic {auth}", "Content-Type": "application/json"}

    def _verify_subscription_signature(self, subscription_id: str, payment_id: str, signature: str) -> bool:
        digest = hmac.new(
            self.settings.razorpay_key_secret.encode(),
            f"{payment_id}|{subscription_id}".encode(),
            hashlib.sha256,
        ).hexdigest()
        return hmac.compare_digest(digest, signature)

    def _verify_webhook_signature(self, payload: bytes, signature: str) -> bool:
        digest = hmac.new(self.settings.razorpay_webhook_secret.encode(), payload, hashlib.sha256).hexdigest()
        return hmac.compare_digest(digest, signature)

    async def _cancel_razorpay_subscription(self, subscription_id: str) -> None:
        async with httpx.AsyncClient(timeout=20) as client:
            response = await client.post(
                f"{self.RAZORPAY_API}/subscriptions/{subscription_id}/cancel",
                headers=self._razorpay_headers(),
                json={"cancel_at_cycle_end": 0},
            )
        if response.status_code >= 400:
            raise AppError(
                "Payment subscription cancellation failed",
                status_code=502,
                code="payment_provider_error",
                user_message="The payment subscription could not be canceled. No local changes were made.",
            )

    async def _transaction_by_payment_id(self, payment_id: str) -> PaymentTransaction | None:
        result = await self.session.execute(select(PaymentTransaction).where(PaymentTransaction.provider_payment_id == payment_id))
        return result.scalar_one_or_none()

    async def _transaction_by_subscription_id(self, subscription_id: str) -> PaymentTransaction | None:
        result = await self.session.execute(
            select(PaymentTransaction)
            .where(PaymentTransaction.provider_subscription_id == subscription_id)
            .order_by(PaymentTransaction.created_at.desc())
        )
        return result.scalars().first()

    async def handle_webhook(self, raw_payload: bytes, event: dict[str, Any], *, signature: str, event_id: str) -> dict[str, bool]:
        if not self.settings.razorpay_webhook_secret or not self._verify_webhook_signature(raw_payload, signature):
            raise AppError("Invalid webhook signature", status_code=400, code="invalid_webhook_signature")
        if not event_id:
            raise AppError("Missing webhook event ID", status_code=400, code="missing_webhook_event_id")
        existing = await self.session.execute(select(BillingWebhookEvent).where(BillingWebhookEvent.provider_event_id == event_id))
        if existing.scalar_one_or_none():
            return {"received": True, "duplicate": True}

        event_name = str(event.get("event") or "")
        payload = event.get("payload") or {}
        payment = ((payload.get("payment") or {}).get("entity") or {})
        subscription = ((payload.get("subscription") or {}).get("entity") or {})
        subscription_id = str(payment.get("subscription_id") or subscription.get("id") or "")
        transaction = await self._transaction_by_subscription_id(subscription_id) if subscription_id else None
        if not transaction:
            raise AppError("Webhook subscription is not associated", status_code=409, code="unknown_payment_subscription")
        self.session.add(BillingWebhookEvent(provider="razorpay", provider_event_id=event_id, event_name=event_name))
        if event_name in {"payment.captured", "subscription.charged"}:
            payment_id = str(payment.get("id") or "")
            if not payment_id:
                raise AppError("Webhook payment is missing an ID", status_code=400, code="invalid_webhook_payload")
            existing_payment = await self._transaction_by_payment_id(payment_id)
            if existing_payment and existing_payment.id != transaction.id:
                raise AppError("Webhook payment was already associated", status_code=409, code="payment_already_associated")
            transaction.provider_payment_id = payment_id
            self._validate_webhook_payment(payment, transaction)
            if transaction.status != "paid":
                transaction.status = "paid"
                await self._activate(transaction.user_id, transaction, provider="razorpay")
        elif event_name == "payment.failed":
            transaction.status = "failed"
            local_subscription = await self._subscription(transaction.user_id)
            if local_subscription:
                local_subscription.payment_status = "failed"
                local_subscription.status = "past_due"
        elif event_name in {"subscription.cancelled", "subscription.completed", "subscription.halted"}:
            local_subscription = await self._subscription(transaction.user_id)
            if local_subscription:
                local_subscription.status = "canceled" if event_name != "subscription.halted" else "past_due"
                local_subscription.plan_type = "free" if event_name != "subscription.halted" else "pro"
                local_subscription.payment_status = "canceled" if event_name != "subscription.halted" else "failed"
        await self.session.flush()
        return {"received": True, "duplicate": False}

    def _validate_webhook_payment(self, payment: dict[str, Any], transaction: PaymentTransaction) -> None:
        if payment.get("subscription_id") != transaction.provider_subscription_id:
            raise AppError("Payment subscription mismatch", status_code=400, code="payment_subscription_mismatch")
        if int(payment.get("amount") or 0) != self.MONTHLY_AMOUNT_PAISE or payment.get("currency") != "INR":
            raise AppError("Payment amount mismatch", status_code=400, code="payment_amount_mismatch")
        if payment.get("status") != "captured":
            raise AppError("Payment is not captured", status_code=400, code="payment_not_captured")

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
            "priceInr": self._plan_for_cycle((subscription.metadata_ or {}).get("billingCycle", "monthly") if subscription else "monthly")["priceInr"],
        }

    def _plan_for_cycle(self, billing_cycle: str) -> dict:
        if billing_cycle == "yearly":
            return {"priceInr": self.settings.pro_yearly_price_inr, "interval": "year"}
        return {"priceInr": self.settings.pro_monthly_price_inr, "interval": "month"}

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
            "providerSubscriptionId": transaction.provider_subscription_id,
            "providerPaymentId": transaction.provider_payment_id,
            "amount": transaction.amount,
            "currency": transaction.currency,
            "status": transaction.status,
            "planType": transaction.plan_type,
            "createdAt": transaction.created_at,
            "updatedAt": transaction.updated_at,
        }
