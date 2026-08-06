from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import DateTime, String, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base

if TYPE_CHECKING:
    from app.models.exercise import Exercise
    from app.models.workout_log import WorkoutLog


class User(Base):
    __tablename__ = "users"

    id: Mapped[str] = mapped_column(String, primary_key=True)
    email: Mapped[str | None] = mapped_column(String, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
    )

    workout_logs: Mapped[list["WorkoutLog"]] = relationship(
        back_populates="user",
        cascade="all, delete-orphan",
    )
    custom_exercises: Mapped[list["Exercise"]] = relationship(
        back_populates="user",
        cascade="all, delete-orphan",
    )
