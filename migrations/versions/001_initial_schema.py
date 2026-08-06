"""initial schema

Revision ID: 001
Revises:
Create Date: 2026-07-03

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "001"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "users",
        sa.Column("id", sa.String(), nullable=False),
        sa.Column("email", sa.String(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_table(
        "exercises",
        sa.Column("id", sa.String(), nullable=False),
        sa.Column("name", sa.String(), nullable=False),
        sa.Column("category", sa.String(), nullable=False),
        sa.Column("equipment", sa.String(), nullable=False),
        sa.Column("rep_label", sa.String(), nullable=False),
        sa.Column("exercise_type", sa.String(), nullable=True),
        sa.Column("tags", sa.JSON(), nullable=True),
        sa.Column("muscles", sa.JSON(), nullable=False),
        sa.Column("steps", sa.JSON(), nullable=False),
        sa.Column("tips", sa.JSON(), nullable=False),
        sa.Column("mistakes", sa.JSON(), nullable=False),
        sa.Column("is_custom", sa.Boolean(), nullable=False),
        sa.Column("source", sa.String(), nullable=False),
        sa.Column("user_id", sa.String(), nullable=True),
        sa.Column("extra", sa.JSON(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_exercises_name"), "exercises", ["name"], unique=False)
    op.create_index(op.f("ix_exercises_user_id"), "exercises", ["user_id"], unique=False)
    op.create_table(
        "sync_cursors",
        sa.Column("user_id", sa.String(), nullable=False),
        sa.Column(
            "last_synced_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("user_id"),
    )
    op.create_table(
        "workout_logs",
        sa.Column("id", sa.String(), nullable=False),
        sa.Column("client_id", sa.String(), nullable=True),
        sa.Column("user_id", sa.String(), nullable=False),
        sa.Column("date", sa.String(), nullable=False),
        sa.Column("exercises", sa.JSON(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_workout_logs_client_id"), "workout_logs", ["client_id"], unique=False)
    op.create_index(op.f("ix_workout_logs_date"), "workout_logs", ["date"], unique=False)
    op.create_index(op.f("ix_workout_logs_user_id"), "workout_logs", ["user_id"], unique=False)


def downgrade() -> None:
    op.drop_index(op.f("ix_workout_logs_user_id"), table_name="workout_logs")
    op.drop_index(op.f("ix_workout_logs_date"), table_name="workout_logs")
    op.drop_index(op.f("ix_workout_logs_client_id"), table_name="workout_logs")
    op.drop_table("workout_logs")
    op.drop_table("sync_cursors")
    op.drop_index(op.f("ix_exercises_user_id"), table_name="exercises")
    op.drop_index(op.f("ix_exercises_name"), table_name="exercises")
    op.drop_table("exercises")
    op.drop_table("users")
