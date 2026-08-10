"""add session_templates table

Revision ID: 004
Revises: 003
Create Date: 2026-08-10

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "004"
down_revision: Union[str, None] = "003"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "session_templates",
        sa.Column("id", sa.String(), nullable=False),
        sa.Column("title", sa.String(), nullable=False),
        sa.Column("emoji", sa.String(), nullable=False),
        sa.Column("description", sa.String(), nullable=False),
        sa.Column("focus", sa.String(), nullable=False),
        sa.Column("category", sa.String(), nullable=False),
        sa.Column("source", sa.String(), nullable=False),
        sa.Column("duration_min", sa.Integer(), nullable=False),
        sa.Column("sort_order", sa.Integer(), nullable=False),
        sa.Column("exercises", sa.JSON(), nullable=False),
        sa.Column("user_id", sa.String(), nullable=True),
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
    op.create_index(op.f("ix_session_templates_category"), "session_templates", ["category"])
    op.create_index(op.f("ix_session_templates_focus"), "session_templates", ["focus"])
    op.create_index(op.f("ix_session_templates_source"), "session_templates", ["source"])
    op.create_index(op.f("ix_session_templates_user_id"), "session_templates", ["user_id"])


def downgrade() -> None:
    op.drop_index(op.f("ix_session_templates_user_id"), table_name="session_templates")
    op.drop_index(op.f("ix_session_templates_source"), table_name="session_templates")
    op.drop_index(op.f("ix_session_templates_focus"), table_name="session_templates")
    op.drop_index(op.f("ix_session_templates_category"), table_name="session_templates")
    op.drop_table("session_templates")
