from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class WorkoutSetSchema(BaseModel):
    weight: float
    reps: float


class SessionExerciseSchema(BaseModel):
    name: str
    sets: list[WorkoutSetSchema]


class WorkoutLogBase(BaseModel):
    date: str
    exercises: list[SessionExerciseSchema]
    client_id: str | None = None


class WorkoutLogCreate(WorkoutLogBase):
    id: str | None = None


class WorkoutLogUpdate(BaseModel):
    date: str | None = None
    exercises: list[SessionExerciseSchema] | None = None


class WorkoutLogRead(WorkoutLogBase):
    model_config = ConfigDict(from_attributes=True)

    id: str
    user_id: str
    created_at: datetime
    updated_at: datetime


class WorkoutLogListResponse(BaseModel):
    items: list[WorkoutLogRead]
    total: int
