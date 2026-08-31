from __future__ import annotations

import re
import uuid
from datetime import datetime, timezone

from fastapi import HTTPException, status
from sqlalchemy import func, or_
from sqlalchemy.orm import Session

from app.models.buddy import BuddyBlock, BuddyLink
from app.models.profile import UserProfile
from app.models.user import User
from app.schemas.buddy import (
    BuddyBlockRequest,
    BuddyInviteRequest,
    BuddyPersonPublic,
    BuddySearchResponse,
    BuddyStateResponse,
)
from app.utils.username import normalize_username

EMAIL_PATTERN = re.compile(r"^[^\s@]+@[^\s@]+\.[^\s@]+$")
SEARCH_LIMIT = 20
OPEN_STATUSES = ("pending", "accepted")


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
        return BuddyService.get_state(db, viewer_id)

    @staticmethod
    def accept(db: Session, viewer_id: str, invite_id: str) -> BuddyStateResponse:
        link = BuddyService._pending_as_addressee(db, viewer_id, invite_id)
        link.status = "accepted"
        link.updated_at = _now()
        db.commit()
        return BuddyService.get_state(db, viewer_id)

    @staticmethod
    def decline(db: Session, viewer_id: str, invite_id: str) -> BuddyStateResponse:
        link = BuddyService._pending_as_addressee(db, viewer_id, invite_id)
        link.status = "declined"
        link.declined_seen_at = None
        link.updated_at = _now()
        db.commit()
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
        existing = db.get(BuddyBlock, (viewer_id, target_id))
        if existing is None:
            db.add(BuddyBlock(blocker_id=viewer_id, blocked_id=target_id))
        db.commit()
        return BuddyService.get_state(db, viewer_id)

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
