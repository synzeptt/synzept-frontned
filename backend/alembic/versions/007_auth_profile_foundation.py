"""Auth profile foundation fields.

Revision ID: 007
Revises: 006
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "007"
down_revision: Union[str, None] = "006"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("users", sa.Column("is_verified", sa.Boolean(), server_default="false", nullable=False))
    op.add_column("user_profiles", sa.Column("display_name", sa.String(120), nullable=True))
    op.add_column(
        "user_profiles",
        sa.Column("onboarding_completed", sa.Boolean(), server_default="false", nullable=False),
    )
    op.add_column(
        "user_profiles",
        sa.Column("communication_style", sa.String(40), server_default="balanced", nullable=False),
    )
    op.add_column("user_profiles", sa.Column("timezone", sa.String(64), server_default="UTC", nullable=False))
    op.add_column(
        "user_profiles",
        sa.Column("profile_metadata", postgresql.JSONB(), server_default="{}", nullable=False),
    )
    op.execute(
        """
        UPDATE user_profiles
        SET display_name = users.display_name
        FROM users
        WHERE user_profiles.user_id = users.id
          AND user_profiles.display_name IS NULL
        """
    )


def downgrade() -> None:
    op.drop_column("user_profiles", "profile_metadata")
    op.drop_column("user_profiles", "timezone")
    op.drop_column("user_profiles", "communication_style")
    op.drop_column("user_profiles", "onboarding_completed")
    op.drop_column("user_profiles", "display_name")
    op.drop_column("users", "is_verified")
