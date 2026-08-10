"""Seed curated system session templates into the database."""

from __future__ import annotations

import json
from pathlib import Path

from sqlalchemy import select

from app.db.session import SessionLocal
from app.models.session_template import SessionTemplate

ROOT = Path(__file__).resolve().parents[2]
SEED_PATH = ROOT / "data" / "session_templates_seed.json"


def load_seed() -> list[dict]:
    if not SEED_PATH.exists():
        raise FileNotFoundError(f"Seed file not found: {SEED_PATH}")
    return json.loads(SEED_PATH.read_text(encoding="utf-8"))


def seed(*, update_existing: bool = True) -> tuple[int, int]:
    records = load_seed()
    created = 0
    updated = 0

    with SessionLocal() as db:
        for item in records:
            payload = {
                "id": item["id"],
                "title": item["title"],
                "emoji": item.get("emoji", ""),
                "description": item.get("description", ""),
                "focus": item["focus"],
                "category": item["category"],
                "source": "system",
                "duration_min": item["duration_min"],
                "sort_order": item.get("sort_order", 0),
                "exercises": item["exercises"],
                "user_id": None,
            }
            existing = db.scalar(
                select(SessionTemplate).where(SessionTemplate.id == payload["id"])
            )
            if existing:
                if update_existing:
                    for key, value in payload.items():
                        setattr(existing, key, value)
                    updated += 1
            else:
                db.add(SessionTemplate(**payload))
                created += 1
        db.commit()

    return created, updated


if __name__ == "__main__":
    created, updated = seed()
    print(f"Seeded system templates from {SEED_PATH}")
    print(f"  created: {created}")
    print(f"  updated: {updated}")
    print(f"  total in file: {created + updated}")
