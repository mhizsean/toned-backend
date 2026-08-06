import re
import uuid

from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session

from app.models.exercise import Exercise
from app.schemas.exercise import ExerciseCreate


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
        search: str | None = None,
        skip: int = 0,
        limit: int = 100,
    ) -> tuple[list[Exercise], int]:
        query = select(Exercise).where(
            or_(Exercise.user_id.is_(None), Exercise.user_id == user_id)
        )
        if category:
            query = query.where(Exercise.category == category)
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
    def create_custom_exercise(
        db: Session,
        user_id: str,
        data: ExerciseCreate,
    ) -> Exercise:
        exercise_id = data.id or slugify(data.name)
        exercise = Exercise(
            id=exercise_id,
            name=data.name,
            category=data.category,
            equipment=data.equipment,
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
