from __future__ import annotations

from typing import Annotated, Any

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials
from sqlalchemy.orm import Session

from app.core.deps import CurrentUser, DbSession, security
from app.models.user import User
from app.schemas.auth import (
    AuthSessionResponse,
    AuthUser,
    ForgotPasswordRequest,
    MessageResponse,
    RefreshTokenRequest,
    ResetPasswordRequest,
    SignInRequest,
    SignUpRequest,
)
from app.schemas.user import AuthMeResponse, UserRead
from app.services.account_service import AccountService
from app.services.supabase_auth import (
    SupabaseAuthError,
    SupabaseAuthService,
    raise_as_http,
)

router = APIRouter(prefix="/auth", tags=["auth"])


def _upsert_user(db: Session, user_id: str, email: str | None) -> User:
    user = db.get(User, user_id)
    if user is None:
        user = User(id=user_id, email=email)
        db.add(user)
    elif email and user.email != email:
        user.email = email
    db.commit()
    db.refresh(user)
    return user


def _session_from_supabase(db: Session, payload: dict[str, Any]) -> AuthSessionResponse:
    raw_user = payload.get("user") or {}
    user_id = raw_user.get("id")
    email = raw_user.get("email")
    access_token = payload.get("access_token")

    local_user = None
    if user_id and access_token:
        local_user = _upsert_user(db, user_id, email)

    auth_user = None
    if user_id:
        auth_user = AuthUser(id=user_id, email=email or (local_user.email if local_user else None))

    message = None
    if not access_token and user_id:
        message = "Check your email to confirm your account before signing in."

    return AuthSessionResponse(
        access_token=access_token,
        refresh_token=payload.get("refresh_token"),
        expires_in=payload.get("expires_in"),
        token_type=payload.get("token_type"),
        user=auth_user,
        message=message,
    )


@router.get("/me", response_model=AuthMeResponse)
def get_me(user: CurrentUser) -> AuthMeResponse:
    return AuthMeResponse(user=UserRead.model_validate(user))


@router.post("/signup", response_model=AuthSessionResponse, status_code=status.HTTP_201_CREATED)
def sign_up(body: SignUpRequest, db: DbSession) -> AuthSessionResponse:
    auth = SupabaseAuthService()
    try:
        payload = auth.sign_up(str(body.email), body.password)
    except SupabaseAuthError as exc:
        raise_as_http(exc)
    return _session_from_supabase(db, payload)


@router.post("/signin", response_model=AuthSessionResponse)
def sign_in(body: SignInRequest, db: DbSession) -> AuthSessionResponse:
    auth = SupabaseAuthService()
    try:
        payload = auth.sign_in(str(body.email), body.password)
    except SupabaseAuthError as exc:
        raise_as_http(exc)
    return _session_from_supabase(db, payload)


@router.post("/refresh", response_model=AuthSessionResponse)
def refresh_session(body: RefreshTokenRequest, db: DbSession) -> AuthSessionResponse:
    """Exchange a refresh token for a new access/refresh pair (keeps users signed in)."""
    auth = SupabaseAuthService()
    try:
        payload = auth.refresh(body.refresh_token)
    except SupabaseAuthError as exc:
        raise_as_http(exc)
    return _session_from_supabase(db, payload)


@router.post("/logout", response_model=MessageResponse)
def logout(
    credentials: Annotated[
        HTTPAuthorizationCredentials | None,
        Depends(security),
    ],
) -> MessageResponse:
    if credentials is None or credentials.scheme.lower() != "bearer":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated",
        )
    auth = SupabaseAuthService()
    try:
        auth.logout(credentials.credentials)
    except SupabaseAuthError as exc:
        raise_as_http(exc)
    return MessageResponse(message="Signed out")


@router.post("/forgot-password", response_model=MessageResponse)
def forgot_password(body: ForgotPasswordRequest) -> MessageResponse:
    auth = SupabaseAuthService()
    try:
        auth.forgot_password(str(body.email), redirect_to=body.redirect_to)
    except SupabaseAuthError as exc:
        raise_as_http(exc)
    # Always generic — avoid email enumeration
    return MessageResponse(
        message="If an account exists for that email, a reset link has been sent."
    )


@router.post("/reset-password", response_model=MessageResponse)
def reset_password(
    body: ResetPasswordRequest,
    credentials: Annotated[
        HTTPAuthorizationCredentials | None,
        Depends(security),
    ],
) -> MessageResponse:
    """Requires the recovery (or logged-in) access token in Authorization."""
    if credentials is None or credentials.scheme.lower() != "bearer":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Recovery or session token required",
        )
    auth = SupabaseAuthService()
    try:
        auth.reset_password(credentials.credentials, body.password)
    except SupabaseAuthError as exc:
        raise_as_http(exc)
    return MessageResponse(message="Password updated")


@router.post("/reset-data", response_model=MessageResponse)
def reset_data(db: DbSession, user: CurrentUser) -> MessageResponse:
    """
    Wipe this user's cloud app data (workouts, custom exercises, sync state).
    Does not delete the Supabase account. Client should also clear local storage.
    """
    counts = AccountService.reset_cloud_data(db, user.id)
    return MessageResponse(
        message=(
            "Cloud data reset "
            f"({counts['workouts_deleted']} workouts, "
            f"{counts['custom_exercises_deleted']} custom exercises)"
        )
    )


@router.delete("/account", response_model=MessageResponse)
def delete_account(db: DbSession, user: CurrentUser) -> MessageResponse:
    """
    Hard-delete the account (not archive):
    - Removes Auth user in Supabase (email free for future signup)
    - Removes all Neon rows for this user
    Client should clear local storage and discard tokens afterward.
    """
    user_id = user.id
    auth = SupabaseAuthService()
    try:
        auth.delete_user(user_id)
    except SupabaseAuthError as exc:
        raise_as_http(exc)

    AccountService.delete_account_data(db, user_id)
    return MessageResponse(message="Account permanently deleted")
