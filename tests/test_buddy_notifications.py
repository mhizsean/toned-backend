from urllib.parse import quote
from unittest.mock import patch

from app.models.buddy import BuddyEodNudge, BuddyNudge
from tests.test_buddy_home import _add_log, _pair, _today
from tests.test_buddy_invites import _seed_dave, as_user

TOKEN_DAVE = "ExponentPushToken[dave-device]"
TOKEN_YOU = "ExponentPushToken[you-device]"


def _pair_with_tokens(client, db_session, test_user):
    dave = _seed_dave(db_session)
    _pair(db_session, test_user.id, dave.id)
    client.post("/api/v1/buddy/push-token", json={"token": TOKEN_YOU})
    with as_user(db_session, dave) as dave_client:
        dave_client.post("/api/v1/buddy/push-token", json={"token": TOKEN_DAVE})
    return dave


def _log_today(client, log_id: str = "w-today"):
    return client.post(
        "/api/v1/workouts",
        json={
            "id": log_id,
            "date": f"{_today()}T12:00:00.000Z",
            "exercises": [
                {"name": "Bench Press", "sets": [{"weight": 70, "reps": 8}]}
            ],
        },
    )


def test_first_completion_today_notifies_buddy(client, db_session, test_user):
    _pair_with_tokens(client, db_session, test_user)
    with patch("app.services.buddy_push.BuddyPushService._post") as post:
        created = _log_today(client)
        assert created.status_code == 201
        post.assert_called_once()
        message = post.call_args.args[0][0]
        assert message["to"] == TOKEN_DAVE
        assert message["data"]["type"] == "buddy-completed"

    with patch("app.services.buddy_push.BuddyPushService._post") as post:
        second = _log_today(client, "w-today-2")
        assert second.status_code == 201
        post.assert_not_called()


def test_completed_push_can_be_turned_off(client, db_session, test_user):
    dave = _pair_with_tokens(client, db_session, test_user)
    with as_user(db_session, dave) as dave_client:
        dave_client.patch(
            "/api/v1/preferences",
            json={"notify_buddy_completed": False},
        )
    with patch("app.services.buddy_push.BuddyPushService._post") as post:
        _log_today(client)
        post.assert_not_called()


def test_started_is_opt_in(client, db_session, test_user):
    dave = _pair_with_tokens(client, db_session, test_user)
    with patch("app.services.buddy_push.BuddyPushService._post") as post:
        started = client.post(
            "/api/v1/buddy/presence",
            json={"status": "started", "session_label": "Upper Body"},
        )
        assert started.status_code == 200
        post.assert_not_called()

    client.post("/api/v1/buddy/presence", json={"status": "finished"})
    with as_user(db_session, dave) as dave_client:
        dave_client.patch(
            "/api/v1/preferences",
            json={"notify_buddy_started": True},
        )
    with patch("app.services.buddy_push.BuddyPushService._post") as post:
        client.post(
            "/api/v1/buddy/presence",
            json={"status": "started", "session_label": "Upper Body"},
        )
        post.assert_called_once()
        assert post.call_args.args[0][0]["data"]["type"] == "buddy-started"


def test_nudge_push_follows_toggle(client, db_session, test_user):
    dave = _pair_with_tokens(client, db_session, test_user)
    with as_user(db_session, dave) as dave_client:
        dave_client.patch(
            "/api/v1/preferences",
            json={"notify_buddy_nudge": False},
        )
    with patch("app.services.buddy_push.BuddyPushService._post") as post:
        nudged = client.post("/api/v1/buddy/nudge")
        assert nudged.status_code == 200
        assert nudged.json()["used"] == 1
        post.assert_not_called()


def test_end_of_day_nudge_logs_activity_without_counting(
    client, db_session, test_user
):
    _pair_with_tokens(client, db_session, test_user)
    today = _today()
    logged = client.post("/api/v1/buddy/eod-nudge", json={"day_key": today})
    assert logged.status_code == 200
    assert logged.json() == {"logged": True, "day_key": today}
    again = client.post("/api/v1/buddy/eod-nudge", json={"day_key": today})
    assert again.json()["logged"] is True
    assert db_session.query(BuddyEodNudge).count() == 1
    assert db_session.query(BuddyNudge).count() == 0
    items = client.get("/api/v1/buddy/activity").json()["items"]
    eod = next(item for item in items if item["kind"] == "eod")
    assert eod["title"] == "Evening reminder to train"


def test_end_of_day_nudge_skipped_if_already_trained(
    client, db_session, test_user
):
    _pair_with_tokens(client, db_session, test_user)
    _add_log(
        db_session,
        "already",
        test_user.id,
        _today(),
        [{"name": "Squat", "sets": [{"weight": 60, "reps": 5}]}],
    )
    skipped = client.post("/api/v1/buddy/eod-nudge", json={"day_key": _today()})
    assert skipped.json()["logged"] is False
    assert db_session.query(BuddyEodNudge).count() == 0


def test_reaction_is_in_activity_and_opt_in_push(
    client, db_session, test_user
):
    dave = _pair_with_tokens(client, db_session, test_user)
    _add_log(
        db_session,
        "dave-squat",
        dave.id,
        _today(),
        [{"name": "Back Squat", "sets": [{"weight": 125, "reps": 3}]}],
    )
    record_path = quote("dave-1:Back Squat", safe="")
    with patch("app.services.buddy_push.BuddyPushService._post") as post:
        added = client.put(
            f"/api/v1/buddy/records/{record_path}/reactions",
            json={"reaction": "fire"},
        )
        assert added.status_code == 200
        post.assert_not_called()

    items = client.get("/api/v1/buddy/activity").json()["items"]
    reacted = next(item for item in items if item["kind"] == "reacted")
    assert "You reacted" in reacted["title"]
    assert "Back Squat" in reacted["title"]

    with as_user(db_session, dave) as dave_client:
        dave_client.patch(
            "/api/v1/preferences",
            json={"notify_buddy_reacted": True},
        )
    with patch("app.services.buddy_push.BuddyPushService._post") as post:
        client.put(
            f"/api/v1/buddy/records/{record_path}/reactions",
            json={"reaction": "clap"},
        )
        post.assert_called_once()
        message = post.call_args.args[0][0]
        assert message["to"] == TOKEN_DAVE
        assert message["data"]["type"] == "buddy-reacted"


def test_preferences_defaults_match_screenshot(client):
    body = client.get("/api/v1/preferences").json()
    assert body["notify_buddy_completed"] is True
    assert body["notify_buddy_started"] is False
    assert body["notify_buddy_nudge"] is True
    assert body["notify_buddy_eod"] is True
    assert body["notify_buddy_reacted"] is False
    assert body["notifications_enabled"] is True


def test_master_off_blocks_all_buddy_push(client, db_session, test_user):
    dave = _pair_with_tokens(client, db_session, test_user)
    with as_user(db_session, dave) as dave_client:
        dave_client.patch(
            "/api/v1/preferences",
            json={"notifications_enabled": False},
        )
    with patch("app.services.buddy_push.BuddyPushService._post") as post:
        _log_today(client)
        post.assert_not_called()
    with patch("app.services.buddy_push.BuddyPushService._post") as post:
        client.post("/api/v1/buddy/nudge")
        post.assert_not_called()

