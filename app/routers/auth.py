from fastapi import APIRouter

from app.core.deps import CurrentUser
from app.schemas.user import AuthMeResponse, UserRead

router = APIRouter(prefix="/auth", tags=["auth"])


@router.get("/me", response_model=AuthMeResponse)
def get_me(user: CurrentUser) -> AuthMeResponse:
    return AuthMeResponse(user=UserRead.model_validate(user))
