from datetime import datetime

from pydantic import BaseModel, ConfigDict


class UserRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    email: str | None
    username: str | None = None
    created_at: datetime


class AuthMeResponse(BaseModel):
    user: UserRead
