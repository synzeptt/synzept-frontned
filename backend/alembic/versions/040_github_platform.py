"""add GitHub development intelligence records

Revision ID: 040_github_platform
Revises: 039_microsoft_365
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision = "040_github_platform"
down_revision = "039_microsoft_365"
branch_labels = None
depends_on = None
UUID = postgresql.UUID(as_uuid=True)


def _entity_columns(repository_fk: bool = True) -> list[sa.Column]:
    columns = [
        sa.Column("id", UUID, primary_key=True),
        sa.Column("user_id", UUID, sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
    ]
    if repository_fk:
        columns.append(sa.Column("repository_id", UUID, sa.ForeignKey("github_repositories.id", ondelete="CASCADE"), nullable=False))
    return columns


def _timestamps() -> list[sa.Column]:
    return [sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False), sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False)]


def upgrade() -> None:
    op.create_table(
        "github_repositories", *_entity_columns(False),
        sa.Column("connected_account_id", UUID, sa.ForeignKey("connected_app_accounts.id", ondelete="CASCADE"), nullable=False),
        sa.Column("provider_repository_id", sa.String(128), nullable=False),
        sa.Column("node_id", sa.String(256), nullable=False, server_default=""),
        sa.Column("full_name", sa.String(500), nullable=False, server_default=""),
        sa.Column("visibility", sa.String(40), nullable=False, server_default="private"),
        sa.Column("default_branch", sa.String(300), nullable=False, server_default=""),
        sa.Column("last_activity_at", sa.DateTime(timezone=True)),
        sa.Column("archived", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("metadata", postgresql.JSONB(), nullable=False, server_default="{}"),
        *_timestamps(), sa.UniqueConstraint("user_id", "provider_repository_id", name="uq_github_repository"),
    )
    op.create_table(
        "github_issues", *_entity_columns(),
        sa.Column("number", sa.Integer(), nullable=False), sa.Column("title", sa.String(500), nullable=False, server_default=""),
        sa.Column("state", sa.String(40), nullable=False, server_default="OPEN"),
        sa.Column("labels", postgresql.JSONB(), nullable=False, server_default="[]"), sa.Column("assignees", postgresql.JSONB(), nullable=False, server_default="[]"),
        sa.Column("due_at", sa.DateTime(timezone=True)), sa.Column("provider_created_at", sa.DateTime(timezone=True)), sa.Column("provider_updated_at", sa.DateTime(timezone=True)), sa.Column("closed_at", sa.DateTime(timezone=True)),
        *_timestamps(), sa.UniqueConstraint("repository_id", "number", name="uq_github_issue"),
    )
    op.create_table(
        "github_pull_requests", *_entity_columns(),
        sa.Column("number", sa.Integer(), nullable=False), sa.Column("title", sa.String(500), nullable=False, server_default=""),
        sa.Column("state", sa.String(40), nullable=False, server_default="OPEN"), sa.Column("draft", sa.Boolean(), nullable=False, server_default=sa.false()), sa.Column("merged", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("review_status", sa.String(80), nullable=False, server_default="review_required"), sa.Column("review_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("provider_created_at", sa.DateTime(timezone=True)), sa.Column("provider_updated_at", sa.DateTime(timezone=True)), sa.Column("merged_at", sa.DateTime(timezone=True)), sa.Column("closed_at", sa.DateTime(timezone=True)),
        *_timestamps(), sa.UniqueConstraint("repository_id", "number", name="uq_github_pull_request"),
    )
    op.create_table(
        "github_commits", *_entity_columns(), sa.Column("sha", sa.String(80), nullable=False), sa.Column("message", sa.String(500), nullable=False, server_default=""), sa.Column("author_login", sa.String(200), nullable=False, server_default=""), sa.Column("committed_at", sa.DateTime(timezone=True)), *_timestamps(), sa.UniqueConstraint("repository_id", "sha", name="uq_github_commit"),
    )
    op.create_table(
        "github_releases", *_entity_columns(), sa.Column("provider_release_id", sa.String(128), nullable=False), sa.Column("name", sa.String(500), nullable=False, server_default=""), sa.Column("tag_name", sa.String(300), nullable=False, server_default=""), sa.Column("draft", sa.Boolean(), nullable=False, server_default=sa.false()), sa.Column("prerelease", sa.Boolean(), nullable=False, server_default=sa.false()), sa.Column("published_at", sa.DateTime(timezone=True)), *_timestamps(), sa.UniqueConstraint("repository_id", "provider_release_id", name="uq_github_release"),
    )
    indexes = {
        "github_repositories": ("user_id", "connected_account_id", "provider_repository_id", "node_id", "full_name", "last_activity_at", "archived"),
        "github_issues": ("user_id", "repository_id", "state", "due_at", "provider_updated_at"),
        "github_pull_requests": ("user_id", "repository_id", "state", "draft", "merged", "review_status", "provider_updated_at"),
        "github_commits": ("user_id", "repository_id", "sha", "committed_at"),
        "github_releases": ("user_id", "repository_id", "provider_release_id", "published_at"),
    }
    for table, columns in indexes.items():
        for column in columns:
            op.create_index(f"ix_{table}_{column}", table, [column])


def downgrade() -> None:
    for table in ("github_releases", "github_commits", "github_pull_requests", "github_issues", "github_repositories"):
        op.drop_table(table)
