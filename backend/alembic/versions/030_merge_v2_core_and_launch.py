"""merge v2 core and launch migration branches

Revision ID: 030_merge_v2_core_and_launch
Revises: 018, 029_timeline_event_types
Create Date: 2026-06-12
"""

from typing import Sequence, Union


revision: str = "030_merge_v2_core_and_launch"
down_revision: Union[str, tuple[str, str]] = ("018", "029_timeline_event_types")
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass
