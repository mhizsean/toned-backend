from fastapi import APIRouter
from fastapi.responses import FileResponse

from app.core.deps import CurrentUser, DbSession
from app.schemas.profile import AvatarListResponse, ProfileResponse, ProfileUpdate
from app.services.avatar_service import list_avatars, resolve_avatar_file
from app.services.profile_service import ProfileService

router = APIRouter(prefix="/profile", tags=["profile"])


@router.get("/avatars", response_model=AvatarListResponse)
def get_avatars() -> AvatarListResponse:
    """Catalogue of selectable avatars. Add files under app/static/profile_avatars to grow the list."""
    return AvatarListResponse(avatars=list_avatars())


@router.get("/avatars/{avatar_id}")
def get_avatar_image(avatar_id: str) -> FileResponse:
    path, media_type = resolve_avatar_file(avatar_id)
    return FileResponse(path, media_type=media_type)


@router.get("", response_model=ProfileResponse)
def get_profile(db: DbSession, user: CurrentUser) -> ProfileResponse:
    return ProfileService.get(db, user.id)


@router.patch("", response_model=ProfileResponse)
def update_profile(
    body: ProfileUpdate,
    db: DbSession,
    user: CurrentUser,
) -> ProfileResponse:
    return ProfileService.update(db, user.id, body)
