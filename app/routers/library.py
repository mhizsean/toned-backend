from fastapi import APIRouter, HTTPException, Query, status

from app.core.deps import CurrentUser, DbSession
from app.schemas.library import (
    LibraryItemRequest,
    LibraryReplaceRequest,
    LibraryResponse,
)
from app.services.library_service import LibraryService

router = APIRouter(prefix="/library", tags=["library"])


@router.get("", response_model=LibraryResponse)
def get_library(db: DbSession, user: CurrentUser) -> LibraryResponse:
    return LibraryService.get(db, user.id)


@router.put("", response_model=LibraryResponse)
def replace_library(
    body: LibraryReplaceRequest,
    db: DbSession,
    user: CurrentUser,
) -> LibraryResponse:
    """Full replace — use after login to sync local library up."""
    return LibraryService.replace(db, user.id, body)


@router.post("/items", response_model=LibraryResponse, status_code=status.HTTP_200_OK)
def add_library_item(
    body: LibraryItemRequest,
    db: DbSession,
    user: CurrentUser,
) -> LibraryResponse:
    return LibraryService.add_item(db, user.id, body)


@router.delete("/items", response_model=LibraryResponse)
def remove_library_item(
    db: DbSession,
    user: CurrentUser,
    id: str | None = Query(default=None, description="Catalogue exercise id"),
    name: str | None = Query(default=None, description="Exercise name"),
) -> LibraryResponse:
    if not id and not name:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail="Provide id and/or name query params",
        )
    return LibraryService.remove_item(db, user.id, item_id=id, name=name)
