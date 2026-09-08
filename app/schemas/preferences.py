from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict

WeightUnit = Literal["kg", "lb"]

NOTIFY_FIELDS = (
    "notify_buddy_completed",
    "notify_buddy_started",
    "notify_buddy_nudge",
    "notify_buddy_eod",
    "notify_buddy_reacted",
    "notify_end_of_day",
    "notify_session_inactivity",
    "notify_rest_complete",
    "notify_morning_plan",
    "notify_streak_at_risk",
    "notify_weekly_plan",
    "notifications_enabled",
)


class PreferencesUpdate(BaseModel):
    weight_unit: WeightUnit | None = None
    notify_buddy_completed: bool | None = None
    notify_buddy_started: bool | None = None
    notify_buddy_nudge: bool | None = None
    notify_buddy_eod: bool | None = None
    notify_buddy_reacted: bool | None = None
    notify_end_of_day: bool | None = None
    notify_session_inactivity: bool | None = None
    notify_rest_complete: bool | None = None
    notify_morning_plan: bool | None = None
    notify_streak_at_risk: bool | None = None
    notify_weekly_plan: bool | None = None
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
    notify_end_of_day: bool = True
    notify_session_inactivity: bool = True
    notify_rest_complete: bool = True
    notify_morning_plan: bool = True
    notify_streak_at_risk: bool = True
    notify_weekly_plan: bool = True
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
    notify_end_of_day: bool | None = None
    notify_session_inactivity: bool | None = None
    notify_rest_complete: bool | None = None
    notify_morning_plan: bool | None = None
    notify_streak_at_risk: bool | None = None
    notify_weekly_plan: bool | None = None
    notifications_enabled: bool | None = None
    signup_nudge_last_shown_at: datetime | None = None
    signup_nudge_dismissed_at: datetime | None = None
