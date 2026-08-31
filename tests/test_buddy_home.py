from datetime import datetime, timedelta, timezone

from app.models.buddy import BuddyLink, BuddyPresence
from app.models.exercise import Exercise
from app.models.schedule import UserSchedule
from app.models.workout_log import WorkoutLog
from tests.test_buddy_invites import _seed_dave, as_user


def _today() -> str:
    return datetime.now(timezone.utc).date().isoformat()


def _shift(days: int) -> str:
    return (datetime.now(timezone.utc).date() + timedelta(days=days)).isoformat()


def _weekday() -> str:
    return ("Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun")[
        datetime.now(timezone.utc).date().weekday()
    ]


def _pair(db_session, requester_id: str, addressee_id: str) -> None:
    db_session.add(
        BuddyLink(
            id="home-link",
            requester_id=requester_id,
            addressee_id=addressee_id,
            status="accepted",
        )
    )
    db_session.commit()


def _add_log(db_session, log_id: str, user_id: str, day: str, exercises: list) -> None:
    db_session.add(
        WorkoutLog(
            id=log_id,
            user_id=user_id,
            date=day,
            exercises=exercises,
        )
    )
    db_session.commit()


def test_home_requires_an_accepted_buddy(client, db_session):
    assert client.get("/api/v1/buddy/home").status_code == 404
    dave = _seed_dave(db_session)
    db_session.add(
        BuddyLink(
            id="pending-home",
            requester_id="user-1",
            addressee_id=dave.id,
            status="pending",
        )
    )
    db_session.commit()
    assert client.get("/api/v1/buddy/home").status_code == 404


def test_home_empty_pair_is_not_started(client, db_session, test_user):
    dave = _seed_dave(db_session)
    _pair(db_session, test_user.id, dave.id)

    response = client.get("/api/v1/buddy/home")
    assert response.status_code == 200
    body = response.json()
    assert body["person"]["id"] == "dave-1"
    assert body["person"]["username"] == "davefitness"
    assert "email" not in body["person"]
    assert body["training_status"] == "not_started"
    assert body["session_label"] == ""
    assert body["updated_at"] is None
    assert body["streak_days"] == 0
    assert body["your_week_sessions"] == 0
    assert body["buddy_week_sessions"] == 0
    assert body["your_records"] == []
    assert body["buddy_records"] == []
    assert body["nudges_used"] == 0
    assert body["nudges_left"] == 3
    assert body["nudge_limit"] == 3


def test_home_completed_today_uses_schedule_label_and_streak(
    client, db_session, test_user
):
    dave = _seed_dave(db_session)
    _pair(db_session, test_user.id, dave.id)
    db_session.add(
        UserSchedule(
            user_id=dave.id,
            schedule={
                _weekday(): {
                    "type": "gym",
                    "focuses": ["Upper Body"],
                    "exercises": [],
                }
            },
        )
    )
    db_session.commit()
    _add_log(
        db_session,
        "dave-today",
        dave.id,
        _today(),
        [{"name": "Bench Press", "sets": [{"weight": 70, "reps": 8}]}],
    )
    _add_log(
        db_session,
        "dave-yesterday",
        dave.id,
        _shift(-1),
        [{"name": "Squat", "sets": [{"weight": 100, "reps": 5}]}],
    )
    _add_log(
        db_session,
        "you-today",
        test_user.id,
        _today(),
        [{"name": "Hip Thrust", "sets": [{"weight": 80, "reps": 10}]}],
    )
    _add_log(
        db_session,
        "you-same-day-again",
        test_user.id,
        _today(),
        [{"name": "RDL", "sets": [{"weight": 90, "reps": 8}]}],
    )

    body = client.get("/api/v1/buddy/home").json()
    assert body["training_status"] == "completed"
    assert body["session_label"] == "Upper Body"
    assert body["updated_at"] is not None
    assert body["streak_days"] == 2
    today = datetime.now(timezone.utc).date()
    monday = today - timedelta(days=today.weekday())
    sunday = monday + timedelta(days=6)
    dave_days = {today, today - timedelta(days=1)}
    assert body["your_week_sessions"] == 1
    assert body["buddy_week_sessions"] == sum(
        1 for day in dave_days if monday <= day <= sunday
    )
    assert body["your_records"][0]["owner"] == "you"
    assert body["buddy_records"][0]["owner"] == "buddy"
    squat = next(row for row in body["buddy_records"] if row["exercise"] == "Squat")
    assert squat["primary"] == "100kg"


