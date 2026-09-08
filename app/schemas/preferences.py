from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict

WeightUnit = Literal["kg", "lb"]


class PreferencesUpdate(BaseModel):
    weight_unit: WeightUnit | None = None
    notify_buddy_completed: bool | None = None
    notify_buddy_started: bool | None = None
    notify_buddy_nudge: bool | None = None
    notify_buddy_eod: bool | None = None
    notify_buddy_reacted: bool | None = None
    notifications_enabled: bool | None = None
    signup_nudge_last_shown_at: datetime | None = None
    signup_nudge_dismissed_at: datetime | None = None


class PreferencesResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    weight_unit: WeightUnit = "kg"
    buddy_nudge_limit: Literal[3] = 3
    notify_buddy_completed: bool = True
    notify_buddy_started: bool = False
    notify_buddy_nudge: bool = True
    notify_buddy_eod: bool = True
    notify_buddy_reacted: bool = False
    notifications_enabled: bool = True
    signup_nudge_last_shown_at: datetime | None = None
    signup_nudge_dismissed_at: datetime | None = None
    updated_at: datetime | None = None


class PreferencesReplaceRequest(BaseModel):
    """Full snapshot for sync push."""

    weight_unit: WeightUnit = "kg"
    notify_buddy_completed: bool | None = None
    notify_buddy_started: bool | None = None
    notify_buddy_nudge: bool | None = None
    notify_buddy_eod: bool | None = None
    notify_buddy_reacted: bool | None = None
    notifications_enabled: bool | None = None
    signup_nudge_last_shown_at: datetime | None = None
    signup_nudge_dismissed_at: datetime | None = None
