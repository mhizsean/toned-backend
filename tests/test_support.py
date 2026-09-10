from app.core.deps import get_optional_user
from app.models.support import SupportMessage


def test_submit_support_saves_message(client, db_session, test_user):
    response = client.post(
        "/api/v1/support",
        json={
            "username": "seanseun",
            "category": "bug",
            "message": "The rest timer froze after the third set.",
        },
    )
    assert response.status_code == 200
    body = response.json()
    assert body["id"]

    row = db_session.get(SupportMessage, body["id"])
    assert row is not None
    assert row.user_id == test_user.id
    assert row.username == "seanseun"
    assert row.category == "bug"
    assert "rest timer" in row.message


def test_submit_support_as_guest(client, db_session):
    client.app.dependency_overrides[get_optional_user] = lambda: None
    response = client.post(
        "/api/v1/support",
        json={
            "username": "guestlift",
            "category": "feedback",
            "message": "Love the weekly plan, keep going.",
        },
    )
    assert response.status_code == 200
    row = db_session.get(SupportMessage, response.json()["id"])
    assert row is not None
    assert row.user_id is None
    assert row.category == "feedback"


def test_submit_support_rejects_short_message(client):
    response = client.post(
        "/api/v1/support",
        json={
            "username": "seanseun",
            "category": "question",
            "message": "Hi",
        },
    )
    assert response.status_code == 422


def test_submit_support_rejects_invalid_category(client):
    response = client.post(
        "/api/v1/support",
        json={
            "username": "seanseun",
            "category": "billing",
            "message": "How do I change my plan?",
        },
    )
    assert response.status_code == 422
