"""Map Toned app focuses → exercises-dataset body_part values."""

from __future__ import annotations

import re
from dataclasses import dataclass

# Must match Toned/src/data/exerciseTypes.ts EXERCISE_CATEGORIES
APP_FOCUSES = (
    "Glutes & Legs",
    "Upper Body",
    "Core & Posture",
    "Full Body",
    "Active Recovery",
)

# Dataset body_part vocabulary (seeded catalogue).
DATASET_BODY_PARTS = (
    "upper arms",
    "upper legs",
    "back",
    "waist",
    "chest",
    "shoulders",
    "lower legs",
    "lower arms",
    "cardio",
    "neck",
)


@dataclass(frozen=True)
class FocusRule:
    """How to filter catalogue + customs for one app focus."""

    # None = no body_part restriction (Full Body)
    body_parts: tuple[str, ...] | None
    # Also match names containing "stretch" (Active Recovery)
    match_stretch_names: bool = False


FOCUS_RULES: dict[str, FocusRule] = {
    "Glutes & Legs": FocusRule(body_parts=("upper legs", "lower legs")),
    "Upper Body": FocusRule(
        body_parts=("chest", "back", "shoulders", "upper arms", "lower arms")
    ),
    "Core & Posture": FocusRule(body_parts=("waist", "neck")),
    "Full Body": FocusRule(body_parts=None),
    "Active Recovery": FocusRule(
        body_parts=("cardio",),
        match_stretch_names=True,
    ),
}

_EMOJI_RE = re.compile(
    "["
    "\U0001F300-\U0001F9FF"
    "\U00002600-\U000026FF"
    "\U00002700-\U000027BF"
    "\U0001FA00-\U0001FAFF"
    "]+",
    flags=re.UNICODE,
)


def normalize_focus(raw: str) -> str | None:
    """Accept 'Upper Body' or '💪 Upper Body' → canonical focus label."""
    stripped = _EMOJI_RE.sub("", raw).strip()
    stripped = re.sub(r"\s+", " ", stripped)
    for focus in APP_FOCUSES:
        if stripped == focus or stripped.startswith(focus):
            return focus
    return None


def parse_focus_params(values: list[str] | None) -> list[str]:
    """
    Expand query values into canonical focuses.
    Supports repeated ?focus=A&focus=B and comma-separated ?focus=A,B.
    Raises ValueError on unknown labels.
    """
    if not values:
        return []

    found: list[str] = []
    seen: set[str] = set()
    for value in values:
        for part in value.split(","):
            part = part.strip()
            if not part:
                continue
            focus = normalize_focus(part)
            if focus is None:
                raise ValueError(
                    f"Unknown focus {part!r}. Expected one of: {', '.join(APP_FOCUSES)}"
                )
            if focus not in seen:
                seen.add(focus)
                found.append(focus)
    return found
