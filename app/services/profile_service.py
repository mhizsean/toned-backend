from __future__ import annotations

from datetime import datetime, timezone

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.models.profile import UserProfile
from app.models.user import User
from app.schemas.profile import ProfileResponse, ProfileUpdate
from app.services.avatar_service import is_valid_avatar_id
from app.utils.username import username_taken


def _to_response(row: UserProfile | None, username: str | None = None) -> ProfileResponse:
    if row is None:
        return ProfileResponse(username=username)
    return ProfileResponse(
        name=row.name or "",
        username=username,
        age=row.age or "",
        gender=row.gender,
        goals=list(row.goals or []),
        frequency=row.frequency,
        experience=row.experience,
        session_length=row.session_length,
        limitations=row.limitations or "",
        height=row.height or "",
        height_unit=row.height_unit or "cm",  # type: ignore[arg-type]
        weight=row.weight or "",
        weight_unit=row.weight_unit or "kg",  # type: ignore[arg-type]
        body_goal=row.body_goal or "",
        body_goal_date=row.body_goal_date or "",
        train_location=row.train_location,
        favourite_exercises=list(row.favourite_exercises or []),
        avatar_id=row.avatar_id,
        updated_at=row.updated_at,
    )


def _username_for(db: Session, user_id: str) -> str | None:
    user = db.get(User, user_id)
    return user.username if user else None


class ProfileService:
    @staticmethod
    def get(db: Session, user_id: str) -> ProfileResponse:
        return _to_response(db.get(UserProfile, user_id), _username_for(db, user_id))

    @staticmethod
    def _ensure_row(db: Session, user_id: str) -> UserProfile:
        row = db.get(UserProfile, user_id)
        if row is None:
            row = UserProfile(user_id=user_id)
            db.add(row)
            db.flush()
        return row

    @staticmethod
    def update(db: Session, user_id: str, body: ProfileUpdate) -> ProfileResponse:
        updates = body.model_dump(exclude_unset=True)
        if "avatar_id" in updates and not is_valid_avatar_id(updates["avatar_id"]):
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
                detail="Unknown avatar_id",
            )
        username = updates.pop("username", None)
        if username is not None:
            if username_taken(db, username, exclude_user_id=user_id):
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail="That username is taken",
                )
            user = db.get(User, user_id)
            if user is not None:
                user.username = username
        row = ProfileService._ensure_row(db, user_id)
        for key, value in updates.items():
            if isinstance(value, str) and key in {
                "name",
                "age",
                "limitations",
                "height",
                "weight",
                "body_goal",
                "body_goal_date",
            }:
                value = value.strip()
            setattr(row, key, value)
        row.updated_at = datetime.now(timezone.utc)
        db.commit()
        db.refresh(row)
        return _to_response(row, _username_for(db, user_id))
