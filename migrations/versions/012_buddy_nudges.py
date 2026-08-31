"""buddy nudges

Revision ID: 012
Revises: 011
Create Date: 2026-08-31

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "012"
down_revision: Union[str, None] = "011"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "buddy_nudges",
        sa.Column("id", sa.String(), nullable=False),
        sa.Column("from_user_id", sa.String(), nullable=False),
        sa.Column("to_user_id", sa.String(), nullable=False),
        sa.Column("day_key", sa.String(length=10), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.CheckConstraint(
            "from_user_id <> to_user_id",
            name="ck_buddy_nudges_not_self",
        ),
        sa.ForeignKeyConstraint(["from_user_id"], ["users.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["to_user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_buddy_nudges_from_user_id", "buddy_nudges", ["from_user_id"])
    op.create_index("ix_buddy_nudges_to_user_id", "buddy_nudges", ["to_user_id"])
    op.create_index("ix_buddy_nudges_day_key", "buddy_nudges", ["day_key"])


def downgrade() -> None:
    op.drop_index("ix_buddy_nudges_day_key", table_name="buddy_nudges")
    op.drop_index("ix_buddy_nudges_to_user_id", table_name="buddy_nudges")
    op.drop_index("ix_buddy_nudges_from_user_id", table_name="buddy_nudges")
    op.drop_table("buddy_nudges")
