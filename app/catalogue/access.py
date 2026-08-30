"""Who can see the full (uncurated) exercise catalogue."""

from __future__ import annotations

from app.config import get_settings

DEFAULT_FULL_ACCESS_EMAILS = frozenset({"seanseun.ss@gmail.com"})


def parse_full_access_emails(raw: str | None) -> set[str]:
    emails = {email.strip().lower() for email in (raw or "").split(",") if email.strip()}
    return set(DEFAULT_FULL_ACCESS_EMAILS) | emails


def has_full_catalogue_access(email: str | None) -> bool:
    if not email or not email.strip():
        return False
    allowed = parse_full_access_emails(get_settings().catalogue_full_access_emails)
    return email.strip().lower() in allowed
