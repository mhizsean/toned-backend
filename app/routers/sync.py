from datetime import datetime, timezone

from fastapi import APIRouter
from pydantic import BaseModel, Field

from app.core.deps import CurrentUser, DbSession
from app.schemas.workout_log import WorkoutLogCreate, WorkoutLogRead
from app.services.sync_service import SyncService

router = APIRouter(prefix="/sync", tags=["sync"])


class SyncPushRequest(BaseModel):
    workouts: list[WorkoutLogCreate] = Field(default_factory=list)


class SyncPullResponse(BaseModel):
    workouts: list[WorkoutLogRead]
    server_time: datetime


class SyncPushResponse(BaseModel):
    workouts: list[WorkoutLogRead]
    server_time: datetime


@router.post("/push", response_model=SyncPushResponse)
def push_changes(
    payload: SyncPushRequest,
    db: DbSession,
    user: CurrentUser,
) -> SyncPushResponse:
    saved = SyncService.push_workouts(db, user.id, payload.workouts)
    return SyncPushResponse(
        workouts=[WorkoutLogRead.model_validate(row) for row in saved],
        server_time=datetime.now(timezone.utc),
    )


@router.get("/pull", response_model=SyncPullResponse)
def pull_changes(
    db: DbSession,
    user: CurrentUser,
    since: datetime | None = None,
) -> SyncPullResponse:
    workouts = SyncService.pull_workouts(db, user.id, since=since)
    return SyncPullResponse(
        workouts=[WorkoutLogRead.model_validate(row) for row in workouts],
        server_time=datetime.now(timezone.utc),
    )
