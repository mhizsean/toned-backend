from datetime import datetime

from pydantic import BaseModel, ConfigDict


class ExerciseBase(BaseModel):
    name: str
    category: str
    equipment: str
    rep_label: str = "reps"
    exercise_type: str | None = None
    tags: list[str] | None = None
    muscles: list[str]
    steps: list[str]
    tips: list[str]
    mistakes: list[str]
    is_custom: bool = False


class ExerciseCreate(ExerciseBase):
    id: str | None = None


class ExerciseRead(ExerciseBase):
    model_config = ConfigDict(from_attributes=True)

    id: str
    source: str = "internal"
    user_id: str | None = None
    created_at: datetime
    updated_at: datetime


class ExerciseListResponse(BaseModel):
    items: list[ExerciseRead]
    total: int
