"""Shared pytest fixtures for AI Career Studio tests."""
import os
import sys
import tempfile
from pathlib import Path

# CRITICAL: set DATABASE_URL BEFORE any backend module is imported,
# so all routers pick up the test DB when they do `from db import engine`.
_tmp = tempfile.NamedTemporaryFile(suffix="_career_test.db", delete=False)
_tmp.close()
os.environ["DATABASE_URL"] = f"sqlite:///{_tmp.name}"

# Now safe to add backend to sys.path
sys.path.insert(0, str(Path(__file__).parent.parent / "backend"))

import pytest
from fastapi.testclient import TestClient

FIXTURES = Path(__file__).parent / "fixtures"


@pytest.fixture(scope="session")
def client():
    """FastAPI test client backed by a temp SQLite file."""
    from main import create_app
    app = create_app()
    with TestClient(app) as c:
        yield c


@pytest.fixture
def session():
    from db import engine
    from sqlmodel import Session
    with Session(engine) as s:
        yield s


def fixture_path(name: str) -> Path:
    return FIXTURES / name


def fixture_bytes(name: str) -> bytes:
    return (FIXTURES / name).read_bytes()
