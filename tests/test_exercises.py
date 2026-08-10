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


def test_patch_custom_exercise(client):
    created = client.post(
        "/api/v1/exercises",
        headers=auth_headers(),
        json={
            "name": "My Move",
            "category": "chest",
            "equipment": "body weight",
            "muscles": ["chest"],
            "steps": ["Do it"],
        },
    ).json()

    response = client.patch(
        f"/api/v1/exercises/{created['id']}",
        headers=auth_headers(),
        json={"name": "My Move v2", "steps": ["Do it slower"]},
    )
    assert response.status_code == 200
    body = response.json()
    assert body["name"] == "My Move v2"
    assert body["steps"] == ["Do it slower"]
    assert body["equipment"] == "body weight"


def test_patch_catalogue_forbidden(client, db_session):
    db_session.add(
        Exercise(
            id="0001",
            name="3/4 sit-up",
            category="waist",
            body_part="waist",
            equipment="body weight",
            muscles=["abs"],
            steps=["Lie down"],
            tips=[],
            mistakes=[],
            is_custom=False,
            source="exercises-dataset",
        )
    )
    db_session.commit()

    response = client.patch(
        "/api/v1/exercises/0001",
        headers=auth_headers(),
        json={"name": "Hacked"},
    )
    assert response.status_code == 404


def test_delete_custom_exercise(client):
    created = client.post(
        "/api/v1/exercises",
        headers=auth_headers(),
        json={
            "name": "Delete Me",
            "category": "back",
            "equipment": "body weight",
            "muscles": ["lats"],
            "steps": ["Pull"],
        },
    ).json()

    response = client.delete(
        f"/api/v1/exercises/{created['id']}",
        headers=auth_headers(),
    )
    assert response.status_code == 204
    assert client.get(f"/api/v1/exercises/{created['id']}").status_code == 404


def _seed_focus_catalogue(db_session):
    rows = [
        ("chest-1", "Bench Press", "chest"),
        ("legs-1", "Squat", "upper legs"),
        ("calf-1", "Calf Raise", "lower legs"),
        ("waist-1", "Crunch", "waist"),
        ("cardio-1", "Jump Rope", "cardio"),
        ("stretch-1", "Hamstring Stretch", "upper legs"),
    ]
    for eid, name, body_part in rows:
        db_session.add(
            Exercise(
                id=eid,
                name=name,
                category=body_part,
                body_part=body_part,
                equipment="body weight",
                muscles=[],
                steps=["Do it"],
                tips=[],
                mistakes=[],
                is_custom=False,
                source="exercises-dataset",
            )
        )
    db_session.commit()


def test_list_focus_mappings(client):
    response = client.get("/api/v1/exercises/focuses")
    assert response.status_code == 200
    body = response.json()
    assert "Upper Body" in body["focuses"]
    assert body["mapping"]["Upper Body"]["body_parts"] == [
        "chest",
        "back",
        "shoulders",
        "upper arms",
        "lower arms",
    ]
    assert body["mapping"]["Full Body"]["body_parts"] is None
    assert body["mapping"]["Active Recovery"]["match_stretch_names"] is True


def test_filter_by_focus_upper_body(client, db_session):
    _seed_focus_catalogue(db_session)

    response = client.get("/api/v1/exercises", params={"focus": "Upper Body"})
    assert response.status_code == 200
    names = {item["name"] for item in response.json()["items"]}
    assert names == {"Bench Press"}


def test_filter_by_focus_glutes_and_legs(client, db_session):
    _seed_focus_catalogue(db_session)

    response = client.get("/api/v1/exercises", params={"focus": "Glutes & Legs"})
    assert response.status_code == 200
    names = {item["name"] for item in response.json()["items"]}
    assert names == {"Squat", "Calf Raise", "Hamstring Stretch"}


def test_filter_by_focus_active_recovery_includes_stretches(client, db_session):
    _seed_focus_catalogue(db_session)

    response = client.get("/api/v1/exercises", params={"focus": "Active Recovery"})
    assert response.status_code == 200
    names = {item["name"] for item in response.json()["items"]}
    assert names == {"Jump Rope", "Hamstring Stretch"}


def test_filter_by_focus_full_body_returns_all(client, db_session):
    _seed_focus_catalogue(db_session)

    response = client.get("/api/v1/exercises", params={"focus": "Full Body"})
    assert response.status_code == 200
    assert response.json()["total"] == 6


def test_filter_by_focus_emoji_and_comma(client, db_session):
    _seed_focus_catalogue(db_session)

    response = client.get(
        "/api/v1/exercises",
        params={"focus": "💪 Upper Body,Core & Posture"},
    )
    assert response.status_code == 200
    names = {item["name"] for item in response.json()["items"]}
    assert names == {"Bench Press", "Crunch"}


def test_filter_by_unknown_focus_422(client):
    response = client.get("/api/v1/exercises", params={"focus": "Legs Day"})
    assert response.status_code == 422


def test_focus_includes_custom_with_app_category(client, db_session):
    _seed_focus_catalogue(db_session)
    client.post(
        "/api/v1/exercises",
        headers=auth_headers(),
        json={
            "name": "My Push",
            "category": "Upper Body",
            "equipment": "dumbbell",
            "muscles": ["chest"],
            "steps": ["Press"],
        },
    )

    response = client.get(
        "/api/v1/exercises",
        params={"focus": "Upper Body"},
        headers=auth_headers(),
    )
    assert response.status_code == 200
    names = {item["name"] for item in response.json()["items"]}
    assert "Bench Press" in names
    assert "My Push" in names