def test_home_week_count_ignores_previous_week(client, db_session, test_user):
    dave = _seed_dave(db_session)
    _pair(db_session, test_user.id, dave.id)
    _add_log(
        db_session,
        "old",
        dave.id,
        _shift(-8),
        [{"name": "Run", "sets": [{"weight": 0, "reps": 20}]}],
    )
    body = client.get("/api/v1/buddy/home").json()
    assert body["buddy_week_sessions"] == 0
    assert body["streak_days"] == 0
    assert body["training_status"] == "not_started"


def test_home_records_keep_best_set_and_empty_reactions(
    client, db_session, test_user
):
    dave = _seed_dave(db_session)
    _pair(db_session, test_user.id, dave.id)
    db_session.add(
        Exercise(
            id="plank-1",
            name="Plank",
            category="waist",
            body_part="waist",
            equipment="body weight",
            muscles=["abs"],
            steps=[],
            tips=[],
            mistakes=[],
            rep_label="seconds",
        )
    )
    db_session.commit()
    _add_log(
        db_session,
        "dave-prs",
        dave.id,
        _shift(-2),
        [
            {"name": "Back Squat", "sets": [{"weight": 100, "reps": 5}, {"weight": 125, "reps": 3}]},
            {"name": "Pull-ups", "sets": [{"weight": 0, "reps": 15}]},
            {"name": "Plank", "sets": [{"weight": 0, "reps": 90}]},
        ],
    )

    records = {
        row["exercise"]: row
        for row in client.get("/api/v1/buddy/home").json()["buddy_records"]
    }
    assert records["Back Squat"]["primary"] == "125kg"
    assert records["Pull-ups"]["primary"] == "15 reps"
    assert records["Plank"]["primary"] == "1m 30s"
    assert records["Back Squat"]["reactions"] == []
    assert records["Back Squat"]["id"] == "buddy:Back Squat"


def test_presence_marks_in_progress_then_clears(client, db_session, test_user):
    dave = _seed_dave(db_session)
    _pair(db_session, test_user.id, dave.id)

    with as_user(db_session, dave) as dave_client:
        started = dave_client.post(
            "/api/v1/buddy/presence",
            json={"status": "started", "session_label": "Upper Body"},
        )
        assert started.status_code == 200

    body = client.get("/api/v1/buddy/home").json()
    assert body["training_status"] == "in_progress"
    assert body["session_label"] == "Upper Body"
    assert body["updated_at"] is not None

    with as_user(db_session, dave) as dave_client:
        finished = dave_client.post(
            "/api/v1/buddy/presence",
            json={"status": "finished"},
        )
        assert finished.json()["training_status"] == "not_started"

    cleared = client.get("/api/v1/buddy/home").json()
    assert cleared["training_status"] == "not_started"
    assert cleared["session_label"] == ""


def test_stale_presence_does_not_count_as_in_progress(
    client, db_session, test_user
):
    dave = _seed_dave(db_session)
    _pair(db_session, test_user.id, dave.id)
    stale = datetime.now(timezone.utc) - timedelta(hours=4)
    db_session.add(
        BuddyPresence(
            user_id=dave.id,
            started_at=stale,
            session_label="Upper Body",
            updated_at=stale,
        )
    )
    db_session.commit()
    body = client.get("/api/v1/buddy/home").json()
    assert body["training_status"] == "not_started"


def test_presence_requires_a_buddy(client):
    response = client.post(
        "/api/v1/buddy/presence",
        json={"status": "started"},
    )
    assert response.status_code == 404
