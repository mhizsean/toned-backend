from __future__ import annotations

import uuid

from sqlalchemy import or_, select
from sqlalchemy.orm import Session

from app.models.session_template import SessionTemplate
from app.schemas.schedule import DaySchedule, ScheduledExercise
from app.schemas.session_template import (
    AddTemplateToPlanRequest,
    SessionTemplateCreate,
    SessionTemplateUpdate,
)
from app.services.exercise_service import slugify
from app.services.schedule_service import ScheduleService


class SessionTemplateService:
    @staticmethod
    def list_templates(
        db: Session,
        *,
        category: str | None = None,
        source: str | None = None,
        user_id: str | None = None,
    ) -> tuple[list[SessionTemplate], int]:
        query = select(SessionTemplate)

        if source == "system":
            query = query.where(SessionTemplate.source == "system")
        elif source == "user":
            if not user_id:
                return [], 0
            query = query.where(
                SessionTemplate.source == "user",
                SessionTemplate.user_id == user_id,
            )
        else:
            if user_id:
                query = query.where(
                    or_(
                        SessionTemplate.source == "system",
                        SessionTemplate.user_id == user_id,
                    )
                )
            else:
                query = query.where(SessionTemplate.source == "system")

        if category:
            query = query.where(SessionTemplate.category == category)

        rows = list(
            db.scalars(
                query.order_by(
                    SessionTemplate.sort_order.asc(),
                    SessionTemplate.title.asc(),
                )
            ).all()
        )
        return rows, len(rows)

    @staticmethod
    def get_template(
        db: Session,
        template_id: str,
        *,
        user_id: str | None = None,
    ) -> SessionTemplate | None:
        row = db.get(SessionTemplate, template_id)
        if row is None:
            return None
        if row.source == "system":
            return row
        if user_id and row.user_id == user_id:
            return row
        return None

    @staticmethod
    def _unique_id(db: Session, base: str) -> str:
        candidate = base[:80] or "template"
        if db.get(SessionTemplate, candidate) is None:
            return candidate
        return f"{candidate[:60]}-{uuid.uuid4().hex[:8]}"

    @staticmethod
    def create_user_template(
        db: Session,
        user_id: str,
        body: SessionTemplateCreate,
    ) -> SessionTemplate:
        base = body.id or slugify(body.title)
        template_id = SessionTemplateService._unique_id(db, base)
        row = SessionTemplate(
            id=template_id,
            title=body.title,
            emoji=body.emoji,
            description=body.description,
            focus=body.focus,
            category=body.category,
            source="user",
            duration_min=body.duration_min,
            sort_order=1000,
            exercises=[ex.model_dump(mode="json") for ex in body.exercises],
            user_id=user_id,
        )
        db.add(row)
        db.commit()
        db.refresh(row)
        return row

    @staticmethod
    def save_template_copy(
        db: Session,
        user_id: str,
        template_id: str,
    ) -> SessionTemplate:
        """Copy a system (or accessible) template into the user's saved library."""
        source = SessionTemplateService.get_template(db, template_id, user_id=user_id)
        if source is None:
            raise LookupError("Template not found")

        # Idempotent: if user already has a copy of this system id, return it
        existing_id = f"saved-{user_id[:8]}-{template_id}"[:100]
        existing = db.get(SessionTemplate, existing_id)
        if existing and existing.user_id == user_id:
            return existing

        copy_id = SessionTemplateService._unique_id(db, existing_id)
        row = SessionTemplate(
            id=copy_id,
            title=source.title,
            emoji=source.emoji,
            description=source.description,
            focus=source.focus,
            category=source.category,
            source="user",
            duration_min=source.duration_min,
            sort_order=source.sort_order,
            exercises=list(source.exercises or []),
            user_id=user_id,
        )
        db.add(row)
        db.commit()
        db.refresh(row)
        return row

    @staticmethod
    def update_user_template(
        db: Session,
        user_id: str,
        template_id: str,
        body: SessionTemplateUpdate,
    ) -> SessionTemplate:
        row = db.get(SessionTemplate, template_id)
        if row is None or row.user_id != user_id or row.source != "user":
            raise LookupError("Template not found")

        data = body.model_dump(exclude_unset=True)
        if body.exercises is not None:
            data["exercises"] = [ex.model_dump(mode="json") for ex in body.exercises]
        for key, value in data.items():
            setattr(row, key, value)
        db.commit()
        db.refresh(row)
        return row

    @staticmethod
    def delete_user_template(db: Session, user_id: str, template_id: str) -> None:
        row = db.get(SessionTemplate, template_id)
        if row is None or row.user_id != user_id or row.source != "user":
            raise LookupError("Template not found")
        db.delete(row)
        db.commit()

    @staticmethod
    def add_to_plan(
        db: Session,
        user_id: str,
        template_id: str,
        body: AddTemplateToPlanRequest,
    ):
        template = SessionTemplateService.get_template(
            db, template_id, user_id=user_id
        )
        if template is None:
            raise LookupError("Template not found")

        planned = [
            ScheduledExercise(
                id=ex.get("id") if isinstance(ex, dict) else getattr(ex, "id", None),
                name=ex["name"] if isinstance(ex, dict) else ex.name,
            )
            for ex in (template.exercises or [])
        ]

        current = ScheduleService.get(db, user_id)
        existing = current.schedule.get(body.day)

        if body.mode == "replace" or existing is None:
            focuses = list(existing.focuses) if existing and existing.focuses else []
            if template.focus and template.focus not in focuses:
                focuses = [template.focus] if not focuses else focuses
            day = DaySchedule(
                type=body.day_type if existing is None else (
                    body.day_type if body.mode == "replace" else existing.type
                ),
                focuses=focuses or ([template.focus] if template.focus else []),
                exercises=planned,
            )
        else:
            merged = list(existing.exercises)
            seen = {
                (ex.id or "").lower() + "|" + ex.name.lower()
                for ex in merged
            }
            for ex in planned:
                key = (ex.id or "").lower() + "|" + ex.name.lower()
                if key not in seen:
                    merged.append(ex)
                    seen.add(key)
            focuses = list(existing.focuses)
            if template.focus and template.focus not in focuses:
                focuses.append(template.focus)
            day = DaySchedule(
                type=existing.type if existing.type != "rest" else body.day_type,
                focuses=focuses,
                exercises=merged,
            )

        return ScheduleService.upsert_day(db, user_id, body.day, day)
