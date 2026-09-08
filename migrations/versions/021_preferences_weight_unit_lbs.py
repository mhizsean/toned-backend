"""align preferences weight_unit with profile kg|lbs

Revision ID: 021
Revises: 020
Create Date: 2026-09-08

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "021"
down_revision: Union[str, None] = "020"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute(
        sa.text(
            "UPDATE user_preferences SET weight_unit = 'lbs' WHERE weight_unit = 'lb'"
        )
    )


def downgrade() -> None:
    op.execute(
        sa.text(
            "UPDATE user_preferences SET weight_unit = 'lb' WHERE weight_unit = 'lbs'"
        )
    )
