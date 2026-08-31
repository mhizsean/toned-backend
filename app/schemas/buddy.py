from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field


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
