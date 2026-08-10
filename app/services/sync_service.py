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
from app.schemas.library import LibraryExercise, LibraryReplaceRequest, LibraryResponse
from app.schemas.preferences import PreferencesReplaceRequest, PreferencesResponse
from app.schemas.schedule import DaySchedule, ScheduleReplaceRequest, ScheduleResponse
from app.schemas.session_template import SessionTemplateCreate, SessionTemplateRead
from app.schemas.sync import (
    MergeStrategy,
    SyncMergeRequest,
    SyncMergeResponse,
    SyncPushRequest,
    SyncPullResponse,
    SyncPushResponse,
)
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

    @staticmethod
    def merge(
        db: Session,
        user_id: str,
        payload: SyncMergeRequest,
    ) -> SyncMergeResponse:
        """Combine guest local data with cloud, persist, return full pull."""
        cloud = SyncService.pull_all(db, user_id, since=None)
        strategy = payload.strategy
        notes: list[str] = []
        local = payload.local

        merged_schedule, schedule_notes = SyncService._merge_schedule(
            local.schedule, cloud.schedule.schedule, strategy
        )
        notes.extend(schedule_notes)

        merged_library, library_notes = SyncService._merge_library(
            local.library, cloud.library.items, strategy
        )
        notes.extend(library_notes)

        merged_prefs, prefs_notes = SyncService._merge_preferences(
            local.preferences, cloud.preferences, strategy
        )
        notes.extend(prefs_notes)

        merged_workouts, workout_notes = SyncService._merge_workouts(
            local.workouts, cloud.workouts, strategy
        )
        notes.extend(workout_notes)

        merged_customs, custom_notes = SyncService._merge_custom_exercises(
            local.custom_exercises, cloud.custom_exercises, strategy
        )
        notes.extend(custom_notes)

        merged_templates, template_notes = SyncService._merge_templates(
            local.templates, cloud.templates, strategy
        )
        notes.extend(template_notes)

        SyncService.push_all(
            db,
            user_id,
            SyncPushRequest(
                workouts=merged_workouts,
                schedule=merged_schedule,
                library=merged_library,
                preferences=merged_prefs,
                custom_exercises=merged_customs,
                templates=merged_templates,
            ),
        )
        pulled = SyncService.pull_all(db, user_id, since=None)
        return SyncMergeResponse(
            **pulled.model_dump(),
            strategy=strategy,
            notes=notes,
        )

    @staticmethod
    def _pick_side(strategy: MergeStrategy, section: str, notes: list[str]) -> str:
        if strategy == "prefer_cloud":
            notes.append(f"{section}: conflict → cloud")
            return "cloud"
        # prefer_local and union conflicts fall back to local
        notes.append(f"{section}: conflict → local")
        return "local"

    @staticmethod
    def _merge_schedule(
        local: dict[str, DaySchedule] | None,
        cloud: dict[str, DaySchedule],
        strategy: MergeStrategy,
    ) -> tuple[dict[str, DaySchedule], list[str]]:
        notes: list[str] = []
        if local is None:
            return {k: v.model_copy(deep=True) for k, v in cloud.items()}, notes

        merged: dict[str, DaySchedule] = {}
        for day in set(local) | set(cloud):
            left = local.get(day)
            right = cloud.get(day)
            if left is None:
                merged[day] = right.model_copy(deep=True)  # type: ignore[union-attr]
            elif right is None:
                merged[day] = left.model_copy(deep=True)
            elif strategy == "union":
                focuses = list(dict.fromkeys([*left.focuses, *right.focuses]))
                seen: set[str] = set()
                exercises = []
                for ex in [*left.exercises, *right.exercises]:
                    key = (ex.id or "") + "|" + ex.name.strip().lower()
                    if key in seen:
                        continue
                    seen.add(key)
                    exercises.append(ex.model_copy(deep=True))
                day_type = left.type
                if left.type == "rest" and right.type != "rest":
                    day_type = right.type
                elif right.type == "rest" and left.type != "rest":
                    day_type = left.type
                elif left.type != right.type:
                    winner = SyncService._pick_side(strategy, f"schedule.{day}.type", notes)
                    day_type = left.type if winner == "local" else right.type
                merged[day] = DaySchedule(
                    type=day_type,
                    focuses=focuses,
                    exercises=exercises,
                )
                notes.append(f"schedule.{day}: unioned exercises/focuses")
            else:
                winner = SyncService._pick_side(strategy, f"schedule.{day}", notes)
                src = left if winner == "local" else right
                merged[day] = src.model_copy(deep=True)
        return merged, notes

    @staticmethod
    def _library_key(item: LibraryExercise) -> str:
        if item.id:
            return f"id:{item.id}"
        return f"name:{item.name.strip().lower()}"

    @staticmethod
    def _merge_library(
        local: list[LibraryExercise] | None,
        cloud: list[LibraryExercise],
        strategy: MergeStrategy,
    ) -> tuple[list[LibraryExercise], list[str]]:
        notes: list[str] = []
        if local is None:
            return [i.model_copy(deep=True) for i in cloud], notes

        by_key: dict[str, LibraryExercise] = {}
        # Seed with non-preferred side first so preferred overwrites
        first, second = (cloud, local) if strategy != "prefer_cloud" else (local, cloud)
        for item in first:
            by_key[SyncService._library_key(item)] = item.model_copy(deep=True)
        for item in second:
            key = SyncService._library_key(item)
            if key in by_key and by_key[key].model_dump() != item.model_dump():
                notes.append(f"library.{key}: conflict → {'cloud' if strategy == 'prefer_cloud' else 'local'}")
            by_key[key] = item.model_copy(deep=True)
        return list(by_key.values()), notes

    @staticmethod
    def _merge_preferences(
        local: PreferencesReplaceRequest | None,
        cloud: PreferencesResponse,
        strategy: MergeStrategy,
    ) -> tuple[PreferencesReplaceRequest, list[str]]:
        notes: list[str] = []
        cloud_as = PreferencesReplaceRequest(
            weight_unit=cloud.weight_unit,
            signup_nudge_last_shown_at=cloud.signup_nudge_last_shown_at,
            signup_nudge_dismissed_at=cloud.signup_nudge_dismissed_at,
        )
        if local is None:
            return cloud_as, notes

        if strategy == "prefer_cloud":
            notes.append("preferences: conflict → cloud")
            return cloud_as, notes
        if strategy == "prefer_local":
            notes.append("preferences: conflict → local")
            return local.model_copy(deep=True), notes

        # union: local weight unit; take later nudge timestamps
        last_shown = local.signup_nudge_last_shown_at
        cloud_shown = cloud.signup_nudge_last_shown_at
        if last_shown and cloud_shown:
            last_shown = max(last_shown, cloud_shown)
        else:
            last_shown = last_shown or cloud_shown

        dismissed = local.signup_nudge_dismissed_at
        cloud_dismissed = cloud.signup_nudge_dismissed_at
        if dismissed and cloud_dismissed:
            dismissed = max(dismissed, cloud_dismissed)
        else:
            dismissed = dismissed or cloud_dismissed

        notes.append("preferences: unioned (local weight_unit, max nudge timestamps)")
        return PreferencesReplaceRequest(
            weight_unit=local.weight_unit,
            signup_nudge_last_shown_at=last_shown,
            signup_nudge_dismissed_at=dismissed,
        ), notes

    @staticmethod
    def _workout_key(item: WorkoutLogCreate | WorkoutLogRead) -> str:
        if item.client_id:
            return f"client:{item.client_id}"
        if getattr(item, "id", None):
            return f"id:{item.id}"
        return f"date:{item.date}"

    @staticmethod
    def _workout_to_create(row: WorkoutLogRead) -> WorkoutLogCreate:
        return WorkoutLogCreate(
            id=row.id,
            date=row.date,
            client_id=row.client_id,
            exercises=row.exercises,
        )

    @staticmethod
    def _merge_workouts(
        local: list[WorkoutLogCreate],
        cloud: list[WorkoutLogRead],
        strategy: MergeStrategy,
    ) -> tuple[list[WorkoutLogCreate], list[str]]:
        notes: list[str] = []
        cloud_creates = [SyncService._workout_to_create(w) for w in cloud]
        by_key: dict[str, WorkoutLogCreate] = {}

        first, second = (
            (local, cloud_creates)
            if strategy == "prefer_cloud"
            else (cloud_creates, local)
        )
        for item in first:
            by_key[SyncService._workout_key(item)] = item.model_copy(deep=True)
        for item in second:
            key = SyncService._workout_key(item)
            if key in by_key:
                SyncService._pick_side(strategy, f"workouts.{key}", notes)
            by_key[key] = item.model_copy(deep=True)
        return list(by_key.values()), notes

    @staticmethod
    def _exercise_key(item: ExerciseCreate | ExerciseRead) -> str:
        if getattr(item, "id", None):
            return f"id:{item.id}"
        return f"name:{item.name.strip().lower()}"

    @staticmethod
    def _exercise_to_create(row: ExerciseRead) -> ExerciseCreate:
        return ExerciseCreate.model_validate(
            row.model_dump(
                exclude={"source", "user_id", "extra", "created_at", "updated_at"}
            )
        )

    @staticmethod
    def _merge_custom_exercises(
        local: list[ExerciseCreate],
        cloud: list[ExerciseRead],
        strategy: MergeStrategy,
    ) -> tuple[list[ExerciseCreate], list[str]]:
        notes: list[str] = []
        cloud_creates = [SyncService._exercise_to_create(e) for e in cloud]
        by_key: dict[str, ExerciseCreate] = {}
        first, second = (
            (local, cloud_creates)
            if strategy == "prefer_cloud"
            else (cloud_creates, local)
        )
        for item in first:
            by_key[SyncService._exercise_key(item)] = item.model_copy(deep=True)
        for item in second:
            key = SyncService._exercise_key(item)
            if key in by_key:
                SyncService._pick_side(strategy, f"custom_exercises.{key}", notes)
            by_key[key] = item.model_copy(deep=True)
        return list(by_key.values()), notes

    @staticmethod
    def _template_key(item: SessionTemplateCreate | SessionTemplateRead) -> str:
        if getattr(item, "id", None):
            return f"id:{item.id}"
        return f"title:{item.title.strip().lower()}"

    @staticmethod
    def _template_to_create(row: SessionTemplateRead) -> SessionTemplateCreate:
        return SessionTemplateCreate(
            id=row.id,
            title=row.title,
            emoji=row.emoji,
            description=row.description,
            focus=row.focus,
            category=row.category,
            duration_min=row.duration_min,
            exercises=row.exercises,
        )

    @staticmethod
    def _merge_templates(
        local: list[SessionTemplateCreate],
        cloud: list[SessionTemplateRead],
        strategy: MergeStrategy,
    ) -> tuple[list[SessionTemplateCreate], list[str]]:
        notes: list[str] = []
        # Only user templates are in cloud.templates from pull_all
        cloud_creates = [SyncService._template_to_create(t) for t in cloud]
        by_key: dict[str, SessionTemplateCreate] = {}
        first, second = (
            (local, cloud_creates)
            if strategy == "prefer_cloud"
            else (cloud_creates, local)
        )
        for item in first:
            by_key[SyncService._template_key(item)] = item.model_copy(deep=True)
        for item in second:
            key = SyncService._template_key(item)
            if key in by_key:
                SyncService._pick_side(strategy, f"templates.{key}", notes)
            by_key[key] = item.model_copy(deep=True)
        return list(by_key.values()), notes
