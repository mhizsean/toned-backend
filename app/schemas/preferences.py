from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict

WeightUnit = Literal["kg", "lb"]
BuddyNudgeLimit = Literal[2, 3]


class PreferencesUpdate(BaseModel):
    weight_unit: WeightUnit | None = None
    buddy_nudge_limit: BuddyNudgeLimit | None = None
    signup_nudge_last_shown_at: datetime | None = None
    signup_nudge_dismissed_at: datetime | None = None


class PreferencesResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    weight_unit: WeightUnit = "kg"
    buddy_nudge_limit: BuddyNudgeLimit = 3
    signup_nudge_last_shown_at: datetime | None = None
    signup_nudge_dismissed_at: datetime | None = None
    updated_at: datetime | None = None


class PreferencesReplaceRequest(BaseModel):
    """Full snapshot for sync push."""

    weight_unit: WeightUnit = "kg"
    buddy_nudge_limit: BuddyNudgeLimit | None = None
    signup_nudge_last_shown_at: datetime | None = None
    signup_nudge_dismissed_at: datetime | None = None
