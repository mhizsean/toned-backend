from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.utils.username import USERNAME_HINT, is_valid_username, normalize_username

HeightUnit = Literal["cm", "ft"]
WeightUnit = Literal["kg", "lbs"]


class AvatarOption(BaseModel):
    id: str
    url: str


class AvatarListResponse(BaseModel):
    avatars: list[AvatarOption]


class ProfileUpdate(BaseModel):
    name: str | None = Field(default=None, max_length=120)
    username: str | None = Field(default=None, min_length=3, max_length=21)
    age: str | None = Field(default=None, max_length=8)
    gender: str | None = Field(default=None, max_length=32)
    goals: list[str] | None = None
    frequency: str | None = Field(default=None, max_length=32)
    experience: str | None = Field(default=None, max_length=32)
    session_length: str | None = Field(default=None, max_length=32)
    limitations: str | None = Field(default=None, max_length=500)
    height: str | None = Field(default=None, max_length=16)
    height_unit: HeightUnit | None = None
    weight: str | None = Field(default=None, max_length=16)
    weight_unit: WeightUnit | None = None
    body_goal: str | None = Field(default=None, max_length=200)
    body_goal_date: str | None = Field(default=None, max_length=64)
    train_location: str | None = Field(default=None, max_length=32)
    favourite_exercises: list[str] | None = None
    avatar_id: str | None = Field(default=None, max_length=80)

    @field_validator("username")
    @classmethod
    def normalize_optional_username(cls, value: str | None) -> str | None:
        if value is None or not value.strip():
            return None
        username = normalize_username(value)
        if not is_valid_username(username):
            raise ValueError(USERNAME_HINT)
        return username


class ProfileResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    name: str = ""
    username: str | None = None
    age: str = ""
    gender: str | None = None
    goals: list[str] = Field(default_factory=list)
    frequency: str | None = None
    experience: str | None = None
    session_length: str | None = None
    limitations: str = ""
    height: str = ""
    height_unit: HeightUnit = "cm"
    weight: str = ""
    weight_unit: WeightUnit = "kg"
    body_goal: str = ""
    body_goal_date: str = ""
    train_location: str | None = None
    favourite_exercises: list[str] = Field(default_factory=list)
    avatar_id: str | None = None
    updated_at: datetime | None = None
