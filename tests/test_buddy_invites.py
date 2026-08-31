from collections.abc import Generator
from contextlib import contextmanager
from unittest.mock import patch

from fastapi.testclient import TestClient

from app.core.deps import get_current_user, get_db, get_optional_user
from app.main import create_app
from app.models.buddy import BuddyBlock, BuddyLink
from app.models.user import User
from tests.test_buddy_search import _add_user


@contextmanager
def as_user(db_session, user: User) -> Generator[TestClient, None, None]:
    app = create_app()

    def override_get_db():
        yield db_session

    app.dependency_overrides[get_db] = override_get_db
    app.dependency_overrides[get_current_user] = lambda: user
    app.dependency_overrides[get_optional_user] = lambda: user
    with TestClient(app) as client:
        yield client
    app.dependency_overrides.clear()


def _seed_dave(db_session) -> User:
    return _add_user(
        db_session,
        "dave-1",
        email="dave@example.com",
        username="davefitness",
        name="Dave",
        goals=["build-muscle"],
        experience="intermediate",
        frequency="5-6x",
    )


def test_get_buddy_empty(client):
    response = client.get("/api/v1/buddy")
    assert response.status_code == 200
    assert response.json() == {
        "status": "none",
        "person": None,
        "invite_id": None,
        "declined_notice": False,
    }


def test_invite_requires_exactly_one_target(client):
    missing = client.post("/api/v1/buddy/invites", json={})
    assert missing.status_code == 422
    both = client.post(
        "/api/v1/buddy/invites",
        json={"email": "a@b.com", "username": "dave"},
    )
    assert both.status_code == 422


def test_invite_unknown_user(client):
    response = client.post(
        "/api/v1/buddy/invites",
        json={"username": "nobody"},
    )
    assert response.status_code == 404


def test_cannot_invite_self(client, db_session, test_user):
    test_user.username = "sean"
    db_session.commit()
    response = client.post(
        "/api/v1/buddy/invites",
        json={"username": "sean"},
    )
    assert response.status_code == 400


def test_invite_accept_and_one_buddy_rule(client, db_session, test_user):
    dave = _seed_dave(db_session)
    rita = _add_user(
        db_session,
        "rita-1",
        email="rita@example.com",
        username="rita",
        name="Rita",
    )

    invited = client.post(
        "/api/v1/buddy/invites",
        json={"username": "davefitness"},
    )
    assert invited.status_code == 200
    body = invited.json()
    assert body["status"] == "outgoing"
    assert body["person"]["id"] == "dave-1"
    assert body["person"]["invited_you"] is False
    invite_id = body["invite_id"]
    assert invite_id

    with as_user(db_session, dave) as dave_client:
        incoming = dave_client.get("/api/v1/buddy")
        assert incoming.json()["status"] == "incoming"
        assert incoming.json()["person"]["id"] == test_user.id
        assert incoming.json()["person"]["invited_you"] is True
        accepted = dave_client.post(f"/api/v1/buddy/invites/{invite_id}/accept")
        assert accepted.status_code == 200
        assert accepted.json()["status"] == "active"
        assert accepted.json()["invite_id"] is None

    mine = client.get("/api/v1/buddy")
    assert mine.json()["status"] == "active"
    assert mine.json()["person"]["username"] == "davefitness"

    blocked_second = client.post(
        "/api/v1/buddy/invites",
        json={"username": "rita"},
    )
    assert blocked_second.status_code == 409

    with as_user(db_session, rita) as rita_client:
        toward_dave = rita_client.post(
            "/api/v1/buddy/invites",
            json={"username": "davefitness"},
        )
        assert toward_dave.status_code == 409


def test_decline_shows_notice_then_both_are_free(client, db_session, test_user):
    dave = _seed_dave(db_session)
    invited = client.post(
        "/api/v1/buddy/invites",
        json={"email": "dave@example.com"},
    )
    invite_id = invited.json()["invite_id"]

    with as_user(db_session, dave) as dave_client:
        declined = dave_client.post(f"/api/v1/buddy/invites/{invite_id}/decline")
        assert declined.json()["status"] == "none"
        assert declined.json()["declined_notice"] is False

    notice = client.get("/api/v1/buddy")
    assert notice.json()["status"] == "none"
    assert notice.json()["declined_notice"] is True

    again = client.post(
        "/api/v1/buddy/invites",
        json={"username": "davefitness"},
    )
    assert again.status_code == 200
    assert again.json()["status"] == "outgoing"
    assert again.json()["declined_notice"] is False


def test_cancel_invite(client, db_session):
    _seed_dave(db_session)
    invited = client.post(
        "/api/v1/buddy/invites",
        json={"username": "davefitness"},
    )
    invite_id = invited.json()["invite_id"]
    cancelled = client.delete(f"/api/v1/buddy/invites/{invite_id}")
    assert cancelled.json()["status"] == "none"
    assert cancelled.json()["declined_notice"] is False
    assert db_session.query(BuddyLink).count() == 0


