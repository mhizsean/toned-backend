from app.models.schedule import UserSchedule


def test_get_schedule_empty(client):
    response = client.get("/api/v1/schedule")
    assert response.status_code == 200
    body = response.json()
    assert body["schedule"] == {}
    assert body["updated_at"] is None


def test_put_full_schedule(client, db_session, test_user):
    payload = {
        "schedule": {
            "Mon": {
                "type": "gym",
                "focuses": ["Glutes & Legs"],
                "exercises": [
                    {"id": "0001", "name": "3/4 sit-up"},
                    {"id": None, "name": "My Custom Curl"},
                ],
            },
            "Wed": {"type": "rest", "focuses": [], "exercises": []},
        }
    }
    response = client.put("/api/v1/schedule", json=payload)
    assert response.status_code == 200
    body = response.json()
    assert body["schedule"]["Mon"]["exercises"][0]["id"] == "0001"
    assert body["schedule"]["Mon"]["exercises"][1]["name"] == "My Custom Curl"
    assert body["schedule"]["Wed"]["type"] == "rest"
    assert body["updated_at"] is not None

    row = db_session.get(UserSchedule, test_user.id)
    assert row is not None
    assert "Mon" in row.schedule


def test_put_and_delete_day(client):
    day = {
        "type": "home",
        "focuses": ["Core"],
        "exercises": [{"id": "0042", "name": "Plank"}],
    }
    response = client.put("/api/v1/schedule/Fri", json=day)
    assert response.status_code == 200
    assert response.json()["schedule"]["Fri"]["exercises"][0]["id"] == "0042"

    response = client.delete("/api/v1/schedule/Fri")
    assert response.status_code == 200
    assert "Fri" not in response.json()["schedule"]


def test_invalid_day_rejected(client):
    response = client.put(
        "/api/v1/schedule/Monday",
        json={"type": "gym", "focuses": [], "exercises": []},
    )
    assert response.status_code == 422
