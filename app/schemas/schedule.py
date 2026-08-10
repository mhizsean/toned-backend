from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator

DayName = Literal["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]
DayType = Literal["gym", "home", "rest"]

VALID_DAYS = ("Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun")


class ScheduledExercise(BaseModel):
    """Catalogue id when known; name always required for display / start workout."""

    id: str | None = Field(
        default=None,
        description="Catalogue exercise id (e.g. '0001'); null for custom-only names",
    )
    name: str = Field(min_length=1, max_length=200)


class DaySchedule(BaseModel):
    type: DayType
    focuses: list[str] = Field(default_factory=list)
    exercises: list[ScheduledExercise] = Field(default_factory=list)


class ScheduleReplaceRequest(BaseModel):
    schedule: dict[str, DaySchedule] = Field(default_factory=dict)

    @field_validator("schedule")
    @classmethod
    def validate_day_keys(cls, value: dict[str, DaySchedule]) -> dict[str, DaySchedule]:
        invalid = [key for key in value if key not in VALID_DAYS]
        if invalid:
            raise ValueError(f"Invalid day keys: {invalid}. Expected one of {list(VALID_DAYS)}")
        return value


class ScheduleResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    schedule: dict[str, DaySchedule] = Field(default_factory=dict)
    updated_at: datetime | None = None
