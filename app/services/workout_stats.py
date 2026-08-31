from __future__ import annotations

from datetime import date, datetime, timedelta
from typing import Any

from app.models.workout_log import WorkoutLog

RECORD_LIMIT = 3


def day_key(raw: str | None) -> str | None:
    value = (raw or "").strip()
    if len(value) >= 10 and value[4] == "-" and value[7] == "-":
        return value[:10]
    return value or None


def unique_day_keys(logs: list[WorkoutLog]) -> list[str]:
    keys: set[str] = set()
    for log in logs:
        key = day_key(log.date)
        if key:
            keys.add(key)
    return sorted(keys, reverse=True)


def current_streak(day_keys: list[str], today: date) -> int:
    if not day_keys:
        return 0
    today_key = today.isoformat()
    yesterday_key = (today - timedelta(days=1)).isoformat()
    latest = day_keys[0]
    if latest not in {today_key, yesterday_key}:
        return 0

    streak = 1
    expected = date.fromisoformat(latest) - timedelta(days=1)
    for key in day_keys[1:]:
        if key != expected.isoformat():
            break
        streak += 1
        expected -= timedelta(days=1)
    return streak


def week_bounds(today: date) -> tuple[date, date]:
    monday = today - timedelta(days=today.weekday())
    return monday, monday + timedelta(days=6)


def week_session_count(day_keys: list[str], today: date) -> int:
    monday, sunday = week_bounds(today)
    count = 0
    for key in day_keys:
        try:
            day = date.fromisoformat(key)
        except ValueError:
            continue
        if monday <= day <= sunday:
            count += 1
    return count


def format_ago(achieved_on: str, today: date) -> str:
    try:
        then = date.fromisoformat(achieved_on)
    except ValueError:
        return achieved_on
    days = (today - then).days
    if days <= 0:
        return "today"
    if days == 1:
        return "1 day ago"
    if days < 7:
        return f"{days} days ago"
    weeks = days // 7
    if weeks == 1:
        return "1 week ago"
    if days < 30:
        return f"{weeks} weeks ago"
    months = max(1, days // 30)
    return "1 month ago" if months == 1 else f"{months} months ago"


def format_duration(total_seconds: float) -> str:
    total = max(0, int(total_seconds))
    minutes, seconds = divmod(total, 60)
    if minutes == 0:
        return f"{seconds}s"
    if seconds == 0:
        return f"{minutes}m"
    return f"{minutes}m {seconds}s"


def format_weight(weight: float) -> str:
    if weight == int(weight):
        return f"{int(weight)}kg"
    return f"{weight}kg"


def format_primary(weight: float, reps: float, rep_label: str | None) -> str:
    if rep_label == "seconds":
        return format_duration(reps)
    if weight <= 0:
        value = int(reps) if reps == int(reps) else reps
        return f"{value} reps"
    return format_weight(weight)


def _finite(value: Any) -> float | None:
    try:
        number = float(value)
    except (TypeError, ValueError):
        return None
    if number != number:  # NaN
        return None
    return number


def _is_better(
    weight: float,
    reps: float,
    current: tuple[float, float] | None,
    rep_label: str | None,
) -> bool:
    if reps <= 0 or weight < 0:
        return False
    if current is None:
        return True
    current_weight, current_reps = current
    if rep_label == "seconds" or weight == 0:
        return reps > current_reps
    if weight > current_weight:
        return True
    if weight == current_weight and reps > current_reps:
        return True
    return False


def personal_records(
    logs: list[WorkoutLog],
    *,
    owner: str,
    today: date,
    rep_labels: dict[str, str] | None = None,
    limit: int = RECORD_LIMIT,
    record_user_id: str | None = None,
) -> list[dict[str, Any]]:
    labels = rep_labels or {}
    record_key = record_user_id or owner
    best: dict[str, dict[str, Any]] = {}

    for log in logs:
        achieved_on = day_key(log.date)
        if not achieved_on:
            continue
        for exercise in log.exercises or []:
            if not isinstance(exercise, dict):
                continue
            name = str(exercise.get("name") or "").strip()
            if not name:
                continue
            label = labels.get(name)
            for raw_set in exercise.get("sets") or []:
                if not isinstance(raw_set, dict):
                    continue
                weight = _finite(raw_set.get("weight"))
                reps = _finite(raw_set.get("reps"))
                if weight is None or reps is None:
                    continue
                current = best.get(name)
                current_tuple = (
                    (current["weight"], current["reps"]) if current else None
                )
                if not _is_better(weight, reps, current_tuple, label):
                    continue
                best[name] = {
                    "weight": weight,
                    "reps": reps,
                    "achieved_on": achieved_on,
                    "rep_label": label,
                }

    ranked = sorted(
        best.items(),
        key=lambda item: (-item[1]["weight"], -item[1]["reps"], item[0].lower()),
    )[:limit]

    records: list[dict[str, Any]] = []
    for name, pr in ranked:
        records.append(
            {
                "id": f"{record_key}:{name}",
                "owner": owner,
                "exercise": name,
                "primary": format_primary(pr["weight"], pr["reps"], pr["rep_label"]),
                "achieved_on": pr["achieved_on"],
                "ago": format_ago(pr["achieved_on"], today),
                "reactions": [],
            }
        )
    return records
