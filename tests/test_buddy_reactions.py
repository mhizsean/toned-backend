from urllib.parse import quote

from app.models.buddy import BuddyRecordReaction
from app.services.account_service import AccountService
from tests.test_buddy_home import _add_log, _pair, _shift, _today
from tests.test_buddy_invites import _seed_dave, as_user


def _react(client, record_id: str, reaction: str):
    return client.put(
        f"/api/v1/buddy/records/{quote(record_id, safe='')}/reactions",
        json={"reaction": reaction},
    )


def test_record_reaction_requires_a_buddy(client):
    response = _react(client, "dave-1:Back Squat", "fire")
    assert response.status_code == 404


def test_toggle_reaction_on_buddy_and_your_records(
    client, db_session, test_user
):
    dave = _seed_dave(db_session)
    _pair(db_session, test_user.id, dave.id)
    _add_log(
        db_session,
        "dave-squat",
        dave.id,
        _shift(-2),
        [{"name": "Back Squat", "sets": [{"weight": 125, "reps": 3}]}],
    )
    _add_log(
        db_session,
        "you-hip",
        test_user.id,
        _today(),
        [{"name": "Hip Thrust", "sets": [{"weight": 80, "reps": 10}]}],
    )

    added = _react(client, "dave-1:Back Squat", "fire")
    assert added.status_code == 200
    assert added.json() == {"id": "dave-1:Back Squat", "reactions": ["fire"]}

    alias = _react(client, "buddy:Back Squat", "clap")
    assert alias.json()["reactions"] == ["clap", "fire"]

    home = client.get("/api/v1/buddy/home").json()
    squat = next(
        row for row in home["buddy_records"] if row["exercise"] == "Back Squat"
    )
    assert squat["id"] == "dave-1:Back Squat"
    assert squat["reactions"] == ["clap", "fire"]

    yours = _react(client, f"{test_user.id}:Hip Thrust", "flex")
    assert yours.json()["reactions"] == ["flex"]
    hip = next(
        row for row in client.get("/api/v1/buddy/home").json()["your_records"]
        if row["exercise"] == "Hip Thrust"
    )
    assert hip["reactions"] == ["flex"]

    removed = _react(client, "dave-1:Back Squat", "fire")
    assert removed.json()["reactions"] == ["clap"]


def test_both_people_can_react_and_unique_emojis_stay(
    client, db_session, test_user
):
    dave = _seed_dave(db_session)
    _pair(db_session, test_user.id, dave.id)
    _add_log(
        db_session,
        "dave-squat",
        dave.id,
        _today(),
        [{"name": "Back Squat", "sets": [{"weight": 125, "reps": 3}]}],
    )
    _react(client, "dave-1:Back Squat", "fire")
    with as_user(db_session, dave) as dave_client:
        dave_client.put(
            f"/api/v1/buddy/records/{quote('dave-1:Back Squat', safe='')}/reactions",
            json={"reaction": "fire"},
        )
        dave_client.put(
            f"/api/v1/buddy/records/{quote('dave-1:Back Squat', safe='')}/reactions",
            json={"reaction": "hands"},
        )

    body = client.get("/api/v1/buddy/home").json()["buddy_records"][0]
    assert body["reactions"] == ["fire", "hands"]

    _react(client, "dave-1:Back Squat", "fire")
    still = client.get("/api/v1/buddy/home").json()["buddy_records"][0]
    assert still["reactions"] == ["fire", "hands"]


def test_unknown_record_and_bad_reaction(client, db_session, test_user):
    dave = _seed_dave(db_session)
    _pair(db_session, test_user.id, dave.id)
    missing = _react(client, "dave-1:No Such Lift", "fire")
    assert missing.status_code == 404
    bad = client.put(
        "/api/v1/buddy/records/dave-1:Squat/reactions",
        json={"reaction": "thumbs"},
    )
    assert bad.status_code == 422


def test_account_reset_wipes_record_reactions(client, db_session, test_user):
    dave = _seed_dave(db_session)
    _pair(db_session, test_user.id, dave.id)
    _add_log(
        db_session,
        "dave-squat",
        dave.id,
        _today(),
        [{"name": "Back Squat", "sets": [{"weight": 125, "reps": 3}]}],
    )
    _react(client, "dave-1:Back Squat", "heart")
    counts = AccountService.reset_cloud_data(db_session, test_user.id)
    assert counts["buddy_record_reactions_deleted"] == 1
    assert db_session.query(BuddyRecordReaction).count() == 0
