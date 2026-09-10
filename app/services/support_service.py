from __future__ import annotations

import uuid

from sqlalchemy.orm import Session

from app.models.support import SupportMessage
from app.schemas.support import SupportSubmitRequest, SupportSubmitResponse


class SupportService:
    @staticmethod
    def create(
        db: Session,
        body: SupportSubmitRequest,
        user_id: str | None,
    ) -> SupportSubmitResponse:
        row = SupportMessage(
            id=str(uuid.uuid4()),
            user_id=user_id,
            username=body.username.strip(),
            category=body.category,
            message=body.message.strip(),
        )
        db.add(row)
        db.commit()
        return SupportSubmitResponse(id=row.id)
