from __future__ import annotations

from sqlalchemy import delete
from sqlalchemy.orm import Session

from app.models.exercise import Exercise
from app.models.library import UserLibrary
from app.models.preferences import UserPreferences
from app.models.schedule import UserSchedule
from app.models.session_template import SessionTemplate
from app.models.sync import SyncCursor
from app.models.user import User
from app.models.workout_log import WorkoutLog


class AccountService:
    @staticmethod
    def reset_cloud_data(db: Session, user_id: str) -> dict[str, int]:
        """Wipe app data for a user in Neon. Keeps the auth/user row."""
        workouts = db.execute(
            delete(WorkoutLog).where(WorkoutLog.user_id == user_id)
        ).rowcount
        customs = db.execute(
            delete(Exercise).where(
                Exercise.user_id == user_id,
                Exercise.is_custom.is_(True),
            )
        ).rowcount
        cursors = db.execute(
            delete(SyncCursor).where(SyncCursor.user_id == user_id)
        ).rowcount
        schedules = db.execute(
            delete(UserSchedule).where(UserSchedule.user_id == user_id)
        ).rowcount
        libraries = db.execute(
            delete(UserLibrary).where(UserLibrary.user_id == user_id)
        ).rowcount
        prefs = db.execute(
            delete(UserPreferences).where(UserPreferences.user_id == user_id)
        ).rowcount
        user_templates = db.execute(
            delete(SessionTemplate).where(
                SessionTemplate.user_id == user_id,
                SessionTemplate.source == "user",
            )
        ).rowcount
        db.commit()
        return {
            "workouts_deleted": int(workouts or 0),
            "custom_exercises_deleted": int(customs or 0),
            "sync_cursors_deleted": int(cursors or 0),
            "schedules_deleted": int(schedules or 0),
            "libraries_deleted": int(libraries or 0),
            "preferences_deleted": int(prefs or 0),
            "user_templates_deleted": int(user_templates or 0),
        }

    @staticmethod
    def delete_account_data(db: Session, user_id: str) -> dict[str, int]:
        """Permanently remove Neon rows for this user (including the users row)."""
        counts = AccountService.reset_cloud_data(db, user_id)
        deleted = db.execute(delete(User).where(User.id == user_id)).rowcount
        db.commit()
        counts["user_deleted"] = int(deleted or 0)
        return counts
