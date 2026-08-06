from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "002"
down_revision: Union[str, None] = "001"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "exercises",
        sa.Column("body_part", sa.String(), nullable=False, server_default=""),
    )
    op.add_column("exercises", sa.Column("target", sa.String(), nullable=True))
    op.add_column("exercises", sa.Column(
        "media_id", sa.String(), nullable=True))
    op.add_column("exercises", sa.Column(
        "muscle_group", sa.String(), nullable=True))
    op.add_column("exercises", sa.Column(
        "secondary_muscles", sa.JSON(), nullable=True))
    op.add_column("exercises", sa.Column(
        "instructions", sa.JSON(), nullable=True))
    op.add_column("exercises", sa.Column(
        "instruction_steps", sa.JSON(), nullable=True))

    # Backfill body_part from category for any pre-existing rows
    op.execute(
        sa.text("UPDATE exercises SET body_part = category WHERE body_part = ''"))

    op.create_index(op.f("ix_exercises_body_part"),
                    "exercises", ["body_part"], unique=False)
    op.create_index(op.f("ix_exercises_category"),
                    "exercises", ["category"], unique=False)
    op.create_index(op.f("ix_exercises_equipment"),
                    "exercises", ["equipment"], unique=False)
    op.create_index(op.f("ix_exercises_target"),
                    "exercises", ["target"], unique=False)
    op.create_index(op.f("ix_exercises_media_id"),
                    "exercises", ["media_id"], unique=False)

    op.alter_column("exercises", "body_part", server_default=None)


def downgrade() -> None:
    op.drop_index(op.f("ix_exercises_media_id"), table_name="exercises")
    op.drop_index(op.f("ix_exercises_target"), table_name="exercises")
    op.drop_index(op.f("ix_exercises_equipment"), table_name="exercises")
    op.drop_index(op.f("ix_exercises_category"), table_name="exercises")
    op.drop_index(op.f("ix_exercises_body_part"), table_name="exercises")
    op.drop_column("exercises", "instruction_steps")
    op.drop_column("exercises", "instructions")
    op.drop_column("exercises", "secondary_muscles")
    op.drop_column("exercises", "muscle_group")
    op.drop_column("exercises", "media_id")
    op.drop_column("exercises", "target")
    op.drop_column("exercises", "body_part")
