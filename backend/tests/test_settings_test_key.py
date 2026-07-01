"""Tests for POST /settings/test-key."""
import importlib
import sys
import pytest
from unittest.mock import patch
from fastapi.testclient import TestClient
from sqlmodel import SQLModel, create_engine
from sqlalchemy.pool import StaticPool


@pytest.fixture(name="client")
def client_fixture():
    test_engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    SQLModel.metadata.create_all(test_engine)
    import db
    original = db.engine
    db.engine = test_engine

    # Reload settings_router/main in place so the app built here (and any
    # @patch on routers.settings_router) target the same module instance,
    # regardless of whether an earlier test already reloaded these modules.
    # `importlib.reload` mutates the existing module object rather than
    # deleting it from sys.modules, which avoids a stale `settings_router`
    # attribute lingering on the `routers` package (a plain
    # `del sys.modules[...]` + re-import would leave `from routers import
    # settings_router` resolving to the old module via that cached attribute).
    import routers.settings_router
    importlib.reload(routers.settings_router)
    if "main" in sys.modules:
        importlib.reload(sys.modules["main"])
    import main

    app = main.create_app()
    with TestClient(app) as client:
        yield client

    db.engine = original
    SQLModel.metadata.drop_all(test_engine)


def _auth_headers(client) -> dict:
    resp = client.post(
        "/api/auth/register",
        json={"username": "settings_test_user", "password": "password123", "email": "settings_test_user@test.local"},
    )
    if resp.status_code == 400:
        resp = client.post("/api/auth/login", data={"username": "settings_test_user", "password": "password123"})
    return {"Authorization": f"Bearer {resp.json()['access_token']}"}


@patch("routers.settings_router.test_provider_key")
def test_test_key_with_literal_value(mock_test, client):
    mock_test.return_value = (True, "Key is valid.")
    headers = _auth_headers(client)
    resp = client.post(
        "/api/settings/test-key",
        json={"provider": "openai", "api_key": "sk-typed-key"},
        headers=headers,
    )
    assert resp.status_code == 200
    assert resp.json() == {"ok": True, "message": "Key is valid."}
    mock_test.assert_called_once_with("openai", "sk-typed-key")


@patch("routers.settings_router.test_provider_key")
def test_test_key_resolves_masked_sentinel_to_stored_key(mock_test, client):
    mock_test.return_value = (False, "openai rejected this key (401 unauthorized).")
    headers = _auth_headers(client)

    # Save a real key first
    client.put("/api/settings", json={"api_key": "sk-stored-key"}, headers=headers)

    resp = client.post(
        "/api/settings/test-key",
        json={"provider": "openai", "api_key": "***"},
        headers=headers,
    )
    assert resp.status_code == 200
    assert resp.json()["ok"] is False
    mock_test.assert_called_once_with("openai", "sk-stored-key")


@patch("routers.settings_router.test_provider_key")
def test_test_key_resolves_masked_sentinel_to_env_var(mock_test, client, monkeypatch):
    mock_test.return_value = (True, "Key is valid.")
    monkeypatch.setenv("OPENROUTER_API_KEY", "sk-env-key")
    headers = _auth_headers(client)

    resp = client.post(
        "/api/settings/test-key",
        json={"provider": "openrouter", "api_key": "***"},
        headers=headers,
    )
    assert resp.status_code == 200
    assert resp.json()["ok"] is True
    mock_test.assert_called_once_with("openrouter", "sk-env-key")


def test_test_key_requires_auth(client):
    resp = client.post(
        "/api/settings/test-key",
        json={"provider": "openai", "api_key": "sk-x"},
    )
    assert resp.status_code == 401
