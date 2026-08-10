from fastapi import APIRouter, HTTPException, Query, status

from app.constants.focus import APP_FOCUSES, FOCUS_RULES, parse_focus_params
from app.core.deps import CurrentUser, DbSession, OptionalUser
from app.schemas.exercise import (
    ExerciseCreate,
    ExerciseListResponse,
    ExerciseRead,
    ExerciseUpdate,
)
from app.services.exercise_service import ExerciseService

router = APIRouter(prefix="/exercises", tags=["exercises"])


@router.get("/focuses")
def list_focus_mappings() -> dict:
    """Public: app focus labels → dataset body_part mapping."""
    return {
        "focuses": list(APP_FOCUSES),
        "mapping": {
            focus: {
                "body_parts": (
                    list(rule.body_parts) if rule.body_parts is not None else None
                ),
                "match_stretch_names": rule.match_stretch_names,
            }
            for focus, rule in FOCUS_RULES.items()
        },
    }


@router.get("", response_model=ExerciseListResponse)
def list_exercises(
    db: DbSession,
    user: OptionalUser,
    category: str | None = None,
    body_part: str | None = None,
    focus: list[str] | None = Query(
        default=None,
        description=(
            "App focus label(s), e.g. Upper Body. Repeat or comma-separate. "
            f"One of: {', '.join(APP_FOCUSES)}"
        ),
    ),
    search: str | None = None,
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=500),
) -> ExerciseListResponse:
    """Public catalogue. Signed-in users also see their own custom exercises."""
    try:
        focuses = parse_focus_params(focus)
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=str(exc),
        ) from exc

    items, total = ExerciseService.list_exercises(
        db,
        user_id=user.id if user else None,
        category=category,
        body_part=body_part,
        focuses=focuses,
        search=search,
        skip=skip,
        limit=limit,
    )
    return ExerciseListResponse(
        items=[ExerciseRead.model_validate(item) for item in items],
        total=total,
    )


@router.get("/{exercise_id}", response_model=ExerciseRead)
def get_exercise(
    exercise_id: str,
    db: DbSession,
    user: OptionalUser,
) -> ExerciseRead:
    """Public for catalogue exercises. Custom exercises require owning user."""
    exercise = ExerciseService.get_exercise(
        db,
        exercise_id,
        user_id=user.id if user else None,
    )
    if exercise is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Exercise not found")
    return ExerciseRead.model_validate(exercise)


@router.post("", response_model=ExerciseRead, status_code=status.HTTP_201_CREATED)
def create_custom_exercise(
    data: ExerciseCreate,
    db: DbSession,
    user: CurrentUser,
) -> ExerciseRead:
    """Creating custom exercises still requires auth."""
    exercise = ExerciseService.create_custom_exercise(db, user.id, data)
    return ExerciseRead.model_validate(exercise)


@router.patch("/{exercise_id}", response_model=ExerciseRead)
def update_custom_exercise(
    exercise_id: str,
    data: ExerciseUpdate,
    db: DbSession,
    user: CurrentUser,
) -> ExerciseRead:
    """Update own custom exercise only (catalogue rows are immutable)."""
    try:
        exercise = ExerciseService.update_custom_exercise(
            db, user.id, exercise_id, data
        )
    except LookupError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(exc),
        ) from exc
    return ExerciseRead.model_validate(exercise)


@router.delete("/{exercise_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_custom_exercise(
    exercise_id: str,
    db: DbSession,
    user: CurrentUser,
) -> None:
    """Delete own custom exercise only."""
    try:
        ExerciseService.delete_custom_exercise(db, user.id, exercise_id)
    except LookupError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(exc),
        ) from exc
