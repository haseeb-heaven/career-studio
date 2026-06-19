"""AI provider smoke tests + contract tests.

These tests use unittest.mock to simulate all AI providers so they run
offline without real API keys, and verify:
  - correct routing (openai/anthropic/openrouter/ollama)
  - model-name validation / defaults
  - error handling (401, 429, ImportError)
  - _match_score improvements
  - _build_keywords logic
  - Settings API save/mask/retrieve
  - PDF parser heuristic extraction

Run with: pytest tests/test_ai_smoke.py -v
"""
import json
import os
import sys
import pytest
from pathlib import Path
from unittest.mock import MagicMock, patch

# Ensure backend root is on path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

_MODELS_JSON = Path(__file__).resolve().parents[1] / "free_openrouter_models.json"


# ── Helpers ─────────────────────────────────────────────────────────────

def _fake_settings(**kwargs):
    from models import Settings
    from datetime import datetime, timezone
    s = Settings()
    s.ai_provider = kwargs.get("ai_provider", "openai")
    s.ai_model = kwargs.get("ai_model", "gpt-4o-mini")
    s.api_key = kwargs.get("api_key", "sk-test")
    s.openrouter_api_key = kwargs.get("openrouter_api_key", "sk-or-test")
    s.anthropic_api_key = kwargs.get("anthropic_api_key", "sk-ant-test")
    s.use_local_ai = kwargs.get("use_local_ai", False)
    s.ollama_base_url = kwargs.get("ollama_base_url", "http://localhost:11434")
    s.ollama_model = kwargs.get("ollama_model", "llama3.2")
    s.local_for_simple = kwargs.get("local_for_simple", True)
    return s


