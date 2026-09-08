from tests.conftest import auth_headers


def test_preferences_defaults(client):
    response = client.get("/api/v1/preferences")
    assert response.status_code == 200
    body = response.json()
    assert body["weight_unit"] == "kg"
    assert body["buddy_nudge_limit"] == 3
    assert body["notifications_enabled"] is True
    assert body["notify_end_of_day"] is True
    assert body["notify_session_inactivity"] is True
    assert body["notify_rest_complete"] is True
    assert body["notify_morning_plan"] is True
    assert body["notify_streak_at_risk"] is True
    assert body["notify_weekly_plan"] is True
    assert body["signup_nudge_last_shown_at"] is None
    assert body["signup_nudge_dismissed_at"] is None


def test_preferences_patch(client):
    response = client.patch(
        "/api/v1/preferences",
        json={
            "weight_unit": "lbs",
            "signup_nudge_last_shown_at": "2026-08-10T12:00:00Z",
        },
    )
    assert response.status_code == 200
    body = response.json()
    assert body["weight_unit"] == "lbs"
    assert body["signup_nudge_last_shown_at"] is not None

    dismiss = client.patch(
        "/api/v1/preferences",
        json={"signup_nudge_dismissed_at": "2026-08-10T12:05:00Z"},
    )
    assert dismiss.status_code == 200
    assert dismiss.json()["signup_nudge_dismissed_at"] is not None
    assert dismiss.json()["weight_unit"] == "lbs"


def test_preferences_nudge_limit_is_fixed_at_three(client):
    patched = client.patch("/api/v1/preferences", json={"buddy_nudge_limit": 2})
    assert patched.status_code == 200
    assert patched.json()["buddy_nudge_limit"] == 3

    still = client.get("/api/v1/preferences")
    assert still.json()["buddy_nudge_limit"] == 3


def test_preferences_accepts_legacy_lb_spelling(client):
    patched = client.patch("/api/v1/preferences", json={"weight_unit": "lb"})
    assert patched.status_code == 200
    assert patched.json()["weight_unit"] == "lbs"


def test_preferences_local_reminders_are_independent_of_buddy_eod(client):
    patched = client.patch(
        "/api/v1/preferences",
        json={
            "notify_end_of_day": False,
            "notify_session_inactivity": False,
            "notify_rest_complete": False,
            "notify_morning_plan": False,
            "notify_streak_at_risk": False,
            "notify_weekly_plan": False,
        },
    )
    assert patched.status_code == 200
    body = patched.json()
    assert body["notify_end_of_day"] is False
    assert body["notify_session_inactivity"] is False
    assert body["notify_rest_complete"] is False
    assert body["notify_morning_plan"] is False
    assert body["notify_streak_at_risk"] is False
    assert body["notify_weekly_plan"] is False
    assert body["notify_buddy_eod"] is True


def test_preferences_in_sync(client):
    push = client.post(
        "/api/v1/sync/push",
        json={
            "preferences": {
                "weight_unit": "lbs",
                "signup_nudge_dismissed_at": "2026-08-01T00:00:00Z",
            }
        },
        headers=auth_headers(),
    )
    assert push.status_code == 200
    assert push.json()["preferences"]["weight_unit"] == "lbs"
    assert push.json()["preferences"]["buddy_nudge_limit"] == 3

    pull = client.get("/api/v1/sync/pull", headers=auth_headers())
    assert pull.status_code == 200
    assert pull.json()["preferences"]["weight_unit"] == "lbs"
    assert pull.json()["preferences"]["buddy_nudge_limit"] == 3


def test_preferences_local_reminders_in_sync(client):
    push = client.post(
        "/api/v1/sync/push",
        json={
            "preferences": {
                "weight_unit": "kg",
                "notify_end_of_day": False,
                "notify_morning_plan": False,
                "notify_buddy_eod": True,
            }
        },
        headers=auth_headers(),
    )
    assert push.status_code == 200
    prefs = push.json()["preferences"]
    assert prefs["notify_end_of_day"] is False
    assert prefs["notify_morning_plan"] is False
    assert prefs["notify_buddy_eod"] is True
    assert prefs["notify_session_inactivity"] is True

    pull = client.get("/api/v1/sync/pull", headers=auth_headers())
    assert pull.json()["preferences"]["notify_end_of_day"] is False
    assert pull.json()["preferences"]["notify_buddy_eod"] is True
