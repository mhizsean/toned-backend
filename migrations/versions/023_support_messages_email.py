"""add email to support_messages

Revision ID: 023
Revises: 022
Create Date: 2026-09-10

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "023"
down_revision: Union[str, None] = "022"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "support_messages",
        sa.Column(
            "email",
            sa.String(length=320),
            nullable=False,
            server_default="",
        ),
    )
    op.alter_column("support_messages", "email", server_default=None)


def downgrade() -> None:
    op.drop_column("support_messages", "email")
