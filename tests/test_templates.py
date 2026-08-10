from app.models.session_template import SessionTemplate
from tests.conftest import auth_headers


def _seed_one(db_session, **overrides):
    row = SessionTemplate(
        id=overrides.get("id", "glutes-legs-full-warmup"),
        title=overrides.get("title", "Glutes & Legs – Full Warmup"),
        emoji="🍑",
        description="Test template",
        focus="Glutes & Legs",
        category=overrides.get("category", "pre-workout"),
        source=overrides.get("source", "system"),
        duration_min=10,
        sort_order=overrides.get("sort_order", 10),
        exercises=overrides.get(
            "exercises",
            [{"id": "3013", "name": "low glute bridge on floor", "sets": 2, "reps": 12}],
        ),
        user_id=overrides.get("user_id"),
    )
    db_session.add(row)
    db_session.commit()
    return row


def test_list_templates_public(client, db_session):
    _seed_one(db_session)
    _seed_one(
        db_session,
        id="steady-state-treadmill",
        title="20-min Incline Walk",
        category="cardio",
        sort_order=60,
    )

    response = client.get("/api/v1/templates")
    assert response.status_code == 200
    body = response.json()
    assert body["total"] == 2
    assert body["items"][0]["exercises"][0]["id"] == "3013"


def test_filter_by_category(client, db_session):
    _seed_one(db_session)
    _seed_one(
        db_session,
        id="hiit-bodyweight",
        title="10-min Bodyweight HIIT",
        category="cardio",
        sort_order=80,
    )

    response = client.get("/api/v1/templates?category=cardio")
    assert response.status_code == 200
    body = response.json()
    assert body["total"] == 1
    assert body["items"][0]["category"] == "cardio"


def test_get_template(client, db_session):
    _seed_one(db_session)
    response = client.get("/api/v1/templates/glutes-legs-full-warmup")
    assert response.status_code == 200
    assert response.json()["title"].startswith("Glutes")


def test_get_template_missing(client):
    response = client.get("/api/v1/templates/missing")
    assert response.status_code == 404


def test_create_template_from_day_edit(client):
    response = client.post(
        "/api/v1/templates",
        headers=auth_headers(),
        json={
            "title": "My Monday Block",
            "emoji": "🔥",
            "focus": "Upper Body",
            "category": "pre-workout",
            "duration_min": 12,
            "exercises": [
                {"id": "0662", "name": "push-up", "sets": 3, "reps": 10},
                {"id": None, "name": "My Custom Move", "sets": 2, "reps": 8},
            ],
        },
    )
    assert response.status_code == 201
    body = response.json()
    assert body["source"] == "user"
    assert body["user_id"] == "user-1"
    assert len(body["exercises"]) == 2


def test_save_system_template_to_library(client, db_session):
    _seed_one(db_session)
    response = client.post(
        "/api/v1/templates/glutes-legs-full-warmup/save",
        headers=auth_headers(),
    )
    assert response.status_code == 201
    body = response.json()
    assert body["source"] == "user"
    assert body["title"].startswith("Glutes")
    assert body["id"].startswith("saved-")


def test_add_template_to_plan_merge(client, db_session):
    _seed_one(
        db_session,
        exercises=[
            {"id": "3013", "name": "low glute bridge on floor", "sets": 2, "reps": 12},
            {"id": "1460", "name": "walking lunge", "sets": 2, "reps": 10},
        ],
    )
    # Seed an existing Mon with one exercise
    client.put(
        "/api/v1/schedule/Mon",
        headers=auth_headers(),
        json={
            "type": "gym",
            "focuses": ["Glutes & Legs"],
            "exercises": [{"id": "3013", "name": "low glute bridge on floor"}],
        },
    )

    response = client.post(
        "/api/v1/templates/glutes-legs-full-warmup/add-to-plan",
        headers=auth_headers(),
        json={"day": "Mon", "mode": "merge"},
    )
    assert response.status_code == 200
    day = response.json()["schedule"]["schedule"]["Mon"]
    names = [ex["name"] for ex in day["exercises"]]
    assert "low glute bridge on floor" in names
    assert "walking lunge" in names
    # no duplicate of 3013
    assert names.count("low glute bridge on floor") == 1


def test_add_template_to_plan_replace_new_day(client, db_session):
    _seed_one(db_session)
    response = client.post(
        "/api/v1/templates/glutes-legs-full-warmup/add-to-plan",
        headers=auth_headers(),
        json={"day": "Fri", "mode": "replace", "day_type": "home"},
    )
    assert response.status_code == 200
    day = response.json()["schedule"]["schedule"]["Fri"]
    assert day["type"] == "home"
    assert len(day["exercises"]) == 1


def test_delete_user_template(client, db_session):
    created = client.post(
        "/api/v1/templates",
        headers=auth_headers(),
        json={
            "title": "Temp",
            "focus": "Core & Posture",
            "category": "post-workout",
            "duration_min": 5,
            "exercises": [{"id": "0276", "name": "dead bug", "sets": 2, "reps": 8}],
        },
    ).json()
    response = client.delete(
        f"/api/v1/templates/{created['id']}",
        headers=auth_headers(),
    )
    assert response.status_code == 204
    assert client.get(f"/api/v1/templates/{created['id']}").status_code == 404
