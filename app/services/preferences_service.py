from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy.orm import Session

from app.models.preferences import UserPreferences
from app.schemas.preferences import (
    PreferencesReplaceRequest,
    PreferencesResponse,
    PreferencesUpdate,
)


def _to_response(row: UserPreferences | None) -> PreferencesResponse:
    if row is None:
        return PreferencesResponse()
    return PreferencesResponse(
        weight_unit=row.weight_unit,  # type: ignore[arg-type]
        signup_nudge_last_shown_at=row.signup_nudge_last_shown_at,
        signup_nudge_dismissed_at=row.signup_nudge_dismissed_at,
        updated_at=row.updated_at,
    )


class PreferencesService:
    @staticmethod
    def get(db: Session, user_id: str) -> PreferencesResponse:
        return _to_response(db.get(UserPreferences, user_id))

    @staticmethod
    def _ensure_row(db: Session, user_id: str) -> UserPreferences:
        row = db.get(UserPreferences, user_id)
        if row is None:
            row = UserPreferences(user_id=user_id, weight_unit="kg")
            db.add(row)
            db.flush()
        return row

    @staticmethod
    def update(
        db: Session,
        user_id: str,
        body: PreferencesUpdate,
    ) -> PreferencesResponse:
        row = PreferencesService._ensure_row(db, user_id)
        updates = body.model_dump(exclude_unset=True)
        for key, value in updates.items():
            setattr(row, key, value)
        row.updated_at = datetime.now(timezone.utc)
        db.commit()
        db.refresh(row)
        return _to_response(row)

    @staticmethod
    def replace(
        db: Session,
        user_id: str,
        body: PreferencesReplaceRequest,
    ) -> PreferencesResponse:
        row = PreferencesService._ensure_row(db, user_id)
        row.weight_unit = body.weight_unit
        row.signup_nudge_last_shown_at = body.signup_nudge_last_shown_at
        row.signup_nudge_dismissed_at = body.signup_nudge_dismissed_at
        row.updated_at = datetime.now(timezone.utc)
        db.commit()
        db.refresh(row)
        return _to_response(row)
