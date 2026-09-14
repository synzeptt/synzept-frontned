"""add Microsoft Teams and Notion metadata records

Revision ID: 042_teams_notion
Revises: 041_slack_platform
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision = "042_teams_notion"
down_revision = "041_slack_platform"
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
        "microsoft_teams", *_base_columns(),
        sa.Column("provider_team_id", sa.String(512), nullable=False),
        sa.Column("display_name", sa.String(300), nullable=False, server_default=""),
        sa.Column("description", sa.Text(), nullable=False, server_default=""),
        sa.Column("is_archived", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("last_activity_at", sa.DateTime(timezone=True)),
        *_timestamps(), sa.UniqueConstraint("user_id", "provider_team_id", name="uq_microsoft_team"),
    )
    op.create_table(
        "microsoft_team_channels", *_base_columns(),
        sa.Column("team_id", UUID, sa.ForeignKey("microsoft_teams.id", ondelete="CASCADE"), nullable=False),
        sa.Column("provider_channel_id", sa.String(512), nullable=False),
        sa.Column("display_name", sa.String(300), nullable=False, server_default=""),
        sa.Column("membership_type", sa.String(40), nullable=False, server_default="standard"),
        sa.Column("last_activity_at", sa.DateTime(timezone=True)),
        *_timestamps(), sa.UniqueConstraint("team_id", "provider_channel_id", name="uq_microsoft_team_channel"),
    )
    op.create_table(
        "microsoft_team_memberships", *_base_columns(),
        sa.Column("team_id", UUID, sa.ForeignKey("microsoft_teams.id", ondelete="CASCADE"), nullable=False),
        sa.Column("provider_user_id", sa.String(512), nullable=False),
        sa.Column("display_name", sa.String(300), nullable=False, server_default=""),
        sa.Column("email", sa.String(320), nullable=False, server_default=""),
        sa.Column("roles", postgresql.JSONB(), nullable=False, server_default="[]"),
        *_timestamps(), sa.UniqueConstraint("team_id", "provider_user_id", name="uq_microsoft_team_membership"),
    )
    op.create_table(
        "microsoft_teams_activities", *_base_columns(),
        sa.Column("team_id", UUID, sa.ForeignKey("microsoft_teams.id", ondelete="CASCADE")),
        sa.Column("channel_id", UUID, sa.ForeignKey("microsoft_team_channels.id", ondelete="CASCADE")),
        sa.Column("provider_activity_id", sa.String(512), nullable=False),
        sa.Column("activity_type", sa.String(40), nullable=False, server_default="channel_message"),
        sa.Column("author_provider_user_id", sa.String(512), nullable=False, server_default=""),
        sa.Column("author_display_name", sa.String(300), nullable=False, server_default=""),
        sa.Column("reply_to_id", sa.String(512), nullable=False, server_default=""),
        sa.Column("mention_user_ids", postgresql.JSONB(), nullable=False, server_default="[]"),
        sa.Column("participant_names", postgresql.JSONB(), nullable=False, server_default="[]"),
        sa.Column("signal_types", postgresql.JSONB(), nullable=False, server_default="[]"),
        sa.Column("occurred_at", sa.DateTime(timezone=True)),
        sa.Column("metadata", postgresql.JSONB(), nullable=False, server_default="{}"),
        *_timestamps(), sa.UniqueConstraint("user_id", "provider_activity_id", name="uq_microsoft_teams_activity"),
    )
    op.create_table(
        "notion_resources", *_base_columns(),
        sa.Column("provider_resource_id", sa.String(128), nullable=False),
        sa.Column("resource_type", sa.String(40), nullable=False),
        sa.Column("title", sa.String(500), nullable=False, server_default=""),
        sa.Column("parent_provider_id", sa.String(128), nullable=False, server_default=""),
        sa.Column("parent_type", sa.String(80), nullable=False, server_default=""),
        sa.Column("provider_created_at", sa.DateTime(timezone=True)),
        sa.Column("provider_edited_at", sa.DateTime(timezone=True)),
        sa.Column("archived", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("metadata", postgresql.JSONB(), nullable=False, server_default="{}"),
        *_timestamps(), sa.UniqueConstraint("user_id", "provider_resource_id", name="uq_notion_resource"),
    )
    indexes = {
        "microsoft_teams": ("user_id", "connected_account_id", "provider_team_id", "is_archived", "last_activity_at"),
        "microsoft_team_channels": ("user_id", "connected_account_id", "team_id", "provider_channel_id", "last_activity_at"),
        "microsoft_team_memberships": ("user_id", "connected_account_id", "team_id", "provider_user_id", "display_name"),
        "microsoft_teams_activities": ("user_id", "connected_account_id", "team_id", "channel_id", "provider_activity_id", "activity_type", "author_provider_user_id", "reply_to_id", "occurred_at"),
        "notion_resources": ("user_id", "connected_account_id", "provider_resource_id", "resource_type", "title", "parent_provider_id", "provider_edited_at", "archived"),
    }
    for table, columns in indexes.items():
        for column in columns:
            op.create_index(f"ix_{table}_{column}", table, [column])


def downgrade() -> None:
    for table in ("notion_resources", "microsoft_teams_activities", "microsoft_team_memberships", "microsoft_team_channels", "microsoft_teams"):
        op.drop_table(table)
