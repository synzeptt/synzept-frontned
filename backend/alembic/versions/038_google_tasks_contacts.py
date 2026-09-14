"""add read-only Google Tasks and Contacts records

Revision ID: 038_google_tasks_contacts
Revises: 037_connected_apps
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision = "038_google_tasks_contacts"
down_revision = "037_connected_apps"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "google_task_lists",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("connected_account_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("connected_app_accounts.id", ondelete="CASCADE"), nullable=False),
        sa.Column("provider_list_id", sa.String(512), nullable=False),
        sa.Column("title", sa.String(300), nullable=False, server_default=""),
        sa.Column("provider_updated_at", sa.DateTime(timezone=True)),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.UniqueConstraint("user_id", "provider_list_id", name="uq_google_task_lists_provider_list"),
    )
    op.create_index("ix_google_task_lists_user_id", "google_task_lists", ["user_id"])
    op.create_index("ix_google_task_lists_connected_account_id", "google_task_lists", ["connected_account_id"])
    op.create_index("ix_google_task_lists_provider_list_id", "google_task_lists", ["provider_list_id"])
    op.create_table(
        "google_tasks",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("connected_account_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("connected_app_accounts.id", ondelete="CASCADE"), nullable=False),
        sa.Column("task_list_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("google_task_lists.id", ondelete="CASCADE"), nullable=False),
        sa.Column("provider_task_id", sa.String(512), nullable=False),
        sa.Column("provider_parent_id", sa.String(512)),
        sa.Column("title", sa.String(500), nullable=False, server_default=""),
        sa.Column("status", sa.String(40), nullable=False, server_default="needsAction"),
        sa.Column("due_at", sa.DateTime(timezone=True)),
        sa.Column("completed_at", sa.DateTime(timezone=True)),
        sa.Column("provider_updated_at", sa.DateTime(timezone=True)),
        sa.Column("position", sa.String(128), nullable=False, server_default=""),
        sa.Column("deleted", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.UniqueConstraint("user_id", "provider_task_id", name="uq_google_tasks_provider_task"),
    )
    for column in ("user_id", "connected_account_id", "task_list_id", "provider_task_id", "provider_parent_id", "status", "due_at", "provider_updated_at", "deleted"):
        op.create_index(f"ix_google_tasks_{column}", "google_tasks", [column])
    op.create_table(
        "google_contacts",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("connected_account_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("connected_app_accounts.id", ondelete="CASCADE"), nullable=False),
        sa.Column("resource_name", sa.String(512), nullable=False),
        sa.Column("etag", sa.String(512), nullable=False, server_default=""),
        sa.Column("display_name", sa.String(300), nullable=False, server_default=""),
        sa.Column("emails", postgresql.JSONB(), nullable=False, server_default="[]"),
        sa.Column("company", sa.String(300), nullable=False, server_default=""),
        sa.Column("job_title", sa.String(300), nullable=False, server_default=""),
        sa.Column("relationship_metadata", postgresql.JSONB(), nullable=False, server_default="{}"),
        sa.Column("provider_updated_at", sa.DateTime(timezone=True)),
        sa.Column("deleted", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.UniqueConstraint("user_id", "resource_name", name="uq_google_contacts_resource_name"),
    )
    for column in ("user_id", "connected_account_id", "resource_name", "display_name", "provider_updated_at", "deleted"):
        op.create_index(f"ix_google_contacts_{column}", "google_contacts", [column])


def downgrade() -> None:
    op.drop_table("google_contacts")
    op.drop_table("google_tasks")
    op.drop_table("google_task_lists")
