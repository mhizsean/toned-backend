"""persist on-device reminder toggles on the account

Revision ID: 019
Revises: 018
Create Date: 2026-09-08

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "019"
down_revision: Union[str, None] = "018"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

COLUMNS = (
    "notify_end_of_day",
    "notify_session_inactivity",
    "notify_rest_complete",
    "notify_morning_plan",
    "notify_streak_at_risk",
    "notify_weekly_plan",
)


def upgrade() -> None:
    for name in COLUMNS:
        op.add_column(
            "user_preferences",
            sa.Column(
                name,
                sa.Boolean(),
                nullable=False,
                server_default=sa.true(),
            ),
        )


def downgrade() -> None:
    for name in reversed(COLUMNS):
        op.drop_column("user_preferences", name)
