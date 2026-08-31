from unittest.mock import patch

import httpx

from app.models.buddy import BuddyPushToken
from app.models.profile import UserProfile
from app.services.account_service import AccountService
from tests.test_buddy_home import _add_log, _today
from tests.test_buddy_invites import _seed_dave, as_user

TOKEN_DAVE = "ExponentPushToken[dave-device]"
TOKEN_YOU = "ExponentPushToken[you-device]"


def _name(db_session, user_id: str, name: str) -> None:
    db_session.add(UserProfile(user_id=user_id, name=name, goals=[]))
    db_session.commit()


def test_register_and_unregister_push_token(client, db_session, test_user):
    saved = client.post("/api/v1/buddy/push-token", json={"token": TOKEN_YOU})
    assert saved.status_code == 200
    row = db_session.get(BuddyPushToken, TOKEN_YOU)
    assert row is not None
    assert row.user_id == test_user.id

    dave = _seed_dave(db_session)
    with as_user(db_session, dave) as dave_client:
        stolen = dave_client.post(
            "/api/v1/buddy/push-token",
            json={"token": TOKEN_YOU},
        )
        assert stolen.status_code == 200
    db_session.refresh(row)
    assert row.user_id == dave.id

    removed = client.request(
        "DELETE",
        "/api/v1/buddy/push-token",
        json={"token": TOKEN_YOU},
    )
    assert removed.status_code == 200
    assert db_session.get(BuddyPushToken, TOKEN_YOU) is not None

    with as_user(db_session, dave) as dave_client:
        dave_client.request(
            "DELETE",
            "/api/v1/buddy/push-token",
            json={"token": TOKEN_YOU},
        )
    assert db_session.get(BuddyPushToken, TOKEN_YOU) is None


def test_invite_accept_decline_nudge_cheer_send_push(
    client, db_session, test_user
):
    _name(db_session, test_user.id, "Sean")
    dave = _seed_dave(db_session)
    with as_user(db_session, dave) as dave_client:
        dave_client.post("/api/v1/buddy/push-token", json={"token": TOKEN_DAVE})
    client.post("/api/v1/buddy/push-token", json={"token": TOKEN_YOU})

    with patch("app.services.buddy_push.BuddyPushService._post") as post:
        invited = client.post(
            "/api/v1/buddy/invites",
            json={"username": "davefitness"},
        )
        assert invited.status_code == 200
        invite_id = invited.json()["invite_id"]
        post.assert_called_once()
        messages = post.call_args.args[0]
        assert messages[0]["to"] == TOKEN_DAVE
        assert messages[0]["data"]["type"] == "buddy-invite"
        assert "Sean invited you" in messages[0]["body"]

    with patch("app.services.buddy_push.BuddyPushService._post") as post:
        with as_user(db_session, dave) as dave_client:
            accepted = dave_client.post(
                f"/api/v1/buddy/invites/{invite_id}/accept"
            )
            assert accepted.status_code == 200
        post.assert_called_once()
        messages = post.call_args.args[0]
        assert messages[0]["to"] == TOKEN_YOU
        assert messages[0]["data"]["type"] == "buddy-accept"
        assert "Dave accepted" in messages[0]["body"]

    with patch("app.services.buddy_push.BuddyPushService._post") as post:
        nudged = client.post("/api/v1/buddy/nudge")
        assert nudged.status_code == 200
        post.assert_called_once()
        messages = post.call_args.args[0]
        assert messages[0]["to"] == TOKEN_DAVE
        assert messages[0]["data"]["type"] == "buddy-nudge"

    _add_log(
        db_session,
        "dave-today",
        dave.id,
        _today(),
        [{"name": "Bench Press", "sets": [{"weight": 70, "reps": 8}]}],
    )
    activity_id = f"completed:dave-1:{_today()}"
    with patch("app.services.buddy_push.BuddyPushService._post") as post:
        first = client.post(f"/api/v1/buddy/activity/{activity_id}/cheer")
        assert first.status_code == 200
        post.assert_called_once()
        messages = post.call_args.args[0]
        assert messages[0]["to"] == TOKEN_DAVE
        assert messages[0]["data"]["type"] == "buddy-cheer"
        post.reset_mock()
        second = client.post(f"/api/v1/buddy/activity/{activity_id}/cheer")
        assert second.status_code == 200
        post.assert_not_called()


def test_decline_notifies_inviter(client, db_session, test_user):
    dave = _seed_dave(db_session)
    client.post("/api/v1/buddy/push-token", json={"token": TOKEN_YOU})
    invited = client.post(
        "/api/v1/buddy/invites",
        json={"username": "davefitness"},
    )
    invite_id = invited.json()["invite_id"]
    with patch("app.services.buddy_push.BuddyPushService._post") as post:
        with as_user(db_session, dave) as dave_client:
            declined = dave_client.post(
                f"/api/v1/buddy/invites/{invite_id}/decline"
            )
            assert declined.status_code == 200
        post.assert_called_once()
        messages = post.call_args.args[0]
        assert messages[0]["to"] == TOKEN_YOU
        assert messages[0]["data"]["type"] == "buddy-decline"


def test_no_push_without_token_or_when_expo_is_down(
    client, db_session, test_user
):
    dave = _seed_dave(db_session)
    with patch("app.services.buddy_push.BuddyPushService._post") as post:
        invited = client.post(
            "/api/v1/buddy/invites",
            json={"username": "davefitness"},
        )
        assert invited.status_code == 200
        post.assert_not_called()
    client.delete(f"/api/v1/buddy/invites/{invited.json()['invite_id']}")

    with as_user(db_session, dave) as dave_client:
        dave_client.post("/api/v1/buddy/push-token", json={"token": TOKEN_DAVE})
    with patch("app.services.buddy_push.httpx.Client") as client_cls:
        client_cls.return_value.__enter__.return_value.post.side_effect = (
            httpx.ConnectError("expo down")
        )
        invited = client.post(
            "/api/v1/buddy/invites",
            json={"username": "davefitness"},
        )
        assert invited.status_code == 200


def test_account_reset_wipes_push_tokens(client, db_session, test_user):
    client.post("/api/v1/buddy/push-token", json={"token": TOKEN_YOU})
    counts = AccountService.reset_cloud_data(db_session, test_user.id)
    assert counts["buddy_push_tokens_deleted"] == 1
    assert db_session.query(BuddyPushToken).count() == 0
