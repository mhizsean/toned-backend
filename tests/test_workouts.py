def _workout(log_id: str = "session-1", elapsed_ms: int = 90_000):
    return {
        "id": log_id,
        "client_id": log_id,
        "date": "2026-09-08T12:00:00.000Z",
        "elapsed_ms": elapsed_ms,
        "exercises": [
            {"name": "Squat", "sets": [{"weight": 60, "reps": 8}]},
        ],
    }


def test_create_list_and_get_workout(client):
    created = client.post("/api/v1/workouts", json=_workout())
    assert created.status_code == 201
    body = created.json()
    assert body["id"] == "session-1"
    assert body["client_id"] == "session-1"
    assert body["elapsed_ms"] == 90_000
    assert body["exercises"][0]["name"] == "Squat"

    listed = client.get("/api/v1/workouts")
    assert listed.status_code == 200
    assert listed.json()["total"] == 1
    assert listed.json()["items"][0]["elapsed_ms"] == 90_000

    fetched = client.get("/api/v1/workouts/session-1")
    assert fetched.status_code == 200
    assert fetched.json()["id"] == "session-1"


def test_create_workout_is_idempotent_for_same_user(client):
    first = client.post("/api/v1/workouts", json=_workout(elapsed_ms=10_000))
    assert first.status_code == 201

    again = client.post("/api/v1/workouts", json=_workout(elapsed_ms=12_000))
    assert again.status_code == 201
    assert again.json()["elapsed_ms"] == 12_000

    listed = client.get("/api/v1/workouts")
    assert listed.json()["total"] == 1


def test_patch_and_delete_workout(client):
    client.post("/api/v1/workouts", json=_workout())

    patched = client.patch(
        "/api/v1/workouts/session-1",
        json={"elapsed_ms": 45_000},
    )
    assert patched.status_code == 200
    assert patched.json()["elapsed_ms"] == 45_000

    deleted = client.delete("/api/v1/workouts/session-1")
    assert deleted.status_code == 204

    missing = client.get("/api/v1/workouts/session-1")
    assert missing.status_code == 404


def test_create_workout_defaults_elapsed_ms(client):
    payload = _workout()
    del payload["elapsed_ms"]
    created = client.post("/api/v1/workouts", json=payload)
    assert created.status_code == 201
    assert created.json()["elapsed_ms"] == 0
