import re
import uuid

from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session

from app.models.exercise import Exercise
from app.schemas.exercise import ExerciseCreate, ExerciseUpdate


def slugify(name: str) -> str:
    slug = name.lower().replace("'", "").replace("'", "")
    slug = re.sub(r"[^a-z0-9]+", "-", slug)
    return slug.strip("-")


class ExerciseService:
    @staticmethod
    def list_exercises(
        db: Session,
        *,
        user_id: str | None = None,
        category: str | None = None,
        body_part: str | None = None,
        search: str | None = None,
        skip: int = 0,
        limit: int = 100,
    ) -> tuple[list[Exercise], int]:
        # Catalogue (user_id IS NULL) is always public; customs only for owner.
        if user_id:
            query = select(Exercise).where(
                or_(Exercise.user_id.is_(None), Exercise.user_id == user_id)
            )
        else:
            query = select(Exercise).where(Exercise.user_id.is_(None))
        if category:
            query = query.where(Exercise.category == category)
        if body_part:
            query = query.where(Exercise.body_part == body_part)
        if search:
            pattern = f"%{search}%"
            query = query.where(Exercise.name.ilike(pattern))

        count_query = select(func.count()).select_from(query.subquery())
        total = db.scalar(count_query) or 0

        rows = db.scalars(
            query.order_by(Exercise.name).offset(skip).limit(limit)
        ).all()
        return list(rows), total

    @staticmethod
    def get_exercise(
        db: Session,
        exercise_id: str,
        *,
        user_id: str | None = None,
    ) -> Exercise | None:
        return db.scalar(
            select(Exercise).where(
                Exercise.id == exercise_id,
                or_(Exercise.user_id.is_(None), Exercise.user_id == user_id),
            )
        )

    @staticmethod
    def _owned_custom(
        db: Session,
        exercise_id: str,
        user_id: str,
    ) -> Exercise | None:
        return db.scalar(
            select(Exercise).where(
                Exercise.id == exercise_id,
                Exercise.user_id == user_id,
                Exercise.is_custom.is_(True),
            )
        )

    @staticmethod
    def create_custom_exercise(
        db: Session,
        user_id: str,
        data: ExerciseCreate,
    ) -> Exercise:
        base_id = data.id or slugify(data.name)
        exercise_id = base_id
        if db.get(Exercise, exercise_id) is not None:
            exercise_id = f"{base_id}-{uuid.uuid4().hex[:8]}"

        exercise = Exercise(
            id=exercise_id,
            name=data.name,
            category=data.category,
            body_part=data.body_part or data.category,
            equipment=data.equipment,
            target=data.target,
            media_id=data.media_id,
            muscle_group=data.muscle_group,
            secondary_muscles=data.secondary_muscles,
            instructions=data.instructions,
            instruction_steps=data.instruction_steps,
            rep_label=data.rep_label,
            exercise_type=data.exercise_type,
            tags=data.tags,
            muscles=data.muscles,
            steps=data.steps,
            tips=data.tips,
            mistakes=data.mistakes,
            is_custom=True,
            source="user",
            user_id=user_id,
        )
        db.add(exercise)
        db.commit()
        db.refresh(exercise)
        return exercise

    @staticmethod
    def update_custom_exercise(
        db: Session,
        user_id: str,
        exercise_id: str,
        data: ExerciseUpdate,
    ) -> Exercise:
        exercise = ExerciseService._owned_custom(db, exercise_id, user_id)
        if exercise is None:
            raise LookupError("Custom exercise not found")

        updates = data.model_dump(exclude_unset=True)
        if "category" in updates and "body_part" not in updates:
            if exercise.body_part == exercise.category:
                updates["body_part"] = updates["category"]
        for key, value in updates.items():
            setattr(exercise, key, value)

        db.commit()
        db.refresh(exercise)
        return exercise

    @staticmethod
    def delete_custom_exercise(
        db: Session,
        user_id: str,
        exercise_id: str,
    ) -> None:
        exercise = ExerciseService._owned_custom(db, exercise_id, user_id)
        if exercise is None:
            raise LookupError("Custom exercise not found")
        db.delete(exercise)
        db.commit()
