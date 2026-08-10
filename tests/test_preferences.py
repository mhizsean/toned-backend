from tests.conftest import auth_headers


def test_preferences_defaults(client):
    response = client.get("/api/v1/preferences")
    assert response.status_code == 200
    body = response.json()
    assert body["weight_unit"] == "kg"
    assert body["signup_nudge_last_shown_at"] is None
    assert body["signup_nudge_dismissed_at"] is None


def test_preferences_patch(client):
    response = client.patch(
        "/api/v1/preferences",
        json={
            "weight_unit": "lb",
            "signup_nudge_last_shown_at": "2026-08-10T12:00:00Z",
        },
    )
    assert response.status_code == 200
    body = response.json()
    assert body["weight_unit"] == "lb"
    assert body["signup_nudge_last_shown_at"] is not None

    dismiss = client.patch(
        "/api/v1/preferences",
        json={"signup_nudge_dismissed_at": "2026-08-10T12:05:00Z"},
    )
    assert dismiss.status_code == 200
    assert dismiss.json()["signup_nudge_dismissed_at"] is not None
    assert dismiss.json()["weight_unit"] == "lb"


def test_preferences_in_sync(client):
    push = client.post(
        "/api/v1/sync/push",
        json={
            "preferences": {
                "weight_unit": "lb",
                "signup_nudge_dismissed_at": "2026-08-01T00:00:00Z",
            }
        },
        headers=auth_headers(),
    )
    assert push.status_code == 200
    assert push.json()["preferences"]["weight_unit"] == "lb"

    pull = client.get("/api/v1/sync/pull", headers=auth_headers())
    assert pull.status_code == 200
    assert pull.json()["preferences"]["weight_unit"] == "lb"
