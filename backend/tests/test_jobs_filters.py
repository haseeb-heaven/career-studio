"""Tests for advanced job search filters, sort, and pagination (Issue #7)."""
import json
import sys
from pathlib import Path
from unittest.mock import patch, MagicMock

sys.path.insert(0, str(Path(__file__).parent.parent))


def _auth(client, username):
    r = client.post(
        "/api/auth/register",
        json={"username": username, "password": "password123", "email": f"{username}@x.com"},
    )
    if r.status_code == 400:
        r = client.post("/api/auth/login", data={"username": username, "password": "password123"})
    return {"Authorization": f"Bearer {r.json()['access_token']}"}


def _profile(client, headers):
    data = json.dumps({
        "full_name": "Dev User",
        "skills": [
            {"name": "Python", "years": 5},
            {"name": "FastAPI", "years": 3},
            {"name": "Machine Learning", "years": 4},
        ],
        "experience": [{"company": "AI Corp", "role": "ML Engineer", "start": "2020"}],
        "education": [{"institution": "MIT", "degree": "BSc", "field": "CS", "start": "2014", "end": "2018"}],
        "certifications": [{"name": "AWS", "issuer": "Amazon", "date": "2023"}],
    }).encode()
    return client.post(
        "/api/import", files={"file": ("p.json", data, "application/json")}, headers=headers
    ).json()["profile_id"]


# Three mock jobs of varying score / type / date / salary
MOCK_JOBS_BODY = json.dumps({
    "jobs": [
        {
            "title": "Python Developer",
            "company_name": "TechCorp",
            "candidate_required_location": "Remote",
            "url": "https://remotive.com/job/1",
            "description": "Looking for Python FastAPI developer with Machine Learning skills. 3+ years of experience.",
            "publication_date": "2026-06-15",
            "job_type": "full_time",
        },
        {
            "title": "Junior Java Developer",
            "company_name": "DataInc",
            "candidate_required_location": "New York, NY",
            "url": "https://remotive.com/job/2",
            "description": "Entry level position. Java backend development.",
            "publication_date": "2026-01-15",
            "job_type": "full_time",
        },
        {
            "title": "Data Scientist",
            "company_name": "MLStartup",
            "candidate_required_location": "Remote",
            "url": "https://remotive.com/job/3",
            "description": "Python and Machine Learning expert needed. AWS certification required. 5+ years experience.",
            "publication_date": "2026-06-18",
            "job_type": "contract",
        },
    ]
}).encode()


def _mock_remotive_only():
    mock_resp = MagicMock()
    mock_resp.read.return_value = MOCK_JOBS_BODY
    mock_resp.__enter__ = lambda s: s
    mock_resp.__exit__ = MagicMock(return_value=False)

    empty = MagicMock()
    empty.read.return_value = b'[]'
    empty.__enter__ = lambda s: s
    empty.__exit__ = MagicMock(return_value=False)
    return mock_resp, empty


# ── Response shape ────────────────────────────────────────────────────────────

def test_search_response_shape(client):
    h = _auth(client, "shape_user")
    pid = _profile(client, h)
    mock_resp, empty = _mock_remotive_only()
    with patch("routers.jobs_router.urllib.request.urlopen") as mu, \
         patch("routers.jobs_router.urllib.request.Request"):
        mu.side_effect = [mock_resp, empty]
        resp = client.get(f"/api/profiles/{pid}/jobs?portal=remotive", headers=h)
    assert resp.status_code == 200
    body = resp.json()
    for k in ("query", "total", "offset", "limit", "has_more", "jobs"):
        assert k in body
    assert body["total"] >= 1
    for job in body["jobs"]:
        assert "match_breakdown" in job
        assert "matched_skills" in job
        assert "missing_skills" in job
        assert "is_remote" in job
        assert "date_posted" in job
        assert "job_type" in job


# ── Filters ───────────────────────────────────────────────────────────────────

def test_min_match_score_filter(client):
    h = _auth(client, "filt_score_user")
    pid = _profile(client, h)
    mock_resp, empty = _mock_remotive_only()
    with patch("routers.jobs_router.urllib.request.urlopen") as mu, \
         patch("routers.jobs_router.urllib.request.Request"):
        mu.side_effect = [mock_resp, empty]
        # First do a baseline search
        base = client.get(f"/api/profiles/{pid}/jobs?portal=remotive&limit=50", headers=h).json()
        baseline_total = base["total"]
        # With a high threshold, fewer results
        strict = client.get(
            f"/api/profiles/{pid}/jobs?portal=remotive&limit=50&min_match_score=70", headers=h
        ).json()
        assert strict["total"] <= baseline_total


def test_date_posted_last_7d_filter(client):
    h = _auth(client, "filt_date_user")
    pid = _profile(client, h)
    mock_resp, empty = _mock_remotive_only()
    with patch("routers.jobs_router.urllib.request.urlopen") as mu, \
         patch("routers.jobs_router.urllib.request.Request"):
        mu.side_effect = [mock_resp, empty]
        resp = client.get(
            f"/api/profiles/{pid}/jobs?portal=remotive&date_posted=last_7d&limit=50", headers=h
        ).json()
        for job in resp["jobs"]:
            # The Jan 15 job should be filtered out
            assert job["date_posted"] == "" or job["date_posted"] >= "2026-06-12"


