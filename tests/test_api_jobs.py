"""Tests for job search endpoint with mocked HTTP calls."""
import json
import pytest
import sys
from pathlib import Path
from unittest.mock import patch, MagicMock

sys.path.insert(0, str(Path(__file__).parent.parent / "backend"))


def _create_profile_with_skills(client) -> int:
    data = json.dumps({
        "full_name": "Dev User",
        "email": "dev@example.com",
        "skills": [
            {"name": "Python", "years": 5},
            {"name": "FastAPI", "years": 3},
            {"name": "Machine Learning", "years": 4},
        ],
        "experience": [{"company": "AI Corp", "role": "ML Engineer", "start": "2020"}],
    }).encode()
    resp = client.post("/api/import", files={"file": ("p.json", data, "application/json")})
    assert resp.status_code == 201
    return resp.json()["profile_id"]


MOCK_REMOTIVE_RESPONSE = json.dumps({
    "jobs": [
        {
            "title": "Python Developer",
            "company_name": "TechCorp",
            "candidate_required_location": "Remote",
            "url": "https://remotive.com/job/1",
            "description": "Looking for Python FastAPI developer with Machine Learning skills",
        },
        {
            "title": "Data Scientist",
            "company_name": "DataInc",
            "candidate_required_location": "Worldwide",
            "url": "https://remotive.com/job/2",
            "description": "Data science role using Python and ML",
        },
    ]
}).encode()

MOCK_REMOTEOK_RESPONSE = json.dumps([
    {"legal": "Legal Info"},  # first item is always metadata, should be skipped
    {
        "position": "ML Engineer",
        "company": "StartupX",
        "location": "Remote",
        "url": "https://remoteok.com/job/3",
        "description": "Machine Learning engineer needed. Python experience required.",
    }
]).encode()


class TestJobSearch:
    def test_job_search_returns_results(self, client):
        pid = _create_profile_with_skills(client)
        mock_resp = MagicMock()
        mock_resp.read.return_value = MOCK_REMOTIVE_RESPONSE
        mock_resp.__enter__ = lambda s: s
        mock_resp.__exit__ = MagicMock(return_value=False)

        mock_ok_resp = MagicMock()
        mock_ok_resp.read.return_value = MOCK_REMOTEOK_RESPONSE
        mock_ok_resp.__enter__ = lambda s: s
        mock_ok_resp.__exit__ = MagicMock(return_value=False)

        with patch("routers.jobs_router.urllib.request.urlopen") as mock_urlopen, \
             patch("routers.jobs_router.urllib.request.Request") as mock_request:
            mock_urlopen.side_effect = [mock_resp, mock_ok_resp]
            resp = client.get(f"/api/profiles/{pid}/jobs?limit=10")

        assert resp.status_code == 200
        body = resp.json()
        assert "query" in body
        assert "jobs" in body
        assert body["query"], "Query should not be empty"

    def test_job_search_match_scores(self, client):
        pid = _create_profile_with_skills(client)
        mock_resp = MagicMock()
        mock_resp.read.return_value = MOCK_REMOTIVE_RESPONSE
        mock_resp.__enter__ = lambda s: s
        mock_resp.__exit__ = MagicMock(return_value=False)

        mock_ok_resp = MagicMock()
        mock_ok_resp.read.return_value = MOCK_REMOTEOK_RESPONSE
        mock_ok_resp.__enter__ = lambda s: s
        mock_ok_resp.__exit__ = MagicMock(return_value=False)

        with patch("routers.jobs_router.urllib.request.urlopen") as mock_urlopen, \
             patch("routers.jobs_router.urllib.request.Request"):
            mock_urlopen.side_effect = [mock_resp, mock_ok_resp]
            resp = client.get(f"/api/profiles/{pid}/jobs?limit=10")

        jobs = resp.json()["jobs"]
        if jobs:
            first = jobs[0]
            assert "match_score" in first
            assert 0 <= first["match_score"] <= 100

    def test_job_search_nonexistent_profile(self, client):
        resp = client.get("/api/profiles/99999/jobs")
        assert resp.status_code == 404

    def test_job_search_graceful_on_api_failure(self, client):
        pid = _create_profile_with_skills(client)
        with patch("routers.jobs_router.urllib.request.urlopen", side_effect=Exception("Network error")), \
             patch("routers.jobs_router.urllib.request.Request"):
            resp = client.get(f"/api/profiles/{pid}/jobs?limit=5")
        assert resp.status_code == 200
        body = resp.json()
        assert body["jobs"] == [] or isinstance(body["jobs"], list)

    def test_query_built_from_skills(self, client):
        pid = _create_profile_with_skills(client)
        mock_resp = MagicMock()
        mock_resp.read.return_value = b'{"jobs": []}'
        mock_resp.__enter__ = lambda s: s
        mock_resp.__exit__ = MagicMock(return_value=False)
        mock_ok = MagicMock()
        mock_ok.read.return_value = b"[]"
        mock_ok.__enter__ = lambda s: s
        mock_ok.__exit__ = MagicMock(return_value=False)

        with patch("routers.jobs_router.urllib.request.urlopen") as mu, \
             patch("routers.jobs_router.urllib.request.Request"):
            mu.side_effect = [mock_resp, mock_ok]
            resp = client.get(f"/api/profiles/{pid}/jobs?limit=10")

        query = resp.json()["query"]
        assert "Python" in query or "ML Engineer" in query or "Machine Learning" in query


class TestMatchScoreUnit:
    def test_full_match(self):
        from routers.jobs_router import _match_score
        score = _match_score("We need Python FastAPI developer", ["Python", "FastAPI"])
        assert score == 100.0

    def test_partial_match(self):
        from routers.jobs_router import _match_score
        score = _match_score("We need Python developer", ["Python", "FastAPI"])
        assert score == 50.0

    def test_no_match(self):
        from routers.jobs_router import _match_score
        score = _match_score("Java enterprise developer needed", ["Python", "FastAPI"])
        assert score == 0.0

    def test_empty_skills(self):
        from routers.jobs_router import _match_score
        score = _match_score("Some job description", [])
        assert score == 0.0

    def test_empty_description(self):
        from routers.jobs_router import _match_score
        score = _match_score("", ["Python"])
        assert score == 0.0

    def test_case_insensitive(self):
        from routers.jobs_router import _match_score
        score = _match_score("We need PYTHON developer", ["Python"])
        assert score == 100.0
