"""
AI provider integration tests — only run when API keys are present.

Each test auto-skips if the required env var / Settings is not configured.
Run with:  pytest tests/test_ai_integration.py -v -s
"""
import os
import sys
import json
from pathlib import Path

# Load .env from backend dir before any imports
_backend = Path(__file__).parent.parent / "backend"
try:
    from dotenv import load_dotenv
    load_dotenv(_backend / ".env")
except ImportError:
    pass

sys.path.insert(0, str(_backend))

import pytest


# ── Shared helpers ────────────────────────────────────────────────────────────

_SIMPLE_SYSTEM = "You are a helpful assistant. Be concise."
_SIMPLE_USER = "Reply with exactly: HELLO_OK"
_ANALYSIS_SYSTEM = (
    "You are a resume analyst. Return JSON: "
    '{"score":75,"strengths":["Python"],"weaknesses":["No leadership"],'
    '"suggestions":["Add metrics"],"ats_keywords":["FastAPI"]}'
)
_ANALYSIS_USER = "Resume: Python developer, 3 years experience."


def _skip_no_key(env_var: str):
    val = os.getenv(env_var, "")
    if not val:
        pytest.skip(f"{env_var} not set in environment / .env")


# ── OpenAI ───────────────────────────────────────────────────────────────────

class TestOpenAI:
    def setup_method(self):
        _skip_no_key("OPENAI_API_KEY")

    def test_simple_completion(self):
        from services.ai_service import _call_openai
        key = os.getenv("OPENAI_API_KEY")
        model = os.getenv("OPENAI_MODEL", "gpt-4o-mini")
        result = _call_openai(key, model, _SIMPLE_SYSTEM, _SIMPLE_USER)
        assert "HELLO_OK" in result, f"Unexpected response: {result}"

    def test_json_analysis(self):
        from services.ai_service import _call_openai
        key = os.getenv("OPENAI_API_KEY")
        model = os.getenv("OPENAI_MODEL", "gpt-4o-mini")
        raw = _call_openai(key, model, _ANALYSIS_SYSTEM, _ANALYSIS_USER)
        raw = raw.strip().lstrip("```json").lstrip("```").rstrip("```")
        data = json.loads(raw)
        assert "score" in data
        assert isinstance(data["score"], (int, float))
        assert 0 <= data["score"] <= 100

    def test_cover_letter_generation(self):
        from services.ai_service import _call_openai
        key = os.getenv("OPENAI_API_KEY")
        model = os.getenv("OPENAI_MODEL", "gpt-4o-mini")
        system = "Write a 1-sentence cover letter intro for the given job."
        user = "Job: Python Developer at TechCorp. Candidate: 5 years Python experience."
        result = _call_openai(key, model, system, user)
        assert len(result) > 20, "Cover letter too short"


# ── Anthropic ────────────────────────────────────────────────────────────────

class TestAnthropic:
    def setup_method(self):
        _skip_no_key("ANTHROPIC_API_KEY")

    def test_simple_completion(self):
        from services.ai_service import _call_anthropic
        key = os.getenv("ANTHROPIC_API_KEY")
        model = os.getenv("ANTHROPIC_MODEL", "claude-haiku-4-5-20251001")
        result = _call_anthropic(key, model, _SIMPLE_SYSTEM, _SIMPLE_USER)
        assert "HELLO_OK" in result, f"Unexpected response: {result}"

    def test_json_analysis(self):
        from services.ai_service import _call_anthropic
        key = os.getenv("ANTHROPIC_API_KEY")
        model = os.getenv("ANTHROPIC_MODEL", "claude-haiku-4-5-20251001")
        raw = _call_anthropic(key, model, _ANALYSIS_SYSTEM, _ANALYSIS_USER)
        raw = raw.strip().lstrip("```json").lstrip("```").rstrip("```")
        data = json.loads(raw)
        assert "score" in data

    def test_cover_letter_generation(self):
        from services.ai_service import _call_anthropic
        key = os.getenv("ANTHROPIC_API_KEY")
        model = os.getenv("ANTHROPIC_MODEL", "claude-haiku-4-5-20251001")
        system = "Write a 1-sentence cover letter intro for the given job."
        user = "Job: Python Developer at TechCorp. Candidate: 5 years Python experience."
        result = _call_anthropic(key, model, system, user)
        assert len(result) > 20


# ── OpenRouter ───────────────────────────────────────────────────────────────

class TestOpenRouter:
    def setup_method(self):
        _skip_no_key("OPENROUTER_API_KEY")

    def test_simple_completion(self):
        from services.ai_service import _call_openrouter
        key = os.getenv("OPENROUTER_API_KEY")
        model = os.getenv("OPENROUTER_MODEL", "meta-llama/llama-3.1-8b-instruct:free")
        result = _call_openrouter(key, model, _SIMPLE_SYSTEM, _SIMPLE_USER)
        assert len(result) > 0, "Empty response from OpenRouter"

    def test_json_analysis(self):
        from services.ai_service import _call_openrouter
        key = os.getenv("OPENROUTER_API_KEY")
        model = os.getenv("OPENROUTER_MODEL", "meta-llama/llama-3.1-8b-instruct:free")
        raw = _call_openrouter(key, model, _ANALYSIS_SYSTEM, _ANALYSIS_USER)
        # OpenRouter free models might wrap in markdown
        clean = raw.strip()
        if "```" in clean:
            lines = clean.splitlines()
            clean = "\n".join(l for l in lines if not l.startswith("```"))
        try:
            data = json.loads(clean)
            assert "score" in data
        except json.JSONDecodeError:
            pytest.xfail(f"Free model returned non-JSON: {raw[:200]}")

    def test_cover_letter_generation(self):
        from services.ai_service import _call_openrouter
        key = os.getenv("OPENROUTER_API_KEY")
        model = os.getenv("OPENROUTER_MODEL", "meta-llama/llama-3.1-8b-instruct:free")
        system = "Write a 1-sentence cover letter intro for the given job."
        user = "Job: Python Developer at TechCorp. Candidate: 5 years Python experience."
        result = _call_openrouter(key, model, system, user)
        assert len(result) > 10


