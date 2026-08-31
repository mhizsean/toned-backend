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


class BuddyPresence(Base):
    """Live 'session started' ping so a buddy can see in-progress before a log is saved."""

    __tablename__ = "buddy_presence"

    user_id: Mapped[str] = mapped_column(
        String,
        ForeignKey("users.id", ondelete="CASCADE"),
        primary_key=True,
    )
    started_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
    )
    session_label: Mapped[str | None] = mapped_column(String(80), nullable=True)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
    )


class BuddyNudge(Base):
    """One row per nudge so the activity feed can show 'You nudged Dave'."""

    __tablename__ = "buddy_nudges"
    __table_args__ = (
        CheckConstraint(
            "from_user_id <> to_user_id",
            name="ck_buddy_nudges_not_self",
        ),
    )

    id: Mapped[str] = mapped_column(String, primary_key=True)
    from_user_id: Mapped[str] = mapped_column(
        String,
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    to_user_id: Mapped[str] = mapped_column(
        String,
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    day_key: Mapped[str] = mapped_column(String(10), nullable=False, index=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
    )


class BuddyCheer(Base):
    """Viewer 👏 on a feed item (stable activity id)."""

    __tablename__ = "buddy_cheers"

    activity_id: Mapped[str] = mapped_column(String, primary_key=True)
    user_id: Mapped[str] = mapped_column(
        String,
        ForeignKey("users.id", ondelete="CASCADE"),
        primary_key=True,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
    )


class BuddyRecordReaction(Base):
    """One emoji from one person on a PR card (`{user_id}:{exercise}`)."""

    __tablename__ = "buddy_record_reactions"
    __table_args__ = (
        CheckConstraint(
            "reaction IN ('clap', 'fire', 'flex', 'heart', 'hands')",
            name="ck_buddy_record_reactions_type",
        ),
    )

    record_id: Mapped[str] = mapped_column(String, primary_key=True)
    user_id: Mapped[str] = mapped_column(
        String,
        ForeignKey("users.id", ondelete="CASCADE"),
        primary_key=True,
    )
    reaction: Mapped[str] = mapped_column(String(16), primary_key=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
    )
