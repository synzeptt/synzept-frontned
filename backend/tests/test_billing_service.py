from types import SimpleNamespace
from uuid import uuid4
from unittest.mock import AsyncMock

import hashlib
import hmac

import pytest

from app.core.exceptions import AppError
from app.models.subscription import PaymentTransaction
from app.schemas.billing import CheckoutCreateIn, PaymentVerifyIn, SubscriptionStatusOut
from app.services.billing_service import BillingService


def _service() -> BillingService:
    service = BillingService(SimpleNamespace())
    service.settings = SimpleNamespace(
        razorpay_key_id="rzp_live_testkey",
        razorpay_key_secret="live-secret",
        razorpay_pro_plan_id="plan_live_123",
        razorpay_webhook_secret="webhook-secret",
        pro_monthly_price_inr=499,
        pro_yearly_price_inr=4999,
    )
    return service


def _transaction() -> PaymentTransaction:
    return PaymentTransaction(
        id=uuid4(),
        user_id=uuid4(),
        provider="razorpay",
        provider_subscription_id="sub_live_123",
        provider_payment_id="pay_live_123",
        amount=499,
        currency="INR",
        status="created",
        plan_type="pro",
    )


def test_razorpay_ready_requires_live_key() -> None:
    service = _service()
    assert service._razorpay_ready is True

    service.settings.razorpay_key_id = "rzp_test_fake"
    assert service._razorpay_ready is False


def test_checkout_create_accepts_plan_type_aliases() -> None:
    assert CheckoutCreateIn.model_validate({"planType": "pro"}).planType == "pro"
    assert CheckoutCreateIn.model_validate({"plan_type": "pro"}).planType == "pro"
    assert CheckoutCreateIn.model_validate({"planType": "pro", "billingCycle": "yearly"}).billingCycle == "yearly"
    assert CheckoutCreateIn.model_validate({"plan_type": "pro", "billing_cycle": "monthly"}).billingCycle == "monthly"


def test_plans_include_yearly_price_and_savings() -> None:
    plans = _service().plans()

    yearly_plan = next(plan for plan in plans if plan["billingCycle"] == "yearly")

    assert yearly_plan["priceInr"] == 4999
    assert yearly_plan["savings"] == "Save ₹989"


def test_monthly_plan_matches_production_price() -> None:
    monthly_plan = next(plan for plan in _service().plans() if plan["planType"] == "pro" and plan["billingCycle"] == "monthly")

    assert monthly_plan["priceInr"] == 499


def test_subscription_status_default_matches_production_price() -> None:
    status = SubscriptionStatusOut(userId=uuid4(), planType="free", status="inactive", paymentStatus="none", isPro=False)

    assert status.priceInr == 499


def test_payment_verify_accepts_razorpay_standard_payload() -> None:
    checkout_id = uuid4()

    payload = PaymentVerifyIn.model_validate(
        {
            "checkout_id": str(checkout_id),
            "razorpay_subscription_id": "sub_live_123",
            "razorpay_payment_id": "pay_live_123",
            "razorpay_signature": "signature",
        }
    )

    assert payload.checkoutId == checkout_id
    assert payload.providerSubscriptionId == "sub_live_123"
    assert payload.providerPaymentId == "pay_live_123"
    assert payload.providerSignature == "signature"


def test_captured_razorpay_payment_passes_validation() -> None:
    transaction = _transaction()

    _service()._validate_razorpay_payment(
        {
            "id": "pay_live_123",
            "subscription_id": "sub_live_123",
            "amount": 49900,
            "currency": "INR",
            "status": "captured",
        },
        transaction,
    )

    assert transaction.status == "created"


@pytest.mark.parametrize(
    ("payment", "code"),
    [
        ({"id": "pay_live_123", "subscription_id": "wrong", "amount": 49900, "currency": "INR", "status": "captured"}, "payment_subscription_mismatch"),
        ({"id": "pay_live_123", "subscription_id": "sub_live_123", "amount": 100, "currency": "INR", "status": "captured"}, "payment_amount_mismatch"),
        ({"id": "pay_live_123", "subscription_id": "sub_live_123", "amount": 49900, "currency": "INR", "status": "authorized"}, "payment_not_captured"),
    ],
)
def test_invalid_razorpay_payment_is_rejected(payment: dict, code: str) -> None:
    transaction = _transaction()

    with pytest.raises(AppError) as exc:
        _service()._validate_razorpay_payment(payment, transaction)

    assert exc.value.code == code
    assert transaction.status == "failed"


