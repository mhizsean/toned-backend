from fastapi import APIRouter, HTTPException, Path, status

from app.core.deps import CurrentUser, DbSession
from app.schemas.schedule import (
    VALID_DAYS,
    DayName,
    DaySchedule,
    ScheduleReplaceRequest,
    ScheduleResponse,
)
from app.services.schedule_service import ScheduleService

router = APIRouter(prefix="/schedule", tags=["schedule"])


def _validate_day(day: str) -> DayName:
    if day not in VALID_DAYS:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail=f"Invalid day '{day}'. Expected one of {list(VALID_DAYS)}",
        )
    return day  # type: ignore[return-value]


@router.get("", response_model=ScheduleResponse)
def get_schedule(db: DbSession, user: CurrentUser) -> ScheduleResponse:
    return ScheduleService.get(db, user.id)


@router.put("", response_model=ScheduleResponse)
def replace_schedule(
    body: ScheduleReplaceRequest,
    db: DbSession,
    user: CurrentUser,
) -> ScheduleResponse:
    return ScheduleService.replace(db, user.id, body)


@router.put("/{day}", response_model=ScheduleResponse)
def upsert_day_schedule(
    body: DaySchedule,
    db: DbSession,
    user: CurrentUser,
    day: str = Path(..., examples=["Mon"]),
) -> ScheduleResponse:
    valid_day = _validate_day(day)
    return ScheduleService.upsert_day(db, user.id, valid_day, body)


@router.delete("/{day}", response_model=ScheduleResponse)
def clear_day_schedule(
    db: DbSession,
    user: CurrentUser,
    day: str = Path(..., examples=["Mon"]),
) -> ScheduleResponse:
    valid_day = _validate_day(day)
    return ScheduleService.clear_day(db, user.id, valid_day)
