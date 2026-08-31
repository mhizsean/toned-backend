from __future__ import annotations

import re

from sqlalchemy import func
from sqlalchemy.orm import Session

from app.models.profile import UserProfile
from app.models.user import User
from app.schemas.buddy import BuddyPersonPublic, BuddySearchResponse
from app.utils.username import normalize_username

EMAIL_PATTERN = re.compile(r"^[^\s@]+@[^\s@]+\.[^\s@]+$")
SEARCH_LIMIT = 20


def _is_email_query(raw: str) -> bool:
    return bool(EMAIL_PATTERN.fullmatch(raw.strip().lower()))


def _to_public_card(user: User, profile: UserProfile | None) -> BuddyPersonPublic:
    return BuddyPersonPublic(
        id=user.id,
        name=(profile.name if profile else "") or "",
        username=user.username,
        avatar_id=profile.avatar_id if profile else None,
        goals=list(profile.goals or []) if profile else [],
        experience=profile.experience if profile else None,
        frequency=profile.frequency if profile else None,
        invited_you=False,
    )


class BuddyService:
    @staticmethod
    def search(
        db: Session,
        viewer_id: str,
        query: str,
    ) -> BuddySearchResponse:
        q = query.strip()
        if not q:
            return BuddySearchResponse(users=[])

        if _is_email_query(q):
            rows = BuddyService._search_by_email(db, viewer_id, q)
        else:
            rows = BuddyService._search_by_username(db, viewer_id, q)

        return BuddySearchResponse(users=rows)

    @staticmethod
    def _excluded_ids(viewer_id: str) -> set[str]:
        """Self now; blocked / already-paired ids land here in step 2."""
        return {viewer_id}

    @staticmethod
    def _search_by_email(
        db: Session,
        viewer_id: str,
        email: str,
    ) -> list[BuddyPersonPublic]:
        excluded = BuddyService._excluded_ids(viewer_id)
        user = (
            db.query(User)
            .filter(func.lower(User.email) == email.strip().lower())
            .first()
        )
        if user is None or user.id in excluded:
            return []
        profile = db.get(UserProfile, user.id)
        return [_to_public_card(user, profile)]

    @staticmethod
    def _search_by_username(
        db: Session,
        viewer_id: str,
        raw: str,
    ) -> list[BuddyPersonPublic]:
        prefix = normalize_username(raw)
        if not prefix:
            return []

        excluded = BuddyService._excluded_ids(viewer_id)
        users = (
            db.query(User)
            .filter(
                User.id.notin_(excluded),
                User.username.isnot(None),
                User.username.ilike(f"{prefix}%"),
            )
            .order_by(User.username)
            .limit(SEARCH_LIMIT)
            .all()
        )
        if not users:
            return []

        profiles = {
            row.user_id: row
            for row in db.query(UserProfile)
            .filter(UserProfile.user_id.in_([user.id for user in users]))
            .all()
        }
        return [_to_public_card(user, profiles.get(user.id)) for user in users]
