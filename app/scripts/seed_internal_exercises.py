"""Seed exercises from the frozen hasaneyldrm/exercises-dataset JSON.

Source: https://github.com/hasaneyldrm/exercises-dataset
Pinned SHA: see data/exercises_dataset.sha

Media (image/gif) is © Gym Visual — we store media_id (+ paths in extra) only.
Do not serve Gym Visual assets commercially until license is gotten
"""

from __future__ import annotations

import json
from pathlib import Path

from sqlalchemy import select

from app.db.session import SessionLocal
from app.models import Exercise  # noqa: F401 — loads User/WorkoutLog too for relationships

ROOT = Path(__file__).resolve().parents[2]
SEED_PATH = ROOT / "data" / "exercises_dataset.json"
SOURCE = "exercises-dataset"


def load_seed() -> list[dict]:
    if not SEED_PATH.exists():
        raise FileNotFoundError(
            f"Seed file not found: {SEED_PATH}\n"
            "Run: python -m app.scripts.download_exercises_dataset"
        )
    return json.loads(SEED_PATH.read_text(encoding="utf-8"))


def _muscles(item: dict) -> list[str]:
    muscles: list[str] = []
    target = item.get("target")
    if target:
        muscles.append(target)
    for muscle in item.get("secondary_muscles") or []:
        if muscle not in muscles:
            muscles.append(muscle)
    return muscles


def to_payload(item: dict) -> dict:
    steps = (item.get("instruction_steps") or {}).get("en") or []
    if not steps and isinstance(item.get("instructions"), dict):
        text = item["instructions"].get("en") or ""
        steps = [line.strip() for line in text.split("\n") if line.strip()]

    return {
        "id": item["id"],
        "name": item["name"],
        "category": item.get("category") or item.get("body_part") or "unknown",
        "body_part": item.get("body_part") or item.get("category") or "unknown",
        "equipment": item.get("equipment") or "body weight",
        "target": item.get("target"),
        "media_id": item.get("media_id"),
        "muscle_group": item.get("muscle_group"),
        "secondary_muscles": item.get("secondary_muscles") or [],
        "instructions": item.get("instructions"),
        "instruction_steps": item.get("instruction_steps"),
        "rep_label": "reps",
        "exercise_type": None,
        "tags": None,
        "muscles": _muscles(item),
        "steps": steps,
        "tips": [],
        "mistakes": [],
        "is_custom": False,
        "source": SOURCE,
        "user_id": None,
        "extra": {
            "attribution": item.get("attribution"),
            "image": item.get("image"),
            "gif_url": item.get("gif_url"),
            "dataset_created_at": item.get("created_at"),
        },
    }


def seed(*, update_existing: bool = True) -> tuple[int, int]:
    records = load_seed()
    created = 0
    updated = 0

    with SessionLocal() as db:
        for item in records:
            payload = to_payload(item)
            existing = db.scalar(select(Exercise).where(
                Exercise.id == payload["id"]))
            if existing:
                if update_existing:
                    for key, value in payload.items():
                        setattr(existing, key, value)
                    updated += 1
            else:
                db.add(Exercise(**payload))
                created += 1
        db.commit()

    return created, updated


if __name__ == "__main__":
    created, updated = seed()
    print(f"Seeded from {SEED_PATH}")
    print(f"  created: {created}")
    print(f"  updated: {updated}")
    print(f"  total in file: {created + updated}")

    from app.scripts.seed_curated_exercises import seed as seed_curated

    curated_created, coached = seed_curated()
    print("Merged curated exercises from data/exercises_seed.json")
    print(f"  created: {curated_created}")
    print(f"  coaching overlaid: {coached}")
