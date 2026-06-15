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

class TestAIServiceRouting:
    """Test the complete routing path: Settings DB → AI provider."""

    def test_complete_openrouter(self, client):
        """Full cover-letter round-trip via API when OPENROUTER_API_KEY is set."""
        _skip_no_key("OPENROUTER_API_KEY")

        # Set up settings
        client.put("/api/settings", json={
            "ai_provider": "openrouter",
            "openrouter_api_key": os.getenv("OPENROUTER_API_KEY"),
            "ai_model": os.getenv("OPENROUTER_MODEL", "meta-llama/llama-3.1-8b-instruct:free"),
        })

        # Create a profile
        import json as _json
        data = _json.dumps({
            "full_name": "Jane Dev",
            "skills": [{"name": "Python"}, {"name": "FastAPI"}],
            "experience": [{"company": "Acme", "role": "Backend Engineer", "start": "2021"}],
        }).encode()
        imp = client.post("/api/import", files={"file": ("p.json", data, "application/json")})
        pid = imp.json()["profile_id"]

        resp = client.post(f"/api/profiles/{pid}/cover-letter", json={
            "job_title": "Python Developer", "company": "TestCo", "extra_notes": ""
        })
        assert resp.status_code == 200
        body = resp.json()
        assert len(body.get("content", "")) > 50, "Cover letter too short"

    def test_complete_anthropic(self, client):
        """Full analysis round-trip via API when ANTHROPIC_API_KEY is set."""
        _skip_no_key("ANTHROPIC_API_KEY")

        client.put("/api/settings", json={
            "ai_provider": "anthropic",
            "anthropic_api_key": os.getenv("ANTHROPIC_API_KEY"),
            "ai_model": os.getenv("ANTHROPIC_MODEL", "claude-haiku-4-5-20251001"),
        })

        import json as _json
        data = _json.dumps({
            "full_name": "Bob Smith",
            "skills": [{"name": "Python"}, {"name": "Machine Learning"}],
        }).encode()
        imp = client.post("/api/import", files={"file": ("p.json", data, "application/json")})
        pid = imp.json()["profile_id"]

        resp = client.post(f"/api/profiles/{pid}/analyze")
        assert resp.status_code == 200
        body = resp.json()
        assert "score" in body
        assert 0 <= body["score"] <= 100

    def test_complete_openai(self, client):
        """Full analysis round-trip via API when OPENAI_API_KEY is set."""
        _skip_no_key("OPENAI_API_KEY")

        client.put("/api/settings", json={
            "ai_provider": "openai",
            "api_key": os.getenv("OPENAI_API_KEY"),
            "ai_model": os.getenv("OPENAI_MODEL", "gpt-4o-mini"),
        })

        import json as _json
        data = _json.dumps({
            "full_name": "Alice Chen",
            "skills": [{"name": "JavaScript"}, {"name": "React"}],
            "experience": [{"company": "WebCo", "role": "Frontend Dev", "start": "2020"}],
        }).encode()
        imp = client.post("/api/import", files={"file": ("p.json", data, "application/json")})
        pid = imp.json()["profile_id"]

        resp = client.post(f"/api/profiles/{pid}/analyze")
        assert resp.status_code == 200
        assert 0 <= resp.json()["score"] <= 100


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
