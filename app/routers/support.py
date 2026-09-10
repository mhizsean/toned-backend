from fastapi import APIRouter

from app.core.deps import DbSession, OptionalUser
from app.schemas.support import SupportSubmitRequest, SupportSubmitResponse
from app.services.support_service import SupportService

router = APIRouter(prefix="/support", tags=["support"])


@router.post("", response_model=SupportSubmitResponse)
def submit_support(
    body: SupportSubmitRequest,
    db: DbSession,
    user: OptionalUser,
) -> SupportSubmitResponse:
    return SupportService.create(db, body, user.id if user else None)
