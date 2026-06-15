from sqlmodel import create_engine, SQLModel, Session
from sqlalchemy import text
from contextlib import contextmanager
import os

DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./career_studio.db")
engine = create_engine(DATABASE_URL, echo=False)


def create_db_and_tables():
    SQLModel.metadata.create_all(engine)


def migrate_db():
    """Add new columns to existing tables without losing data."""
    new_settings_cols = [
        ("use_local_ai",    "INTEGER DEFAULT 0"),
        ("ollama_base_url", "TEXT DEFAULT 'http://localhost:11434'"),
        ("ollama_model",    "TEXT DEFAULT 'llama3.2'"),
        ("local_for_simple","INTEGER DEFAULT 1"),
        ("adzuna_app_id",  "TEXT DEFAULT ''"),
        ("adzuna_app_key", "TEXT DEFAULT ''"),
    ]
    with engine.connect() as conn:
        try:
            existing = {row[1] for row in conn.execute(text("PRAGMA table_info(settings)")).fetchall()}
            for col, defn in new_settings_cols:
                if col not in existing:
                    conn.execute(text(f"ALTER TABLE settings ADD COLUMN {col} {defn}"))
            conn.commit()
        except Exception:
            pass  # Table may not exist yet; create_all handles it


@contextmanager
def get_session():
    with Session(engine) as session:
        yield session


def get_session_dep():
    with Session(engine) as session:
        yield session
