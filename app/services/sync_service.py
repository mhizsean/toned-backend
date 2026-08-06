from datetime import datetime, timezone
import uuid

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.sync import SyncCursor
from app.models.workout_log import WorkoutLog
from app.schemas.workout_log import WorkoutLogCreate


class SyncService:
    @staticmethod
    def push_workouts(
        db: Session,
        user_id: str,
        workouts: list[WorkoutLogCreate],
    ) -> list[WorkoutLog]:
        saved: list[WorkoutLog] = []
        for item in workouts:
            workout_id = item.id or str(uuid.uuid4())
            existing = db.get(WorkoutLog, workout_id)
            payload = {
                "date": item.date,
                "exercises": [ex.model_dump() for ex in item.exercises],
                "client_id": item.client_id or workout_id,
                "user_id": user_id,
            }
            if existing and existing.user_id == user_id:
                for key, value in payload.items():
                    setattr(existing, key, value)
                saved.append(existing)
            else:
                log = WorkoutLog(id=workout_id, **payload)
                db.add(log)
                saved.append(log)

        cursor = db.get(SyncCursor, user_id)
        now = datetime.now(timezone.utc)
        if cursor:
            cursor.last_synced_at = now
        else:
            db.add(SyncCursor(user_id=user_id, last_synced_at=now))

        db.commit()
        for row in saved:
            db.refresh(row)
        return saved

    @staticmethod
    def pull_workouts(
        db: Session,
        user_id: str,
        since: datetime | None = None,
    ) -> list[WorkoutLog]:
        query = select(WorkoutLog).where(WorkoutLog.user_id == user_id)
        if since:
            query = query.where(WorkoutLog.updated_at > since)
        return list(
            db.scalars(query.order_by(WorkoutLog.updated_at.asc())).all()
        )
