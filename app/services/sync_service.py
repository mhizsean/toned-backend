from __future__ import annotations

import uuid
from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.exercise import Exercise
from app.models.session_template import SessionTemplate
from app.models.sync import SyncCursor
from app.models.workout_log import WorkoutLog
from app.schemas.exercise import ExerciseCreate, ExerciseRead
from app.schemas.library import LibraryReplaceRequest, LibraryResponse
from app.schemas.preferences import PreferencesResponse
from app.schemas.schedule import ScheduleReplaceRequest, ScheduleResponse
from app.schemas.session_template import SessionTemplateCreate, SessionTemplateRead
from app.schemas.sync import SyncPushRequest, SyncPullResponse, SyncPushResponse
from app.schemas.workout_log import WorkoutLogCreate, WorkoutLogRead
from app.services.exercise_service import ExerciseService, slugify
from app.services.library_service import LibraryService
from app.services.preferences_service import PreferencesService
from app.services.schedule_service import ScheduleService
from app.services.session_template_service import SessionTemplateService


class SyncService:
    @staticmethod
    def push_workouts(
        db: Session,
        user_id: str,
        workouts: list[WorkoutLogCreate],
    ) -> list[WorkoutLog]:
        saved: list[WorkoutLog] = []
        for item in workouts:
            workout_id = item.id or str(uuid.uuid4())
            existing = db.get(WorkoutLog, workout_id)
            payload = {
                "date": item.date,
                "exercises": [ex.model_dump() for ex in item.exercises],
                "client_id": item.client_id or workout_id,
                "user_id": user_id,
            }
            if existing and existing.user_id == user_id:
                for key, value in payload.items():
                    setattr(existing, key, value)
                saved.append(existing)
            elif existing is None:
                log = WorkoutLog(id=workout_id, **payload)
                db.add(log)
                saved.append(log)
            else:
                # id owned by someone else — assign a new id
                workout_id = str(uuid.uuid4())
                log = WorkoutLog(id=workout_id, **payload)
                db.add(log)
                saved.append(log)

        SyncService._touch_cursor(db, user_id)
        db.commit()
        for row in saved:
            db.refresh(row)
        return saved

    @staticmethod
    def pull_workouts(
        db: Session,
        user_id: str,
        since: datetime | None = None,
    ) -> list[WorkoutLog]:
        query = select(WorkoutLog).where(WorkoutLog.user_id == user_id)
        if since:
            query = query.where(WorkoutLog.updated_at > since)
        return list(
            db.scalars(query.order_by(WorkoutLog.updated_at.asc())).all()
        )

    @staticmethod
    def _touch_cursor(db: Session, user_id: str) -> None:
        now = datetime.now(timezone.utc)
        cursor = db.get(SyncCursor, user_id)
        if cursor:
            cursor.last_synced_at = now
        else:
            db.add(SyncCursor(user_id=user_id, last_synced_at=now))

    @staticmethod
    def _upsert_custom_exercises(
        db: Session,
        user_id: str,
        items: list[ExerciseCreate],
    ) -> list[Exercise]:
        saved: list[Exercise] = []
        for data in items:
            base_id = data.id or slugify(data.name)
            existing = db.get(Exercise, base_id)
            if existing and existing.user_id == user_id and existing.is_custom:
                updates = data.model_dump(exclude={"id"})
                if not updates.get("body_part"):
                    updates["body_part"] = updates.get("category") or existing.body_part
                for key, value in updates.items():
                    setattr(existing, key, value)
                existing.is_custom = True
                existing.source = "user"
                saved.append(existing)
            elif existing is None:
                saved.append(
                    ExerciseService.create_custom_exercise(db, user_id, data)
                )
            else:
                # Collision with catalogue or another user — create with unique id
                clone = data.model_copy(update={"id": None})
                saved.append(
                    ExerciseService.create_custom_exercise(db, user_id, clone)
                )
        return saved

    @staticmethod
    def _upsert_templates(
        db: Session,
        user_id: str,
        items: list[SessionTemplateCreate],
    ) -> list[SessionTemplate]:
        saved: list[SessionTemplate] = []
        for data in items:
            if data.id:
                existing = db.get(SessionTemplate, data.id)
                if existing and existing.user_id == user_id and existing.source == "user":
                    existing.title = data.title
                    existing.emoji = data.emoji
                    existing.description = data.description
                    existing.focus = data.focus
                    existing.category = data.category
                    existing.duration_min = data.duration_min
                    existing.exercises = [
                        ex.model_dump(mode="json") for ex in data.exercises
                    ]
                    saved.append(existing)
                    continue
            saved.append(
                SessionTemplateService.create_user_template(db, user_id, data)
            )
        return saved

    @staticmethod
    def push_all(
        db: Session,
        user_id: str,
        payload: SyncPushRequest,
    ) -> SyncPushResponse:
        workouts = SyncService.push_workouts(db, user_id, payload.workouts)

        schedule: ScheduleResponse | None = None
        if payload.schedule is not None:
            schedule = ScheduleService.replace(
                db,
                user_id,
                ScheduleReplaceRequest(schedule=payload.schedule),
            )

        library: LibraryResponse | None = None
        if payload.library is not None:
            library = LibraryService.replace(
                db,
                user_id,
                LibraryReplaceRequest(items=payload.library),
            )

        preferences: PreferencesResponse | None = None
        if payload.preferences is not None:
            preferences = PreferencesService.replace(
                db, user_id, payload.preferences
            )

        customs = SyncService._upsert_custom_exercises(
            db, user_id, payload.custom_exercises
        )
        templates = SyncService._upsert_templates(db, user_id, payload.templates)

        SyncService._touch_cursor(db, user_id)
        db.commit()

        for row in customs:
            db.refresh(row)
        for row in templates:
            db.refresh(row)

        return SyncPushResponse(
            workouts=[WorkoutLogRead.model_validate(row) for row in workouts],
            schedule=schedule,
            library=library,
            preferences=preferences,
            custom_exercises=[ExerciseRead.model_validate(row) for row in customs],
            templates=[SessionTemplateRead.model_validate(row) for row in templates],
            server_time=datetime.now(timezone.utc),
        )

    @staticmethod
    def pull_custom_exercises(
        db: Session,
        user_id: str,
        since: datetime | None = None,
    ) -> list[Exercise]:
        query = select(Exercise).where(
            Exercise.user_id == user_id,
            Exercise.is_custom.is_(True),
        )
        if since:
            query = query.where(Exercise.updated_at > since)
        return list(db.scalars(query.order_by(Exercise.updated_at.asc())).all())

    @staticmethod
    def pull_user_templates(
        db: Session,
        user_id: str,
        since: datetime | None = None,
    ) -> list[SessionTemplate]:
        query = select(SessionTemplate).where(
            SessionTemplate.user_id == user_id,
            SessionTemplate.source == "user",
        )
        if since:
            query = query.where(SessionTemplate.updated_at > since)
        return list(
            db.scalars(query.order_by(SessionTemplate.updated_at.asc())).all()
        )

    @staticmethod
    def pull_all(
        db: Session,
        user_id: str,
        since: datetime | None = None,
    ) -> SyncPullResponse:
        workouts = SyncService.pull_workouts(db, user_id, since=since)
        customs = SyncService.pull_custom_exercises(db, user_id, since=since)
        templates = SyncService.pull_user_templates(db, user_id, since=since)
        # Schedule + library + preferences are small full snapshots (ignore since for v1)
        schedule = ScheduleService.get(db, user_id)
        library = LibraryService.get(db, user_id)
        preferences = PreferencesService.get(db, user_id)

        return SyncPullResponse(
            workouts=[WorkoutLogRead.model_validate(row) for row in workouts],
            schedule=schedule,
            library=library,
            preferences=preferences,
            custom_exercises=[ExerciseRead.model_validate(row) for row in customs],
            templates=[SessionTemplateRead.model_validate(row) for row in templates],
            server_time=datetime.now(timezone.utc),
        )
