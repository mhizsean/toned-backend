from app.models.buddy import BuddyNudge
from app.services.account_service import AccountService
from tests.test_buddy_home import _pair
from tests.test_buddy_invites import _seed_dave, as_user


def test_nudge_requires_an_accepted_buddy(client):
    response = client.post("/api/v1/buddy/nudge")
    assert response.status_code == 404


def test_nudge_counts_up_to_three_then_rejects(client, db_session, test_user):
    dave = _seed_dave(db_session)
    _pair(db_session, test_user.id, dave.id)

    first = client.post("/api/v1/buddy/nudge")
    assert first.status_code == 200
    assert first.json() == {"used": 1, "left": 2, "limit": 3}

    second = client.post("/api/v1/buddy/nudge")
    assert second.json() == {"used": 2, "left": 1, "limit": 3}

    third = client.post("/api/v1/buddy/nudge")
    assert third.json() == {"used": 3, "left": 0, "limit": 3}

    blocked = client.post("/api/v1/buddy/nudge")
    assert blocked.status_code == 429
    assert db_session.query(BuddyNudge).count() == 3

    home = client.get("/api/v1/buddy/home").json()
    assert home["nudges_used"] == 3
    assert home["nudges_left"] == 0
    assert home["nudge_limit"] == 3


def test_nudge_cap_is_per_sender_and_resets_next_day(
    client, db_session, test_user
):
    dave = _seed_dave(db_session)
    _pair(db_session, test_user.id, dave.id)
    db_session.add(
        BuddyNudge(
            id="old-nudge",
            from_user_id=test_user.id,
            to_user_id=dave.id,
            day_key="2026-08-01",
        )
    )
    db_session.commit()

    with as_user(db_session, dave) as dave_client:
        theirs = dave_client.post("/api/v1/buddy/nudge")
        assert theirs.json()["used"] == 1

    mine = client.post("/api/v1/buddy/nudge")
    assert mine.json() == {"used": 1, "left": 2, "limit": 3}
    assert client.get("/api/v1/buddy/home").json()["nudges_used"] == 1


def test_account_reset_wipes_nudges(client, db_session, test_user):
    dave = _seed_dave(db_session)
    _pair(db_session, test_user.id, dave.id)
    client.post("/api/v1/buddy/nudge")

    counts = AccountService.reset_cloud_data(db_session, test_user.id)
    assert counts["buddy_nudges_deleted"] == 1
    assert db_session.query(BuddyNudge).count() == 0
