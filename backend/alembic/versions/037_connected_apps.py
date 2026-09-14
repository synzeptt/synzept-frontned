"""create connected app account storage

Revision ID: 037_connected_apps
Revises: 037_conversation_schema_repair
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision = "037_connected_apps"
down_revision = "037_conversation_schema_repair"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "connected_app_accounts",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("provider", sa.String(80), nullable=False),
        sa.Column("status", sa.String(40), nullable=False, server_default="not_connected"),
        sa.Column("scopes", postgresql.JSONB(), nullable=False, server_default="[]"),
        sa.Column("encrypted_refresh_token", sa.Text(), nullable=True),
        sa.Column("encrypted_access_token", sa.Text(), nullable=True),
        sa.Column("access_token_expires_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("sync_token", sa.Text(), nullable=True),
        sa.Column("last_synced_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("last_error_code", sa.String(80), nullable=True),
        sa.Column("last_error_message", sa.Text(), nullable=True),
        sa.Column("provider_account_id", sa.String(240), nullable=True),
        sa.Column("metadata", postgresql.JSONB(), nullable=False, server_default="{}"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.UniqueConstraint("user_id", "provider", name="uq_connected_app_user_provider"),
    )
    op.create_index("ix_connected_app_accounts_user_id", "connected_app_accounts", ["user_id"])
    op.create_index("ix_connected_app_accounts_provider", "connected_app_accounts", ["provider"])
    op.create_index("ix_connected_app_accounts_status", "connected_app_accounts", ["status"])


def downgrade() -> None:
    op.drop_index("ix_connected_app_accounts_status", table_name="connected_app_accounts")
    op.drop_index("ix_connected_app_accounts_provider", table_name="connected_app_accounts")
    op.drop_index("ix_connected_app_accounts_user_id", table_name="connected_app_accounts")
    op.drop_table("connected_app_accounts")
