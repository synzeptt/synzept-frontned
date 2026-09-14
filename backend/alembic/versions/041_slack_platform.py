"""add Slack collaboration intelligence records

Revision ID: 041_slack_platform
Revises: 040_github_platform
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision = "041_slack_platform"
down_revision = "040_github_platform"
branch_labels = None
depends_on = None
UUID = postgresql.UUID(as_uuid=True)


def _base_columns() -> list[sa.Column]:
    return [
        sa.Column("id", UUID, primary_key=True),
        sa.Column("user_id", UUID, sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("connected_account_id", UUID, sa.ForeignKey("connected_app_accounts.id", ondelete="CASCADE"), nullable=False),
    ]


def _timestamps() -> list[sa.Column]:
    return [
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    ]


def upgrade() -> None:
    op.create_table(
        "slack_channels", *_base_columns(),
        sa.Column("provider_channel_id", sa.String(128), nullable=False),
        sa.Column("name", sa.String(300), nullable=False, server_default=""),
        sa.Column("channel_type", sa.String(40), nullable=False, server_default="channel"),
        sa.Column("is_private", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("is_member", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("is_archived", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("member_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("last_activity_at", sa.DateTime(timezone=True)),
        *_timestamps(), sa.UniqueConstraint("user_id", "provider_channel_id", name="uq_slack_channel"),
    )
    op.create_table(
        "slack_users", *_base_columns(),
        sa.Column("provider_user_id", sa.String(128), nullable=False),
        sa.Column("display_name", sa.String(300), nullable=False, server_default=""),
        sa.Column("real_name", sa.String(300), nullable=False, server_default=""),
        sa.Column("title", sa.String(300), nullable=False, server_default=""),
        sa.Column("is_bot", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("deleted", sa.Boolean(), nullable=False, server_default=sa.false()),
        *_timestamps(), sa.UniqueConstraint("user_id", "provider_user_id", name="uq_slack_user"),
    )
    op.create_table(
        "slack_conversation_activities", *_base_columns(),
        sa.Column("channel_id", UUID, sa.ForeignKey("slack_channels.id", ondelete="CASCADE"), nullable=False),
        sa.Column("provider_message_ts", sa.String(64), nullable=False),
        sa.Column("author_provider_user_id", sa.String(128), nullable=False, server_default=""),
        sa.Column("thread_ts", sa.String(64), nullable=False, server_default=""),
        sa.Column("reply_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("mention_user_ids", postgresql.JSONB(), nullable=False, server_default="[]"),
        sa.Column("participant_user_ids", postgresql.JSONB(), nullable=False, server_default="[]"),
        sa.Column("signal_types", postgresql.JSONB(), nullable=False, server_default="[]"),
        sa.Column("occurred_at", sa.DateTime(timezone=True)),
        sa.Column("is_direct", sa.Boolean(), nullable=False, server_default=sa.false()),
        *_timestamps(), sa.UniqueConstraint("channel_id", "provider_message_ts", name="uq_slack_activity"),
    )
    indexes = {
        "slack_channels": ("user_id", "connected_account_id", "provider_channel_id", "channel_type", "is_member", "is_archived", "last_activity_at"),
        "slack_users": ("user_id", "connected_account_id", "provider_user_id", "display_name", "deleted"),
        "slack_conversation_activities": ("user_id", "connected_account_id", "channel_id", "author_provider_user_id", "thread_ts", "occurred_at", "is_direct"),
    }
    for table, columns in indexes.items():
        for column in columns:
            op.create_index(f"ix_{table}_{column}", table, [column])


def downgrade() -> None:
    for table in ("slack_conversation_activities", "slack_users", "slack_channels"):
        op.drop_table(table)
