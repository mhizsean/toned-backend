from __future__ import annotations

from collections import defaultdict
from datetime import date, datetime, time, timezone
from typing import Any

from app.models.buddy import BuddyNudge, BuddyPresence
from app.models.workout_log import WorkoutLog
from app.schemas.buddy import BuddyActivityItem
from app.services.workout_stats import (
    day_key,
    personal_records,
    week_bounds,
)

WEEKDAYS = ("Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun")


def first_name(name: str | None, fallback: str = "them") -> str:
    first = (name or "").strip().split()[:1]
    return first[0] if first else fallback


def as_utc(value: datetime | None) -> datetime | None:
    if value is None:
        return None
    if value.tzinfo is None:
        return value.replace(tzinfo=timezone.utc)
    return value


def clock_label(value: datetime) -> str:
    hour12 = value.hour % 12 or 12
    suffix = "AM" if value.hour < 12 else "PM"
    return f"{hour12}:{value:%M} {suffix}"


def section_and_label(when: datetime, today: date) -> tuple[str, str]:
    day = when.date()
    if day == today:
        return "today", clock_label(when)
    return "week", WEEKDAYS[day.weekday()]


def midday(day: date) -> datetime:
    return datetime.combine(day, time(12, 0), tzinfo=timezone.utc)


def in_week(day: date, monday: date, sunday: date) -> bool:
    return monday <= day <= sunday


def group_logs_by_day(logs: list[WorkoutLog]) -> dict[str, list[WorkoutLog]]:
    grouped: dict[str, list[WorkoutLog]] = defaultdict(list)
    for log in logs:
        key = day_key(log.date)
        if key:
            grouped[key].append(log)
    return grouped


def workout_detail(logs: list[WorkoutLog]) -> str | None:
    exercise_count = 0
    set_count = 0
    for log in logs:
        for exercise in log.exercises or []:
            if not isinstance(exercise, dict):
                continue
            sets = exercise.get("sets") or []
            if not exercise.get("name") and not sets:
                continue
            exercise_count += 1
            set_count += len(sets) if isinstance(sets, list) else 0
    if exercise_count == 0:
        return None
    exercise_word = "exercise" if exercise_count == 1 else "exercises"
    set_word = "set" if set_count == 1 else "sets"
    return f"{exercise_count} {exercise_word} · {set_count} {set_word}"


def latest_stamp(logs: list[WorkoutLog], fallback: datetime) -> datetime:
    latest = fallback
    for log in logs:
        stamp = as_utc(log.updated_at or log.created_at)
        if stamp is not None and stamp > latest:
            latest = stamp
    return latest


def completed_title(name: str, session_label: str) -> str:
    if session_label:
        return f"{name} completed {session_label}"
    return f"{name} completed a workout"


def build_activity_items(
    *,
    viewer_id: str,
    buddy_id: str,
    buddy_name: str,
    today: date,
    your_logs: list[WorkoutLog],
    buddy_logs: list[WorkoutLog],
    nudges: list[BuddyNudge],
    presence: BuddyPresence | None,
    session_label_for,
    prs: list[dict[str, Any]],
    cheered_ids: set[str],
) -> list[BuddyActivityItem]:
    monday, sunday = week_bounds(today)
    today_key = today.isoformat()
    buddy_first = first_name(buddy_name, "them")
    built: list[tuple[datetime, BuddyActivityItem]] = []

    buddy_by_day = group_logs_by_day(buddy_logs)
    your_days = set(group_logs_by_day(your_logs))

    for key, logs in buddy_by_day.items():
        try:
            day = date.fromisoformat(key)
        except ValueError:
            continue
        if not in_week(day, monday, sunday):
            continue
        when = latest_stamp(logs, midday(day))
        if key == today_key:
            section, time_label = "today", clock_label(when)
        else:
            section, time_label = "week", WEEKDAYS[day.weekday()]
        activity_id = f"completed:{buddy_id}:{key}"
        built.append(
            (
                when,
                BuddyActivityItem(
                    id=activity_id,
                    section=section,
                    time_label=time_label,
                    kind="completed",
                    title=completed_title(buddy_first, session_label_for(buddy_id, day)),
                    detail=workout_detail(logs),
                    can_cheer=True,
                    cheered=activity_id in cheered_ids,
                ),
            )
        )
        if key in your_days:
            both_id = f"both:{key}"
            both_when = midday(day)
            both_section, both_label = (
                ("today", clock_label(when))
                if key == today_key
                else ("week", WEEKDAYS[day.weekday()])
            )
            built.append(
                (
                    both_when,
                    BuddyActivityItem(
                        id=both_id,
                        section=both_section,
                        time_label=both_label,
                        kind="both",
                        title="Both completed workouts",
                        can_cheer=False,
                    ),
                )
            )

    if presence is not None:
        started = as_utc(presence.started_at) or datetime.now(timezone.utc)
        if started.date() == today:
            activity_id = f"started:{buddy_id}:{today_key}"
            section, time_label = section_and_label(started, today)
            built.append(
                (
                    started,
                    BuddyActivityItem(
                        id=activity_id,
                        section=section,
                        time_label=time_label,
                        kind="started",
                        title=f"{buddy_first} started training",
                    ),
                )
            )

    for nudge in nudges:
        when = as_utc(nudge.created_at) or midday(date.fromisoformat(nudge.day_key))
        try:
            day = date.fromisoformat(nudge.day_key)
        except ValueError:
            continue
        if not in_week(day, monday, sunday):
            continue
        section, time_label = section_and_label(when, today)
        if day != today:
            section, time_label = "week", WEEKDAYS[day.weekday()]
        you_sent = nudge.from_user_id == viewer_id
        title = (
            f"You nudged {buddy_first}"
            if you_sent
            else f"{buddy_first} nudged you"
        )
        built.append(
            (
                when,
                BuddyActivityItem(
                    id=f"nudge:{nudge.id}",
                    section=section,
                    time_label=time_label,
                    kind="nudge",
                    title=title,
                ),
            )
        )

    for pr in prs:
        achieved_on = pr.get("achieved_on") or ""
        try:
            day = date.fromisoformat(achieved_on)
        except ValueError:
            continue
        if not in_week(day, monday, sunday):
            continue
        when = midday(day)
        if day == today:
            section, time_label = "today", clock_label(when)
        else:
            section, time_label = "week", WEEKDAYS[day.weekday()]
        exercise = pr.get("exercise") or "exercise"
        primary = pr.get("primary") or ""
        suffix = f" ({primary})" if primary else ""
        activity_id = f"pr:{buddy_id}:{exercise}:{achieved_on}"
        built.append(
            (
                when,
                BuddyActivityItem(
                    id=activity_id,
                    section=section,
                    time_label=time_label,
                    kind="pr",
                    title=f"{buddy_first} PR'd {exercise}{suffix} 🔥",
                ),
            )
        )

    built.sort(key=lambda row: row[0], reverse=True)
    return [item for _, item in built]