# ── Via Settings DB (end-to-end) ─────────────────────────────────────────────

def _get_ai_auth_headers(client, username: str = "ai_routing_user", password: str = "password123") -> dict:
    """Register (or login if already exists) and return auth headers."""
    resp = client.post("/api/auth/register", json={"username": username, "password": password})
    if resp.status_code == 400:  # already registered
        resp = client.post("/api/auth/login", data={"username": username, "password": password})
    if resp.status_code not in (200, 201):
        raise AssertionError(f"Auth failed ({resp.status_code}): {resp.text}")
    return {"Authorization": f"Bearer {resp.json()['access_token']}"}


class TestAIServiceRouting:
    """Test the complete routing path: Settings DB → AI provider."""

    def _api_call(self, client, provider: str, key_field: str, api_key: str, model: str, endpoint: str, body: dict):
        """Helper: configure settings then call an AI endpoint. Returns response."""
        headers = _get_ai_auth_headers(client, f"ai_routing_{provider}")
        resp = client.put("/api/settings", json={
            "ai_provider": provider,
            key_field: api_key,
            "ai_model": model,
        }, headers=headers)
        assert resp.status_code == 200, f"Settings update failed: {resp.text}"
        import json as _json
        data = _json.dumps({
            "full_name": "Test Developer",
            "skills": [{"name": "Python"}, {"name": "FastAPI"}],
            "experience": [{"company": "Acme", "role": "Backend Engineer", "start": "2021"}],
        }).encode()
        imp = client.post("/api/import", files={"file": ("p.json", data, "application/json")}, headers=headers)
        pid = imp.json()["profile_id"]
        return client.post(f"/api/profiles/{pid}/{endpoint}", json=body, headers=headers)

    def _assert_ai_ok(self, resp, endpoint: str):
        """Assert 200, or xfail on quota/rate-limit/missing-dependency errors."""
        if resp.status_code == 502:
            detail = resp.json().get("detail", "")
            if any(s in detail for s in ["429", "quota", "rate", "insufficient", "402"]):
                pytest.xfail(f"API quota/rate-limit: {detail[:120]}")
            if any(s in detail.lower() for s in ["401", "user not found", "invalid"]):
                pytest.xfail(f"API auth error (check key validity): {detail[:120]}")
            if "litellm" in detail.lower() or "not installed" in detail.lower():
                pytest.xfail(f"Missing optional dependency: {detail[:120]}")
            pytest.fail(f"Unexpected 502: {detail[:200]}")
        assert resp.status_code == 200, f"Expected 200, got {resp.status_code}: {resp.text[:200]}"
        if endpoint == "analyze":
            assert 0 <= resp.json()["score"] <= 100
        elif endpoint == "cover-letter":
            assert len(resp.json().get("content", "")) > 20

    def test_complete_openrouter(self, client):
        """Full cover-letter round-trip via API when OPENROUTER_API_KEY is set."""
        _skip_no_key("OPENROUTER_API_KEY")
        resp = self._api_call(
            client, "openrouter", "openrouter_api_key",
            os.getenv("OPENROUTER_API_KEY"),
            os.getenv("OPENROUTER_MODEL", "meta-llama/llama-3.1-8b-instruct:free"),
            "cover-letter", {"job_title": "Python Developer", "company": "TestCo", "extra_notes": ""}
        )
        self._assert_ai_ok(resp, "cover-letter")

    def test_complete_anthropic(self, client):
        """Full analysis round-trip via API when ANTHROPIC_API_KEY is set."""
        _skip_no_key("ANTHROPIC_API_KEY")
        resp = self._api_call(
            client, "anthropic", "anthropic_api_key",
            os.getenv("ANTHROPIC_API_KEY"),
            os.getenv("ANTHROPIC_MODEL", "claude-haiku-4-5-20251001"),
            "analyze", {}
        )
        self._assert_ai_ok(resp, "analyze")

    def test_complete_openai(self, client):
        """Full analysis round-trip via API when OPENAI_API_KEY is set."""
        _skip_no_key("OPENAI_API_KEY")
        resp = self._api_call(
            client, "openai", "api_key",
            os.getenv("OPENAI_API_KEY"),
            os.getenv("OPENAI_MODEL", "gpt-4o-mini"),
            "analyze", {}
        )
        self._assert_ai_ok(resp, "analyze")


# ── .env detection helper ─────────────────────────────────────────────────────

class TestEnvConfig:
    def test_env_file_detected(self):
        """Verifies .env loading works (passes even if no keys are set)."""
        env_path = _backend / ".env"
        if not env_path.exists():
            pytest.skip(".env file not found in backend dir")
        content = env_path.read_text()
        assert len(content) > 0, ".env file is empty"
        # Check at least one key is present
        has_key = any(
            key in content
            for key in ["OPENAI_API_KEY", "ANTHROPIC_API_KEY", "OPENROUTER_API_KEY"]
        )
        assert has_key, ".env has no recognized AI provider keys"
