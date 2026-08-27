from __future__ import annotations

from pathlib import Path

from fastapi import HTTPException, status

AVATAR_DIR = Path(__file__).resolve().parent.parent / "static" / "profile_avatars"
AVATAR_IMAGE_TYPES = {".png": "image/png", ".jpg": "image/jpeg", ".jpeg": "image/jpeg", ".webp": "image/webp"}


def _avatar_files() -> list[Path]:
    if not AVATAR_DIR.exists():
        return []
    files = [
        path
        for path in AVATAR_DIR.iterdir()
        if path.is_file() and path.suffix.lower() in AVATAR_IMAGE_TYPES
    ]
    return sorted(files, key=lambda path: path.stem)


def list_avatar_ids() -> list[str]:
    return [path.stem for path in _avatar_files()]


def list_avatars() -> list[dict[str, str]]:
    return [
        {
            "id": path.stem,
            "url": f"/profile/avatars/{path.stem}",
        }
        for path in _avatar_files()
    ]


def resolve_avatar_file(avatar_id: str) -> tuple[Path, str]:
    if "/" in avatar_id or "\\" in avatar_id or ".." in avatar_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Avatar not found")
    for path in _avatar_files():
        if path.stem == avatar_id:
            return path, AVATAR_IMAGE_TYPES[path.suffix.lower()]
    raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Avatar not found")


def is_valid_avatar_id(avatar_id: str | None) -> bool:
    if avatar_id is None:
        return True
    return avatar_id in list_avatar_ids()
