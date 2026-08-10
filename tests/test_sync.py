from tests.conftest import auth_headers


def test_sync_push_and_pull_workouts(client):
    workout = {
        "date": "2026-07-03T10:00:00.000Z",
        "client_id": "client-session-1",
        "exercises": [
            {
                "name": "Squat",
                "sets": [{"weight": 60, "reps": 8}],
            }
        ],
    }

    push = client.post(
        "/api/v1/sync/push",
        json={"workouts": [workout]},
        headers=auth_headers(),
    )
    assert push.status_code == 200
    pushed = push.json()["workouts"]
    assert len(pushed) == 1
    assert pushed[0]["exercises"][0]["name"] == "Squat"

    pull = client.get("/api/v1/sync/pull", headers=auth_headers())
    assert pull.status_code == 200
    body = pull.json()
    assert len(body["workouts"]) == 1
    assert body["workouts"][0]["client_id"] == "client-session-1"
    assert body["schedule"]["schedule"] == {}
    assert body["library"]["items"] == []
    assert body["preferences"]["weight_unit"] == "kg"


def test_sync_push_schedule_library_and_full(client):
    payload = {
        "workouts": [],
        "schedule": {
            "Mon": {
                "type": "gym",
                "focuses": ["Glutes & Legs"],
                "exercises": [{"id": "3013", "name": "low glute bridge on floor"}],
            }
        },
        "library": [
            {"id": "0662", "name": "push-up"},
            {"id": None, "name": "My Curl"},
        ],
        "custom_exercises": [
            {
                "name": "Synced Custom",
                "category": "chest",
                "equipment": "body weight",
                "muscles": ["chest"],
                "steps": ["Push"],
            }
        ],
        "templates": [
            {
                "title": "Synced Template",
                "focus": "Upper Body",
                "category": "pre-workout",
                "duration_min": 8,
                "exercises": [
                    {"id": "0662", "name": "push-up", "sets": 2, "reps": 10}
                ],
            }
        ],
    }

    push = client.post("/api/v1/sync/push", json=payload, headers=auth_headers())
    assert push.status_code == 200
    pushed = push.json()
    assert pushed["schedule"]["schedule"]["Mon"]["type"] == "gym"
    assert len(pushed["library"]["items"]) == 2
    assert len(pushed["custom_exercises"]) == 1
    assert len(pushed["templates"]) == 1

    full = client.post("/api/v1/sync/full", json={}, headers=auth_headers())
    assert full.status_code == 200
    body = full.json()
    assert "Mon" in body["schedule"]["schedule"]
    assert len(body["library"]["items"]) == 2
    assert any(ex["name"] == "Synced Custom" for ex in body["custom_exercises"])
    assert any(t["title"] == "Synced Template" for t in body["templates"])
