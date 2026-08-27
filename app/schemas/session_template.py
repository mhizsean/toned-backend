from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

from app.schemas.schedule import DayName, DayType, ScheduleResponse

TemplateCategory = Literal[
    "pre-workout",
    "cardio",
    "post-workout",
    "glutes-legs",
    "upper-body",
    "core-posture",
]
TEMPLATE_CATEGORY_PATTERN = (
    "^(pre-workout|cardio|post-workout|glutes-legs|upper-body|core-posture)$"
)
TemplateSource = Literal["system", "user"]
AddToPlanMode = Literal["merge", "replace"]


class TemplateExercise(BaseModel):
    id: str | None = Field(
        default=None,
        description="Catalogue exercise id when known",
    )
    name: str = Field(min_length=1, max_length=200)
    sets: int = Field(ge=1, le=50)
    reps: int = Field(ge=1, le=500)
    phase: str | None = Field(default=None, max_length=40)
    duration_min: int | None = Field(default=None, ge=1, le=180)
    level: float | None = Field(default=None, ge=0, le=50)
    effort_label: str | None = Field(default=None, max_length=24)
    note: str | None = Field(default=None, max_length=200)


class SessionTemplateCreate(BaseModel):
    """Save current block as a user session template (from day edit / builder)."""

    title: str = Field(min_length=1, max_length=120)
    emoji: str = Field(default="💪", max_length=16)
    description: str = Field(default="", max_length=500)
    focus: str = Field(min_length=1, max_length=80)
    category: TemplateCategory
    duration_min: int = Field(ge=1, le=180)
    exercises: list[TemplateExercise] = Field(min_length=1)
    id: str | None = Field(
        default=None,
        description="Optional id; server generates one if omitted",
    )
    origin_id: str | None = Field(
        default=None,
        description="System template id this user copy was saved from",
    )


class SessionTemplateUpdate(BaseModel):
    title: str | None = Field(default=None, min_length=1, max_length=120)
    emoji: str | None = Field(default=None, max_length=16)
    description: str | None = Field(default=None, max_length=500)
    focus: str | None = Field(default=None, min_length=1, max_length=80)
    category: TemplateCategory | None = None
    duration_min: int | None = Field(default=None, ge=1, le=180)
    exercises: list[TemplateExercise] | None = Field(default=None, min_length=1)


class AddTemplateToPlanRequest(BaseModel):
    day: DayName
    mode: AddToPlanMode = "merge"
    day_type: DayType = "gym"
    """Used when the day does not exist yet, or with mode=replace for type."""


class AddTemplateToPlanResponse(BaseModel):
    schedule: ScheduleResponse
    message: str


class SessionTemplateRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    title: str
    emoji: str
    description: str
    focus: str
    category: TemplateCategory
    source: TemplateSource
    duration_min: int
    sort_order: int
    exercises: list[TemplateExercise]
    user_id: str | None = None
    origin_id: str | None = None
    created_at: datetime
    updated_at: datetime


class SessionTemplateListResponse(BaseModel):
    items: list[SessionTemplateRead]
    total: int
