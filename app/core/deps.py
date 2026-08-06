from collections.abc import Generator
from typing import Annotated

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session

from app.core.security import TokenPayload, decode_supabase_jwt
from app.db.session import get_db
from app.models.user import User

security = HTTPBearer(auto_error=False)


def get_current_user_payload(
    credentials: Annotated[
        HTTPAuthorizationCredentials | None,
        Depends(security),
    ],
) -> TokenPayload:
    if credentials is None or credentials.scheme.lower() != "bearer":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated",
        )
    return decode_supabase_jwt(credentials.credentials)


def get_current_user(
    db: Annotated[Session, Depends(get_db)],
    payload: Annotated[TokenPayload, Depends(get_current_user_payload)],
) -> User:
    user = db.get(User, payload.sub)
    if user is None:
        user = User(id=payload.sub, email=payload.email)
        db.add(user)
        db.commit()
        db.refresh(user)
    return user


DbSession = Annotated[Session, Depends(get_db)]
CurrentUser = Annotated[User, Depends(get_current_user)]
