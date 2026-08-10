from fastapi import APIRouter

from app.core.deps import CurrentUser, DbSession
from app.schemas.preferences import PreferencesResponse, PreferencesUpdate
from app.services.preferences_service import PreferencesService

router = APIRouter(prefix="/preferences", tags=["preferences"])


@router.get("", response_model=PreferencesResponse)
def get_preferences(db: DbSession, user: CurrentUser) -> PreferencesResponse:
    return PreferencesService.get(db, user.id)


@router.patch("", response_model=PreferencesResponse)
def update_preferences(
    body: PreferencesUpdate,
    db: DbSession,
    user: CurrentUser,
) -> PreferencesResponse:
    """Update nudge timestamps and/or weight unit. Theme stays on-device."""
    return PreferencesService.update(db, user.id, body)
