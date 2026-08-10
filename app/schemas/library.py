from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class LibraryExercise(BaseModel):
    """Catalogue id when known; name always required (matches local library later)."""

    id: str | None = Field(
        default=None,
        description="Catalogue exercise id (e.g. '0001'); null for name-only / custom",
    )
    name: str = Field(min_length=1, max_length=200)


class LibraryReplaceRequest(BaseModel):
    items: list[LibraryExercise] = Field(default_factory=list)


class LibraryItemRequest(BaseModel):
    id: str | None = None
    name: str = Field(min_length=1, max_length=200)


class LibraryResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    items: list[LibraryExercise] = Field(default_factory=list)
    updated_at: datetime | None = None
