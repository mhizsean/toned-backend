from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy.orm import Session

from app.models.library import UserLibrary
from app.schemas.library import (
    LibraryExercise,
    LibraryItemRequest,
    LibraryReplaceRequest,
    LibraryResponse,
)


def _key(item: LibraryExercise) -> str:
    if item.id:
        return f"id:{item.id}"
    return f"name:{item.name.strip().lower()}"


def _dump_items(items: list[LibraryExercise]) -> list[dict]:
    return [item.model_dump(mode="json") for item in items]


class LibraryService:
    @staticmethod
    def get(db: Session, user_id: str) -> LibraryResponse:
        row = db.get(UserLibrary, user_id)
        if row is None:
            return LibraryResponse(items=[], updated_at=None)
        return LibraryResponse(
            items=[LibraryExercise.model_validate(item) for item in (row.items or [])],
            updated_at=row.updated_at,
        )

    @staticmethod
    def replace(
        db: Session,
        user_id: str,
        body: LibraryReplaceRequest,
    ) -> LibraryResponse:
        # Dedupe while preserving order
        seen: set[str] = set()
        unique: list[LibraryExercise] = []
        for item in body.items:
            k = _key(item)
            if k in seen:
                continue
            seen.add(k)
            unique.append(item)

        payload = _dump_items(unique)
        now = datetime.now(timezone.utc)
        row = db.get(UserLibrary, user_id)
        if row is None:
            row = UserLibrary(user_id=user_id, items=payload, updated_at=now)
            db.add(row)
        else:
            row.items = payload
            row.updated_at = now
        db.commit()
        db.refresh(row)
        return LibraryService.get(db, user_id)

    @staticmethod
    def add_item(
        db: Session,
        user_id: str,
        body: LibraryItemRequest,
    ) -> LibraryResponse:
        item = LibraryExercise(id=body.id, name=body.name)

        current = LibraryService.get(db, user_id)
        items = list(current.items)
        k = _key(item)
        if any(_key(existing) == k for existing in items):
            return current
        # Prefer upgrading name-only entry when same name gets an id
        if item.id:
            items = [
                existing
                for existing in items
                if not (
                    existing.id is None
                    and existing.name.strip().lower() == item.name.strip().lower()
                )
            ]
        items.append(item)
        return LibraryService.replace(db, user_id, LibraryReplaceRequest(items=items))

    @staticmethod
    def remove_item(
        db: Session,
        user_id: str,
        *,
        item_id: str | None = None,
        name: str | None = None,
    ) -> LibraryResponse:
        if not item_id and not name:
            raise ValueError("Provide id or name")
        current = LibraryService.get(db, user_id)
        filtered: list[LibraryExercise] = []
        for existing in current.items:
            if item_id and existing.id == item_id:
                continue
            if name and existing.name.strip().lower() == name.strip().lower():
                continue
            filtered.append(existing)
        return LibraryService.replace(
            db, user_id, LibraryReplaceRequest(items=filtered)
        )
