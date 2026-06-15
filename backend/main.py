from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from sqlmodel import SQLModel
from db import engine, migrate_db
from routers import import_router, profile_router, export_router
from routers import logs_router, settings_router, analysis_router, jobs_router


def create_tables():
    SQLModel.metadata.create_all(engine)
    migrate_db()


def create_app() -> FastAPI:
    create_tables()
    app = FastAPI(title="Career Studio", version="0.1.0")
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["http://localhost:5173"],
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
    return app


app = create_app()
