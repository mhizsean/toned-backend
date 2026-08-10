from datetime import datetime

from fastapi import APIRouter, Query

from app.core.deps import CurrentUser, DbSession
from app.schemas.sync import (
    SyncMergeRequest,
    SyncMergeResponse,
    SyncPullResponse,
    SyncPushRequest,
    SyncPushResponse,
)
from app.services.sync_service import SyncService

router = APIRouter(prefix="/sync", tags=["sync"])


@router.post("/push", response_model=SyncPushResponse)
def push_changes(
    payload: SyncPushRequest,
    db: DbSession,
    user: CurrentUser,
) -> SyncPushResponse:
    """
    Upload local changes. Sections omitted are left untouched.
    schedule / library are replaced entirely when sent (last-write-wins).
    """
    return SyncService.push_all(db, user.id, payload)


@router.get("/pull", response_model=SyncPullResponse)
def pull_changes(
    db: DbSession,
    user: CurrentUser,
    since: datetime | None = Query(
        default=None,
        description="Only return workouts/customs/templates updated after this time",
    ),
) -> SyncPullResponse:
    """Download cloud state. Schedule + library always returned in full."""
    return SyncService.pull_all(db, user.id, since=since)


@router.post("/full", response_model=SyncPullResponse)
def sync_full(
    payload: SyncPushRequest,
    db: DbSession,
    user: CurrentUser,
) -> SyncPullResponse:
    """Push then pull — convenient after login / app open."""
    SyncService.push_all(db, user.id, payload)
    return SyncService.pull_all(db, user.id, since=None)


@router.post("/merge", response_model=SyncMergeResponse)
def sync_merge(
    payload: SyncMergeRequest,
    db: DbSession,
    user: CurrentUser,
) -> SyncMergeResponse:
    """
    First-login merge: combine guest `local` snapshot with existing cloud data,
    persist the result, return full pull + conflict notes.

    Strategies:
    - prefer_local (default): guest device wins on conflicts; lists still union
    - prefer_cloud: cloud wins on conflicts (e.g. reinstall trusting server)
    - union: combine schedule days / lists; prefs take local weight_unit + max nudge times
    """
    return SyncService.merge(db, user.id, payload)
