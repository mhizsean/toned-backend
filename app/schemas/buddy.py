from __future__ import annotations

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
