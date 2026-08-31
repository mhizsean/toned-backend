from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import CheckConstraint, DateTime, ForeignKey, Integer, String, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base

if TYPE_CHECKING:
    from app.models.user import User


class UserPreferences(Base):
    """Cross-device product prefs (not UI theme)."""

    __tablename__ = "user_preferences"
    __table_args__ = (
        CheckConstraint(
            "buddy_nudge_limit IN (2, 3)",
            name="ck_user_preferences_buddy_nudge_limit",
        ),
    )

    user_id: Mapped[str] = mapped_column(
        String,
        ForeignKey("users.id", ondelete="CASCADE"),
        primary_key=True,
    )
    weight_unit: Mapped[str] = mapped_column(String, nullable=False, default="kg")
    buddy_nudge_limit: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=3,
        server_default="3",
    )
    signup_nudge_last_shown_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    signup_nudge_dismissed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
    )

    user: Mapped["User"] = relationship(back_populates="preferences")
