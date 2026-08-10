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
cp .env.example .env   # set DATABASE_URL (Neon recommended) + optional Supabase secrets
alembic upgrade head
python -m app.scripts.download_exercises_dataset
python -m app.scripts.seed_internal_exercises
uvicorn app.main:app --reload --port 8000
```

### Database (Neon free tier)

No Docker required. Create a project at [console.neon.tech](https://console.neon.tech), copy the connection string into `.env`, and change the scheme to `postgresql+psycopg://`:

```
DATABASE_URL=postgresql+psycopg://USER:PASS@ep-XXXX.REGION.aws.neon.tech/neondb?sslmode=require
```

Local Postgres works too (`localhost:5432`). Tableau is not used for this flow.

### Exercise catalogue

Pinned snapshot of [hasaneyldrm/exercises-dataset](https://github.com/hasaneyldrm/exercises-dataset) (commit in `data/exercises_dataset.sha`) → downloaded to `data/exercises_dataset.json` (~17MB, gitignored; 1,324 rows). `media_id` is stored for a future Gym Visual license; image/GIF files are not imported.

Quick check after seeding:

```bash
python -c "
from app.db.database import SessionLocal
from app.models.exercise import Exercise
db = SessionLocal()
print('Total:', db.query(Exercise).count())
print('Chest:', db.query(Exercise).filter(Exercise.body_part=='chest').count())
print('One:', db.query(Exercise).first().name)
"
```

Health check: `GET http://localhost:8000/health`

API base: `http://localhost:8000/api/v1`

## Auth

Auth is proxied through Supabase GoTrue. Guest users need no token for the exercise catalogue.

| Method | Path | Auth | Purpose |
|---|---|---|---|
| `POST` | `/auth/signup` | public | create account |
| `POST` | `/auth/signin` | public | email/password login |
| `POST` | `/auth/refresh` | public | refresh access token via `refresh_token` |
| `POST` | `/auth/logout` | Bearer | invalidate session |
| `POST` | `/auth/forgot-password` | public | email reset link |
| `POST` | `/auth/reset-password` | Bearer (recovery) | set new password |
| `POST` | `/auth/reset-data` | Bearer | wipe cloud workouts/customs (keeps account) |
| `DELETE` | `/auth/account` | Bearer | hard-delete Auth + Neon data (email reusable) |
| `GET` | `/auth/me` | Bearer | current user + upsert Neon row |

Store `access_token` from signup/signin on the device and send:

```
Authorization: Bearer <access_token>
```

`GET /api/v1/exercises` remains public. Custom exercises, workouts, and sync still require a token.

Requires `SUPABASE_URL`, `SUPABASE_ANON_KEY`, and `SUPABASE_JWT_SECRET` in `.env`.
`DELETE /auth/account` also needs `SUPABASE_SERVICE_ROLE_KEY` (server-only; hard delete so the email can be reused).

## Schedule

Weekly plan for signed-in users (`Authorization: Bearer <access_token>`).

| Method | Path | Purpose |
|---|---|---|
| `GET` | `/schedule` | full week |
| `PUT` | `/schedule` | replace week |
| `PUT` | `/schedule/{day}` | upsert one day (`Mon`…`Sun`) |
| `DELETE` | `/schedule/{day}` | clear one day |

Each planned exercise stores catalogue `id` (nullable for customs) plus `name`:

```json
{
  "schedule": {
    "Mon": {
      "type": "gym",
      "focuses": ["Glutes & Legs"],
      "exercises": [
        { "id": "0001", "name": "3/4 sit-up" },
        { "id": null, "name": "My Custom Curl" }
      ]
    }
  }
}
```

Home / start workout reads `schedule[today]` for exercise names (and ids when present).

## Scripts

```bash
# Download pinned exercises-dataset JSON (once; gitignored)
python -m app.scripts.download_exercises_dataset

# Seed catalogue from data/exercises_dataset.json
python -m app.scripts.seed_internal_exercises
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
