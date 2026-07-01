"""synzept knows you phase 1

Revision ID: 019
Revises: 018
Create Date: 2026-06-05
"""

from alembic import op
import sqlalchemy as sa

from app.database.types import JSONB


revision = "019"
down_revision = "018"
branch_labels = None
depends_on = None


def upgrade() -> None:
    for column in (
        "personal",
        "professional",
        "goals",
        "preferences",
        "learning",
        "current_focus",
    ):
        op.add_column("user_understanding", sa.Column(column, JSONB(), nullable=False, server_default=sa.text("'{}'")))

    op.add_column(
        "learning_suggestions",
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )


def downgrade() -> None:
    op.drop_column("learning_suggestions", "updated_at")
    for column in (
        "current_focus",
        "learning",
        "preferences",
        "goals",
        "professional",
        "personal",
    ):
        op.drop_column("user_understanding", column)
