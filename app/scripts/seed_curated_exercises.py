"""Merge curated Toned exercises (data/exercises_seed.json) into the catalogue.

The third-party exercises-dataset is missing staples like barbell hip thrust.
This upserts those rows and overlays coaching (tips/mistakes/steps) onto
dataset rows when the normalized name already exists.
"""

from __future__ import annotations

import json
import re
from pathlib import Path

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.session import SessionLocal
from app.models import Exercise  # noqa: F401
from app.services.exercise_service import slugify

ROOT = Path(__file__).resolve().parents[2]
SEED_PATH = ROOT / "data" / "exercises_seed.json"
SOURCE = "toned-seed"

CATEGORY_TO_BODY_PART = {
    "Glutes & Legs": "upper legs",
    "Upper Body": "chest",
    "Core & Posture": "waist",
    "Full Body": "upper legs",
    "Active Recovery": "cardio",
}

MUSCLE_TO_BODY_PART = {
    "glutes": "upper legs",
    "hamstrings": "upper legs",
    "quads": "upper legs",
    "quadriceps": "upper legs",
    "inner thighs": "upper legs",
    "adductors": "upper legs",
    "abductors": "upper legs",
    "hip": "upper legs",
    "calves": "lower legs",
    "chest": "chest",
    "pectorals": "chest",
    "pecs": "chest",
    "back": "back",
    "lats": "back",
    "traps": "back",
    "shoulders": "shoulders",
    "deltoids": "shoulders",
    "front deltoids": "shoulders",
    "rear deltoids": "shoulders",
    "biceps": "upper arms",
    "triceps": "upper arms",
    "forearms": "lower arms",
    "core": "waist",
    "abs": "waist",
    "obliques": "waist",
    "neck": "neck",
}


def normalize_name(name: str) -> str:
    return re.sub(r"[^a-z0-9]+", " ", name.lower()).strip()


def load_seed(path: Path = SEED_PATH) -> list[dict]:
    if not path.exists():
        raise FileNotFoundError(f"Seed file not found: {path}")
    return json.loads(path.read_text(encoding="utf-8"))


def infer_body_part(item: dict) -> str:
    for muscle in item.get("muscles") or []:
        mapped = MUSCLE_TO_BODY_PART.get(str(muscle).strip().lower())
        if mapped:
            return mapped
    return CATEGORY_TO_BODY_PART.get(item.get("category") or "", "upper legs")


def curated_id(name: str) -> str:
    return f"toned-{slugify(name)}"


def to_payload(item: dict) -> dict:
    body_part = infer_body_part(item)
    name = item["name"].strip()
    return {
        "id": curated_id(name),
        "name": name,
        "category": body_part,
        "body_part": body_part,
        "equipment": (item.get("equipment") or "Bodyweight").strip(),
        "target": (item.get("muscles") or [None])[0],
        "media_id": None,
        "muscle_group": item.get("category"),
        "secondary_muscles": (item.get("muscles") or [])[1:] or [],
        "instructions": None,
        "instruction_steps": None,
        "rep_label": item.get("repLabel") or "reps",
        "exercise_type": (
            "stretch" if item.get("category") == "Active Recovery" else "strength"
        ),
        "tags": None,
        "muscles": item.get("muscles") or [],
        "steps": item.get("steps") or [],
        "tips": item.get("tips") or [],
        "mistakes": item.get("mistakes") or [],
        "is_custom": False,
        "source": SOURCE,
        "user_id": None,
        "extra": {"coaching_source": SOURCE},
    }


def _apply_coaching(exercise: Exercise, item: dict) -> bool:
    changed = False
    tips = item.get("tips") or []
    mistakes = item.get("mistakes") or []
    steps = item.get("steps") or []
    if tips and not exercise.tips:
        exercise.tips = tips
        changed = True
    if mistakes and not exercise.mistakes:
        exercise.mistakes = mistakes
        changed = True
    if steps and not exercise.steps:
        exercise.steps = steps
        changed = True
    return changed


def merge_curated(db: Session, records: list[dict]) -> tuple[int, int]:
    existing = list(
        db.scalars(select(Exercise).where(Exercise.is_custom.is_(False)))
    )
    by_name = {normalize_name(ex.name): ex for ex in existing}
    by_id = {ex.id: ex for ex in existing}

    created = 0
    coached = 0
    for item in records:
        name = (item.get("name") or "").strip()
        if not name:
            continue
        match = by_name.get(normalize_name(name)) or by_id.get(curated_id(name))
        if match:
            if _apply_coaching(match, item):
                coached += 1
            continue
        payload = to_payload(item)
        exercise = Exercise(**payload)
        db.add(exercise)
        by_name[normalize_name(name)] = exercise
        by_id[payload["id"]] = exercise
        created += 1
    return created, coached


def seed(db: Session | None = None) -> tuple[int, int]:
    records = load_seed()
    if db is not None:
        created, coached = merge_curated(db, records)
        db.commit()
        return created, coached

    with SessionLocal() as session:
        created, coached = merge_curated(session, records)
        session.commit()
        return created, coached


if __name__ == "__main__":
    created, coached = seed()
    print(f"Merged curated catalogue from {SEED_PATH}")
    print(f"  created: {created}")
    print(f"  coaching overlaid: {coached}")
