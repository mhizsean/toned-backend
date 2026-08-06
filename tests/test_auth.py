from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient

from app.core.deps import get_db
from app.main import create_app
from app.models.exercise import Exercise
from app.models.sync import SyncCursor
from app.models.workout_log import WorkoutLog
from app.models.user import User
from app.services.supabase_auth import SupabaseAuthError


@pytest.fixture
def auth_client(db_session) -> TestClient:
    """Client with DB override but real auth dependencies (no fake current user)."""
    app = create_app()

    def override_get_db():
        yield db_session

    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as client:
        yield client
    app.dependency_overrides.clear()


def test_signup_creates_session_and_user(auth_client, db_session):
    fake = {
        "access_token": "access-1",
        "refresh_token": "refresh-1",
        "expires_in": 3600,
        "token_type": "bearer",
        "user": {"id": "uid-signup", "email": "new@toned.app"},
    }
    with patch("app.routers.auth.SupabaseAuthService") as cls:
        cls.return_value.sign_up.return_value = fake
        response = auth_client.post(
            "/api/v1/auth/signup",
            json={"email": "new@toned.app", "password": "secret12"},
        )
    assert response.status_code == 201
    body = response.json()
    assert body["access_token"] == "access-1"
    assert body["user"]["id"] == "uid-signup"
    assert db_session.get(User, "uid-signup") is not None


def test_signin_invalid_credentials(auth_client):
    with patch("app.routers.auth.SupabaseAuthService") as cls:
        cls.return_value.sign_in.side_effect = SupabaseAuthError(
            "Invalid login credentials",
            status_code=400,
        )
        response = auth_client.post(
            "/api/v1/auth/signin",
            json={"email": "a@b.com", "password": "wrongpass"},
        )
    assert response.status_code == 400
    assert "Invalid" in response.json()["detail"]


def test_refresh_returns_new_session(auth_client, db_session):
    fake = {
        "access_token": "access-2",
        "refresh_token": "refresh-2",
        "expires_in": 3600,
        "token_type": "bearer",
        "user": {"id": "uid-refresh", "email": "r@toned.app"},
    }
    with patch("app.routers.auth.SupabaseAuthService") as cls:
        cls.return_value.refresh.return_value = fake
        response = auth_client.post(
            "/api/v1/auth/refresh",
            json={"refresh_token": "refresh-1"},
        )
    assert response.status_code == 200
    assert response.json()["access_token"] == "access-2"
    assert db_session.get(User, "uid-refresh") is not None


def test_forgot_password_generic_message(auth_client):
    with patch("app.routers.auth.SupabaseAuthService") as cls:
        cls.return_value.forgot_password.return_value = None
        response = auth_client.post(
            "/api/v1/auth/forgot-password",
            json={"email": "a@b.com"},
        )
    assert response.status_code == 200
    assert "reset link" in response.json()["message"].lower()


def test_reset_password_requires_token(auth_client):
    response = auth_client.post(
        "/api/v1/auth/reset-password",
        json={"password": "newpass1"},
    )
    assert response.status_code == 401


def test_reset_password_ok(auth_client):
    with patch("app.routers.auth.SupabaseAuthService") as cls:
        cls.return_value.reset_password.return_value = {"id": "uid"}
        response = auth_client.post(
            "/api/v1/auth/reset-password",
            headers={"Authorization": "Bearer recovery-token"},
            json={"password": "newpass1"},
        )
    assert response.status_code == 200
    cls.return_value.reset_password.assert_called_once_with("recovery-token", "newpass1")


def test_logout_ok(auth_client):
    with patch("app.routers.auth.SupabaseAuthService") as cls:
        cls.return_value.logout.return_value = None
        response = auth_client.post(
            "/api/v1/auth/logout",
            headers={"Authorization": "Bearer access-token"},
        )
    assert response.status_code == 200
    assert response.json()["message"] == "Signed out"


def test_reset_data_wipes_user_cloud_rows(client, db_session, test_user):
    db_session.add_all(
        [
            WorkoutLog(
                id="w1",
                client_id="c1",
                user_id=test_user.id,
                date="2026-08-06",
                exercises=[],
            ),
            Exercise(
                id="custom-1",
                name="My Curl",
                category="upper arms",
                body_part="upper arms",
                equipment="dumbbell",
                muscles=["biceps"],
                steps=["Curl"],
                tips=[],
                mistakes=[],
                is_custom=True,
                source="user",
                user_id=test_user.id,
            ),
            SyncCursor(user_id=test_user.id),
        ]
    )
    db_session.commit()

    response = client.post("/api/v1/auth/reset-data")
    assert response.status_code == 200
    assert db_session.get(WorkoutLog, "w1") is None
    assert db_session.get(Exercise, "custom-1") is None
    assert db_session.get(SyncCursor, test_user.id) is None
    # Account row kept
    assert db_session.get(User, test_user.id) is not None


def test_delete_account_hard_deletes_auth_and_neon(client, db_session, test_user):
    user_id = test_user.id
    db_session.add(
        WorkoutLog(
            id="w2",
            client_id="c2",
            user_id=user_id,
            date="2026-08-06",
            exercises=[],
        )
    )
    db_session.commit()

    with patch("app.routers.auth.SupabaseAuthService") as cls:
        cls.return_value.delete_user.return_value = None
        response = client.delete("/api/v1/auth/account")

    assert response.status_code == 200
    assert "permanently deleted" in response.json()["message"].lower()
    cls.return_value.delete_user.assert_called_once_with(user_id)
    assert db_session.get(WorkoutLog, "w2") is None
    assert db_session.get(User, user_id) is None
