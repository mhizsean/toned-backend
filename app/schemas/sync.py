from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, Field

from app.schemas.exercise import ExerciseCreate, ExerciseRead
from app.schemas.library import LibraryExercise, LibraryResponse
from app.schemas.preferences import PreferencesReplaceRequest, PreferencesResponse
from app.schemas.schedule import DaySchedule, ScheduleResponse
from app.schemas.session_template import SessionTemplateCreate, SessionTemplateRead
from app.schemas.workout_log import WorkoutLogCreate, WorkoutLogRead


class SyncPushRequest(BaseModel):
    """
    Push local changes. Omitted sections are left unchanged on the server.
    schedule / library / preferences are full snapshots when provided (last-write-wins).
    """

    workouts: list[WorkoutLogCreate] = Field(default_factory=list)
    schedule: dict[str, DaySchedule] | None = None
    library: list[LibraryExercise] | None = None
    preferences: PreferencesReplaceRequest | None = None
    custom_exercises: list[ExerciseCreate] = Field(default_factory=list)
    templates: list[SessionTemplateCreate] = Field(default_factory=list)


class SyncPushResponse(BaseModel):
    workouts: list[WorkoutLogRead] = Field(default_factory=list)
    schedule: ScheduleResponse | None = None
    library: LibraryResponse | None = None
    preferences: PreferencesResponse | None = None
    custom_exercises: list[ExerciseRead] = Field(default_factory=list)
    templates: list[SessionTemplateRead] = Field(default_factory=list)
    server_time: datetime


class SyncPullResponse(BaseModel):
    workouts: list[WorkoutLogRead] = Field(default_factory=list)
    schedule: ScheduleResponse
    library: LibraryResponse
    preferences: PreferencesResponse
    custom_exercises: list[ExerciseRead] = Field(default_factory=list)
    templates: list[SessionTemplateRead] = Field(default_factory=list)
    server_time: datetime
