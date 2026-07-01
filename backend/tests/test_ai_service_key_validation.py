"""Unit tests for test_provider_key() in ai_service.py."""
import sys
from pathlib import Path
from unittest.mock import patch, MagicMock
sys.path.insert(0, str(Path(__file__).parent.parent))

from services.ai_service import test_provider_key


def _mock_response(status_code):
    resp = MagicMock()
    resp.status_code = status_code
    return resp


def test_empty_key_is_invalid():
    ok, msg = test_provider_key("openai", "")
    assert ok is False
    assert "no" in msg.lower()


def test_unknown_provider_is_invalid():
    ok, msg = test_provider_key("bogus", "sk-something")
    assert ok is False
    assert "unknown provider" in msg.lower()


@patch("services.ai_service.httpx.get")
def test_openai_valid_key(mock_get):
    mock_get.return_value = _mock_response(200)
    ok, msg = test_provider_key("openai", "sk-real-key")
    assert ok is True
    called_url = mock_get.call_args[0][0]
    assert "api.openai.com" in called_url


@patch("services.ai_service.httpx.get")
def test_openai_invalid_key_401(mock_get):
    mock_get.return_value = _mock_response(401)
    ok, msg = test_provider_key("openai", "sk-bad-key")
    assert ok is False
    assert "401" in msg


@patch("services.ai_service.httpx.get")
def test_anthropic_valid_key(mock_get):
    mock_get.return_value = _mock_response(200)
    ok, msg = test_provider_key("anthropic", "sk-ant-real-key")
    assert ok is True
    called_url = mock_get.call_args[0][0]
    assert "api.anthropic.com" in called_url


@patch("services.ai_service.httpx.get")
def test_openrouter_valid_key(mock_get):
    mock_get.return_value = _mock_response(200)
    ok, msg = test_provider_key("openrouter", "sk-or-real-key")
    assert ok is True
    called_url = mock_get.call_args[0][0]
    assert "openrouter.ai/api/v1/auth/key" in called_url


@patch("services.ai_service.httpx.get")
def test_network_error_is_invalid(mock_get):
    mock_get.side_effect = Exception("connection refused")
    ok, msg = test_provider_key("openai", "sk-real-key")
    assert ok is False
    assert "connection refused" in msg
