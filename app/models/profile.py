from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import DateTime, ForeignKey, JSON, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base

if TYPE_CHECKING:
    from app.models.user import User


class UserProfile(Base):
    """Signed-in user profile (training prefs, metrics, selected avatar)."""

    __tablename__ = "user_profiles"

    user_id: Mapped[str] = mapped_column(
        String,
        ForeignKey("users.id", ondelete="CASCADE"),
        primary_key=True,
    )
    name: Mapped[str] = mapped_column(String(120), nullable=False, default="")
    age: Mapped[str] = mapped_column(String(8), nullable=False, default="")
    gender: Mapped[str | None] = mapped_column(String(32), nullable=True)
    goals: Mapped[list] = mapped_column(JSON, nullable=False, default=list)
    frequency: Mapped[str | None] = mapped_column(String(32), nullable=True)
    experience: Mapped[str | None] = mapped_column(String(32), nullable=True)
    session_length: Mapped[str | None] = mapped_column(String(32), nullable=True)
    limitations: Mapped[str] = mapped_column(Text, nullable=False, default="")
    height: Mapped[str] = mapped_column(String(16), nullable=False, default="")
    height_unit: Mapped[str] = mapped_column(String(8), nullable=False, default="cm")
    weight: Mapped[str] = mapped_column(String(16), nullable=False, default="")
    weight_unit: Mapped[str] = mapped_column(String(8), nullable=False, default="kg")
    body_goal: Mapped[str] = mapped_column(String(200), nullable=False, default="")
    body_goal_date: Mapped[str] = mapped_column(String(64), nullable=False, default="")
    train_location: Mapped[str | None] = mapped_column(String(32), nullable=True)
    favourite_exercises: Mapped[list] = mapped_column(JSON, nullable=False, default=list)
    avatar_id: Mapped[str | None] = mapped_column(String(80), nullable=True)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
    )

    user: Mapped["User"] = relationship(back_populates="profile")
