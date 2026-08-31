"""Import all ORM models so SQLAlchemy relationship strings resolve."""

from app.models.buddy import BuddyBlock, BuddyCheer, BuddyLink, BuddyNudge, BuddyPresence
from app.models.exercise import Exercise
from app.models.library import UserLibrary
from app.models.preferences import UserPreferences
from app.models.profile import UserProfile
from app.models.schedule import UserSchedule
from app.models.session_template import SessionTemplate
from app.models.sync import SyncCursor
from app.models.user import User
from app.models.workout_log import WorkoutLog

__all__ = [
    "BuddyBlock",
    "BuddyCheer",
    "BuddyLink",
    "BuddyNudge",
    "BuddyPresence",
    "Exercise",
    "UserLibrary",
    "UserPreferences",
    "UserProfile",
    "UserSchedule",
    "SessionTemplate",
    "SyncCursor",
    "User",
    "WorkoutLog",
]