def test_job_type_filter(client):
    h = _auth(client, "filt_type_user")
    pid = _profile(client, h)
    mock_resp, empty = _mock_remotive_only()
    with patch("routers.jobs_router.urllib.request.urlopen") as mu, \
         patch("routers.jobs_router.urllib.request.Request"):
        mu.side_effect = [mock_resp, empty]
        resp = client.get(
            f"/api/profiles/{pid}/jobs?portal=remotive&job_type=contract&limit=50", headers=h
        ).json()
        for job in resp["jobs"]:
            assert job["job_type"] == "contract"


def test_sort_recent(client):
    h = _auth(client, "filt_sort_user")
    pid = _profile(client, h)
    mock_resp, empty = _mock_remotive_only()
    with patch("routers.jobs_router.urllib.request.urlopen") as mu, \
         patch("routers.jobs_router.urllib.request.Request"):
        mu.side_effect = [mock_resp, empty]
        resp = client.get(
            f"/api/profiles/{pid}/jobs?portal=remotive&sort=recent&limit=50", headers=h
        ).json()
        dates = [j["date_posted"] for j in resp["jobs"] if j["date_posted"]]
        # Should be descending
        assert dates == sorted(dates, reverse=True)


def test_sort_best_match_default(client):
    h = _auth(client, "filt_default_user")
    pid = _profile(client, h)
    mock_resp, empty = _mock_remotive_only()
    with patch("routers.jobs_router.urllib.request.urlopen") as mu, \
         patch("routers.jobs_router.urllib.request.Request"):
        mu.side_effect = [mock_resp, empty]
        resp = client.get(f"/api/profiles/{pid}/jobs?portal=remotive&limit=50", headers=h).json()
        scores = [j["match_score"] for j in resp["jobs"]]
        # Default sort is best_match: scores should be descending
        assert scores == sorted(scores, reverse=True)


def test_invalid_sort_returns_400(client):
    h = _auth(client, "filt_bad_sort")
    pid = _profile(client, h)
    resp = client.get(f"/api/profiles/{pid}/jobs?sort=invalid_sort", headers=h)
    assert resp.status_code == 400


# ── Pagination ───────────────────────────────────────────────────────────────

def test_pagination(client):
    h = _auth(client, "paging_user")
    pid = _profile(client, h)
    mock_resp, empty = _mock_remotive_only()
    with patch("routers.jobs_router.urllib.request.urlopen") as mu, \
         patch("routers.jobs_router.urllib.request.Request"):
        # Each /jobs call hits Remotive once. Two calls → two mock responses.
        mu.side_effect = [mock_resp, mock_resp]
        first = client.get(
            f"/api/profiles/{pid}/jobs?portal=remotive&limit=1&offset=0", headers=h
        ).json()
        second = client.get(
            f"/api/profiles/{pid}/jobs?portal=remotive&limit=1&offset=1", headers=h
        ).json()
        assert first["limit"] == 1
        assert first["offset"] == 0
        assert second["offset"] == 1
        if first["total"] > 1:
            assert first["jobs"][0]["id"] != second["jobs"][0]["id"]


# ── Missing skills / matched skills ──────────────────────────────────────────

def test_matched_and_missing_skills_in_response(client):
    h = _auth(client, "gap_user")
    pid = _profile(client, h)
    mock_resp, empty = _mock_remotive_only()
    with patch("routers.jobs_router.urllib.request.urlopen") as mu, \
         patch("routers.jobs_router.urllib.request.Request"):
        mu.side_effect = [mock_resp, empty]
        resp = client.get(f"/api/profiles/{pid}/jobs?portal=remotive&limit=50", headers=h).json()
        # At least one job should have Python in matched_skills
        python_matches = [j for j in resp["jobs"] if "Python" in j.get("matched_skills", [])]
        assert len(python_matches) >= 1


def test_match_breakdown_has_six_factors(client):
    h = _auth(client, "breakdown_user")
    pid = _profile(client, h)
    mock_resp, empty = _mock_remotive_only()
    with patch("routers.jobs_router.urllib.request.urlopen") as mu, \
         patch("routers.jobs_router.urllib.request.Request"):
        mu.side_effect = [mock_resp, empty]
        resp = client.get(f"/api/profiles/{pid}/jobs?portal=remotive&limit=50", headers=h).json()
        for job in resp["jobs"]:
            bd = job["match_breakdown"]
            for k in ("skills", "years", "education", "location", "certifications", "title"):
                assert k in bd, f"Missing {k} in breakdown for job {job['id']}"


# ── Source badge / remote flag ────────────────────────────────────────────────

def test_is_remote_flag_set_correctly(client):
    h = _auth(client, "remote_flag_user")
    pid = _profile(client, h)
    mock_resp, empty = _mock_remotive_only()
    with patch("routers.jobs_router.urllib.request.urlopen") as mu, \
         patch("routers.jobs_router.urllib.request.Request"):
        mu.side_effect = [mock_resp, empty]
        resp = client.get(f"/api/profiles/{pid}/jobs?portal=remotive&limit=50", headers=h).json()
        remote_jobs = [j for j in resp["jobs"] if "remote" in (j["location"] or "").lower()]
        assert all(j["is_remote"] for j in remote_jobs)
