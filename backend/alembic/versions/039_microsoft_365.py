"""add Microsoft 365 provider records

Revision ID: 039_microsoft_365
Revises: 038_google_tasks_contacts
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision = "039_microsoft_365"
down_revision = "038_google_tasks_contacts"
branch_labels = None
depends_on = None

UUID = postgresql.UUID(as_uuid=True)


def _common() -> list[sa.Column]:
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
        "microsoft_mail_messages", *_common(),
        sa.Column("provider_message_id", sa.String(512), nullable=False),
        sa.Column("conversation_id", sa.String(512), nullable=False, server_default=""),
        sa.Column("sender_name", sa.String(300), nullable=False, server_default=""),
        sa.Column("sender_email", sa.String(320), nullable=False, server_default=""),
        sa.Column("received_at", sa.DateTime(timezone=True)),
        sa.Column("is_read", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("folder_id", sa.String(512), nullable=False, server_default=""),
        sa.Column("categories", postgresql.JSONB(), nullable=False, server_default="[]"),
        sa.Column("deleted", sa.Boolean(), nullable=False, server_default=sa.false()),
        *_timestamps(), sa.UniqueConstraint("user_id", "provider_message_id", name="uq_microsoft_mail_message"),
    )
    op.create_table(
        "microsoft_drive_items", *_common(),
        sa.Column("provider_item_id", sa.String(512), nullable=False),
        sa.Column("name", sa.String(500), nullable=False, server_default=""),
        sa.Column("mime_type", sa.String(240), nullable=False, server_default=""),
        sa.Column("modified_at", sa.DateTime(timezone=True)),
        sa.Column("shared", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("deleted", sa.Boolean(), nullable=False, server_default=sa.false()),
        *_timestamps(), sa.UniqueConstraint("user_id", "provider_item_id", name="uq_microsoft_drive_item"),
    )
    op.create_table(
        "microsoft_task_lists", *_common(),
        sa.Column("provider_list_id", sa.String(512), nullable=False),
        sa.Column("title", sa.String(300), nullable=False, server_default=""),
        *_timestamps(), sa.UniqueConstraint("user_id", "provider_list_id", name="uq_microsoft_task_list"),
    )
    op.create_table(
        "microsoft_tasks", *_common(),
        sa.Column("task_list_id", UUID, sa.ForeignKey("microsoft_task_lists.id", ondelete="CASCADE"), nullable=False),
        sa.Column("provider_task_id", sa.String(512), nullable=False),
        sa.Column("title", sa.String(500), nullable=False, server_default=""),
        sa.Column("status", sa.String(40), nullable=False, server_default="notStarted"),
        sa.Column("importance", sa.String(40), nullable=False, server_default="normal"),
        sa.Column("due_at", sa.DateTime(timezone=True)),
        sa.Column("completed_at", sa.DateTime(timezone=True)),
        sa.Column("recurrence", postgresql.JSONB(), nullable=False, server_default="{}"),
        sa.Column("provider_updated_at", sa.DateTime(timezone=True)),
        sa.Column("deleted", sa.Boolean(), nullable=False, server_default=sa.false()),
        *_timestamps(), sa.UniqueConstraint("user_id", "provider_task_id", name="uq_microsoft_task"),
    )
    op.create_table(
        "microsoft_contacts", *_common(),
        sa.Column("provider_contact_id", sa.String(512), nullable=False),
        sa.Column("display_name", sa.String(300), nullable=False, server_default=""),
        sa.Column("emails", postgresql.JSONB(), nullable=False, server_default="[]"),
        sa.Column("company", sa.String(300), nullable=False, server_default=""),
        sa.Column("job_title", sa.String(300), nullable=False, server_default=""),
        sa.Column("relationship_metadata", postgresql.JSONB(), nullable=False, server_default="{}"),
        sa.Column("provider_updated_at", sa.DateTime(timezone=True)),
        sa.Column("deleted", sa.Boolean(), nullable=False, server_default=sa.false()),
        *_timestamps(), sa.UniqueConstraint("user_id", "provider_contact_id", name="uq_microsoft_contact"),
    )
    indexes = {
        "microsoft_mail_messages": ("user_id", "connected_account_id", "provider_message_id", "conversation_id", "sender_email", "received_at", "is_read", "deleted"),
        "microsoft_drive_items": ("user_id", "connected_account_id", "provider_item_id", "modified_at", "deleted"),
        "microsoft_task_lists": ("user_id", "connected_account_id", "provider_list_id"),
        "microsoft_tasks": ("user_id", "connected_account_id", "task_list_id", "provider_task_id", "status", "due_at", "provider_updated_at", "deleted"),
        "microsoft_contacts": ("user_id", "connected_account_id", "provider_contact_id", "display_name", "provider_updated_at", "deleted"),
    }
    for table, columns in indexes.items():
        for column in columns:
            op.create_index(f"ix_{table}_{column}", table, [column])


def downgrade() -> None:
    for table in ("microsoft_contacts", "microsoft_tasks", "microsoft_task_lists", "microsoft_drive_items", "microsoft_mail_messages"):
        op.drop_table(table)
