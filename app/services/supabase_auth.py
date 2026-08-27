from __future__ import annotations

from typing import Any

import httpx
from fastapi import HTTPException, status

from app.config import Settings, get_settings


class SupabaseAuthError(Exception):
    def __init__(self, message: str, *, status_code: int = 400, code: str | None = None):
        super().__init__(message)
        self.message = message
        self.status_code = status_code
        self.code = code


class SupabaseAuthService:
    """Thin client for Supabase GoTrue (email/password auth)."""

    def __init__(self, settings: Settings | None = None) -> None:
        self.settings = settings or get_settings()

    def _ensure_configured(self) -> None:
        if not self.settings.supabase_url or not self.settings.supabase_anon_key:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Supabase auth is not configured",
            )

    def _ensure_admin_configured(self) -> None:
        self._ensure_configured()
        if not self.settings.supabase_service_role_key:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Supabase service role key is not configured",
            )

    def _headers(
        self,
        *,
        access_token: str | None = None,
        use_service_role: bool = False,
    ) -> dict[str, str]:
        if use_service_role:
            self._ensure_admin_configured()
            key = self.settings.supabase_service_role_key
        else:
            self._ensure_configured()
            key = self.settings.supabase_anon_key
        return {
            "apikey": key,
            "Authorization": f"Bearer {access_token or key}",
            "Content-Type": "application/json",
        }

    def _url(self, path: str) -> str:
        return f"{self.settings.supabase_url.rstrip('/')}/auth/v1{path}"

    def _request(
        self,
        method: str,
        path: str,
        *,
        json: dict[str, Any] | None = None,
        access_token: str | None = None,
        params: dict[str, str] | None = None,
        use_service_role: bool = False,
    ) -> dict[str, Any] | None:
        try:
            with httpx.Client(timeout=20.0, trust_env=False) as client:
                response = client.request(
                    method,
                    self._url(path),
                    headers=self._headers(
                        access_token=access_token,
                        use_service_role=use_service_role,
                    ),
                    json=json,
                    params=params,
                )
        except httpx.HTTPError as exc:
            raise HTTPException(
                status_code=status.HTTP_502_BAD_GATEWAY,
                detail=f"Auth provider unreachable: {exc}",
            ) from exc

        if response.status_code >= 400:
            payload: dict[str, Any]
            try:
                payload = response.json()
            except ValueError:
                payload = {"msg": response.text or "Auth request failed"}
            message = (
                payload.get("error_description")
                or payload.get("msg")
                or payload.get("error")
                or payload.get("message")
                or "Auth request failed"
            )
            raise SupabaseAuthError(
                str(message),
                status_code=response.status_code,
                code=payload.get("error_code") or payload.get("error"),
            )

        if response.status_code == 204 or not response.content:
            return None
        return response.json()

    def sign_up(self, email: str, password: str) -> dict[str, Any]:
        data = self._request(
            "POST",
            "/signup",
            json={"email": email, "password": password},
        )
        return data or {}

    def sign_in(self, email: str, password: str) -> dict[str, Any]:
        data = self._request(
            "POST",
            "/token",
            params={"grant_type": "password"},
            json={"email": email, "password": password},
        )
        return data or {}

    def refresh(self, refresh_token: str) -> dict[str, Any]:
        data = self._request(
            "POST",
            "/token",
            params={"grant_type": "refresh_token"},
            json={"refresh_token": refresh_token},
        )
        return data or {}

    def logout(self, access_token: str) -> None:
        self._request("POST", "/logout", access_token=access_token)

    def forgot_password(self, email: str, *, redirect_to: str | None = None) -> None:
        body: dict[str, Any] = {"email": email}
        if redirect_to:
            body["redirect_to"] = redirect_to
        self._request("POST", "/recover", json=body)

    def generate_link(
        self,
        email: str,
        *,
        link_type: str,
        redirect_to: str | None = None,
        password: str | None = None,
    ) -> dict[str, Any]:
        """Admin: create OTP/link without sending email (used for AUTH_DEV_OTP)."""
        body: dict[str, Any] = {"email": email, "type": link_type}
        if redirect_to:
            body["redirect_to"] = redirect_to
        if password:
            body["password"] = password
        data = self._request(
            "POST",
            "/admin/generate_link",
            json=body,
            use_service_role=True,
        )
        return data or {}

    def verify_otp(
        self,
        email: str,
        token: str,
        *,
        otp_type: str = "signup",
    ) -> dict[str, Any]:
        """Confirm email with the 6-digit code from the signup (or other) email."""
        data = self._request(
            "POST",
            "/verify",
            json={"email": email, "token": token, "type": otp_type},
        )
        return data or {}

    def resend_otp(self, email: str, *, otp_type: str = "signup") -> dict[str, Any] | None:
        """Resend signup / email_change OTP. Response is intentionally opaque."""
        return self._request(
            "POST",
            "/resend",
            json={"email": email, "type": otp_type},
        )

    def reset_password(self, access_token: str, new_password: str) -> dict[str, Any]:
        data = self._request(
            "PUT",
            "/user",
            access_token=access_token,
            json={"password": new_password},
        )
        return data or {}

    def delete_user(self, user_id: str) -> None:
        """Hard-delete Auth user so the same email can sign up again."""
        self._request(
            "DELETE",
            f"/admin/users/{user_id}",
            params={"should_soft_delete": "false"},
            use_service_role=True,
        )


def raise_as_http(exc: SupabaseAuthError) -> None:
    # Map common GoTrue codes to clearer client statuses
    code = (exc.status_code if 400 <= exc.status_code < 500 else 400)
    raise HTTPException(status_code=code, detail=exc.message) from exc
