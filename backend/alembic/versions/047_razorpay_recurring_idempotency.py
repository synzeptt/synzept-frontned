"""add recurring Razorpay identifiers and idempotency constraints

Revision ID: 047_razorpay_recurring_idempotency
Revises: 046_fix_action_execution_timestamp_timezone
Create Date: 2026-09-18
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision = "047_razorpay_recurring_idempotency"
down_revision = "046_fix_action_execution_timestamp_timezone"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("payment_transactions", sa.Column("provider_subscription_id", sa.String(length=120), nullable=True))
    op.create_table(
        "billing_webhook_events",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("provider", sa.String(length=40), nullable=False, server_default="razorpay"),
        sa.Column("provider_event_id", sa.String(length=160), nullable=False),
        sa.Column("event_name", sa.String(length=80), nullable=False),
        sa.Column("processed_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("provider_event_id", name="uq_billing_webhook_events_provider_event_id"),
    )
    op.create_index("ix_billing_webhook_events_provider_event_id", "billing_webhook_events", ["provider_event_id"])
    op.create_index(
        "ix_payment_transactions_provider_subscription_id",
        "payment_transactions",
        ["provider_subscription_id"],
    )
    op.create_unique_constraint(
        "uq_payment_transactions_provider_payment_id",
        "payment_transactions",
        ["provider_payment_id"],
    )


def downgrade() -> None:
    op.drop_constraint("uq_payment_transactions_provider_payment_id", "payment_transactions", type_="unique")
    op.drop_index("ix_payment_transactions_provider_subscription_id", table_name="payment_transactions")
    op.drop_column("payment_transactions", "provider_subscription_id")
    op.drop_index("ix_billing_webhook_events_provider_event_id", table_name="billing_webhook_events")
    op.drop_table("billing_webhook_events")