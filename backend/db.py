import logging
import os
import sqlite3
from contextlib import contextmanager
from sqlmodel import create_engine, SQLModel, Session
from sqlalchemy import event, text
from sqlalchemy.engine import Engine
from sqlalchemy.exc import IntegrityError

_logger = logging.getLogger(__name__)

DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./career_studio_new.db")
engine = create_engine(DATABASE_URL, echo=False)


@event.listens_for(Engine, "connect")
def _set_sqlite_pragma(dbapi_connection, connection_record):
    if isinstance(dbapi_connection, sqlite3.Connection):
        cursor = dbapi_connection.cursor()
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.close()


def create_db_and_tables():
    SQLModel.metadata.create_all(engine)


def migrate_db():
    """Add new columns to existing tables without losing data."""
    new_settings_cols = [
        ("user_id", "INTEGER"),
        ("use_local_ai",    "INTEGER DEFAULT 0"),
        ("ollama_base_url", "TEXT DEFAULT 'http://localhost:11434'"),
        ("ollama_model",    "TEXT DEFAULT 'llama3.2'"),
        ("local_for_simple","INTEGER DEFAULT 1"),
        ("use_deep_semantic_matching", "INTEGER DEFAULT 0"),
        ("adzuna_app_id",  "TEXT DEFAULT ''"),
        ("adzuna_app_key", "TEXT DEFAULT ''"),
        ("linkedin_api_key", "TEXT DEFAULT ''"),
        ("indeed_api_key", "TEXT DEFAULT ''"),
        ("glassdoor_api_key", "TEXT DEFAULT ''"),
        ("findwork_api_key", "TEXT DEFAULT ''"),
        ("jooble_api_key", "TEXT DEFAULT ''"),
        ("reed_api_key", "TEXT DEFAULT ''"),
        ("usajobs_api_key", "TEXT DEFAULT ''"),
    ]
    new_profile_cols = [
        ("user_id", "INTEGER"),
    ]
    new_jobmatch_cols = [
        ("date_posted",       "TEXT DEFAULT ''"),
        ("job_type",          "TEXT DEFAULT ''"),
        ("industry",          "TEXT DEFAULT ''"),
        ("salary_min",        "INTEGER DEFAULT 0"),
        ("salary_max",        "INTEGER DEFAULT 0"),
        ("is_remote",         "INTEGER DEFAULT 0"),
        ("is_expired",        "INTEGER DEFAULT 0"),
        ("match_breakdown",   "TEXT DEFAULT ''"),
        ("matched_skills",    "TEXT DEFAULT '[]'"),
        ("missing_skills",    "TEXT DEFAULT '[]'"),
        ("skill_details",     "TEXT DEFAULT '[]'"),
        ("gaps",              "TEXT DEFAULT '{}'"),
        ("insight",           "TEXT DEFAULT ''"),
        ("confidence",        "TEXT DEFAULT ''"),
    ]
    new_cert_cols = [
        ("cert_id", "TEXT DEFAULT ''"),
    ]
    with engine.connect() as conn:
        try:
            try:
                conn.execute(text("CREATE UNIQUE INDEX IF NOT EXISTS ux_user_email ON user(email)"))
            except IntegrityError:
                conn.rollback()
                _logger.warning(
                    "Strict user email index skipped because legacy duplicate emails exist; "
                    "creating a unique index for non-empty emails instead."
                )
                try:
                    conn.execute(text("CREATE UNIQUE INDEX IF NOT EXISTS ux_user_email ON user(email) WHERE email != ''"))
                except IntegrityError:
                    conn.rollback()
                    _logger.warning(
                        "User email index skipped because legacy duplicate non-empty emails exist. "
                        "New registrations are still checked in application code."
                    )
            conn.commit()
        except Exception as exc:
            _logger.error("Failed to migrate user email index: %s", exc)
            raise
        try:
            existing = {row[1] for row in conn.execute(text("PRAGMA table_info(settings)")).fetchall()}
            for col, defn in new_settings_cols:
                if col not in existing:
                    conn.execute(text(f"ALTER TABLE settings ADD COLUMN {col} {defn}"))
            conn.commit()
        except Exception as exc:
            _logger.error("Failed to migrate settings table: %s", exc)
            raise
        try:
            conn.execute(text("CREATE UNIQUE INDEX IF NOT EXISTS ux_settings_user_id ON settings(user_id)"))
            conn.commit()
        except Exception as exc:
            _logger.error("Failed to migrate settings user index: %s", exc)
            raise
        try:
            existing = {row[1] for row in conn.execute(text("PRAGMA table_info(profile)")).fetchall()}
            for col, defn in new_profile_cols:
                if col not in existing:
                    conn.execute(text(f"ALTER TABLE profile ADD COLUMN {col} {defn}"))
            conn.commit()
        except Exception as exc:
            _logger.error("Failed to migrate profile table: %s", exc)
            raise
        try:
            conn.execute(text("CREATE INDEX IF NOT EXISTS idx_activitylog_profile_id ON activitylog(profile_id)"))
            conn.commit()
        except Exception as exc:
            _logger.error("Failed to migrate activity log index: %s", exc)
            raise
        try:
            existing = {row[1] for row in conn.execute(text("PRAGMA table_info(jobmatch)")).fetchall()}
            for col, defn in new_jobmatch_cols:
                if col not in existing:
                    conn.execute(text(f"ALTER TABLE jobmatch ADD COLUMN {col} {defn}"))
            conn.commit()
        except Exception as exc:
            _logger.error("Failed to migrate jobmatch table: %s", exc)
            raise
        try:
            existing = {row[1] for row in conn.execute(text("PRAGMA table_info(certification)")).fetchall()}
            for col, defn in new_cert_cols:
                if col not in existing:
                    conn.execute(text(f"ALTER TABLE certification ADD COLUMN {col} {defn}"))
            conn.commit()
        except Exception as exc:
            _logger.error("Failed to migrate certification table: %s", exc)
            raise


@contextmanager
def get_session():
    with Session(engine) as session:
        yield session


def get_session_dep():
    with Session(engine) as session:
        yield session