def test_subscription_signature_is_exact() -> None:
    service = _service()
    expected = hmac.new(b"live-secret", b"pay_live_123|sub_live_123", hashlib.sha256).hexdigest()

    assert service._verify_subscription_signature("sub_live_123", "pay_live_123", expected)
    assert not service._verify_subscription_signature("sub_live_123", "pay_live_123", "wrong")


def test_webhook_signature_is_exact() -> None:
    service = _service()
    payload = b'{"event":"payment.captured"}'
    expected = hmac.new(b"webhook-secret", payload, hashlib.sha256).hexdigest()

    assert service._verify_webhook_signature(payload, expected)
    assert not service._verify_webhook_signature(payload, "wrong")


@pytest.mark.asyncio
async def test_duplicate_webhook_is_ignored() -> None:
    service = _service()
    service.session.execute = AsyncMock(return_value=SimpleNamespace(scalar_one_or_none=lambda: _transaction()))
    signature = hmac.new(b"webhook-secret", b"{}", hashlib.sha256).hexdigest()

    result = await service.handle_webhook(b"{}", {"event": "payment.captured"}, signature=signature, event_id="evt_1")

    assert result == {"received": True, "duplicate": True}


@pytest.mark.asyncio
async def test_webhook_captured_payment_activates_subscription() -> None:
    service = _service()
    transaction = _transaction()
    service.session.execute = AsyncMock(return_value=SimpleNamespace(scalar_one_or_none=lambda: None))
    service._transaction_by_subscription_id = AsyncMock(return_value=transaction)
    service._transaction_by_payment_id = AsyncMock(return_value=None)
    service._activate = AsyncMock()
    service.session.add = lambda _: None
    service.session.flush = AsyncMock()
    event = {
        "event": "payment.captured",
        "payload": {
            "payment": {
                "entity": {
                    "id": "pay_live_123",
                    "subscription_id": "sub_live_123",
                    "amount": 49900,
                    "currency": "INR",
                    "status": "captured",
                }
            }
        },
    }
    raw = b'{"event":"payment.captured"}'
    signature = hmac.new(b"webhook-secret", raw, hashlib.sha256).hexdigest()

    result = await service.handle_webhook(raw, event, signature=signature, event_id="evt_2")

    assert result == {"received": True, "duplicate": False}
    assert transaction.status == "paid"
    service._activate.assert_awaited_once_with(transaction.user_id, transaction, provider="razorpay")


@pytest.mark.asyncio
async def test_invalid_webhook_signature_is_rejected() -> None:
    service = _service()
    with pytest.raises(AppError) as exc:
        await service.handle_webhook(b"{}", {"event": "payment.captured"}, signature="wrong", event_id="evt_3")

    assert exc.value.code == "invalid_webhook_signature"


@pytest.mark.asyncio
async def test_provider_cancellation_failure_preserves_local_state() -> None:
    service = _service()
    subscription = SimpleNamespace(
        provider="razorpay",
        provider_subscription_id="sub_live_123",
        status="active",
        plan_type="pro",
        payment_status="paid",
        current_period_end=None,
    )
    service._subscription = AsyncMock(return_value=subscription)
    service._cancel_razorpay_subscription = AsyncMock(side_effect=AppError("provider unavailable", status_code=502, code="payment_provider_error"))

    with pytest.raises(AppError) as exc:
        await service.cancel(SimpleNamespace(id=uuid4()))

    assert exc.value.code == "payment_provider_error"
    assert subscription.status == "active"
    assert subscription.plan_type == "pro"


@pytest.mark.asyncio
async def test_repeated_verified_payment_is_idempotent() -> None:
    service = _service()
    transaction = _transaction()
    transaction.status = "paid"
    service._owned_transaction = AsyncMock(return_value=transaction)
    subscription = SimpleNamespace(
        status="active",
        plan_type="pro",
        payment_status="paid",
        current_period_end=None,
        cancel_at_period_end=False,
        provider="razorpay",
        metadata_={"billingCycle": "monthly"},
    )
    service._subscription = AsyncMock(return_value=subscription)

    result = await service.verify_payment(
        SimpleNamespace(id=transaction.user_id),
        PaymentVerifyIn(
            checkoutId=transaction.id,
            providerSubscriptionId="sub_live_123",
            providerPaymentId="pay_live_123",
            providerSignature="signature",
        ),
    )

    assert result["isPro"] is True
