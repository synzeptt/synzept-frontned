"""learning engine phase 4

Revision ID: 022
Revises: 021
Create Date: 2026-06-05
"""

from alembic import op
import sqlalchemy as sa

revision = "022"
down_revision = "021"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("learning_observations", sa.Column("source", sa.String(length=80), nullable=False, server_default="manual"))
    op.add_column("learning_observations", sa.Column("content", sa.Text(), nullable=False, server_default=""))
    op.add_column("learning_observations", sa.Column("status", sa.String(length=20), nullable=False, server_default="observed"))
    op.add_column(
        "learning_observations",
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.execute("UPDATE learning_observations SET source = source_type WHERE source_type IS NOT NULL")
    op.execute("UPDATE learning_observations SET content = signal WHERE signal IS NOT NULL")
    op.create_index("ix_learning_observations_source", "learning_observations", ["source"])
    op.create_index("ix_learning_observations_status", "learning_observations", ["status"])
    op.create_unique_constraint(
        "uq_learning_observations_user_source_content",
        "learning_observations",
        ["user_id", "source", "content"],
    )


def downgrade() -> None:
    op.drop_constraint("uq_learning_observations_user_source_content", "learning_observations", type_="unique")
    op.drop_index("ix_learning_observations_status", table_name="learning_observations")
    op.drop_index("ix_learning_observations_source", table_name="learning_observations")
    op.drop_column("learning_observations", "updated_at")
    op.drop_column("learning_observations", "status")
    op.drop_column("learning_observations", "content")
    op.drop_column("learning_observations", "source")