def test_remove_accepted_buddy(client, db_session):
    dave = _seed_dave(db_session)
    invited = client.post(
        "/api/v1/buddy/invites",
        json={"username": "davefitness"},
    )
    invite_id = invited.json()["invite_id"]
    with as_user(db_session, dave) as dave_client:
        dave_client.post(f"/api/v1/buddy/invites/{invite_id}/accept")

    removed = client.delete("/api/v1/buddy")
    assert removed.json()["status"] == "none"
    with as_user(db_session, dave) as dave_client:
        assert dave_client.get("/api/v1/buddy").json()["status"] == "none"


def test_block_prevents_reinvite_and_search(client, db_session):
    dave = _seed_dave(db_session)
    invited = client.post(
        "/api/v1/buddy/invites",
        json={"username": "davefitness"},
    )
    invite_id = invited.json()["invite_id"]
    with as_user(db_session, dave) as dave_client:
        dave_client.post(f"/api/v1/buddy/invites/{invite_id}/accept")

    blocked = client.post("/api/v1/buddy/block")
    assert blocked.json()["status"] == "none"
    assert db_session.get(BuddyBlock, ("user-1", "dave-1")) is not None

    hidden = client.get("/api/v1/buddies/search?q=dave")
    assert hidden.json()["users"] == []

    reinvite = client.post(
        "/api/v1/buddy/invites",
        json={"username": "davefitness"},
    )
    assert reinvite.status_code == 403

    with as_user(db_session, dave) as dave_client:
        back = dave_client.post(
            "/api/v1/buddy/invites",
            json={"email": "test@example.com"},
        )
        assert back.status_code == 403


def test_search_hides_users_who_already_have_a_buddy(client, db_session):
    dave = _seed_dave(db_session)
    invited = client.post(
        "/api/v1/buddy/invites",
        json={"username": "davefitness"},
    )
    assert invited.status_code == 200
    hidden = client.get("/api/v1/buddies/search?q=dave")
    assert hidden.json()["users"] == []

    with as_user(db_session, dave) as dave_client:
        assert dave_client.get("/api/v1/buddies/search?q=test").json()["users"] == []


def test_accept_is_only_for_invitee(client, db_session):
    _seed_dave(db_session)
    invited = client.post(
        "/api/v1/buddy/invites",
        json={"username": "davefitness"},
    )
    invite_id = invited.json()["invite_id"]
    forbidden = client.post(f"/api/v1/buddy/invites/{invite_id}/accept")
    assert forbidden.status_code == 403

    missing = client.post("/api/v1/buddy/invites/not-a-real-id/accept")
    assert missing.status_code == 404


def test_reset_data_does_not_leave_ghost_buddy(client, db_session, test_user):
    dave = _seed_dave(db_session)
    invited = client.post(
        "/api/v1/buddy/invites",
        json={"username": "davefitness"},
    )
    invite_id = invited.json()["invite_id"]
    with as_user(db_session, dave) as dave_client:
        dave_client.post(f"/api/v1/buddy/invites/{invite_id}/accept")

    reset = client.post("/api/v1/auth/reset-data")
    assert reset.status_code == 200
    assert client.get("/api/v1/buddy").json()["status"] == "none"
    assert db_session.get(User, test_user.id) is not None

    with as_user(db_session, dave) as dave_client:
        assert dave_client.get("/api/v1/buddy").json()["status"] == "none"
        rita = _add_user(
            db_session,
            "rita-reset",
            email="rita-reset@example.com",
            username="ritareset",
            name="Rita",
        )
        again = dave_client.post(
            "/api/v1/buddy/invites",
            json={"username": rita.username},
        )
        assert again.status_code == 200
        assert again.json()["status"] == "outgoing"


def test_reset_data_clears_pending_invite_for_the_other_person(
    client, db_session
):
    dave = _seed_dave(db_session)
    invited = client.post(
        "/api/v1/buddy/invites",
        json={"username": "davefitness"},
    )
    assert invited.json()["status"] == "outgoing"

    assert client.post("/api/v1/auth/reset-data").status_code == 200

    with as_user(db_session, dave) as dave_client:
        assert dave_client.get("/api/v1/buddy").json()["status"] == "none"


def test_delete_account_does_not_leave_ghost_buddy(client, db_session, test_user):
    user_id = test_user.id
    dave = _seed_dave(db_session)
    invited = client.post(
        "/api/v1/buddy/invites",
        json={"username": "davefitness"},
    )
    invite_id = invited.json()["invite_id"]
    with as_user(db_session, dave) as dave_client:
        dave_client.post(f"/api/v1/buddy/invites/{invite_id}/accept")

    with patch("app.routers.auth.SupabaseAuthService") as cls:
        cls.return_value.delete_user.return_value = None
        deleted = client.delete("/api/v1/auth/account")

    assert deleted.status_code == 200
    cls.return_value.delete_user.assert_called_once_with(user_id)
    assert db_session.get(User, user_id) is None
    assert db_session.get(User, dave.id) is not None
    assert db_session.query(BuddyLink).count() == 0
    assert db_session.query(BuddyBlock).count() == 0

    with as_user(db_session, dave) as dave_client:
        assert dave_client.get("/api/v1/buddy").json()["status"] == "none"
        rita = _add_user(
            db_session,
            "rita-delete",
            email="rita-delete@example.com",
            username="ritadelete",
            name="Rita",
        )
        again = dave_client.post(
            "/api/v1/buddy/invites",
            json={"username": rita.username},
        )
        assert again.status_code == 200
        assert again.json()["status"] == "outgoing"
