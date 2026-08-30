import re

from sqlalchemy.orm import Session

USERNAME_PATTERN = re.compile(r"^[a-z][a-z0-9_]{2,19}$")
USERNAME_HINT = (
    "Username must be 3–20 characters, start with a letter, "
    "and use only letters, numbers, or underscores"
)


def normalize_username(raw: str) -> str:
    return raw.strip().lstrip("@").lower()


def is_valid_username(value: str) -> bool:
    return bool(USERNAME_PATTERN.fullmatch(value))


def username_taken(
    db: Session,
    username: str,
    exclude_user_id: str | None = None,
) -> bool:
    from app.models.user import User

    query = db.query(User).filter(User.username == username)
    if exclude_user_id:
        query = query.filter(User.id != exclude_user_id)
    return query.first() is not None
