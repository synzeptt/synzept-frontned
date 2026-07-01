from types import SimpleNamespace
from uuid import uuid4

import pytest

from app.core.exceptions import AppError
from app.models.subscription import PaymentTransaction
from app.schemas.billing import CheckoutCreateIn, PaymentVerifyIn
from app.services.billing_service import BillingService


def _service() -> BillingService:
    service = BillingService(SimpleNamespace())
    service.settings = SimpleNamespace(
        razorpay_key_id="rzp_live_testkey",
        razorpay_key_secret="live-secret",
        pro_monthly_price_inr=399,
        pro_yearly_price_inr=3999,
    )
    return service


def _transaction() -> PaymentTransaction:
    return PaymentTransaction(
        id=uuid4(),
        user_id=uuid4(),
        provider="razorpay",
        provider_order_id="order_live_123",
        provider_payment_id="pay_live_123",
        amount=399,
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


def test_payment_verify_accepts_razorpay_standard_payload() -> None:
    checkout_id = uuid4()

    payload = PaymentVerifyIn.model_validate(
        {
            "checkout_id": str(checkout_id),
            "razorpay_order_id": "order_live_123",
            "razorpay_payment_id": "pay_live_123",
            "razorpay_signature": "signature",
        }
    )

    assert payload.checkoutId == checkout_id
    assert payload.providerOrderId == "order_live_123"
    assert payload.providerPaymentId == "pay_live_123"
    assert payload.providerSignature == "signature"


def test_captured_razorpay_payment_passes_validation() -> None:
    transaction = _transaction()

    _service()._validate_razorpay_payment(
        {
            "id": "pay_live_123",
            "order_id": "order_live_123",
            "amount": 39900,
            "currency": "INR",
            "status": "captured",
        },
        transaction,
    )

    assert transaction.status == "created"


@pytest.mark.parametrize(
    ("payment", "code"),
    [
        ({"id": "pay_live_123", "order_id": "wrong", "amount": 39900, "currency": "INR", "status": "captured"}, "payment_order_mismatch"),
        ({"id": "pay_live_123", "order_id": "order_live_123", "amount": 100, "currency": "INR", "status": "captured"}, "payment_amount_mismatch"),
        ({"id": "pay_live_123", "order_id": "order_live_123", "amount": 39900, "currency": "INR", "status": "authorized"}, "payment_not_captured"),
    ],
)
def test_invalid_razorpay_payment_is_rejected(payment: dict, code: str) -> None:
    transaction = _transaction()

    with pytest.raises(AppError) as exc:
        _service()._validate_razorpay_payment(payment, transaction)

    assert exc.value.code == code
    assert transaction.status == "failed"
