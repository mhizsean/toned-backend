from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field, model_validator


class ExerciseBase(BaseModel):
    name: str
    category: str
    body_part: str | None = None
    equipment: str
    target: str | None = None
    media_id: str | None = None
    muscle_group: str | None = None
    secondary_muscles: list[str] | None = None
    instructions: dict | None = None
    instruction_steps: dict | None = None
    rep_label: str = "reps"
    exercise_type: str | None = None
    tags: list[str] | None = None
    muscles: list[str] = Field(default_factory=list)
    steps: list[str] = Field(default_factory=list)
    tips: list[str] = Field(default_factory=list)
    mistakes: list[str] = Field(default_factory=list)
    is_custom: bool = False

    @model_validator(mode="after")
    def default_body_part(self) -> "ExerciseBase":
        if not self.body_part:
            self.body_part = self.category
        return self


class ExerciseCreate(ExerciseBase):
    id: str | None = None


class ExerciseUpdate(BaseModel):
    """Partial update for the owner's custom exercises only."""

    name: str | None = None
    category: str | None = None
    body_part: str | None = None
    equipment: str | None = None
    target: str | None = None
    media_id: str | None = None
    muscle_group: str | None = None
    secondary_muscles: list[str] | None = None
    instructions: dict | None = None
    instruction_steps: dict | None = None
    rep_label: str | None = None
    exercise_type: str | None = None
    tags: list[str] | None = None
    muscles: list[str] | None = None
    steps: list[str] | None = None
    tips: list[str] | None = None
    mistakes: list[str] | None = None


class ExerciseRead(ExerciseBase):
    model_config = ConfigDict(from_attributes=True)

    id: str
    source: str = "exercises-dataset"
    user_id: str | None = None
    extra: dict | None = None
    created_at: datetime
    updated_at: datetime


class ExerciseListResponse(BaseModel):
    items: list[ExerciseRead]
    total: int
