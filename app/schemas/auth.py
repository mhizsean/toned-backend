from __future__ import annotations

from pydantic import BaseModel, EmailStr, Field


class SignUpRequest(BaseModel):
    email: EmailStr
    password: str = Field(min_length=6, max_length=72)


class SignInRequest(BaseModel):
    email: EmailStr
    password: str = Field(min_length=6, max_length=72)


class ForgotPasswordRequest(BaseModel):
    email: EmailStr
    redirect_to: str | None = Field(
        default=None,
        description="Deep link / URL Supabase redirects to after the email link",
    )


class ResetPasswordRequest(BaseModel):
    password: str = Field(min_length=6, max_length=72)


class RefreshTokenRequest(BaseModel):
    refresh_token: str = Field(min_length=1)


class AuthUser(BaseModel):
    id: str
    email: str | None = None


class AuthSessionResponse(BaseModel):
    access_token: str | None = None
    refresh_token: str | None = None
    expires_in: int | None = None
    token_type: str | None = None
    user: AuthUser | None = None
    message: str | None = None


class MessageResponse(BaseModel):
    message: str
