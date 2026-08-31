"""buddy notification toggles and end-of-day nudge log

Revision ID: 016
Revises: 015
Create Date: 2026-08-31

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "016"
down_revision: Union[str, None] = "015"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "user_preferences",
        sa.Column(
            "notify_buddy_completed",
            sa.Boolean(),
            nullable=False,
            server_default=sa.true(),
        ),
    )
    op.add_column(
        "user_preferences",
        sa.Column(
            "notify_buddy_started",
            sa.Boolean(),
            nullable=False,
            server_default=sa.false(),
        ),
    )
    op.add_column(
        "user_preferences",
        sa.Column(
            "notify_buddy_nudge",
            sa.Boolean(),
            nullable=False,
            server_default=sa.true(),
        ),
    )
    op.add_column(
        "user_preferences",
        sa.Column(
            "notify_buddy_eod",
            sa.Boolean(),
            nullable=False,
            server_default=sa.true(),
        ),
    )
    op.add_column(
        "user_preferences",
        sa.Column(
            "notify_buddy_reacted",
            sa.Boolean(),
            nullable=False,
            server_default=sa.false(),
        ),
    )
    op.create_table(
        "buddy_eod_nudges",
        sa.Column("id", sa.String(), nullable=False),
        sa.Column("user_id", sa.String(), nullable=False),
        sa.Column("day_key", sa.String(length=10), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("user_id", "day_key", name="uq_buddy_eod_nudges_day"),
    )
    op.create_index(
        "ix_buddy_eod_nudges_user_id",
        "buddy_eod_nudges",
        ["user_id"],
    )


def downgrade() -> None:
    op.drop_index("ix_buddy_eod_nudges_user_id", table_name="buddy_eod_nudges")
    op.drop_table("buddy_eod_nudges")
    op.drop_column("user_preferences", "notify_buddy_reacted")
    op.drop_column("user_preferences", "notify_buddy_eod")
    op.drop_column("user_preferences", "notify_buddy_nudge")
    op.drop_column("user_preferences", "notify_buddy_started")
    op.drop_column("user_preferences", "notify_buddy_completed")
