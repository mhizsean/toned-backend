"""buddy push tokens and daily nudge cap

Revision ID: 015
Revises: 014
Create Date: 2026-08-31

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "015"
down_revision: Union[str, None] = "014"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "user_preferences",
        sa.Column(
            "buddy_nudge_limit",
            sa.Integer(),
            nullable=False,
            server_default="3",
        ),
    )
    op.create_check_constraint(
        "ck_user_preferences_buddy_nudge_limit",
        "user_preferences",
        "buddy_nudge_limit IN (2, 3)",
    )
    op.create_table(
        "buddy_push_tokens",
        sa.Column("token", sa.String(length=200), nullable=False),
        sa.Column("user_id", sa.String(), nullable=False),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("token"),
    )
    op.create_index(
        "ix_buddy_push_tokens_user_id",
        "buddy_push_tokens",
        ["user_id"],
    )


def downgrade() -> None:
    op.drop_index("ix_buddy_push_tokens_user_id", table_name="buddy_push_tokens")
    op.drop_table("buddy_push_tokens")
    op.drop_constraint(
        "ck_user_preferences_buddy_nudge_limit",
        "user_preferences",
        type_="check",
    )
    op.drop_column("user_preferences", "buddy_nudge_limit")