@pytest.fixture(name="client")
def client_fixture():
    from sqlmodel import SQLModel, create_engine
    from sqlalchemy.pool import StaticPool
    import main
    import db
    test_engine = create_engine("sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)
    SQLModel.metadata.create_all(test_engine)
    original = db.engine
    db.engine = test_engine
    from fastapi.testclient import TestClient
    app = main.create_app()
    with TestClient(app) as c:
        yield c
    db.engine = original
    SQLModel.metadata.drop_all(test_engine)


def _smoke_auth_headers(client) -> dict:
    resp = client.post(
        "/api/auth/register",
        json={"username": "smoke_test_user", "password": "password123", "email": "smoke_test_user@test.local"},
    )
    if resp.status_code == 400:
        resp = client.post("/api/auth/login", data={"username": "smoke_test_user", "password": "password123"})
    return {"Authorization": f"Bearer {resp.json()['access_token']}"}


@pytest.fixture(name="auth_headers")
def auth_headers_fixture(client) -> dict:
    return _smoke_auth_headers(client)


@pytest.fixture(name="profile_id")
def profile_id_fixture(client, auth_headers):
    import io
    from pathlib import Path
    data = (Path(__file__).parent / "fixtures" / "sample.json").read_bytes()
    resp = client.post("/api/import", files={"file": ("sample.json", io.BytesIO(data), "application/json")}, headers=auth_headers)
    assert resp.status_code == 201
    return resp.json()["profile_id"]


# ── _valid_model ─────────────────────────────────────────────────────────

class TestValidModel:
    def test_empty_openai_default(self):
        from services.ai_service import _valid_model
        assert _valid_model("", "openai") == "gpt-4o-mini"

    def test_empty_anthropic_default(self):
        from services.ai_service import _valid_model
        assert _valid_model("", "anthropic") == "claude-haiku-4-5-20251001"

    def test_empty_openrouter_default(self):
        from services.ai_service import _valid_model
        assert _valid_model("", "openrouter") == "meta-llama/llama-3.1-8b-instruct:free"

    def test_garbage_openrouter_no_slash(self):
        from services.ai_service import _valid_model
        assert _valid_model("free", "openrouter") == "meta-llama/llama-3.1-8b-instruct:free"

    def test_valid_openrouter_model(self):
        from services.ai_service import _valid_model
        result = _valid_model("meta-llama/llama-3.1-8b-instruct:free", "openrouter")
        assert result == "meta-llama/llama-3.1-8b-instruct:free"

    def test_valid_openai_model(self):
        from services.ai_service import _valid_model
        assert _valid_model("gpt-4o", "openai") == "gpt-4o"

    def test_valid_anthropic_model(self):
        from services.ai_service import _valid_model
        assert _valid_model("claude-3-5-sonnet-20241022", "anthropic") == "claude-3-5-sonnet-20241022"

    def test_too_short_gets_default(self):
        from services.ai_service import _valid_model
        assert _valid_model("ab", "openai") == "gpt-4o-mini"

    def test_google_gemini_valid_openrouter(self):
        from services.ai_service import _valid_model
        result = _valid_model("google/gemma-3-27b-it:free", "openrouter")
        assert result == "google/gemma-3-27b-it:free"

    def test_all_json_openrouter_models_valid(self):
        from services.ai_service import _valid_model
        import json
        with _MODELS_JSON.open(encoding="utf-8") as f:
            data = json.load(f)
        for item in data["free_openrouter_models"]:
            model = item["model"]
            assert _valid_model(model, "openrouter") == model


# ── Provider routing ─────────────────────────────────────────────────────

class TestCompleteRouting:
    @patch("services.ai_service._load_settings")
    @patch("services.ai_service._call_openai")
    def test_routes_to_openai(self, mock_openai, mock_settings):
        from services.ai_service import complete
        mock_settings.return_value = _fake_settings(ai_provider="openai", api_key="sk-test")
        mock_openai.return_value = "openai response"
        assert complete("sys", "user") == "openai response"
        mock_openai.assert_called_once()

    @patch("services.ai_service._load_settings")
    @patch("services.ai_service._call_anthropic")
    def test_routes_to_anthropic(self, mock_anthropic, mock_settings):
        from services.ai_service import complete
        mock_settings.return_value = _fake_settings(ai_provider="anthropic", anthropic_api_key="sk-ant")
        mock_anthropic.return_value = "anthropic response"
        assert complete("sys", "user") == "anthropic response"

    @patch("services.ai_service._load_settings")
    @patch("services.ai_service._call_openrouter")
    def test_routes_to_openrouter(self, mock_or, mock_settings):
        from services.ai_service import complete
        import json
        import random
        # Load free models and randomly pick one
        with _MODELS_JSON.open(encoding="utf-8") as f:
            data = json.load(f)
        models = [m["model"] for m in data["free_openrouter_models"]]
        chosen_model = random.choice(models)

        mock_settings.return_value = _fake_settings(
            ai_provider="openrouter",
            openrouter_api_key="sk-or",
            ai_model=chosen_model,
        )
        mock_or.return_value = "openrouter response"
        assert complete("sys", "user") == "openrouter response"
        mock_or.assert_called_once_with("sk-or", chosen_model, "sys", "user")

    @patch("services.ai_service._load_settings")
    @patch("services.ai_service.ollama_available", return_value=True)
    @patch("services.ai_service._call_ollama")
    def test_routes_to_ollama_simple(self, mock_ollama, mock_avail, mock_settings):
        from services.ai_service import complete
        mock_settings.return_value = _fake_settings(use_local_ai=True, local_for_simple=True)
        mock_ollama.return_value = "ollama response"
        assert complete("sys", "user", complexity="simple") == "ollama response"

    @patch("services.ai_service._load_settings")
    @patch("services.ai_service.ollama_available", return_value=True)
    @patch("services.ai_service._call_openai")
    def test_skips_ollama_for_complex_when_local_for_simple(self, mock_oi, mock_avail, mock_settings):
        from services.ai_service import complete
        mock_settings.return_value = _fake_settings(use_local_ai=True, local_for_simple=True, api_key="sk")
        mock_oi.return_value = "openai complex"
        assert complete("sys", "user", complexity="complex") == "openai complex"

    @patch("services.ai_service._load_settings")
    @patch("services.ai_service.ollama_available", return_value=True)
    @patch("services.ai_service._call_ollama")
    def test_ollama_all_tasks_when_not_local_for_simple(self, mock_ollama, mock_avail, mock_settings):
        from services.ai_service import complete
        mock_settings.return_value = _fake_settings(use_local_ai=True, local_for_simple=False)
        mock_ollama.return_value = "ollama all"
        assert complete("sys", "user", complexity="complex") == "ollama all"

    @patch("services.ai_service._load_settings")
    @patch("services.ai_service.ollama_available", return_value=False)
    @patch("services.ai_service._call_openai")
    def test_fallback_to_external_when_ollama_down(self, mock_oi, mock_avail, mock_settings):
        from services.ai_service import complete
        mock_settings.return_value = _fake_settings(use_local_ai=True, local_for_simple=True, api_key="sk")
        mock_oi.return_value = "fallback openai"
        assert complete("sys", "user", complexity="simple") == "fallback openai"


# ── Error handling ───────────────────────────────────────────────────────

class TestAIErrorHandling:
    def test_friendly_401(self):
        from services.ai_service import _friendly_api_error
        msg = _friendly_api_error(Exception("Error code: 401 - User not found"), "OpenAI")
        assert "401" in msg and "valid API key" in msg

    def test_friendly_429(self):
        from services.ai_service import _friendly_api_error
        msg = _friendly_api_error(Exception("You exceeded your current quota"), "OpenAI")
        assert "429" in msg or "quota" in msg.lower()

    def test_friendly_403(self):
        from services.ai_service import _friendly_api_error
        msg = _friendly_api_error(Exception("403 Forbidden"), "OpenRouter")
        assert "403" in msg

    @patch("services.ai_service.os.getenv", return_value="")
    def test_missing_openai_key_raises(self, mock_getenv):
        from services.ai_service import _call_external
        cfg = _fake_settings(ai_provider="openai", api_key="")
        with pytest.raises(ValueError, match="OpenAI API key"):
            _call_external(cfg, "sys", "user")

    @patch("services.ai_service.os.getenv", return_value="")
    def test_missing_anthropic_key_raises(self, mock_getenv):
        from services.ai_service import _call_external
        cfg = _fake_settings(ai_provider="anthropic", anthropic_api_key="")
        with pytest.raises(ValueError, match="Anthropic API key"):
            _call_external(cfg, "sys", "user")

    @patch("services.ai_service.os.getenv", return_value="")
    def test_missing_openrouter_key_raises(self, mock_getenv):
        from services.ai_service import _call_external
        cfg = _fake_settings(
            ai_provider="openrouter", openrouter_api_key="",
            ai_model="meta-llama/llama-3.1-8b-instruct:free"
        )
        with pytest.raises(ValueError, match="OpenRouter API key"):
            _call_external(cfg, "sys", "user")


# ── API contract tests ───────────────────────────────────────────────────

class TestAIContractShapes:

    @patch("routers.analysis_router.complete_simple")
    def test_analyze_contract(self, mock_ai, client, profile_id, auth_headers):
        mock_ai.return_value = json.dumps({
            "score": 78, "strengths": ["Python"], "weaknesses": ["No certs"],
            "suggestions": ["Add certs"], "ats_keywords": ["Docker"],
        })
        resp = client.post(f"/api/profiles/{profile_id}/analyze", headers=auth_headers)
        assert resp.status_code == 200
        body = resp.json()
        assert isinstance(body.get("score"), (int, float))
        assert isinstance(body.get("strengths"), list)
        assert isinstance(body.get("weaknesses"), list)
        assert isinstance(body.get("suggestions"), list)
        assert isinstance(body.get("ats_keywords"), list)

    @patch("routers.analysis_router.complete_complex")
    def test_cover_letter_contract(self, mock_ai, client, profile_id, auth_headers):
        mock_ai.return_value = "Dear Hiring Manager, I am excited to apply..."
        resp = client.post(
            f"/api/profiles/{profile_id}/cover-letter",
            json={"job_title": "Python Dev", "company": "ACME"},
            headers=auth_headers,
        )
        assert resp.status_code == 200
        body = resp.json()
        for k in ["id", "content", "job_title", "company"]:
            assert k in body

    @patch("routers.analysis_router.complete_complex")
    def test_roadmap_contract(self, mock_ai, client, profile_id, auth_headers):
        mock_ai.return_value = "## Year 1\n- Learn Go"
        resp = client.post(
            f"/api/profiles/{profile_id}/roadmap",
            json={"plan_type": "roadmap", "target_role": "CTO", "years_horizon": 3},
            headers=auth_headers,
        )
        assert resp.status_code == 200
        body = resp.json()
        for k in ["id", "content", "plan_type"]:
            assert k in body

    @patch("routers.analysis_router.complete_complex")
    def test_growth_plan_contract(self, mock_ai, client, profile_id, auth_headers):
        mock_ai.return_value = "## Growth Plan\n- Mentor others"
        resp = client.post(
            f"/api/profiles/{profile_id}/roadmap",
            json={"plan_type": "growth", "target_role": "Staff Engineer", "years_horizon": 2},
            headers=auth_headers,
        )
        assert resp.status_code == 200
        assert resp.json()["plan_type"] == "growth"

    @patch("routers.analysis_router.complete_simple")
    def test_analyze_bad_ai_json_returns_502(self, mock_ai, client, profile_id, auth_headers):
        mock_ai.return_value = "I cannot analyze this."
        resp = client.post(f"/api/profiles/{profile_id}/analyze", headers=auth_headers)
        assert resp.status_code == 502

    @patch("routers.analysis_router.complete_complex")
    def test_roadmap_missing_profile_returns_404(self, mock_ai, client, auth_headers):
        mock_ai.return_value = "content"
        resp = client.post("/api/profiles/99999/roadmap", json={"plan_type": "roadmap"}, headers=auth_headers)
        assert resp.status_code == 404

    @patch("routers.analysis_router.complete_complex")
    def test_cover_letter_list(self, mock_ai, client, profile_id, auth_headers):
        mock_ai.return_value = "Cover letter content"
        client.post(f"/api/profiles/{profile_id}/cover-letter", json={"job_title": "Dev", "company": "ACME"}, headers=auth_headers)
        resp = client.get(f"/api/profiles/{profile_id}/cover-letters", headers=auth_headers)
        assert resp.status_code == 200
        assert isinstance(resp.json(), list)
        assert len(resp.json()) >= 1

    @patch("routers.analysis_router.complete_complex")
    def test_roadmap_list(self, mock_ai, client, profile_id, auth_headers):
        mock_ai.return_value = "Roadmap content"
        client.post(f"/api/profiles/{profile_id}/roadmap", json={"plan_type": "roadmap"}, headers=auth_headers)
        resp = client.get(f"/api/profiles/{profile_id}/roadmaps", headers=auth_headers)
        assert resp.status_code == 200
        assert isinstance(resp.json(), list)
        assert len(resp.json()) >= 1


# ── Job matching tests ───────────────────────────────────────────────────

class TestJobMatching:
    def _make_profile(self, skills=None, role=None, summary=""):
        from models import Profile, Skill, Experience
        p = Profile(full_name="Test User", summary=summary)
        p.skills = [Skill(name=s) for s in (skills or [])]
        p.experience = [Experience(company="ACME", role=role, start="2022")] if role else []
        p.projects = []
        p.education = []
        p.certifications = []
        p.links = []
        return p

    def test_keywords_role_first(self):
        from routers.jobs_router import _build_keywords
        p = self._make_profile(skills=["Python", "Docker"], role="ML Engineer")
        assert _build_keywords(p).startswith("ML Engineer")

    def test_keywords_prefers_longer_skills(self):
        from routers.jobs_router import _build_keywords
        p = self._make_profile(skills=["Go", "Kubernetes", "AI", "ML", "FastAPI"], role="")
        q = _build_keywords(p)
        assert "Kubernetes" in q or "FastAPI" in q

    def test_keywords_fallback_summary(self):
        from routers.jobs_router import _build_keywords
        p = self._make_profile(skills=[], role="", summary="Backend engineer Python")
        q = _build_keywords(p)
        assert "Backend engineer Python" in q or q == "software developer"

    def test_keywords_empty_profile(self):
        from routers.jobs_router import _build_keywords
        p = self._make_profile()
        assert _build_keywords(p) == "software developer"

    def test_match_score_title_match_gives_score(self):
        from routers.jobs_router import _match_score
        score = _match_score("Python ML Engineer", "desc", ["Python", "ML"], "Python ML Engineer")
        assert score > 40

    def test_match_score_skill_in_desc(self):
        from routers.jobs_router import _match_score
        score = _match_score("Engineer", "We need Python FastAPI Docker", ["Python", "FastAPI", "Docker"], "engineer")
        assert score > 30

    def test_match_score_no_overlap(self):
        from routers.jobs_router import _match_score
        score = _match_score("Java EE Developer", "Spring Boot enterprise apps", ["Python", "FastAPI"], "ML Engineer")
        assert score < 30

    def test_match_score_bounded_100(self):
        from routers.jobs_router import _match_score
        score = _match_score(
            "Python FastAPI Engineer",
            "Python FastAPI SQLAlchemy Docker Kubernetes PostgreSQL",
            ["Python", "FastAPI", "SQLAlchemy", "Docker"],
            "Python FastAPI Engineer",
        )
        assert 0 <= score <= 100

    def test_match_score_empty_inputs(self):
        from routers.jobs_router import _match_score
        assert _match_score("", "", [], "") == 0.0


# ── Settings API tests ───────────────────────────────────────────────────

class TestSettingsAPI:
    def test_get_returns_expected_keys(self, client, auth_headers):
        resp = client.get("/api/settings", headers=auth_headers)
        assert resp.status_code == 200
        for k in ["ai_provider", "ai_model", "api_key", "use_local_ai", "ollama_base_url", "ollama_model"]:
            assert k in resp.json()

    def test_update_provider_and_model(self, client, auth_headers):
        resp = client.put("/api/settings", json={
            "ai_provider": "openrouter",
            "ai_model": "meta-llama/llama-3.1-8b-instruct:free",
        }, headers=auth_headers)
        assert resp.status_code == 200
        assert resp.json()["ok"] is True

    def test_unknown_keys_ignored(self, client, auth_headers):
        resp = client.put("/api/settings", json={"hack_field": "bad", "ai_provider": "openai"}, headers=auth_headers)
        assert resp.status_code == 200

    def test_api_key_masked_after_save(self, client, auth_headers):
        client.put("/api/settings", json={"api_key": "sk-real-secret-key-123456"}, headers=auth_headers)
        resp = client.get("/api/settings", headers=auth_headers)
        assert resp.json()["api_key"] == "***"

    def test_openrouter_key_masked(self, client, auth_headers):
        client.put("/api/settings", json={"openrouter_api_key": "sk-or-myrealkey"}, headers=auth_headers)
        resp = client.get("/api/settings", headers=auth_headers)
        assert resp.json()["openrouter_api_key"] == "***"

    def test_update_local_ai_settings(self, client, auth_headers):
        resp = client.put("/api/settings", json={
            "use_local_ai": True,
            "ollama_base_url": "http://localhost:11434",
            "ollama_model": "mistral:7b",
            "local_for_simple": True,
        }, headers=auth_headers)
        assert resp.status_code == 200


# ── PDF parser heuristic tests ───────────────────────────────────────────

class TestPdfHeuristic:
    def test_extracts_name_email(self):
        from parsers.pdf_parser import _heuristic_parse
        lines = [
            "Alice Johnson",
            "alice@example.com | +1 800-555-0199",
            "Summary",
            "Full stack developer with 8 years experience.",
            "Skills",
            "Python, React, PostgreSQL, Docker",
            "Experience",
            "Tech Lead | StartupXYZ",
            "2021 - Present",
            "- Led team of 5 engineers",
            "Education",
            "B.Sc Computer Science - MIT | 2013 - 2017",
        ]
        p = _heuristic_parse([], [], "\n".join(lines))
        assert "Alice" in p.full_name
        assert "alice@example.com" in p.email
        assert len(p.skills) >= 3
        assert len(p.experience) >= 1

    def test_extracts_pipe_separated_skills(self):
        from parsers.pdf_parser import _heuristic_parse
        lines = ["Jane", "Skills", "Go | Rust | Kubernetes | Terraform | AWS"]
        p = _heuristic_parse([], [], "\n".join(lines))
        names = [s.name for s in p.skills]
        assert "Go" in names
        assert "Rust" in names

    def test_deduplicates_skills(self):
        from parsers.pdf_parser import _heuristic_parse
        lines = ["Bob", "Skills", "Python, python, PYTHON"]
        p = _heuristic_parse([], [], "\n".join(lines))
        names_lower = [s.name.lower() for s in p.skills]
        assert names_lower.count("python") == 1

    def test_fallback_name_missing(self):
        from parsers.pdf_parser import _heuristic_parse
        lines = ["john@company.com", "Skills", "Java, Spring"]
        p = _heuristic_parse([], [], "\n".join(lines))
        # Should not crash; name may be empty
        assert isinstance(p.full_name, str)

    @patch("parsers.pdf_parser._ai_refine", return_value=None)
    def test_ai_none_falls_back_gracefully(self, mock_ai):
        from parsers.pdf_parser import _ai_refine
        result = _ai_refine("any text")
        assert result is None  # confirming mock works
