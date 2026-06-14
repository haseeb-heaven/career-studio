from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from sqlmodel import SQLModel
from db import engine
from routers import import_router, profile_router, export_router


def create_tables():
    SQLModel.metadata.create_all(engine)


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
    return app


app = create_app()
