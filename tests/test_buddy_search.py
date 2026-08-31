from fastapi.testclient import TestClient

from app.core.deps import get_db
from app.main import create_app
from app.models.profile import UserProfile
from app.models.user import User


def _add_user(
    db_session,
    user_id: str,
    *,
    email: str,
    username: str | None = None,
    name: str = "",
    goals: list | None = None,
    experience: str | None = None,
    frequency: str | None = None,
    avatar_id: str | None = None,
) -> User:
    user = User(id=user_id, email=email, username=username)
    db_session.add(user)
    db_session.add(
        UserProfile(
            user_id=user_id,
            name=name,
            goals=goals or [],
            experience=experience,
            frequency=frequency,
            avatar_id=avatar_id,
        )
    )
    db_session.commit()
    return user


def test_search_requires_auth(db_session):
    app = create_app()

    def override_get_db():
        yield db_session

    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as bare:
        response = bare.get("/api/v1/buddies/search?q=dave")
    app.dependency_overrides.clear()
    assert response.status_code == 401


def test_empty_query_returns_no_users(client):
    response = client.get("/api/v1/buddies/search?q=")
    assert response.status_code == 200
    assert response.json() == {"users": []}


def test_search_by_username_prefix(client, db_session, test_user):
    test_user.username = "sean"
    db_session.commit()
    _add_user(
        db_session,
        "dave-1",
        email="dave@example.com",
        username="davefitness",
        name="Dave",
        goals=["build-muscle"],
        experience="intermediate",
        frequency="5-6x",
        avatar_id="toned-avatar-01",
    )
    _add_user(
        db_session,
        "rita-1",
        email="rita@example.com",
        username="rita",
        name="Rita",
        goals=["tone-up"],
        experience="beginner",
        frequency="3-4x",
    )

    response = client.get("/api/v1/buddies/search?q=@Dave")
    assert response.status_code == 200
    users = response.json()["users"]
    assert len(users) == 1
    dave = users[0]
    assert dave == {
        "id": "dave-1",
        "name": "Dave",
        "username": "davefitness",
        "avatar_id": "toned-avatar-01",
        "goals": ["build-muscle"],
        "experience": "intermediate",
        "frequency": "5-6x",
        "invited_you": False,
    }
    assert "email" not in dave


def test_search_excludes_self(client, db_session, test_user):
    test_user.username = "tester"
    db_session.commit()

    response = client.get("/api/v1/buddies/search?q=test")
    assert response.status_code == 200
    assert response.json()["users"] == []


def test_search_by_exact_email_does_not_return_email(client, db_session):
    _add_user(
        db_session,
        "hidden-1",
        email="hidden@example.com",
        username="quietlift",
        name="Quinn",
        goals=["general-fitness"],
        experience="advanced",
        frequency="daily",
    )

    miss = client.get("/api/v1/buddies/search?q=hidden@")
    assert miss.json()["users"] == []

    hit = client.get("/api/v1/buddies/search?q=Hidden@example.com")
    assert hit.status_code == 200
    users = hit.json()["users"]
    assert len(users) == 1
    assert users[0]["id"] == "hidden-1"
    assert users[0]["username"] == "quietlift"
    assert users[0]["goals"] == ["general-fitness"]
    assert users[0]["frequency"] == "daily"
    assert "email" not in users[0]


def test_search_email_does_not_match_self(client, db_session, test_user):
    response = client.get("/api/v1/buddies/search?q=test@example.com")
    assert response.status_code == 200
    assert response.json()["users"] == []


def test_search_unknown_returns_empty(client):
    response = client.get("/api/v1/buddies/search?q=nobody")
    assert response.status_code == 200
    assert response.json()["users"] == []
