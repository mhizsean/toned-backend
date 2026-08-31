from datetime import datetime
from typing import Literal

from sqlalchemy import CheckConstraint, DateTime, ForeignKey, String, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base

BuddyLinkStatus = Literal["pending", "accepted", "declined"]


class BuddyLink(Base):
    """One pending or accepted pair at a time; declined rows stay for the inviter toast."""

    __tablename__ = "buddy_links"
    __table_args__ = (
        CheckConstraint(
            "requester_id <> addressee_id",
            name="ck_buddy_links_not_self",
        ),
        CheckConstraint(
            "status IN ('pending', 'accepted', 'declined')",
            name="ck_buddy_links_status",
        ),
    )

    id: Mapped[str] = mapped_column(String, primary_key=True)
    requester_id: Mapped[str] = mapped_column(
        String,
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    addressee_id: Mapped[str] = mapped_column(
        String,
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    status: Mapped[str] = mapped_column(String(16), nullable=False, index=True)
    declined_seen_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
    )


class BuddyBlock(Base):
    __tablename__ = "buddy_blocks"
    __table_args__ = (
        UniqueConstraint("blocker_id", "blocked_id", name="uq_buddy_blocks_pair"),
        CheckConstraint(
            "blocker_id <> blocked_id",
            name="ck_buddy_blocks_not_self",
        ),
    )

    blocker_id: Mapped[str] = mapped_column(
        String,
        ForeignKey("users.id", ondelete="CASCADE"),
        primary_key=True,
    )
    blocked_id: Mapped[str] = mapped_column(
        String,
        ForeignKey("users.id", ondelete="CASCADE"),
        primary_key=True,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
    )
