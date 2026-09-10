from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, EmailStr, Field, field_validator

SupportCategory = Literal["bug", "question", "feedback", "account", "other"]


class SupportSubmitRequest(BaseModel):
    username: str = Field(min_length=1, max_length=40)
    email: EmailStr
    category: SupportCategory
    message: str = Field(min_length=8, max_length=4000)

    @field_validator("username")
    @classmethod
    def strip_username(cls, value: str) -> str:
        stripped = value.strip()
        if not stripped:
            raise ValueError("cannot be empty")
        return stripped

    @field_validator("email")
    @classmethod
    def normalize_email(cls, value: EmailStr) -> str:
        return str(value).strip().lower()

    @field_validator("message")
    @classmethod
    def strip_message(cls, value: str) -> str:
        stripped = value.strip()
        if len(stripped) < 8:
            raise ValueError("must be at least 8 characters")
        return stripped


class SupportSubmitResponse(BaseModel):
    id: str
