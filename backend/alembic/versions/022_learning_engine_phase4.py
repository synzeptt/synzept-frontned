"""learning engine phase 4

Revision ID: 022
Revises: 021
Create Date: 2026-06-05
"""

from alembic import op
import sqlalchemy as sa

from app.database.types import UUID


revision = "022"
down_revision = "021"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "learning_observations",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("user_id", UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("source", sa.String(length=80), nullable=False, server_default="manual"),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column("status", sa.String(length=20), nullable=False, server_default="observed"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.UniqueConstraint("user_id", "source", "content", name="uq_learning_observations_user_source_content"),
    )
    op.create_index("ix_learning_observations_user_id", "learning_observations", ["user_id"])
    op.create_index("ix_learning_observations_source", "learning_observations", ["source"])
    op.create_index("ix_learning_observations_status", "learning_observations", ["status"])


def downgrade() -> None:
    op.drop_index("ix_learning_observations_status", table_name="learning_observations")
    op.drop_index("ix_learning_observations_source", table_name="learning_observations")
    op.drop_index("ix_learning_observations_user_id", table_name="learning_observations")
    op.drop_table("learning_observations")
