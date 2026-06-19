import io
import pytest
from fastapi.testclient import TestClient
from sqlmodel import Session, SQLModel, create_engine
from sqlalchemy.pool import StaticPool
from pathlib import Path
import main  # imports create_app
from models import Profile

FIXTURES = Path(__file__).parent / "fixtures"

# ── Test fixtures ──────────────────────────────────────────────────

@pytest.fixture(name="client")
def client_fixture():
    """TestClient wired to an in-memory SQLite DB via dependency override."""
    test_engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    SQLModel.metadata.create_all(test_engine)

    # Patch the module-level engine used by routers
    import db
    original = db.engine
    db.engine = test_engine

    app = main.create_app()
    with TestClient(app) as client:
        yield client

    db.engine = original
    SQLModel.metadata.drop_all(test_engine)


def _auth_headers(client) -> dict:
    """Register a test user and return auth headers."""
    resp = client.post(
        "/api/auth/register",
        json={"username": "api_test_user", "password": "password123", "email": "api_test_user@test.local"},
    )
    if resp.status_code == 400:
        resp = client.post("/api/auth/login", data={"username": "api_test_user", "password": "password123"})
    return {"Authorization": f"Bearer {resp.json()['access_token']}"}


# ── Import endpoint ────────────────────────────────────────────────

def test_import_json(client):
    data = (FIXTURES / "sample.json").read_bytes()
    resp = client.post("/api/import", files={"file": ("sample.json", io.BytesIO(data), "application/json")})
    assert resp.status_code == 201
    body = resp.json()
    assert body["profile_id"] == 1
    assert isinstance(body["warnings"], list)


def test_import_csv(client):
    data = (FIXTURES / "sample.csv").read_bytes()
    resp = client.post("/api/import", files={"file": ("sample.csv", io.BytesIO(data), "text/csv")})
    assert resp.status_code == 201
    assert resp.json()["profile_id"] == 1


def test_import_xml(client):
    data = (FIXTURES / "sample.xml").read_bytes()
    resp = client.post("/api/import", files={"file": ("sample.xml", io.BytesIO(data), "application/xml")})
    assert resp.status_code == 201


def test_import_unsupported_type(client):
    resp = client.post("/api/import", files={"file": ("sample.txt", io.BytesIO(b"hello"), "text/plain")})
    assert resp.status_code == 400


# ── Profile CRUD ───────────────────────────────────────────────────

def _import_json(client, headers=None) -> int:
    data = (FIXTURES / "sample.json").read_bytes()
    resp = client.post("/api/import", files={"file": ("sample.json", io.BytesIO(data), "application/json")}, headers=headers)
    return resp.json()["profile_id"]


def test_list_profiles_empty(client):
    headers = _auth_headers(client)
    resp = client.get("/api/profiles", headers=headers)
    assert resp.status_code == 200
    assert resp.json() == []


def test_get_profile(client):
    headers = _auth_headers(client)
    pid = _import_json(client, headers=headers)
    resp = client.get(f"/api/profiles/{pid}", headers=headers)
    assert resp.status_code == 200
    body = resp.json()
    assert "Jane" in body["full_name"]
    assert len(body["skills"]) > 0


def test_patch_profile(client):
    headers = _auth_headers(client)
    pid = _import_json(client, headers=headers)
    resp = client.patch(f"/api/profiles/{pid}", json={"full_name": "Jane Updated"}, headers=headers)
    assert resp.status_code == 200
    assert resp.json()["full_name"] == "Jane Updated"


def test_delete_profile(client):
    headers = _auth_headers(client)
    pid = _import_json(client, headers=headers)
    resp = client.delete(f"/api/profiles/{pid}", headers=headers)
    assert resp.status_code == 204
    resp2 = client.get(f"/api/profiles/{pid}")
    assert resp2.status_code == 404


# ── Export endpoint ────────────────────────────────────────────────

@pytest.mark.parametrize("fmt,mime", [
    ("json", "application/json"),
    ("csv",  "text/csv"),
    ("xml",  "application/xml"),
    ("docx", "application/vnd.openxmlformats-officedocument.wordprocessingml.document"),
    ("pdf",  "application/pdf"),
])
def test_export_formats(client, fmt, mime):
    headers = _auth_headers(client)
    pid = _import_json(client, headers=headers)
    resp = client.get(f"/api/profiles/{pid}/export/{fmt}", headers=headers)
    assert resp.status_code == 200
    assert mime in resp.headers["content-type"]
    assert len(resp.content) > 0


def test_export_invalid_format(client):
    headers = _auth_headers(client)
    pid = _import_json(client, headers=headers)
    resp = client.get(f"/api/profiles/{pid}/export/xyz", headers=headers)
    assert resp.status_code == 400
