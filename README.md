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

`GET /api/v1/exercises` remains public. Custom exercises require a token:

| Method | Path | Purpose |
|---|---|---|
| `GET` | `/exercises` | list catalogue (+ own customs when signed in) |
| `GET` | `/exercises/focuses` | app focus → `body_part` mapping |
| `GET` | `/exercises/{id}` | one exercise |
| `POST` | `/exercises` | create custom |
| `PATCH` | `/exercises/{id}` | update own custom |
| `DELETE` | `/exercises/{id}` | delete own custom |

### Focus filter

App day focuses (`Glutes & Legs`, `Upper Body`, …) don’t match dataset `body_part` values (`chest`, `upper legs`, …). Use:

```
GET /api/v1/exercises?focus=Upper Body
GET /api/v1/exercises?focus=Glutes & Legs&focus=Core & Posture
GET /api/v1/exercises?focus=💪 Upper Body,Active Recovery
```

| App focus | Maps to `body_part` |
|---|---|
| Glutes & Legs | `upper legs`, `lower legs` |
| Upper Body | `chest`, `back`, `shoulders`, `upper arms`, `lower arms` |
| Core & Posture | `waist`, `neck` |
| Full Body | all (no anatomy filter) |
| Active Recovery | `cardio` + names containing `stretch` |

Customs whose `category` is an app focus label are included under that focus. Raw `?body_part=` / `?category=` still work for dataset vocab. Unknown focus → `422`.

Catalogue rows cannot be patched/deleted.

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

## Session templates

Curated system blocks for the Sessions screen (pre-workout / cardio / post-workout).
Exercises reference catalogue `id` + `name`.

| Method | Path | Auth | Purpose |
|---|---|---|---|
| `GET` | `/templates` | public | list system (+ your saved if signed in) |
| `GET` | `/templates/{id}` | public* | one template |
| `POST` | `/templates` | JWT | **save as session template** (from day edit) |
| `POST` | `/templates/{id}/save` | JWT | bookmark system template → Saved |
| `POST` | `/templates/{id}/add-to-plan` | JWT | **add template to a day plan** |
| `PATCH` | `/templates/{id}` | JWT | edit your saved template |
| `DELETE` | `/templates/{id}` | JWT | remove your saved template |

\*User-owned templates require the owning user's token.

**Day-edit save sheet**

- Save as session template → `POST /templates`
- Add / update day plan → `PUT /schedule/{day}` (already exists)

**From Sessions screen**

- Bookmark → `POST /templates/{id}/save`
- Add to day → `POST /templates/{id}/add-to-plan` with `{ "day": "Mon", "mode": "merge" | "replace", "day_type": "gym" }`

Seed:

```bash
python -m app.scripts.seed_session_templates
```

Source JSON: `data/session_templates_seed.json` (10 templates).

## Library

Saved exercises for Plan / pickers (`Authorization: Bearer` required).

| Method | Path | Purpose |
|---|---|---|
| `GET` | `/library` | full saved list |
| `PUT` | `/library` | replace list (sync after login) |
| `POST` | `/library/items` | add one `{ id?, name }` |
| `DELETE` | `/library/items?id=` or `?name=` | remove one |

```json
{
  "items": [
    { "id": "0662", "name": "push-up" },
    { "id": null, "name": "My Custom Curl" }
  ]
}
```

Local app today stores names only (`toned_library`); when wiring sync, map to `{ id, name }` (id null until resolved from catalogue).

## Sync

JWT required. Workouts-only payloads still work; other sections are optional.

| Method | Path | Purpose |
|---|---|---|
| `POST` | `/sync/push` | upload local changes |
| `GET` | `/sync/pull?since=` | download cloud state |
| `POST` | `/sync/full` | push then pull (after login / app open) |
| `POST` | `/sync/merge` | first-login merge of guest local + cloud |

### First-login merge

After guest → signup/login, send the on-device snapshot once:

```json
{
  "strategy": "prefer_local",
  "local": {
    "workouts": [],
    "schedule": {},
    "library": [],
    "preferences": { "weight_unit": "lb" },
    "custom_exercises": [],
    "templates": []
  }
}
```

| Strategy | When to use |
|---|---|
| `prefer_local` (default) | Guest had data on device; device wins conflicts |
| `prefer_cloud` | Reinstall / trust server; cloud wins conflicts |
| `union` | Combine schedule day exercises/focuses; prefs take local `weight_unit` + later nudge timestamps |

Lists (library, workouts, customs, templates) are always unioned by id/`client_id`/name; conflicts use the strategy. Omitted `schedule` / `library` / `preferences` keep cloud as-is for that section. Response is a full pull plus `notes` listing conflict resolutions.

Push body (omit a section to leave it unchanged on the server):

```json
{
  "workouts": [{ "date": "2026-08-10", "client_id": "…", "exercises": [] }],
  "schedule": { "Mon": { "type": "gym", "focuses": ["Glutes & Legs"], "exercises": [] } },
  "library": [{ "id": "0662", "name": "push-up" }],
  "custom_exercises": [{ "name": "My Move", "category": "chest", "equipment": "body weight", "muscles": [], "steps": [] }],
  "templates": [{ "title": "My Block", "focus": "Upper Body", "category": "pre-workout", "duration_min": 10, "exercises": [] }]
}
```

- `schedule` / `library`: full replace when sent (last-write-wins)
- `preferences`: full replace when sent (weight unit + signup nudge timestamps; **no theme**)
- `workouts` / `custom_exercises` / `templates`: upsert
- Pull always returns full `schedule` + `library` + `preferences`; `since` filters workouts/customs/templates only

## Preferences

JWT required. Theme stays on-device — not stored here.

| Method | Path | Purpose |
|---|---|---|
| `GET` | `/preferences` | current prefs (defaults if unset) |
| `PATCH` | `/preferences` | update fields |

```json
{
  "weight_unit": "kg",
  "signup_nudge_last_shown_at": "2026-08-10T12:00:00Z",
  "signup_nudge_dismissed_at": null
}
```

Use nudge timestamps for the monthly “sign up so your data isn’t lost” prompt.

## Scripts

```bash
# Download pinned exercises-dataset JSON (once; gitignored)
python -m app.scripts.download_exercises_dataset

# Seed catalogue from data/exercises_dataset.json
python -m app.scripts.seed_internal_exercises

# Seed system session templates
python -m app.scripts.seed_session_templates
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
