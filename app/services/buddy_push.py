from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

import httpx
from sqlalchemy.orm import Session

from app.config import get_settings
from app.models.buddy import BuddyPushToken
from app.models.preferences import UserPreferences
from app.models.profile import UserProfile
from app.services.buddy_activity import first_name

EXPO_PUSH_URL = "https://exp.host/--/api/v2/push/send"

PUSH_COPY = {
    "buddy-invite": (
        "Buddy invite",
        "{name} invited you to be their workout buddy",
    ),
    "buddy-accept": (
        "Buddy invite accepted",
        "{name} accepted your buddy invite",
    ),
    "buddy-decline": (
        "Buddy invite declined",
        "{name} declined your buddy invite",
    ),
    "buddy-nudge": (
        "Buddy nudge",
        "{name} nudged you to train",
    ),
    "buddy-cheer": (
        "Buddy cheer",
        "{name} cheered your workout",
    ),
    "buddy-completed": (
        "Buddy finished training",
        "{name} completed today's workout",
    ),
    "buddy-started": (
        "Buddy started training",
        "{name} started a workout",
    ),
    "buddy-reacted": (
        "Buddy reacted",
        "{name} reacted {emoji} to {exercise}",
    ),
}

# None = always send (invite lifecycle). Others follow the screenshot defaults.
NOTIFY_PREF_COLUMN = {
    "buddy-completed": "notify_buddy_completed",
    "buddy-started": "notify_buddy_started",
    "buddy-nudge": "notify_buddy_nudge",
    "buddy-eod-nudge": "notify_buddy_eod",
    "buddy-reacted": "notify_buddy_reacted",
}

NOTIFY_PREF_DEFAULT = {
    "notify_buddy_completed": True,
    "notify_buddy_started": False,
    "notify_buddy_nudge": True,
    "notify_buddy_eod": True,
    "notify_buddy_reacted": False,
}


class BuddyPushService:
    @staticmethod
    def register(db: Session, user_id: str, token: str) -> None:
        value = token.strip()
        if not value:
            return
        row = db.get(BuddyPushToken, value)
        if row is None:
            db.add(BuddyPushToken(token=value, user_id=user_id))
        else:
            row.user_id = user_id
            row.updated_at = datetime.now(timezone.utc)
        db.commit()

    @staticmethod
    def unregister(db: Session, user_id: str, token: str) -> None:
        row = db.get(BuddyPushToken, token.strip())
        if row is None or row.user_id != user_id:
            return
        db.delete(row)
        db.commit()

    @staticmethod
    def allowed(db: Session, user_id: str, event: str) -> bool:
        row = db.get(UserPreferences, user_id)
        if row is not None and not bool(row.notifications_enabled):
            return False
        column = NOTIFY_PREF_COLUMN.get(event)
        if column is None:
            return True
        default = NOTIFY_PREF_DEFAULT[column]
        if row is None:
            return default
        value = getattr(row, column, None)
        if value is None:
            return default
        return bool(value)

    @staticmethod
    def notify_event(
        db: Session,
        *,
        recipient_id: str,
        actor_id: str,
        event: str,
        extra: dict[str, Any] | None = None,
    ) -> None:
        if recipient_id == actor_id or event not in PUSH_COPY:
            return
        if not BuddyPushService.allowed(db, recipient_id, event):
            return
        title_template, body_template = PUSH_COPY[event]
        name = BuddyPushService._actor_name(db, actor_id)
        BuddyPushService.notify(
            db,
            recipient_id,
            title=title_template,
            body=body_template.format(name=name, **(extra or {})),
            data={"type": event},
        )

    @staticmethod
    def notify(
        db: Session,
        user_id: str,
        *,
        title: str,
        body: str,
        data: dict[str, Any] | None = None,
    ) -> None:
        tokens = [
            row.token
            for row in db.query(BuddyPushToken)
            .filter(BuddyPushToken.user_id == user_id)
            .all()
        ]
        if not tokens:
            return
        messages = [
            {
                "to": token,
                "title": title,
                "body": body,
                "sound": "default",
                "data": data or {},
            }
            for token in tokens
        ]
        BuddyPushService._post(messages)

    @staticmethod
    def _actor_name(db: Session, user_id: str) -> str:
        profile = db.get(UserProfile, user_id)
        return first_name(profile.name if profile else None, "Someone")

    @staticmethod
    def _post(messages: list[dict[str, Any]]) -> None:
        headers = {
            "Accept": "application/json",
            "Accept-Encoding": "gzip, deflate",
            "Content-Type": "application/json",
        }
        expo_token = getattr(get_settings(), "expo_access_token", "") or ""
        if expo_token:
            headers["Authorization"] = f"Bearer {expo_token}"
        try:
            with httpx.Client(timeout=10.0, trust_env=False) as client:
                client.post(EXPO_PUSH_URL, json=messages, headers=headers)
        except httpx.HTTPError:
            return
