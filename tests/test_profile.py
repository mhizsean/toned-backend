from app.models.profile import UserProfile
from app.models.user import User
from app.services.avatar_service import list_avatar_ids


def test_list_avatars_from_folder(client):
    response = client.get("/api/v1/profile/avatars")
    assert response.status_code == 200
    body = response.json()
    ids = [item["id"] for item in body["avatars"]]
    assert ids == list_avatar_ids()
    assert "toned-avatar-01" in ids
    assert len(ids) >= 10
    assert body["avatars"][0]["url"] == f"/profile/avatars/{ids[0]}"


def test_avatar_image_is_public(client):
    response = client.get("/api/v1/profile/avatars/toned-avatar-01")
    assert response.status_code == 200
    assert response.headers["content-type"].startswith("image/")
    assert len(response.content) > 100


def test_unknown_avatar_image_404(client):
    response = client.get("/api/v1/profile/avatars/not-a-real-avatar")
    assert response.status_code == 404


def test_get_profile_empty(client):
    response = client.get("/api/v1/profile")
    assert response.status_code == 200
    body = response.json()
    assert body["name"] == ""
    assert body["goals"] == []
    assert body["avatar_id"] is None
    assert body["updated_at"] is None


def test_patch_profile_saves_fields(client, db_session, test_user):
    response = client.patch(
        "/api/v1/profile",
        json={
            "name": "Sam",
            "age": "28",
            "gender": "female",
            "goals": ["tone-up", "build-muscle"],
            "frequency": "3-4x",
            "experience": "intermediate",
            "session_length": "45",
            "limitations": "Knee issues",
            "height": "165",
            "height_unit": "cm",
            "weight": "60",
            "weight_unit": "kg",
            "body_goal": "Get stronger",
            "body_goal_date": "Dec 2026",
            "train_location": "home",
            "favourite_exercises": ["Hip Thrust"],
            "avatar_id": "toned-avatar-03",
        },
    )
    assert response.status_code == 200
    body = response.json()
    assert body["name"] == "Sam"
    assert body["goals"] == ["tone-up", "build-muscle"]
    assert body["avatar_id"] == "toned-avatar-03"
    assert body["favourite_exercises"] == ["Hip Thrust"]
    assert body["updated_at"] is not None

    row = db_session.get(UserProfile, test_user.id)
    assert row is not None
    assert row.name == "Sam"
    assert row.avatar_id == "toned-avatar-03"


def test_patch_profile_sets_unique_username(client, db_session, test_user):
    response = client.patch(
        "/api/v1/profile",
        json={"username": "Sam_Lift"},
    )
    assert response.status_code == 200
    assert response.json()["username"] == "sam_lift"
    db_session.refresh(test_user)
    assert test_user.username == "sam_lift"


def test_patch_profile_rejects_taken_username(client, db_session, test_user):
    db_session.add(User(id="other", email="o@example.com", username="taken_name"))
    db_session.commit()
    response = client.patch(
        "/api/v1/profile",
        json={"username": "taken_name"},
    )
    assert response.status_code == 409


def test_patch_profile_rejects_unknown_avatar(client):
    response = client.patch(
        "/api/v1/profile",
        json={"avatar_id": "made-up-avatar"},
    )
    assert response.status_code == 422
