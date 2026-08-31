import uuid

from fastapi import APIRouter, HTTPException, Query, status
from sqlalchemy import func, select

from app.core.deps import CurrentUser, DbSession
from app.models.workout_log import WorkoutLog
from app.services.buddy_service import BuddyService
from app.schemas.workout_log import (
    WorkoutLogCreate,
    WorkoutLogListResponse,
    WorkoutLogRead,
    WorkoutLogUpdate,
)

router = APIRouter(prefix="/workouts", tags=["workouts"])


def _serialize_log(log: WorkoutLog) -> WorkoutLogRead:
    return WorkoutLogRead.model_validate(log)


@router.get("", response_model=WorkoutLogListResponse)
def list_workouts(
    db: DbSession,
    user: CurrentUser,
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=200),
) -> WorkoutLogListResponse:
    base = select(WorkoutLog).where(WorkoutLog.user_id == user.id)
    total = db.scalar(select(func.count()).select_from(base.subquery())) or 0
    items = db.scalars(
        base.order_by(WorkoutLog.date.desc(), WorkoutLog.updated_at.desc())
        .offset(skip)
        .limit(limit)
    ).all()
    return WorkoutLogListResponse(
        items=[_serialize_log(item) for item in items],
        total=total,
    )


@router.get("/{workout_id}", response_model=WorkoutLogRead)
def get_workout(
    workout_id: str,
    db: DbSession,
    user: CurrentUser,
) -> WorkoutLogRead:
    log = db.get(WorkoutLog, workout_id)
    if log is None or log.user_id != user.id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Workout not found")
    return _serialize_log(log)


@router.post("", response_model=WorkoutLogRead, status_code=status.HTTP_201_CREATED)
def create_workout(
    data: WorkoutLogCreate,
    db: DbSession,
    user: CurrentUser,
) -> WorkoutLogRead:
    workout_id = data.id or str(uuid.uuid4())
    key = (data.date or "")[:10]
    before = BuddyService.workout_day_counts(db, user.id, {key})
    log = WorkoutLog(
        id=workout_id,
        user_id=user.id,
        client_id=data.client_id or workout_id,
        date=data.date,
        exercises=[ex.model_dump() for ex in data.exercises],
    )
    db.add(log)
    db.commit()
    db.refresh(log)
    BuddyService.on_workouts_saved(
        db, user.id, day_keys={key}, counts_before=before
    )
    return _serialize_log(log)


@router.patch("/{workout_id}", response_model=WorkoutLogRead)
def update_workout(
    workout_id: str,
    data: WorkoutLogUpdate,
    db: DbSession,
    user: CurrentUser,
) -> WorkoutLogRead:
    log = db.get(WorkoutLog, workout_id)
    if log is None or log.user_id != user.id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Workout not found")

    if data.date is not None:
        log.date = data.date
    if data.exercises is not None:
        log.exercises = [ex.model_dump() for ex in data.exercises]

    db.commit()
    db.refresh(log)
    return _serialize_log(log)


@router.delete("/{workout_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_workout(
    workout_id: str,
    db: DbSession,
    user: CurrentUser,
) -> None:
    log = db.get(WorkoutLog, workout_id)
    if log is None or log.user_id != user.id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Workout not found")
    db.delete(log)
    db.commit()
