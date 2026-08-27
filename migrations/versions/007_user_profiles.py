"""add user_profiles table

Revision ID: 007
Revises: 006
Create Date: 2026-08-27

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "007"
down_revision: Union[str, None] = "006"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "user_profiles",
        sa.Column("user_id", sa.String(), nullable=False),
        sa.Column("name", sa.String(length=120), nullable=False, server_default=""),
        sa.Column("age", sa.String(length=8), nullable=False, server_default=""),
        sa.Column("gender", sa.String(length=32), nullable=True),
        sa.Column("goals", sa.JSON(), nullable=False),
        sa.Column("frequency", sa.String(length=32), nullable=True),
        sa.Column("experience", sa.String(length=32), nullable=True),
        sa.Column("session_length", sa.String(length=32), nullable=True),
        sa.Column("limitations", sa.Text(), nullable=False, server_default=""),
        sa.Column("height", sa.String(length=16), nullable=False, server_default=""),
        sa.Column("height_unit", sa.String(length=8), nullable=False, server_default="cm"),
        sa.Column("weight", sa.String(length=16), nullable=False, server_default=""),
        sa.Column("weight_unit", sa.String(length=8), nullable=False, server_default="kg"),
        sa.Column("body_goal", sa.String(length=200), nullable=False, server_default=""),
        sa.Column("body_goal_date", sa.String(length=64), nullable=False, server_default=""),
        sa.Column("train_location", sa.String(length=32), nullable=True),
        sa.Column("favourite_exercises", sa.JSON(), nullable=False),
        sa.Column("avatar_id", sa.String(length=80), nullable=True),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("user_id"),
    )


def downgrade() -> None:
    op.drop_table("user_profiles")
