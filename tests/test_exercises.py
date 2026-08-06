from app.models.exercise import Exercise
from tests.conftest import auth_headers


def test_list_exercises_empty(client):
    response = client.get("/api/v1/exercises", headers=auth_headers())
    assert response.status_code == 200
    body = response.json()
    assert body["items"] == []
    assert body["total"] == 0


def test_get_exercise_not_found(client):
    response = client.get("/api/v1/exercises/missing", headers=auth_headers())
    assert response.status_code == 404


def test_list_exercises_with_data(client, db_session):
    exercise = Exercise(
        id="hip-thrust-barbell",
        name="Hip Thrust (Barbell)",
        category="Glutes & Legs",
        equipment="Barbell",
        rep_label="reps",
        muscles=["Glutes"],
        steps=["Drive hips up"],
        tips=["Squeeze glutes"],
        mistakes=["Hyperextending"],
        is_custom=False,
        source="internal",
    )
    db_session.add(exercise)
    db_session.commit()

    response = client.get("/api/v1/exercises", headers=auth_headers())
    assert response.status_code == 200
    body = response.json()
    assert body["total"] == 1
    assert body["items"][0]["name"] == "Hip Thrust (Barbell)"
