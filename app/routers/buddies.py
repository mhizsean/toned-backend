from fastapi import APIRouter, Query

from app.core.deps import CurrentUser, DbSession
from app.schemas.buddy import BuddySearchResponse
from app.services.buddy_service import BuddyService

router = APIRouter(prefix="/buddies", tags=["buddies"])


@router.get("/search", response_model=BuddySearchResponse)
def search_buddies(
    db: DbSession,
    user: CurrentUser,
    q: str = Query(default="", max_length=80),
) -> BuddySearchResponse:
    """Find users by name, username prefix, or exact email. Never returns email."""
    return BuddyService.search(db, user.id, q)
