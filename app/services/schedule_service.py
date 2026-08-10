from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy.orm import Session

from app.models.schedule import UserSchedule
from app.schemas.schedule import DaySchedule, ScheduleReplaceRequest, ScheduleResponse


def _dump_day(day: DaySchedule) -> dict:
    return day.model_dump(mode="json")


def _dump_schedule(schedule: dict[str, DaySchedule]) -> dict:
    return {day: _dump_day(payload) for day, payload in schedule.items()}


class ScheduleService:
    @staticmethod
    def get(db: Session, user_id: str) -> ScheduleResponse:
        row = db.get(UserSchedule, user_id)
        if row is None:
            return ScheduleResponse(schedule={}, updated_at=None)
        return ScheduleResponse(
            schedule={
                day: DaySchedule.model_validate(payload)
                for day, payload in (row.schedule or {}).items()
            },
            updated_at=row.updated_at,
        )

    @staticmethod
    def replace(db: Session, user_id: str, body: ScheduleReplaceRequest) -> ScheduleResponse:
        row = db.get(UserSchedule, user_id)
        payload = _dump_schedule(body.schedule)
        now = datetime.now(timezone.utc)
        if row is None:
            row = UserSchedule(user_id=user_id, schedule=payload, updated_at=now)
            db.add(row)
        else:
            row.schedule = payload
            row.updated_at = now
        db.commit()
        db.refresh(row)
        return ScheduleService.get(db, user_id)

    @staticmethod
    def upsert_day(db: Session, user_id: str, day: str, body: DaySchedule) -> ScheduleResponse:
        row = db.get(UserSchedule, user_id)
        now = datetime.now(timezone.utc)
        current = dict(row.schedule) if row and row.schedule else {}
        current[day] = _dump_day(body)
        if row is None:
            row = UserSchedule(user_id=user_id, schedule=current, updated_at=now)
            db.add(row)
        else:
            row.schedule = current
            row.updated_at = now
        db.commit()
        db.refresh(row)
        return ScheduleService.get(db, user_id)

    @staticmethod
    def clear_day(db: Session, user_id: str, day: str) -> ScheduleResponse:
        row = db.get(UserSchedule, user_id)
        if row is None or not row.schedule or day not in row.schedule:
            return ScheduleService.get(db, user_id)
        updated = dict(row.schedule)
        updated.pop(day, None)
        row.schedule = updated
        row.updated_at = datetime.now(timezone.utc)
        db.commit()
        db.refresh(row)
        return ScheduleService.get(db, user_id)
