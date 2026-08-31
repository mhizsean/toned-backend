from datetime import datetime, timedelta, timezone

from app.models.buddy import BuddyCheer
from app.models.schedule import UserSchedule
from app.services.account_service import AccountService
from tests.test_buddy_home import _add_log, _pair, _today, _weekday
from tests.test_buddy_invites import _seed_dave, as_user


def _week_day_not_today() -> str:
    today = datetime.now(timezone.utc).date()
    if today.weekday() > 0:
        return (today - timedelta(days=1)).isoformat()
    return (today + timedelta(days=1)).isoformat()


def test_activity_requires_an_accepted_buddy(client):
    assert client.get("/api/v1/buddy/activity").status_code == 404


def test_activity_empty_when_paired(client, db_session, test_user):
    dave = _seed_dave(db_session)
    _pair(db_session, test_user.id, dave.id)
    response = client.get("/api/v1/buddy/activity")
    assert response.status_code == 200
    assert response.json() == {"items": []}


def test_activity_mixes_nudge_completed_pr_both_and_started(
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
        [
            {"name": "Bench Press", "sets": [{"weight": 70, "reps": 8}]},
            {"name": "Row", "sets": [{"weight": 50, "reps": 10}]},
        ],
    )
    _add_log(
        db_session,
        "you-today",
        test_user.id,
        _today(),
        [{"name": "Hip Thrust", "sets": [{"weight": 80, "reps": 10}]}],
    )
    other_day = _week_day_not_today()
    _add_log(
        db_session,
        "dave-pr-day",
        dave.id,
        other_day,
        [{"name": "Back Squat", "sets": [{"weight": 125, "reps": 3}]}],
    )
    _add_log(
        db_session,
        "you-pr-day",
        test_user.id,
        other_day,
        [{"name": "RDL", "sets": [{"weight": 90, "reps": 8}]}],
    )

    client.post("/api/v1/buddy/nudge")
    with as_user(db_session, dave) as dave_client:
        dave_client.post(
            "/api/v1/buddy/presence",
            json={"status": "started", "session_label": "Upper Body"},
        )

    items = client.get("/api/v1/buddy/activity").json()["items"]
    by_kind = {}
    for item in items:
        by_kind.setdefault(item["kind"], []).append(item)

    completed = by_kind["completed"]
    today_completed = next(item for item in completed if item["section"] == "today")
    assert today_completed["title"] == "Dave completed Upper Body"
    assert today_completed["detail"] == "2 exercises · 2 sets"
    assert today_completed["can_cheer"] is True
    assert today_completed["cheered"] is False
    assert today_completed["id"] == f"completed:dave-1:{_today()}"

    assert any(item["title"] == "You nudged Dave" for item in by_kind["nudge"])
    assert any(item["title"] == "Dave started training" for item in by_kind["started"])
    assert any(
        item["title"] == "Dave PR'd Back Squat (125kg) 🔥" for item in by_kind["pr"]
    )
    assert any(item["title"] == "Both completed workouts" for item in by_kind["both"])


def test_their_nudge_uses_invitee_voice(client, db_session, test_user):
    dave = _seed_dave(db_session)
    _pair(db_session, test_user.id, dave.id)
    with as_user(db_session, dave) as dave_client:
        dave_client.post("/api/v1/buddy/nudge")
    items = client.get("/api/v1/buddy/activity").json()["items"]
    assert items[0]["title"] == "Dave nudged you"
    assert items[0]["kind"] == "nudge"
    assert items[0]["can_cheer"] is False


def test_cheer_completed_workout_is_idempotent(client, db_session, test_user):
    dave = _seed_dave(db_session)
    _pair(db_session, test_user.id, dave.id)
    _add_log(
        db_session,
        "dave-today",
        dave.id,
        _today(),
        [{"name": "Bench Press", "sets": [{"weight": 70, "reps": 8}]}],
    )
    activity_id = f"completed:dave-1:{_today()}"
    first = client.post(f"/api/v1/buddy/activity/{activity_id}/cheer")
    assert first.status_code == 200
    assert first.json() == {"id": activity_id, "cheered": True}
    second = client.post(f"/api/v1/buddy/activity/{activity_id}/cheer")
    assert second.status_code == 200
    item = client.get("/api/v1/buddy/activity").json()["items"][0]
    assert item["id"] == activity_id
    assert item["cheered"] is True
    assert db_session.query(BuddyCheer).count() == 1


def test_cannot_cheer_nudge_or_unknown(client, db_session, test_user):
    dave = _seed_dave(db_session)
    _pair(db_session, test_user.id, dave.id)
    nudged = client.post("/api/v1/buddy/nudge").json()
    items = client.get("/api/v1/buddy/activity").json()["items"]
    nudge_id = items[0]["id"]
    assert client.post(f"/api/v1/buddy/activity/{nudge_id}/cheer").status_code == 404
    assert client.post("/api/v1/buddy/activity/not-real/cheer").status_code == 404
    assert nudged["used"] == 1


def test_account_reset_wipes_cheers(client, db_session, test_user):
    dave = _seed_dave(db_session)
    _pair(db_session, test_user.id, dave.id)
    _add_log(
        db_session,
        "dave-today",
        dave.id,
        _today(),
        [{"name": "Bench Press", "sets": [{"weight": 70, "reps": 8}]}],
    )
    activity_id = f"completed:dave-1:{_today()}"
    client.post(f"/api/v1/buddy/activity/{activity_id}/cheer")
    counts = AccountService.reset_cloud_data(db_session, test_user.id)
    assert counts["buddy_cheers_deleted"] == 1
    assert db_session.query(BuddyCheer).count() == 0
