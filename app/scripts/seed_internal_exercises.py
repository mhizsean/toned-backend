"""Seed internal exercises from data/exercises_seed.json into the database."""

from __future__ import annotations

import json
from pathlib import Path

from sqlalchemy import select

from app.db.session import SessionLocal
from app.models.exercise import Exercise
from app.services.exercise_service import slugify

ROOT = Path(__file__).resolve().parents[2]
SEED_PATH = ROOT / "data" / "exercises_seed.json"


def load_seed() -> list[dict]:
    if not SEED_PATH.exists():
        raise FileNotFoundError(f"Seed file not found: {SEED_PATH}")
    return json.loads(SEED_PATH.read_text(encoding="utf-8"))


def seed() -> int:
    records = load_seed()
    created = 0

    with SessionLocal() as db:
        for item in records:
            exercise_id = item.get("id") or slugify(item["name"])
            existing = db.scalar(select(Exercise).where(Exercise.id == exercise_id))
            payload = {
                "id": exercise_id,
                "name": item["name"],
                "category": item["category"],
                "equipment": item["equipment"],
                "rep_label": item.get("repLabel", "reps"),
                "exercise_type": item.get("exerciseType"),
                "tags": item.get("tags"),
                "muscles": item["muscles"],
                "steps": item["steps"],
                "tips": item["tips"],
                "mistakes": item["mistakes"],
                "is_custom": False,
                "source": "internal",
                "user_id": None,
            }
            if existing:
                for key, value in payload.items():
                    setattr(existing, key, value)
            else:
                db.add(Exercise(**payload))
                created += 1
        db.commit()

    return created


if __name__ == "__main__":
    count = seed()
    print(f"Seeded {count} new exercises from {SEED_PATH}")
