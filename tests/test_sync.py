from tests.conftest import auth_headers


def test_sync_push_and_pull(client):
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
    pulled = pull.json()["workouts"]
    assert len(pulled) == 1
    assert pulled[0]["client_id"] == "client-session-1"
