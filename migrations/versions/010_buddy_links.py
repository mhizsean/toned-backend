"""buddy links and blocks

Revision ID: 010
Revises: 009
Create Date: 2026-08-31

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "010"
down_revision: Union[str, None] = "009"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "buddy_links",
        sa.Column("id", sa.String(), nullable=False),
        sa.Column("requester_id", sa.String(), nullable=False),
        sa.Column("addressee_id", sa.String(), nullable=False),
        sa.Column("status", sa.String(length=16), nullable=False),
        sa.Column("declined_seen_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.CheckConstraint(
            "requester_id <> addressee_id",
            name="ck_buddy_links_not_self",
        ),
        sa.CheckConstraint(
            "status IN ('pending', 'accepted', 'declined')",
            name="ck_buddy_links_status",
        ),
        sa.ForeignKeyConstraint(["requester_id"], ["users.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["addressee_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_buddy_links_requester_id", "buddy_links", ["requester_id"])
    op.create_index("ix_buddy_links_addressee_id", "buddy_links", ["addressee_id"])
    op.create_index("ix_buddy_links_status", "buddy_links", ["status"])

    op.create_table(
        "buddy_blocks",
        sa.Column("blocker_id", sa.String(), nullable=False),
        sa.Column("blocked_id", sa.String(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.CheckConstraint(
            "blocker_id <> blocked_id",
            name="ck_buddy_blocks_not_self",
        ),
        sa.ForeignKeyConstraint(["blocker_id"], ["users.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["blocked_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("blocker_id", "blocked_id"),
        sa.UniqueConstraint("blocker_id", "blocked_id", name="uq_buddy_blocks_pair"),
    )


def downgrade() -> None:
    op.drop_table("buddy_blocks")
    op.drop_index("ix_buddy_links_status", table_name="buddy_links")
    op.drop_index("ix_buddy_links_addressee_id", table_name="buddy_links")
    op.drop_index("ix_buddy_links_requester_id", table_name="buddy_links")
    op.drop_table("buddy_links")
