from fastapi import APIRouter, HTTPException, Query, status

from app.core.deps import CurrentUser, DbSession, OptionalUser
from app.schemas.session_template import (
    AddTemplateToPlanRequest,
    AddTemplateToPlanResponse,
    SessionTemplateCreate,
    SessionTemplateListResponse,
    SessionTemplateRead,
    SessionTemplateUpdate,
)
from app.services.session_template_service import SessionTemplateService

router = APIRouter(prefix="/templates", tags=["templates"])


@router.get("", response_model=SessionTemplateListResponse)
def list_templates(
    db: DbSession,
    user: OptionalUser,
    category: str | None = Query(
        default=None,
        pattern="^(pre-workout|cardio|post-workout)$",
    ),
    source: str | None = Query(
        default=None,
        pattern="^(system|user)$",
        description="Omit for system + your saved templates when signed in",
    ),
) -> SessionTemplateListResponse:
    items, total = SessionTemplateService.list_templates(
        db,
        category=category,
        source=source,
        user_id=user.id if user else None,
    )
    return SessionTemplateListResponse(
        items=[SessionTemplateRead.model_validate(item) for item in items],
        total=total,
    )


@router.post("", response_model=SessionTemplateRead, status_code=status.HTTP_201_CREATED)
def create_template(
    body: SessionTemplateCreate,
    db: DbSession,
    user: CurrentUser,
) -> SessionTemplateRead:
    """Save as session template (e.g. from day-edit save sheet)."""
    row = SessionTemplateService.create_user_template(db, user.id, body)
    return SessionTemplateRead.model_validate(row)


@router.get("/{template_id}", response_model=SessionTemplateRead)
def get_template(
    template_id: str,
    db: DbSession,
    user: OptionalUser,
) -> SessionTemplateRead:
    row = SessionTemplateService.get_template(
        db,
        template_id,
        user_id=user.id if user else None,
    )
    if row is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Template not found",
        )
    return SessionTemplateRead.model_validate(row)


@router.post("/{template_id}/save", response_model=SessionTemplateRead, status_code=status.HTTP_201_CREATED)
def save_template(
    template_id: str,
    db: DbSession,
    user: CurrentUser,
) -> SessionTemplateRead:
    """Bookmark / copy a system template into the user's Saved library."""
    try:
        row = SessionTemplateService.save_template_copy(db, user.id, template_id)
    except LookupError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(exc),
        ) from exc
    return SessionTemplateRead.model_validate(row)


@router.post("/{template_id}/add-to-plan", response_model=AddTemplateToPlanResponse)
def add_template_to_plan(
    template_id: str,
    body: AddTemplateToPlanRequest,
    db: DbSession,
    user: CurrentUser,
) -> AddTemplateToPlanResponse:
    """Add template exercises into a weekday on the user's schedule."""
    try:
        schedule = SessionTemplateService.add_to_plan(db, user.id, template_id, body)
    except LookupError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(exc),
        ) from exc
    return AddTemplateToPlanResponse(
        schedule=schedule,
        message=f"Added to {body.day} ({body.mode})",
    )


@router.patch("/{template_id}", response_model=SessionTemplateRead)
def update_template(
    template_id: str,
    body: SessionTemplateUpdate,
    db: DbSession,
    user: CurrentUser,
) -> SessionTemplateRead:
    try:
        row = SessionTemplateService.update_user_template(
            db, user.id, template_id, body
        )
    except LookupError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(exc),
        ) from exc
    return SessionTemplateRead.model_validate(row)


@router.delete("/{template_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_template(
    template_id: str,
    db: DbSession,
    user: CurrentUser,
) -> None:
    try:
        SessionTemplateService.delete_user_template(db, user.id, template_id)
    except LookupError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(exc),
        ) from exc
