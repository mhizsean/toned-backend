from urllib.parse import unquote

from fastapi import APIRouter

from app.core.deps import CurrentUser, DbSession
from app.schemas.buddy import (
    BuddyActivityResponse,
    BuddyBlockRequest,
    BuddyCheerResponse,
    BuddyHomeResponse,
    BuddyInviteRequest,
    BuddyNudgeResponse,
    BuddyPresenceRequest,
    BuddyRecordReactionsRequest,
    BuddyRecordReactionsResponse,
    BuddyStateResponse,
)
from app.services.buddy_service import BuddyService

router = APIRouter(prefix="/buddy", tags=["buddy"])


@router.get("", response_model=BuddyStateResponse)
def get_buddy(db: DbSession, user: CurrentUser) -> BuddyStateResponse:
    return BuddyService.get_state(db, user.id)


@router.get("/home", response_model=BuddyHomeResponse)
def get_buddy_home(db: DbSession, user: CurrentUser) -> BuddyHomeResponse:
    return BuddyService.get_home(db, user.id)


@router.post("/presence", response_model=BuddyHomeResponse)
def set_buddy_presence(
    body: BuddyPresenceRequest,
    db: DbSession,
    user: CurrentUser,
) -> BuddyHomeResponse:
    return BuddyService.set_presence(db, user.id, body)


@router.post("/nudge", response_model=BuddyNudgeResponse)
def nudge_buddy(db: DbSession, user: CurrentUser) -> BuddyNudgeResponse:
    return BuddyService.nudge(db, user.id)


@router.get("/activity", response_model=BuddyActivityResponse)
def get_buddy_activity(db: DbSession, user: CurrentUser) -> BuddyActivityResponse:
    return BuddyService.get_activity(db, user.id)


@router.post("/activity/{activity_id}/cheer", response_model=BuddyCheerResponse)
def cheer_activity(
    activity_id: str,
    db: DbSession,
    user: CurrentUser,
) -> BuddyCheerResponse:
    return BuddyService.cheer(db, user.id, activity_id)


@router.put("/records/{record_id}/reactions", response_model=BuddyRecordReactionsResponse)
def toggle_record_reaction(
    record_id: str,
    body: BuddyRecordReactionsRequest,
    db: DbSession,
    user: CurrentUser,
) -> BuddyRecordReactionsResponse:
    return BuddyService.toggle_record_reaction(
        db, user.id, unquote(record_id), body
    )


@router.post("/invites", response_model=BuddyStateResponse)
def create_invite(
    body: BuddyInviteRequest,
    db: DbSession,
    user: CurrentUser,
) -> BuddyStateResponse:
    return BuddyService.invite(db, user.id, body)


@router.post("/invites/{invite_id}/accept", response_model=BuddyStateResponse)
def accept_invite(
    invite_id: str,
    db: DbSession,
    user: CurrentUser,
) -> BuddyStateResponse:
    return BuddyService.accept(db, user.id, invite_id)


@router.post("/invites/{invite_id}/decline", response_model=BuddyStateResponse)
def decline_invite(
    invite_id: str,
    db: DbSession,
    user: CurrentUser,
) -> BuddyStateResponse:
    return BuddyService.decline(db, user.id, invite_id)


@router.delete("/invites/{invite_id}", response_model=BuddyStateResponse)
def cancel_invite(
    invite_id: str,
    db: DbSession,
    user: CurrentUser,
) -> BuddyStateResponse:
    return BuddyService.cancel(db, user.id, invite_id)


@router.delete("", response_model=BuddyStateResponse)
def remove_buddy(db: DbSession, user: CurrentUser) -> BuddyStateResponse:
    return BuddyService.remove(db, user.id)


@router.post("/block", response_model=BuddyStateResponse)
def block_buddy(
    db: DbSession,
    user: CurrentUser,
    body: BuddyBlockRequest | None = None,
) -> BuddyStateResponse:
    return BuddyService.block(db, user.id, body or BuddyBlockRequest())
