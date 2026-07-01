import logging
import os
import warnings
from dotenv import load_dotenv
load_dotenv()  # pick up .env from backend dir (or parent) before anything else

from fastapi import FastAPI

_DEV_SECRET = "ai-career-studio-dev-secret-2026"
_logger = logging.getLogger(__name__)


def _check_secret_key() -> None:
    """Warn loudly if SECRET_KEY is still the insecure development default."""
    key = os.getenv("SECRET_KEY", "")
    if not key or key == _DEV_SECRET:
        msg = (
            "SECRET_KEY is using the insecure development default. "
            "Set the SECRET_KEY environment variable to a random 32+ character string "
            "before deploying to production — all encrypted API keys and JWT tokens "
            "will be compromised if this default is used in production."
        )
        if os.getenv("ENVIRONMENT", "development").lower() == "production":
            raise RuntimeError(msg)
        warnings.warn(msg, stacklevel=2)
        _logger.warning(msg)
from fastapi.middleware.cors import CORSMiddleware
from sqlmodel import SQLModel
from db import engine, migrate_db
from routers import import_router, profile_router, export_router
from routers import logs_router, settings_router, analysis_router, jobs_router, sections_router, auth_router
from routers import resume_editor_router
from routers.settings_router import run_startup_migration


def create_tables():
    SQLModel.metadata.create_all(engine)
    migrate_db()


def create_app() -> FastAPI:
    _check_secret_key()
    create_tables()
    run_startup_migration()
    app = FastAPI(title="AI Career Studio", version="0.1.0")
    cors_origins_env = os.getenv("CORS_ORIGINS", "")
    allowed_origins = (
        [o.strip() for o in cors_origins_env.split(",") if o.strip()]
        if cors_origins_env
        else ["http://localhost:5173", "http://localhost:4173"]
    )
    app.add_middleware(
        CORSMiddleware,
        allow_origins=allowed_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    app.include_router(import_router.router, prefix="/api")
    app.include_router(profile_router.router, prefix="/api")
    app.include_router(export_router.router, prefix="/api")
    app.include_router(logs_router.router, prefix="/api")
    app.include_router(settings_router.router, prefix="/api")
    app.include_router(analysis_router.router, prefix="/api")
    app.include_router(jobs_router.router, prefix="/api")
    app.include_router(sections_router.router, prefix="/api")
    app.include_router(auth_router.router, prefix="/api")
    app.include_router(resume_editor_router.router, prefix="/api")
    return app


app = create_app()
# Trigger reload to pick up litellm package

