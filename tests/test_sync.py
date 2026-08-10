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


def test_sync_merge_prefer_local_unions_and_resolves_conflicts(client):
    # Existing cloud state
    cloud = client.post(
        "/api/v1/sync/push",
        json={
            "workouts": [
                {
                    "date": "2026-07-01T10:00:00.000Z",
                    "client_id": "shared-session",
                    "exercises": [{"name": "Cloud Squat", "sets": [{"weight": 40, "reps": 5}]}],
                },
                {
                    "date": "2026-07-02T10:00:00.000Z",
                    "client_id": "cloud-only",
                    "exercises": [{"name": "Cloud Row", "sets": [{"weight": 30, "reps": 8}]}],
                },
            ],
            "schedule": {
                "Mon": {
                    "type": "gym",
                    "focuses": ["Upper Body"],
                    "exercises": [{"id": "0662", "name": "push-up"}],
                },
                "Wed": {
                    "type": "rest",
                    "focuses": [],
                    "exercises": [],
                },
            },
            "library": [{"id": "0662", "name": "push-up"}],
            "preferences": {
                "weight_unit": "kg",
                "signup_nudge_last_shown_at": "2026-07-01T00:00:00Z",
            },
        },
        headers=auth_headers(),
    )
    assert cloud.status_code == 200

    # Guest local snapshot conflicts on Mon + shared workout; adds Tue + library item
    merge = client.post(
        "/api/v1/sync/merge",
        json={
            "strategy": "prefer_local",
            "local": {
                "workouts": [
                    {
                        "date": "2026-07-01T12:00:00.000Z",
                        "client_id": "shared-session",
                        "exercises": [
                            {"name": "Local Squat", "sets": [{"weight": 60, "reps": 8}]}
                        ],
                    },
                    {
                        "date": "2026-07-03T10:00:00.000Z",
                        "client_id": "local-only",
                        "exercises": [
                            {"name": "Local Curl", "sets": [{"weight": 12, "reps": 12}]}
                        ],
                    },
                ],
                "schedule": {
                    "Mon": {
                        "type": "home",
                        "focuses": ["Glutes & Legs"],
                        "exercises": [
                            {"id": "3013", "name": "low glute bridge on floor"}
                        ],
                    },
                    "Tue": {
                        "type": "gym",
                        "focuses": ["Core"],
                        "exercises": [],
                    },
                },
                "library": [
                    {"id": "0662", "name": "push-up"},
                    {"id": None, "name": "My Curl"},
                ],
                "preferences": {
                    "weight_unit": "lb",
                    "signup_nudge_last_shown_at": "2026-08-01T00:00:00Z",
                },
            },
        },
        headers=auth_headers(),
    )
    assert merge.status_code == 200
    body = merge.json()
    assert body["strategy"] == "prefer_local"

    schedule = body["schedule"]["schedule"]
    assert schedule["Mon"]["type"] == "home"
    assert schedule["Mon"]["focuses"] == ["Glutes & Legs"]
    assert schedule["Tue"]["type"] == "gym"
    assert schedule["Wed"]["type"] == "rest"

    names = {item["name"] for item in body["library"]["items"]}
    assert names == {"push-up", "My Curl"}

    assert body["preferences"]["weight_unit"] == "lb"

    by_client = {w["client_id"]: w for w in body["workouts"]}
    assert set(by_client) == {"shared-session", "cloud-only", "local-only"}
    assert by_client["shared-session"]["exercises"][0]["name"] == "Local Squat"

    assert any("schedule.Mon" in n for n in body["notes"])


def test_sync_merge_union_combines_day_exercises(client):
    client.post(
        "/api/v1/sync/push",
        json={
            "schedule": {
                "Mon": {
                    "type": "gym",
                    "focuses": ["Upper Body"],
                    "exercises": [{"id": "0662", "name": "push-up"}],
                }
            }
        },
        headers=auth_headers(),
    )

    merge = client.post(
        "/api/v1/sync/merge",
        json={
            "strategy": "union",
            "local": {
                "schedule": {
                    "Mon": {
                        "type": "gym",
                        "focuses": ["Glutes & Legs"],
                        "exercises": [
                            {"id": "3013", "name": "low glute bridge on floor"}
                        ],
                    }
                }
            },
        },
        headers=auth_headers(),
    )
    assert merge.status_code == 200
    mon = merge.json()["schedule"]["schedule"]["Mon"]
    assert set(mon["focuses"]) == {"Upper Body", "Glutes & Legs"}
    assert {ex["id"] for ex in mon["exercises"]} == {"0662", "3013"}


def test_sync_merge_prefer_cloud_keeps_cloud_on_conflict(client):
    client.post(
        "/api/v1/sync/push",
        json={
            "schedule": {
                "Fri": {
                    "type": "gym",
                    "focuses": ["Cloud Focus"],
                    "exercises": [{"id": "0662", "name": "push-up"}],
                }
            },
            "preferences": {"weight_unit": "kg"},
        },
        headers=auth_headers(),
    )

    merge = client.post(
        "/api/v1/sync/merge",
        json={
            "strategy": "prefer_cloud",
            "local": {
                "schedule": {
                    "Fri": {
                        "type": "home",
                        "focuses": ["Local Focus"],
                        "exercises": [],
                    }
                },
                "preferences": {"weight_unit": "lb"},
            },
        },
        headers=auth_headers(),
    )
    assert merge.status_code == 200
    body = merge.json()
    assert body["schedule"]["schedule"]["Fri"]["type"] == "gym"
    assert body["schedule"]["schedule"]["Fri"]["focuses"] == ["Cloud Focus"]
    assert body["preferences"]["weight_unit"] == "kg"
