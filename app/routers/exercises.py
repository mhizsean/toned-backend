from fastapi import APIRouter, HTTPException, Query, status

from app.core.deps import CurrentUser, DbSession, OptionalUser
from app.schemas.exercise import ExerciseCreate, ExerciseListResponse, ExerciseRead
from app.services.exercise_service import ExerciseService

router = APIRouter(prefix="/exercises", tags=["exercises"])


@router.get("", response_model=ExerciseListResponse)
def list_exercises(
    db: DbSession,
    user: OptionalUser,
    category: str | None = None,
    body_part: str | None = None,
    search: str | None = None,
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=500),
) -> ExerciseListResponse:
    """Public catalogue. Signed-in users also see their own custom exercises."""
    items, total = ExerciseService.list_exercises(
        db,
        user_id=user.id if user else None,
        category=category,
        body_part=body_part,
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
