from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import get_settings
from app.routers import (
    auth,
    buddies,
    buddy,
    exercises,
    library,
    preferences,
    profile,
    schedule,
    sync,
    templates,
    workouts,
)


@asynccontextmanager
async def lifespan(_: FastAPI):
    yield


def create_app() -> FastAPI:
    settings = get_settings()
    app = FastAPI(title=settings.app_name, lifespan=lifespan)

    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    prefix = settings.api_v1_prefix
    app.include_router(auth.router, prefix=prefix)
    app.include_router(buddies.router, prefix=prefix)
    app.include_router(buddy.router, prefix=prefix)
    app.include_router(exercises.router, prefix=prefix)
    app.include_router(library.router, prefix=prefix)
    app.include_router(profile.router, prefix=prefix)
    app.include_router(preferences.router, prefix=prefix)
    app.include_router(schedule.router, prefix=prefix)
    app.include_router(templates.router, prefix=prefix)
    app.include_router(workouts.router, prefix=prefix)
    app.include_router(sync.router, prefix=prefix)

    @app.get("/health")
    def health() -> dict[str, str]:
        return {"status": "ok"}

    return app


app = create_app()
