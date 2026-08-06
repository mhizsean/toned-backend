from dataclasses import dataclass

import jwt
from fastapi import HTTPException, status
from jwt import PyJWTError

from app.config import get_settings


@dataclass
class TokenPayload:
    sub: str
    email: str | None = None


def decode_supabase_jwt(token: str) -> TokenPayload:
    settings = get_settings()
    if not settings.supabase_jwt_secret:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Auth is not configured",
        )

    try:
        payload = jwt.decode(
            token,
            settings.supabase_jwt_secret,
            algorithms=["HS256"],
            audience="authenticated",
        )
    except PyJWTError as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token",
        ) from exc

    sub = payload.get("sub")
    if not sub:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token missing subject",
        )

    return TokenPayload(sub=sub, email=payload.get("email"))
