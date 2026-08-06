# Toned Backend

FastAPI backend for the Toned workout app. Handles exercise catalogue, workout logs, and client sync against a Postgres database (Supabase).

## Structure

```
app/
  main.py           # FastAPI entrypoint
  config.py         # pydantic-settings
  db/               # SQLAlchemy engine + Base
  models/           # ORM tables
  schemas/          # Pydantic request/response models
  routers/          # API route groups
  services/         # Business logic
  core/             # Auth + shared dependencies
  scripts/          # One-off maintenance scripts
data/
  exercises_seed.json
migrations/         # Alembic
tests/
```

## Quick start

```bash
cd Toned-backend
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env   # fill in DATABASE_URL + Supabase secrets
alembic upgrade head
python -m app.scripts.seed_internal_exercises
uvicorn app.main:app --reload --port 8000
```

Health check: `GET http://localhost:8000/health`

API base: `http://localhost:8000/api/v1`

## Auth

Routes expect a Supabase access token:

```
Authorization: Bearer <supabase_jwt>
```

`GET /api/v1/auth/me` verifies the token and upserts the user row.

## Scripts

```bash
# Seed built-in exercises from data/exercises_seed.json
python -m app.scripts.seed_internal_exercises

# Third-party import (stub)
python -m app.scripts.import_third_party --source wger
```

## Migrations

```bash
alembic revision --autogenerate -m "describe change"
alembic upgrade head
```

## Tests

```bash
pytest
```
