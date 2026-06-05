"""synzept knows you phase 1

Revision ID: 019
Revises: 018
Create Date: 2026-06-05
"""

from alembic import op
import sqlalchemy as sa

from app.database.types import JSONB, UUID


revision = "019"
down_revision = "010"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "user_understanding",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("user_id", UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("category", sa.String(length=50), nullable=False),
        sa.Column("title", sa.String(length=120), nullable=False),
        sa.Column("value", sa.Text(), nullable=False, server_default=""),
        sa.Column("source", sa.String(length=16), nullable=False, server_default="user"),
        sa.Column("confidence", sa.Float(), nullable=True),
        sa.Column("learned_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("personal", JSONB(), nullable=False, server_default=sa.text("'{}'")),
        sa.Column("professional", JSONB(), nullable=False, server_default=sa.text("'{}'")),
        sa.Column("goals", JSONB(), nullable=False, server_default=sa.text("'{}'")),
        sa.Column("preferences", JSONB(), nullable=False, server_default=sa.text("'{}'")),
        sa.Column("learning", JSONB(), nullable=False, server_default=sa.text("'{}'")),
        sa.Column("current_focus", JSONB(), nullable=False, server_default=sa.text("'{}'")),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.CheckConstraint("source IN ('user', 'learned')", name="ck_user_understanding_source"),
    )
    op.create_index("ix_user_understanding_user_id", "user_understanding", ["user_id"])
    op.create_index("ix_user_understanding_category", "user_understanding", ["category"])
    op.create_index("ix_user_understanding_source", "user_understanding", ["source"])

    op.create_table(
        "learning_suggestions",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("user_id", UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("title", sa.String(length=160), nullable=False),
        sa.Column("description", sa.Text(), nullable=False),
        sa.Column("confidence", sa.Float(), nullable=False, server_default="0.5"),
        sa.Column("status", sa.String(length=20), nullable=False, server_default="pending"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.CheckConstraint("status IN ('pending', 'accepted', 'ignored')", name="ck_learning_suggestions_status"),
    )
    op.create_index("ix_learning_suggestions_user_id", "learning_suggestions", ["user_id"])
    op.create_index("ix_learning_suggestions_status", "learning_suggestions", ["status"])


def downgrade() -> None:
    op.drop_index("ix_learning_suggestions_status", table_name="learning_suggestions")
    op.drop_index("ix_learning_suggestions_user_id", table_name="learning_suggestions")
    op.drop_table("learning_suggestions")
    op.drop_index("ix_user_understanding_source", table_name="user_understanding")
    op.drop_index("ix_user_understanding_category", table_name="user_understanding")
    op.drop_index("ix_user_understanding_user_id", table_name="user_understanding")
    op.drop_table("user_understanding")
