from __future__ import annotations

from sqlalchemy import delete
from sqlalchemy.orm import Session

from app.models.buddy import (
    BuddyBlock,
    BuddyCheer,
    BuddyLink,
    BuddyNudge,
    BuddyPresence,
    BuddyRecordReaction,
)
from app.models.exercise import Exercise
from app.models.library import UserLibrary
from app.models.preferences import UserPreferences
from app.models.profile import UserProfile
from app.models.schedule import UserSchedule
from app.models.session_template import SessionTemplate
from app.models.sync import SyncCursor
from app.models.user import User
from app.models.workout_log import WorkoutLog


class AccountService:
    @staticmethod
    def reset_cloud_data(db: Session, user_id: str) -> dict[str, int]:
        """Wipe app data for a user in Neon. Keeps the auth/user row."""
        links = db.execute(
            delete(BuddyLink).where(
                (BuddyLink.requester_id == user_id)
                | (BuddyLink.addressee_id == user_id)
            )
        ).rowcount
        blocks = db.execute(
            delete(BuddyBlock).where(
                (BuddyBlock.blocker_id == user_id)
                | (BuddyBlock.blocked_id == user_id)
            )
        ).rowcount
        presence = db.execute(
            delete(BuddyPresence).where(BuddyPresence.user_id == user_id)
        ).rowcount
        nudges = db.execute(
            delete(BuddyNudge).where(
                (BuddyNudge.from_user_id == user_id)
                | (BuddyNudge.to_user_id == user_id)
            )
        ).rowcount
        cheers = db.execute(
            delete(BuddyCheer).where(BuddyCheer.user_id == user_id)
        ).rowcount
        reactions = db.execute(
            delete(BuddyRecordReaction).where(
                (BuddyRecordReaction.user_id == user_id)
                | (BuddyRecordReaction.record_id.startswith(f"{user_id}:"))
            )
        ).rowcount
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
        profiles = db.execute(
            delete(UserProfile).where(UserProfile.user_id == user_id)
        ).rowcount
        user_templates = db.execute(
            delete(SessionTemplate).where(
                SessionTemplate.user_id == user_id,
                SessionTemplate.source == "user",
            )
        ).rowcount
        db.commit()
        return {
            "buddy_links_deleted": int(links or 0),
            "buddy_blocks_deleted": int(blocks or 0),
            "buddy_presence_deleted": int(presence or 0),
            "buddy_nudges_deleted": int(nudges or 0),
            "buddy_cheers_deleted": int(cheers or 0),
            "buddy_record_reactions_deleted": int(reactions or 0),
            "workouts_deleted": int(workouts or 0),
            "custom_exercises_deleted": int(customs or 0),
            "sync_cursors_deleted": int(cursors or 0),
            "schedules_deleted": int(schedules or 0),
            "libraries_deleted": int(libraries or 0),
            "preferences_deleted": int(prefs or 0),
            "profiles_deleted": int(profiles or 0),
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
