from __future__ import annotations

import re
import uuid
from datetime import datetime, timedelta, timezone

from fastapi import HTTPException, status
from sqlalchemy import func, or_
from sqlalchemy.orm import Session

from app.models.buddy import (
    BuddyBlock,
    BuddyCheer,
    BuddyLink,
    BuddyNudge,
    BuddyPresence,
    BuddyRecordReaction,
)
from app.models.exercise import Exercise
from app.models.preferences import UserPreferences
from app.models.profile import UserProfile
from app.models.schedule import UserSchedule
from app.models.user import User
from app.models.workout_log import WorkoutLog
from app.schemas.buddy import (
    BuddyActivityResponse,
    BuddyBlockRequest,
    BuddyCheerResponse,
    BuddyHomeRecord,
    BuddyHomeResponse,
    BuddyInviteRequest,
    BuddyNudgeResponse,
    BuddyPersonPublic,
    BuddyPresenceRequest,
    BuddyRecordReactionsRequest,
    BuddyRecordReactionsResponse,
    BuddySearchResponse,
    BuddyStateResponse,
    BUDDY_REACTIONS,
)
from app.services.buddy_activity import build_activity_items
from app.services.buddy_push import BuddyPushService
from app.services.workout_stats import (
    current_streak,
    day_key,
    personal_records,
    unique_day_keys,
    week_bounds,
    week_session_count,
)
from app.utils.username import normalize_username

EMAIL_PATTERN = re.compile(r"^[^\s@]+@[^\s@]+\.[^\s@]+$")
SEARCH_LIMIT = 20
OPEN_STATUSES = ("pending", "accepted")
PRESENCE_TTL = timedelta(hours=3)
DAILY_NUDGE_LIMIT = 3


def _is_email_query(raw: str) -> bool:
    return bool(EMAIL_PATTERN.fullmatch(raw.strip().lower()))


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _to_public_card(
    user: User,
    profile: UserProfile | None,
    *,
    invited_you: bool = False,
) -> BuddyPersonPublic:
    return BuddyPersonPublic(
        id=user.id,
        name=(profile.name if profile else "") or "",
        username=user.username,
        avatar_id=profile.avatar_id if profile else None,
        goals=list(profile.goals or []) if profile else [],
        experience=profile.experience if profile else None,
        frequency=profile.frequency if profile else None,
        invited_you=invited_you,
    )


def _card_for(db: Session, user: User, *, invited_you: bool = False) -> BuddyPersonPublic:
    return _to_public_card(user, db.get(UserProfile, user.id), invited_you=invited_you)


