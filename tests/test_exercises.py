from app.models.exercise import Exercise
from tests.conftest import auth_headers


def test_list_exercises_empty_public(client):
    response = client.get("/api/v1/exercises")
    assert response.status_code == 200
    body = response.json()
    assert body["items"] == []
    assert body["total"] == 0


def test_get_exercise_not_found_public(client):
    response = client.get("/api/v1/exercises/missing")
    assert response.status_code == 404


def test_list_exercises_with_data_public(client, db_session):
    exercise = Exercise(
        id="hip-thrust-barbell",
        name="Hip Thrust (Barbell)",
        category="upper legs",
        body_part="upper legs",
        equipment="barbell",
        target="glutes",
        media_id=None,
        muscles=["glutes"],
        steps=["Drive hips up"],
        tips=["Squeeze glutes"],
        mistakes=["Hyperextending"],
        is_custom=False,
        source="exercises-dataset",
    )
    db_session.add(exercise)
    db_session.commit()

    response = client.get("/api/v1/exercises")
    assert response.status_code == 200
    body = response.json()
    assert body["total"] == 1
    assert body["items"][0]["name"] == "Hip Thrust (Barbell)"


def test_create_custom_exercise_requires_auth(db_session):
    from fastapi.testclient import TestClient

    from app.core.deps import get_db
    from app.main import create_app

    app = create_app()

    def override_get_db():
        yield db_session

    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as bare_client:
        response = bare_client.post(
            "/api/v1/exercises",
            json={
                "name": "My Move",
                "category": "chest",
                "equipment": "body weight",
                "muscles": ["chest"],
                "steps": ["Do it"],
            },
        )
    assert response.status_code == 401
    app.dependency_overrides.clear()


def test_create_custom_exercise_authenticated(client):
    response = client.post(
        "/api/v1/exercises",
        headers=auth_headers(),
        json={
            "name": "My Move",
            "category": "chest",
            "equipment": "body weight",
            "muscles": ["chest"],
            "steps": ["Do it"],
        },
    )
    assert response.status_code == 201
    body = response.json()
    assert body["name"] == "My Move"
    assert body["is_custom"] is True
