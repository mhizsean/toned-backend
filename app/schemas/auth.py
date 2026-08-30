from __future__ import annotations

from pydantic import BaseModel, EmailStr, Field, field_validator

from app.utils.username import USERNAME_HINT, is_valid_username, normalize_username


class SignUpRequest(BaseModel):
    email: EmailStr
    password: str = Field(min_length=6, max_length=72)
    username: str = Field(min_length=3, max_length=21)

    @field_validator("username")
    @classmethod
    def normalize_and_validate_username(cls, value: str) -> str:
        username = normalize_username(value)
        if not is_valid_username(username):
            raise ValueError(USERNAME_HINT)
        return username


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


class VerifyOtpRequest(BaseModel):
    email: EmailStr
    token: str = Field(
        min_length=6,
        max_length=10,
        pattern=r"^\d+$",
        description="6–10 digit OTP from the confirmation email",
    )
    type: str = Field(
        default="signup",
        description="GoTrue verify type: signup | recovery | invite | magiclink | email_change",
    )
    username: str | None = Field(default=None, min_length=3, max_length=21)

    @field_validator("username")
    @classmethod
    def normalize_optional_username(cls, value: str | None) -> str | None:
        if value is None or not value.strip():
            return None
        username = normalize_username(value)
        if not is_valid_username(username):
            raise ValueError(USERNAME_HINT)
        return username


class ResendOtpRequest(BaseModel):
    email: EmailStr
    type: str = Field(
        default="signup",
        description="GoTrue resend type: signup | email_change",
    )


class AuthUser(BaseModel):
    id: str
    email: str | None = None
    username: str | None = None


class AuthSessionResponse(BaseModel):
    access_token: str | None = None
    refresh_token: str | None = None
    expires_in: int | None = None
    token_type: str | None = None
    user: AuthUser | None = None
    message: str | None = None


class MessageResponse(BaseModel):
    message: str


class UsernameAvailableResponse(BaseModel):
    available: bool
    reason: str | None = None
