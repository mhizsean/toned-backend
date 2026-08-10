def test_library_empty(client):
    response = client.get("/api/v1/library")
    assert response.status_code == 200
    body = response.json()
    assert body["items"] == []
    assert body["updated_at"] is None


def test_put_and_get_library(client):
    payload = {
        "items": [
            {"id": "0662", "name": "push-up"},
            {"id": None, "name": "My Custom Curl"},
            {"id": "0662", "name": "push-up"},  # duplicate ignored
        ]
    }
    response = client.put("/api/v1/library", json=payload)
    assert response.status_code == 200
    body = response.json()
    assert len(body["items"]) == 2
    assert body["items"][0]["id"] == "0662"
    assert body["updated_at"] is not None

    got = client.get("/api/v1/library")
    assert got.json()["items"] == body["items"]


def test_add_and_remove_library_item(client):
    client.put("/api/v1/library", json={"items": []})
    add = client.post(
        "/api/v1/library/items",
        json={"id": "3013", "name": "low glute bridge on floor"},
    )
    assert add.status_code == 200
    assert len(add.json()["items"]) == 1

    # idempotent add
    again = client.post(
        "/api/v1/library/items",
        json={"id": "3013", "name": "low glute bridge on floor"},
    )
    assert len(again.json()["items"]) == 1

    removed = client.delete("/api/v1/library/items?id=3013")
    assert removed.status_code == 200
    assert removed.json()["items"] == []


def test_remove_by_name(client):
    client.put(
        "/api/v1/library",
        json={"items": [{"id": None, "name": "Nordic Curl"}]},
    )
    response = client.delete("/api/v1/library/items?name=Nordic%20Curl")
    assert response.status_code == 200
    assert response.json()["items"] == []


def test_remove_requires_query(client):
    response = client.delete("/api/v1/library/items")
    assert response.status_code == 422
