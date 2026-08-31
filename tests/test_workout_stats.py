from datetime import date

from app.models.workout_log import WorkoutLog
from app.services.workout_stats import (
    current_streak,
    day_key,
    format_ago,
    format_primary,
    personal_records,
    unique_day_keys,
    week_session_count,
)


def _log(log_id: str, day: str, exercises: list) -> WorkoutLog:
    return WorkoutLog(
        id=log_id,
        user_id="user-1",
        date=day,
        exercises=exercises,
    )


def test_day_key_strips_time():
    assert day_key("2026-08-31T18:00:00") == "2026-08-31"
    assert day_key("2026-08-31") == "2026-08-31"


def test_current_streak_counts_consecutive_days_ending_today():
    today = date(2026, 8, 31)
    days = ["2026-08-31", "2026-08-30", "2026-08-29", "2026-08-27"]
    assert current_streak(days, today) == 3


def test_current_streak_can_start_from_yesterday():
    today = date(2026, 8, 31)
    assert current_streak(["2026-08-30", "2026-08-29"], today) == 2


def test_current_streak_breaks_if_latest_is_older_than_yesterday():
    today = date(2026, 8, 31)
    assert current_streak(["2026-08-28"], today) == 0


def test_week_session_count_is_unique_days_mon_sun():
    today = date(2026, 8, 31)  # Monday
    days = [
        "2026-08-31",
        "2026-08-31",
        "2026-08-30",  # previous Sunday, last week
        "2026-09-02",
        "2026-09-07",  # next Monday
    ]
    # unique_day_keys would already unique; pass unique list
    assert week_session_count(
        ["2026-09-07", "2026-09-02", "2026-08-31", "2026-08-30"],
        today,
    ) == 2


def test_format_ago_uses_calendar_days():
    today = date(2026, 8, 31)
    assert format_ago("2026-08-31", today) == "today"
    assert format_ago("2026-08-30", today) == "1 day ago"
    assert format_ago("2026-08-24", today) == "1 week ago"


def test_personal_records_picks_heavier_set_and_limits_to_three():
    logs = [
        _log(
            "a",
            "2026-08-20",
            [{"name": "Back Squat", "sets": [{"weight": 100, "reps": 5}]}],
        ),
        _log(
            "b",
            "2026-08-24",
            [
                {"name": "Back Squat", "sets": [{"weight": 125, "reps": 3}]},
                {"name": "Pull-ups", "sets": [{"weight": 0, "reps": 15}]},
                {"name": "Bench Press", "sets": [{"weight": 70, "reps": 8}]},
                {"name": "Deadlift", "sets": [{"weight": 140, "reps": 2}]},
            ],
        ),
    ]
    records = personal_records(logs, owner="buddy", today=date(2026, 8, 31))
    assert [row["exercise"] for row in records] == [
        "Deadlift",
        "Back Squat",
        "Bench Press",
    ]
    squat = next(row for row in records if row["exercise"] == "Back Squat")
    assert squat["primary"] == "125kg"
    assert squat["ago"] == "1 week ago"
    assert squat["owner"] == "buddy"
    assert squat["reactions"] == []


def test_personal_records_formats_bodyweight_and_seconds():
    logs = [
        _log(
            "c",
            "2026-08-31",
            [
                {"name": "Pull-ups", "sets": [{"weight": 0, "reps": 15}]},
                {"name": "Plank", "sets": [{"weight": 0, "reps": 90}]},
            ],
        )
    ]
    records = personal_records(
        logs,
        owner="you",
        today=date(2026, 8, 31),
        rep_labels={"Plank": "seconds"},
    )
    by_name = {row["exercise"]: row for row in records}
    assert by_name["Pull-ups"]["primary"] == "15 reps"
    assert by_name["Plank"]["primary"] == "1m 30s"


def test_unique_day_keys_newest_first():
    logs = [
        _log("1", "2026-08-10", []),
        _log("2", "2026-08-12T10:00:00", []),
        _log("3", "2026-08-10T18:00:00", []),
    ]
    assert unique_day_keys(logs) == ["2026-08-12", "2026-08-10"]


def test_format_primary_weight():
    assert format_primary(80, 10, None) == "80kg"
    assert format_primary(0, 12, None) == "12 reps"
    assert format_primary(0, 45, "seconds") == "45s"
