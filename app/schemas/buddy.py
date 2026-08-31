from __future__ import annotations

from datetime import datetime
from typing import Literal, Self

from pydantic import BaseModel, ConfigDict, Field, model_validator

BuddyViewStatus = Literal["none", "outgoing", "incoming", "active"]


class BuddyPersonPublic(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    name: str = ""
    username: str | None = None
    avatar_id: str | None = None
    goals: list[str] = Field(default_factory=list)
    experience: str | None = None
    frequency: str | None = None
    invited_you: bool = False


class BuddySearchResponse(BaseModel):
    users: list[BuddyPersonPublic] = Field(default_factory=list)


class BuddyInviteRequest(BaseModel):
    email: str | None = None
    username: str | None = None

    @model_validator(mode="after")
    def exactly_one_target(self) -> Self:
        email = (self.email or "").strip()
        username = (self.username or "").strip()
        if bool(email) == bool(username):
            raise ValueError("Provide exactly one of email or username")
        self.email = email or None
        self.username = username or None
        return self


class BuddyBlockRequest(BaseModel):
    user_id: str | None = None


class BuddyStateResponse(BaseModel):
    status: BuddyViewStatus
    person: BuddyPersonPublic | None = None
    invite_id: str | None = None
    declined_notice: bool = False


BuddyTrainingStatus = Literal["not_started", "in_progress", "completed"]
BuddyRecordOwner = Literal["you", "buddy"]
BuddyPresenceStatus = Literal["started", "finished"]
BuddyReaction = Literal["clap", "fire", "flex", "heart", "hands"]
BUDDY_REACTIONS: tuple[BuddyReaction, ...] = (
    "clap",
    "fire",
    "flex",
    "heart",
    "hands",
)


class BuddyHomeRecord(BaseModel):
    id: str
    owner: BuddyRecordOwner
    exercise: str
    primary: str
    achieved_on: str
    ago: str
    reactions: list[BuddyReaction] = Field(default_factory=list)


class BuddyHomeResponse(BaseModel):
    person: BuddyPersonPublic
    training_status: BuddyTrainingStatus
    session_label: str = ""
    updated_at: datetime | None = None
    streak_days: int = 0
    your_week_sessions: int = 0
    buddy_week_sessions: int = 0
    your_records: list[BuddyHomeRecord] = Field(default_factory=list)
    buddy_records: list[BuddyHomeRecord] = Field(default_factory=list)
    nudges_used: int = 0
    nudges_left: int = 3
    nudge_limit: int = 3


class BuddyPresenceRequest(BaseModel):
    status: BuddyPresenceStatus
    session_label: str | None = None


class BuddyNudgeResponse(BaseModel):
    used: int
    left: int
    limit: int = 3


BuddyActivityKind = Literal["completed", "nudge", "started", "pr", "both"]
BuddyActivitySection = Literal["today", "week"]


class BuddyActivityItem(BaseModel):
    id: str
    section: BuddyActivitySection
    time_label: str
    kind: BuddyActivityKind
    title: str
    detail: str | None = None
    can_cheer: bool = False
    cheered: bool = False


class BuddyActivityResponse(BaseModel):
    items: list[BuddyActivityItem] = Field(default_factory=list)


class BuddyCheerResponse(BaseModel):
    id: str
    cheered: bool = True


class BuddyRecordReactionsRequest(BaseModel):
    reaction: BuddyReaction


class BuddyRecordReactionsResponse(BaseModel):
    id: str
    reactions: list[BuddyReaction] = Field(default_factory=list)