class BuddyService:
    @staticmethod
    def search(db: Session, viewer_id: str, query: str) -> BuddySearchResponse:
        q = query.strip()
        if not q:
            return BuddySearchResponse(users=[])

        if _is_email_query(q):
            rows = BuddyService._search_by_email(db, viewer_id, q)
        else:
            rows = BuddyService._search_by_username(db, viewer_id, q)

        return BuddySearchResponse(users=rows)

    @staticmethod
    def get_state(db: Session, viewer_id: str) -> BuddyStateResponse:
        link = BuddyService._open_link(db, viewer_id)
        if link is not None:
            other = BuddyService._other_user(db, link, viewer_id)
            if link.status == "accepted":
                view = "active"
            elif link.requester_id == viewer_id:
                view = "outgoing"
            else:
                view = "incoming"
            return BuddyStateResponse(
                status=view,
                person=_card_for(db, other, invited_you=view == "incoming"),
                invite_id=link.id if link.status == "pending" else None,
                declined_notice=False,
            )

        return BuddyStateResponse(
            status="none",
            declined_notice=BuddyService._has_unseen_decline(db, viewer_id),
        )

    @staticmethod
    def invite(
        db: Session,
        viewer_id: str,
        body: BuddyInviteRequest,
    ) -> BuddyStateResponse:
        target = BuddyService._resolve_target(db, body)
        if target.id == viewer_id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="You can't invite yourself",
            )
        if BuddyService._is_blocked(db, viewer_id, target.id):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You can't invite this user",
            )
        if BuddyService._open_link(db, viewer_id) is not None:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="You already have a buddy invite",
            )
        if BuddyService._open_link(db, target.id) is not None:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="They already have a buddy",
            )

        BuddyService._mark_declines_seen(db, viewer_id)
        link = BuddyLink(
            id=str(uuid.uuid4()),
            requester_id=viewer_id,
            addressee_id=target.id,
            status="pending",
        )
        db.add(link)
        db.commit()
        BuddyPushService.notify_event(
            db,
            recipient_id=target.id,
            actor_id=viewer_id,
            event="buddy-invite",
        )
        return BuddyService.get_state(db, viewer_id)

    @staticmethod
    def accept(db: Session, viewer_id: str, invite_id: str) -> BuddyStateResponse:
        link = BuddyService._pending_as_addressee(db, viewer_id, invite_id)
        link.status = "accepted"
        link.updated_at = _now()
        requester_id = link.requester_id
        db.commit()
        BuddyPushService.notify_event(
            db,
            recipient_id=requester_id,
            actor_id=viewer_id,
            event="buddy-accept",
        )
        return BuddyService.get_state(db, viewer_id)

    @staticmethod
    def decline(db: Session, viewer_id: str, invite_id: str) -> BuddyStateResponse:
        link = BuddyService._pending_as_addressee(db, viewer_id, invite_id)
        link.status = "declined"
        link.declined_seen_at = None
        link.updated_at = _now()
        requester_id = link.requester_id
        db.commit()
        BuddyPushService.notify_event(
            db,
            recipient_id=requester_id,
            actor_id=viewer_id,
            event="buddy-decline",
        )
        return BuddyService.get_state(db, viewer_id)

    @staticmethod
    def cancel(db: Session, viewer_id: str, invite_id: str) -> BuddyStateResponse:
        link = db.get(BuddyLink, invite_id)
        if (
            link is None
            or link.status != "pending"
            or link.requester_id != viewer_id
        ):
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Invite not found",
            )
        db.delete(link)
        db.commit()
        return BuddyService.get_state(db, viewer_id)

    @staticmethod
    def remove(db: Session, viewer_id: str) -> BuddyStateResponse:
        link = BuddyService._open_link(db, viewer_id)
        if link is None or link.status != "accepted":
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="You don't have a buddy to remove",
            )
        other_id = BuddyService._other_id(link, viewer_id)
        BuddyService._wipe_record_reactions(db, [viewer_id, other_id])
        db.delete(link)
        db.commit()
        return BuddyService.get_state(db, viewer_id)

    @staticmethod
    def block(
        db: Session,
        viewer_id: str,
        body: BuddyBlockRequest,
    ) -> BuddyStateResponse:
        target_id = (body.user_id or "").strip() or None
        if target_id is None:
            link = BuddyService._open_link(db, viewer_id)
            if link is None:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="No buddy to block",
                )
            target_id = BuddyService._other_id(link, viewer_id)
        if target_id == viewer_id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="You can't block yourself",
            )
        if db.get(User, target_id) is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found",
            )

        BuddyService._delete_links_between(db, viewer_id, target_id)
        BuddyService._wipe_record_reactions(db, [viewer_id, target_id])
        existing = db.get(BuddyBlock, (viewer_id, target_id))
        if existing is None:
            db.add(BuddyBlock(blocker_id=viewer_id, blocked_id=target_id))
        db.commit()
        return BuddyService.get_state(db, viewer_id)

    @staticmethod
    def get_home(
        db: Session,
        viewer_id: str,
        now: datetime | None = None,
    ) -> BuddyHomeResponse:
        now = now or _now()
        today = now.date()
        link = BuddyService._accepted_link(db, viewer_id)
        if link is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="You don't have a buddy",
            )
        buddy = BuddyService._other_user(db, link, viewer_id)
        your_logs = BuddyService._logs_for(db, viewer_id)
        buddy_logs = BuddyService._logs_for(db, buddy.id)
        your_days = unique_day_keys(your_logs)
        buddy_days = unique_day_keys(buddy_logs)
        today_key = today.isoformat()
        presence = BuddyService._live_presence(db, buddy.id, now)
        completed_today = today_key in set(buddy_days)

        if presence is not None:
            training_status = "in_progress"
            session_label = (presence.session_label or "").strip() or (
                BuddyService._session_label_for(db, buddy.id, today)
            )
            updated_at = presence.updated_at or presence.started_at
        elif completed_today:
            training_status = "completed"
            session_label = BuddyService._session_label_for(db, buddy.id, today)
            updated_at = BuddyService._latest_log_at(buddy_logs, today_key)
        else:
            training_status = "not_started"
            session_label = ""
            updated_at = None

        labels = BuddyService._rep_labels(db, your_logs + buddy_logs)
        used, left, limit = BuddyService._nudge_counts(db, viewer_id, today.isoformat())
        your_records = personal_records(
            your_logs,
            owner="you",
            today=today,
            rep_labels=labels,
            record_user_id=viewer_id,
        )
        buddy_records = personal_records(
            buddy_logs,
            owner="buddy",
            today=today,
            rep_labels=labels,
            record_user_id=buddy.id,
        )
        reactions = BuddyService._reactions_for_records(
            db, [row["id"] for row in your_records + buddy_records]
        )
        for row in your_records + buddy_records:
            row["reactions"] = reactions.get(row["id"], [])
        return BuddyHomeResponse(
            person=_card_for(db, buddy),
            training_status=training_status,
            session_label=session_label,
            updated_at=updated_at,
            streak_days=current_streak(buddy_days, today),
            your_week_sessions=week_session_count(your_days, today),
            buddy_week_sessions=week_session_count(buddy_days, today),
            your_records=[BuddyHomeRecord.model_validate(row) for row in your_records],
            buddy_records=[
                BuddyHomeRecord.model_validate(row) for row in buddy_records
            ],
            nudges_used=used,
            nudges_left=left,
            nudge_limit=limit,
        )

    @staticmethod
    def set_presence(
        db: Session,
        viewer_id: str,
        body: BuddyPresenceRequest,
    ) -> BuddyHomeResponse:
        if BuddyService._accepted_link(db, viewer_id) is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="You don't have a buddy",
            )
        existing = db.get(BuddyPresence, viewer_id)
        if body.status == "finished":
            if existing is not None:
                db.delete(existing)
                db.commit()
            return BuddyService.get_home(db, viewer_id)

        label = (body.session_label or "").strip() or None
        now = _now()
        if existing is None:
            db.add(
                BuddyPresence(
                    user_id=viewer_id,
                    started_at=now,
                    session_label=label,
                    updated_at=now,
                )
            )
        else:
            existing.started_at = now
            existing.session_label = label
            existing.updated_at = now
        db.commit()
        return BuddyService.get_home(db, viewer_id)

    @staticmethod
    def nudge(
        db: Session,
        viewer_id: str,
        now: datetime | None = None,
    ) -> BuddyNudgeResponse:
        now = now or _now()
        today_key = now.date().isoformat()
        link = BuddyService._accepted_link(db, viewer_id)
        if link is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="You don't have a buddy",
            )
        used, left, limit = BuddyService._nudge_counts(db, viewer_id, today_key)
        if left <= 0:
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail="Daily nudge limit reached",
            )
        buddy_id = BuddyService._other_id(link, viewer_id)
        db.add(
            BuddyNudge(
                id=str(uuid.uuid4()),
                from_user_id=viewer_id,
                to_user_id=buddy_id,
                day_key=today_key,
                created_at=now,
            )
        )
        db.commit()
        used += 1
        BuddyPushService.notify_event(
            db,
            recipient_id=buddy_id,
            actor_id=viewer_id,
            event="buddy-nudge",
        )
        return BuddyNudgeResponse(
            used=used,
            left=limit - used,
            limit=limit,
        )

    @staticmethod
    def get_activity(
        db: Session,
        viewer_id: str,
        now: datetime | None = None,
    ) -> BuddyActivityResponse:
        now = now or _now()
        link = BuddyService._accepted_link(db, viewer_id)
        if link is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="You don't have a buddy",
            )
        buddy = BuddyService._other_user(db, link, viewer_id)
        items = BuddyService._activity_items(db, viewer_id, buddy, now)
        return BuddyActivityResponse(items=items)

    @staticmethod
    def cheer(
        db: Session,
        viewer_id: str,
        activity_id: str,
    ) -> BuddyCheerResponse:
        activity_id = (activity_id or "").strip()
        items = BuddyService.get_activity(db, viewer_id).items
        match = next((item for item in items if item.id == activity_id), None)
        if match is None or not match.can_cheer:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Activity not found",
            )
        existing = db.get(BuddyCheer, (activity_id, viewer_id))
        if existing is None:
            db.add(BuddyCheer(activity_id=activity_id, user_id=viewer_id))
            db.commit()
            link = BuddyService._accepted_link(db, viewer_id)
            if link is not None:
                buddy = BuddyService._other_user(db, link, viewer_id)
                BuddyPushService.notify_event(
                    db,
                    recipient_id=buddy.id,
                    actor_id=viewer_id,
                    event="buddy-cheer",
                )
        return BuddyCheerResponse(id=activity_id, cheered=True)

    @staticmethod
    def toggle_record_reaction(
        db: Session,
        viewer_id: str,
        record_id: str,
        body: BuddyRecordReactionsRequest,
    ) -> BuddyRecordReactionsResponse:
        link = BuddyService._accepted_link(db, viewer_id)
        if link is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="You don't have a buddy",
            )
        buddy_id = BuddyService._other_id(link, viewer_id)
        resolved = BuddyService._resolve_record_id(
            db, record_id, viewer_id, buddy_id
        )
        existing = db.get(
            BuddyRecordReaction, (resolved, viewer_id, body.reaction)
        )
        if existing is None:
            db.add(
                BuddyRecordReaction(
                    record_id=resolved,
                    user_id=viewer_id,
                    reaction=body.reaction,
                )
            )
        else:
            db.delete(existing)
        db.commit()
        reactions = BuddyService._reactions_for_records(db, [resolved]).get(
            resolved, []
        )
        return BuddyRecordReactionsResponse(id=resolved, reactions=reactions)

    @staticmethod
    def _resolve_record_id(
        db: Session,
        raw: str,
        viewer_id: str,
        buddy_id: str,
    ) -> str:
        value = (raw or "").strip()
        if ":" not in value:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Record not found",
            )
        prefix, exercise = value.split(":", 1)
        exercise = exercise.strip()
        if prefix == "you":
            prefix = viewer_id
        elif prefix == "buddy":
            prefix = buddy_id
        if not exercise or prefix not in {viewer_id, buddy_id}:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Record not found",
            )
        names = {
            row["exercise"]
            for row in personal_records(
                BuddyService._logs_for(db, prefix),
                owner="buddy" if prefix == buddy_id else "you",
                today=_now().date(),
                limit=500,
                record_user_id=prefix,
            )
        }
        if exercise not in names:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Record not found",
            )
        return f"{prefix}:{exercise}"

    @staticmethod
    def _reactions_for_records(
        db: Session, record_ids: list[str]
    ) -> dict[str, list[str]]:
        if not record_ids:
            return {}
        rows = (
            db.query(BuddyRecordReaction)
            .filter(BuddyRecordReaction.record_id.in_(record_ids))
            .all()
        )
        grouped: dict[str, set[str]] = {}
        for row in rows:
            grouped.setdefault(row.record_id, set()).add(row.reaction)
        return {
            record_id: [item for item in BUDDY_REACTIONS if item in types]
            for record_id, types in grouped.items()
        }

    @staticmethod
    def _wipe_record_reactions(db: Session, user_ids: list[str]) -> None:
        if not user_ids:
            return
        (
            db.query(BuddyRecordReaction)
            .filter(
                or_(
                    BuddyRecordReaction.user_id.in_(user_ids),
                    or_(
                        *[
                            BuddyRecordReaction.record_id.startswith(f"{user_id}:")
                            for user_id in user_ids
                        ]
                    ),
                )
            )
            .delete(synchronize_session=False)
        )

    @staticmethod
    def _activity_items(db: Session, viewer_id: str, buddy: User, now: datetime):
        today = now.date()
        monday, sunday = week_bounds(today)
        your_logs = BuddyService._logs_for(db, viewer_id)
        buddy_logs = BuddyService._logs_for(db, buddy.id)
        labels = BuddyService._rep_labels(db, buddy_logs)
        prs = personal_records(
            buddy_logs,
            owner="buddy",
            today=today,
            rep_labels=labels,
            limit=20,
        )
        monday_key = monday.isoformat()
        sunday_key = sunday.isoformat()
        nudges = (
            db.query(BuddyNudge)
            .filter(
                or_(
                    (BuddyNudge.from_user_id == viewer_id)
                    & (BuddyNudge.to_user_id == buddy.id),
                    (BuddyNudge.from_user_id == buddy.id)
                    & (BuddyNudge.to_user_id == viewer_id),
                ),
                BuddyNudge.day_key >= monday_key,
                BuddyNudge.day_key <= sunday_key,
            )
            .all()
        )
        cheered_ids = {
            row.activity_id
            for row in db.query(BuddyCheer).filter(BuddyCheer.user_id == viewer_id).all()
        }
        profile = db.get(UserProfile, buddy.id)
        return build_activity_items(
            viewer_id=viewer_id,
            buddy_id=buddy.id,
            buddy_name=(profile.name if profile else "") or "",
            today=today,
            your_logs=your_logs,
            buddy_logs=buddy_logs,
            nudges=list(nudges),
            presence=BuddyService._live_presence(db, buddy.id, now),
            session_label_for=lambda user_id, day: BuddyService._session_label_for(
                db, user_id, day
            ),
            prs=prs,
            cheered_ids=cheered_ids,
        )

    @staticmethod
    def _nudge_limit(db: Session, user_id: str) -> int:
        row = db.get(UserPreferences, user_id)
        if row is not None and row.buddy_nudge_limit in (2, 3):
            return int(row.buddy_nudge_limit)
        return DAILY_NUDGE_LIMIT

    @staticmethod
    def _nudge_counts(
        db: Session,
        viewer_id: str,
        today_key: str,
    ) -> tuple[int, int, int]:
        limit = BuddyService._nudge_limit(db, viewer_id)
        used = (
            db.query(func.count(BuddyNudge.id))
            .filter(
                BuddyNudge.from_user_id == viewer_id,
                BuddyNudge.day_key == today_key,
            )
            .scalar()
            or 0
        )
        used = int(used)
        return used, max(0, limit - used), limit

    @staticmethod
    def _accepted_link(db: Session, user_id: str) -> BuddyLink | None:
        return (
            db.query(BuddyLink)
            .filter(
                BuddyLink.status == "accepted",
                or_(
                    BuddyLink.requester_id == user_id,
                    BuddyLink.addressee_id == user_id,
                ),
            )
            .first()
        )

    @staticmethod
    def _logs_for(db: Session, user_id: str) -> list[WorkoutLog]:
        return list(
            db.query(WorkoutLog)
            .filter(WorkoutLog.user_id == user_id)
            .order_by(WorkoutLog.date.desc(), WorkoutLog.updated_at.desc())
            .all()
        )

    @staticmethod
    def _rep_labels(db: Session, logs: list[WorkoutLog]) -> dict[str, str]:
        names: set[str] = set()
        for log in logs:
            for exercise in log.exercises or []:
                if isinstance(exercise, dict):
                    name = str(exercise.get("name") or "").strip()
                    if name:
                        names.add(name)
        if not names:
            return {}
        rows = (
            db.query(Exercise.name, Exercise.rep_label)
            .filter(Exercise.name.in_(names))
            .all()
        )
        return {name: label for name, label in rows if label}

    @staticmethod
    def _session_label_for(db: Session, user_id: str, today) -> str:
        schedule_row = db.get(UserSchedule, user_id)
        if schedule_row is None or not schedule_row.schedule:
            return ""
        weekday = ("Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun")[today.weekday()]
        day = schedule_row.schedule.get(weekday) or {}
        if not isinstance(day, dict):
            return ""
        focuses = day.get("focuses") or []
        if not focuses:
            return ""
        return str(focuses[0]).strip()

    @staticmethod
    def _latest_log_at(logs: list[WorkoutLog], today_key: str) -> datetime | None:
        latest: datetime | None = None
        for log in logs:
            if day_key(log.date) != today_key:
                continue
            stamp = log.updated_at or log.created_at
            if latest is None or (stamp is not None and stamp > latest):
                latest = stamp
        return latest

    @staticmethod
    def _live_presence(
        db: Session,
        user_id: str,
        now: datetime,
    ) -> BuddyPresence | None:
        row = db.get(BuddyPresence, user_id)
        if row is None:
            return None
        started = row.started_at
        if started is None:
            return None
        if started.tzinfo is None:
            started = started.replace(tzinfo=timezone.utc)
        compare = now if now.tzinfo else now.replace(tzinfo=timezone.utc)
        if compare - started > PRESENCE_TTL:
            return None
        return row

    @staticmethod
    def _excluded_ids(db: Session, viewer_id: str) -> set[str]:
        excluded = {viewer_id}
        excluded |= BuddyService._busy_user_ids(db)
        excluded |= BuddyService._blocked_with(db, viewer_id)
        return excluded

    @staticmethod
    def _busy_user_ids(db: Session) -> set[str]:
        rows = (
            db.query(BuddyLink.requester_id, BuddyLink.addressee_id)
            .filter(BuddyLink.status.in_(OPEN_STATUSES))
            .all()
        )
        ids: set[str] = set()
        for requester_id, addressee_id in rows:
            ids.add(requester_id)
            ids.add(addressee_id)
        return ids

    @staticmethod
    def _blocked_with(db: Session, viewer_id: str) -> set[str]:
        rows = (
            db.query(BuddyBlock)
            .filter(
                or_(
                    BuddyBlock.blocker_id == viewer_id,
                    BuddyBlock.blocked_id == viewer_id,
                )
            )
            .all()
        )
        other_ids: set[str] = set()
        for row in rows:
            other_ids.add(
                row.blocked_id if row.blocker_id == viewer_id else row.blocker_id
            )
        return other_ids

    @staticmethod
    def _is_blocked(db: Session, user_a: str, user_b: str) -> bool:
        return (
            db.get(BuddyBlock, (user_a, user_b)) is not None
            or db.get(BuddyBlock, (user_b, user_a)) is not None
        )

    @staticmethod
    def _open_link(db: Session, user_id: str) -> BuddyLink | None:
        return (
            db.query(BuddyLink)
            .filter(
                BuddyLink.status.in_(OPEN_STATUSES),
                or_(
                    BuddyLink.requester_id == user_id,
                    BuddyLink.addressee_id == user_id,
                ),
            )
            .first()
        )

    @staticmethod
    def _has_unseen_decline(db: Session, requester_id: str) -> bool:
        return (
            db.query(BuddyLink)
            .filter(
                BuddyLink.requester_id == requester_id,
                BuddyLink.status == "declined",
                BuddyLink.declined_seen_at.is_(None),
            )
            .first()
            is not None
        )

    @staticmethod
    def _mark_declines_seen(db: Session, requester_id: str) -> None:
        (
            db.query(BuddyLink)
            .filter(
                BuddyLink.requester_id == requester_id,
                BuddyLink.status == "declined",
                BuddyLink.declined_seen_at.is_(None),
            )
            .update({"declined_seen_at": _now()}, synchronize_session=False)
        )

    @staticmethod
    def _other_id(link: BuddyLink, viewer_id: str) -> str:
        return (
            link.addressee_id
            if link.requester_id == viewer_id
            else link.requester_id
        )

    @staticmethod
    def _other_user(db: Session, link: BuddyLink, viewer_id: str) -> User:
        user = db.get(User, BuddyService._other_id(link, viewer_id))
        if user is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found",
            )
        return user

    @staticmethod
    def _pending_as_addressee(
        db: Session,
        viewer_id: str,
        invite_id: str,
    ) -> BuddyLink:
        link = db.get(BuddyLink, invite_id)
        if link is None or link.status != "pending":
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Invite not found",
            )
        if link.addressee_id != viewer_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="This invite is not for you",
            )
        return link

    @staticmethod
    def _resolve_target(db: Session, body: BuddyInviteRequest) -> User:
        if body.email:
            user = (
                db.query(User)
                .filter(func.lower(User.email) == body.email.strip().lower())
                .first()
            )
        else:
            username = normalize_username(body.username or "")
            user = db.query(User).filter(User.username == username).first()
        if user is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="No user found",
            )
        return user

    @staticmethod
    def _delete_links_between(db: Session, user_a: str, user_b: str) -> None:
        (
            db.query(BuddyLink)
            .filter(
                or_(
                    (BuddyLink.requester_id == user_a)
                    & (BuddyLink.addressee_id == user_b),
                    (BuddyLink.requester_id == user_b)
                    & (BuddyLink.addressee_id == user_a),
                )
            )
            .delete(synchronize_session=False)
        )

    @staticmethod
    def _search_by_email(
        db: Session,
        viewer_id: str,
        email: str,
    ) -> list[BuddyPersonPublic]:
        excluded = BuddyService._excluded_ids(db, viewer_id)
        user = (
            db.query(User)
            .filter(func.lower(User.email) == email.strip().lower())
            .first()
        )
        if user is None or user.id in excluded:
            return []
        return [_card_for(db, user)]

    @staticmethod
    def _search_by_username(
        db: Session,
        viewer_id: str,
        raw: str,
    ) -> list[BuddyPersonPublic]:
        prefix = normalize_username(raw)
        if not prefix:
            return []

        excluded = BuddyService._excluded_ids(db, viewer_id)
        users = (
            db.query(User)
            .filter(
                User.id.notin_(excluded),
                User.username.isnot(None),
                User.username.ilike(f"{prefix}%"),
            )
            .order_by(User.username)
            .limit(SEARCH_LIMIT)
            .all()
        )
        return [_card_for(db, user) for user in users]
