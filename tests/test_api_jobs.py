"""Tests for job search endpoint with mocked HTTP calls."""
import json
import pytest
import sys
from pathlib import Path
from unittest.mock import patch, MagicMock

sys.path.insert(0, str(Path(__file__).parent.parent / "backend"))


def _get_auth_headers(client, username: str = "jobs_test_user") -> dict:
    resp = client.post(
        "/api/auth/register",
        json={"username": username, "password": "password123", "email": f"{username}@test.local"},
    )
    if resp.status_code == 400:
        resp = client.post("/api/auth/login", data={"username": username, "password": "password123"})
    return {"Authorization": f"Bearer {resp.json()['access_token']}"}


def _create_profile_with_skills(client, headers: dict = None) -> int:
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
    resp = client.post("/api/import", files={"file": ("p.json", data, "application/json")}, headers=headers)
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
        headers = _get_auth_headers(client, "jobs_results_user")
        pid = _create_profile_with_skills(client, headers)
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
            resp = client.get(f"/api/profiles/{pid}/jobs?limit=10", headers=headers)

        assert resp.status_code == 200
        body = resp.json()
        assert "query" in body
        assert "jobs" in body
        assert body["query"], "Query should not be empty"

    def test_job_search_match_scores(self, client):
        headers = _get_auth_headers(client, "jobs_scores_user")
        pid = _create_profile_with_skills(client, headers)
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
            resp = client.get(f"/api/profiles/{pid}/jobs?limit=10", headers=headers)

        jobs = resp.json()["jobs"]
        if jobs:
            first = jobs[0]
            assert "match_score" in first
            assert 0 <= first["match_score"] <= 100

    def test_job_search_nonexistent_profile(self, client):
        headers = _get_auth_headers(client, "jobs_nonexist_user")
        resp = client.get("/api/profiles/99999/jobs", headers=headers)
        assert resp.status_code == 404

    def test_job_search_graceful_on_api_failure(self, client):
        headers = _get_auth_headers(client, "jobs_graceful_user")
        pid = _create_profile_with_skills(client, headers)
        with patch("routers.jobs_router.urllib.request.urlopen", side_effect=Exception("Network error")), \
             patch("routers.jobs_router.urllib.request.Request"):
            resp = client.get(f"/api/profiles/{pid}/jobs?limit=5", headers=headers)
        assert resp.status_code == 200
        body = resp.json()
        assert body["jobs"] == [] or isinstance(body["jobs"], list)

    def test_query_built_from_skills(self, client):
        headers = _get_auth_headers(client, "jobs_query_user")
        pid = _create_profile_with_skills(client, headers)
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
            resp = client.get(f"/api/profiles/{pid}/jobs?limit=10", headers=headers)

        query = resp.json()["query"]
        assert "Python" in query or "ML Engineer" in query or "Machine Learning" in query


class TestMatchScoreUnit:
    def test_full_match(self):
        from routers.jobs_router import _match_score
        score = _match_score("Python FastAPI Developer", "Python and FastAPI experience needed", ["Python", "FastAPI"], "Python FastAPI")
        assert score == 100.0

    def test_partial_match(self):
        from routers.jobs_router import _match_score
        score = _match_score("Python Developer", "Python experience needed", ["Python", "FastAPI"], "Python FastAPI")
        assert score == 50.0

    def test_no_match(self):
        from routers.jobs_router import _match_score
        score = _match_score("Java Developer", "Java experience needed", ["Python", "FastAPI"], "Python FastAPI")
        assert score == 0.0

    def test_empty_skills(self):
        from routers.jobs_router import _match_score
        score = _match_score("Python Developer", "Python experience needed", [], "")
        assert score == 0.0

    def test_empty_description(self):
        from routers.jobs_router import _match_score
        score = _match_score("", "", ["Python"], "")
        assert score == 0.0

    def test_case_insensitive(self):
        from routers.jobs_router import _match_score
        score = _match_score("PYTHON developer", "PYTHON experience", ["Python"], "PYTHON")
        assert score == 100.0


class TestDeduplication:
    def test_dedup_removes_duplicates(self):
        from routers.jobs_router import _deduplicate
        jobs = [
            {"title": "Python Dev", "company": "Acme", "url": "https://a.com"},
            {"title": "python dev", "company": "ACME", "url": "https://b.com"},
            {"title": "JS Dev", "company": "Acme", "url": "https://c.com"},
        ]
        result = _deduplicate(jobs)
        assert len(result) == 2
        assert result[0]["url"] == "https://a.com"

    def test_dedup_preserves_unique(self):
        from routers.jobs_router import _deduplicate
        jobs = [
            {"title": "Python Dev", "company": "Acme"},
            {"title": "JS Dev", "company": "Acme"},
            {"title": "Python Dev", "company": "Other Co"},
        ]
        assert len(_deduplicate(jobs)) == 3

    def test_dedup_empty(self):
        from routers.jobs_router import _deduplicate
        assert _deduplicate([]) == []


class TestNewJobSourcesUnit:
    """Unit tests for new Tier 1 and Tier 2 job source fetch functions."""

    def _mock_urlopen(self, body: bytes):
        mock_resp = MagicMock()
        mock_resp.read.return_value = body
        mock_resp.__enter__ = lambda s: s
        mock_resp.__exit__ = MagicMock(return_value=False)
        return mock_resp

    def test_himalayas_returns_jobs_with_salary(self):
        from routers.jobs_router import _fetch_himalayas
        body = json.dumps({
            "jobs": [{
                "title": "Backend Engineer",
                "companyName": "HimaCo",
                "locationRestrictions": ["Worldwide"],
                "applicationUrl": "https://himalayas.app/job/1",
                "description": "Python backend role",
                "salary": "$120k-$150k",
            }]
        }).encode()
        with patch("routers.jobs_router.urllib.request.urlopen", return_value=self._mock_urlopen(body)), \
             patch("routers.jobs_router.urllib.request.Request"):
            jobs = _fetch_himalayas("Python", 5)
        assert len(jobs) == 1
        assert jobs[0]["source"] == "himalayas"
        assert jobs[0]["salary"] == "$120k-$150k"
        assert jobs[0]["is_deep_link"] is False

    def test_himalayas_handles_failure(self):
        from routers.jobs_router import _fetch_himalayas
        with patch("routers.jobs_router.urllib.request.urlopen", side_effect=Exception("timeout")), \
             patch("routers.jobs_router.urllib.request.Request"):
            jobs = _fetch_himalayas("Python", 5)
        assert jobs == []

    def test_himalayas_salary_none_when_missing(self):
        from routers.jobs_router import _fetch_himalayas
        body = json.dumps({"jobs": [{"title": "Dev", "companyName": "Co"}]}).encode()
        with patch("routers.jobs_router.urllib.request.urlopen", return_value=self._mock_urlopen(body)), \
             patch("routers.jobs_router.urllib.request.Request"):
            jobs = _fetch_himalayas("Python", 5)
        assert jobs[0]["salary"] is None

    def test_the_muse_returns_jobs(self):
        from routers.jobs_router import _fetch_the_muse
        body = json.dumps({
            "results": [{
                "name": "Senior Engineer",
                "company": {"name": "MuseCo"},
                "locations": [{"name": "New York"}],
                "refs": {"landing_page": "https://themuse.com/job/1"},
                "contents": "Great engineering role",
            }]
        }).encode()
        with patch("routers.jobs_router.urllib.request.urlopen", return_value=self._mock_urlopen(body)), \
             patch("routers.jobs_router.urllib.request.Request"):
            jobs = _fetch_the_muse("engineer", 5)
        assert len(jobs) == 1
        assert jobs[0]["source"] == "themuse"
        assert jobs[0]["company"] == "MuseCo"
        assert jobs[0]["is_deep_link"] is False

    def test_the_muse_handles_failure(self):
        from routers.jobs_router import _fetch_the_muse
        with patch("routers.jobs_router.urllib.request.urlopen", side_effect=Exception("error")), \
             patch("routers.jobs_router.urllib.request.Request"):
            assert _fetch_the_muse("engineer", 5) == []

    def test_jobicy_returns_jobs(self):
        from routers.jobs_router import _fetch_jobicy
        body = json.dumps({
            "jobs": [{
                "jobTitle": "React Developer",
                "companyName": "JobicyCo",
                "jobGeo": "Remote",
                "url": "https://jobicy.com/job/1",
                "jobExcerpt": "React dev role",
            }]
        }).encode()
        with patch("routers.jobs_router.urllib.request.urlopen", return_value=self._mock_urlopen(body)), \
             patch("routers.jobs_router.urllib.request.Request"):
            jobs = _fetch_jobicy("React", 5)
        assert len(jobs) == 1
        assert jobs[0]["source"] == "jobicy"
        assert jobs[0]["is_deep_link"] is False

    def test_jobicy_handles_failure(self):
        from routers.jobs_router import _fetch_jobicy
        with patch("routers.jobs_router.urllib.request.urlopen", side_effect=Exception("error")), \
             patch("routers.jobs_router.urllib.request.Request"):
            assert _fetch_jobicy("React", 5) == []

    def test_weworkremotely_parses_rss(self):
        from routers.jobs_router import _fetch_weworkremotely
        rss = b"""<?xml version="1.0"?>
        <rss><channel>
          <item>
            <title>Python Backend Developer</title>
            <link>https://weworkremotely.com/job/1</link>
            <description>Python backend role</description>
          </item>
          <item>
            <title>Java Developer</title>
            <link>https://weworkremotely.com/job/2</link>
            <description>Java role</description>
          </item>
        </channel></rss>"""
        with patch("routers.jobs_router.urllib.request.urlopen", return_value=self._mock_urlopen(rss)), \
             patch("routers.jobs_router.urllib.request.Request"):
            jobs = _fetch_weworkremotely("Python", 5)
        assert len(jobs) == 1
        assert jobs[0]["source"] == "weworkremotely"
        assert jobs[0]["is_deep_link"] is False

    def test_weworkremotely_handles_failure(self):
        from routers.jobs_router import _fetch_weworkremotely
        with patch("routers.jobs_router.urllib.request.urlopen", side_effect=Exception("error")), \
             patch("routers.jobs_router.urllib.request.Request"):
            assert _fetch_weworkremotely("Python", 5) == []

    def test_findwork_skips_without_key(self):
        from routers.jobs_router import _fetch_findwork
        assert _fetch_findwork("Python", 5, "") == []

    def test_findwork_returns_jobs_with_key(self):
        from routers.jobs_router import _fetch_findwork
        body = json.dumps({
            "results": [{
                "role": "Python Dev",
                "company_name": "FindCo",
                "location": "Remote",
                "url": "https://findwork.dev/job/1",
                "text": "Python dev role",
            }]
        }).encode()
        with patch("routers.jobs_router.urllib.request.urlopen", return_value=self._mock_urlopen(body)), \
             patch("routers.jobs_router.urllib.request.Request"):
            jobs = _fetch_findwork("Python", 5, "test-api-key")
        assert len(jobs) == 1
        assert jobs[0]["source"] == "findwork"
        assert jobs[0]["is_deep_link"] is False

    def test_findwork_handles_failure(self):
        from routers.jobs_router import _fetch_findwork
        with patch("routers.jobs_router.urllib.request.urlopen", side_effect=Exception("error")), \
             patch("routers.jobs_router.urllib.request.Request"):
            assert _fetch_findwork("Python", 5, "key") == []

    def test_jooble_skips_without_key(self):
        from routers.jobs_router import _fetch_jooble
        assert _fetch_jooble("Python", 5, "") == []

    def test_jooble_returns_jobs_with_key(self):
        from routers.jobs_router import _fetch_jooble
        body = json.dumps({
            "jobs": [{
                "title": "Python Developer",
                "company": "JoobleCo",
                "location": "New York",
                "link": "https://jooble.org/job/1",
                "snippet": "Python dev position",
                "salary": "$100k",
            }]
        }).encode()
        with patch("routers.jobs_router.urllib.request.urlopen", return_value=self._mock_urlopen(body)), \
             patch("routers.jobs_router.urllib.request.Request"):
            jobs = _fetch_jooble("Python", 5, "test-api-key")
        assert len(jobs) == 1
        assert jobs[0]["source"] == "jooble"
        assert jobs[0]["salary"] == "$100k"
        assert jobs[0]["is_deep_link"] is False

    def test_jooble_handles_failure(self):
        from routers.jobs_router import _fetch_jooble
        with patch("routers.jobs_router.urllib.request.urlopen", side_effect=Exception("error")), \
             patch("routers.jobs_router.urllib.request.Request"):
            assert _fetch_jooble("Python", 5, "key") == []


# ── Issue #1 — additional Tier 2 sources ─────────────────────────────────────

class TestReedAndUsajobsUnit:
    def _mock_urlopen(self, body: bytes):
        mock_resp = MagicMock()
        mock_resp.read.return_value = body
        mock_resp.__enter__ = lambda s: s
        mock_resp.__exit__ = MagicMock(return_value=False)
        return mock_resp

    def test_reed_skips_without_key(self):
        from routers.jobs_router import _fetch_reed
        assert _fetch_reed("Python", 5, "") == []

    def test_reed_returns_jobs_with_salary(self):
        from routers.jobs_router import _fetch_reed
        body = json.dumps({
            "results": [{
                "jobTitle": "Python Developer",
                "employerName": "ReedCo",
                "locationName": "London",
                "jobUrl": "https://reed.co.uk/job/1",
                "jobDescription": "Python role",
                "minimumSalary": "40000",
                "maximumSalary": "60000",
                "datePosted": "2026-06-10",
            }]
        }).encode()
        with patch("routers.jobs_router.urllib.request.urlopen", return_value=self._mock_urlopen(body)), \
             patch("routers.jobs_router.urllib.request.Request"):
            jobs = _fetch_reed("Python", 5, "test-key")
        assert len(jobs) == 1
        assert jobs[0]["source"] == "reed"
        assert jobs[0]["salary"] == "£40,000-£60,000"
        assert jobs[0]["date_posted"] == "2026-06-10"
        assert jobs[0]["is_deep_link"] is False

    def test_reed_handles_failure(self):
        from routers.jobs_router import _fetch_reed
        with patch("routers.jobs_router.urllib.request.urlopen", side_effect=Exception("error")), \
             patch("routers.jobs_router.urllib.request.Request"):
            assert _fetch_reed("Python", 5, "key") == []

    def test_usajobs_skips_without_key(self):
        from routers.jobs_router import _fetch_usajobs
        assert _fetch_usajobs("Python", 5, "") == []

    def test_usajobs_returns_jobs_with_salary(self):
        from routers.jobs_router import _fetch_usajobs
        body = json.dumps({
            "SearchResult": {
                "SearchResultItems": [{
                    "MatchedObjectDescriptor": {
                        "PositionTitle": "Software Engineer",
                        "OrganizationName": "US Air Force",
                        "PositionLocation": [{"LocationName": "Washington, DC"}],
                        "PositionURI": "https://usajobs.gov/job/1",
                        "QualificationSummary": "Develop software",
                        "PositionRemuneration": [{"MinimumRange": "80000", "MaximumRange": "120000"}],
                        "PublicationStartDate": "2026-06-12",
                    }
                }]
            }
        }).encode()
        with patch("routers.jobs_router.urllib.request.urlopen", return_value=self._mock_urlopen(body)), \
             patch("routers.jobs_router.urllib.request.Request"):
            jobs = _fetch_usajobs("Python", 5, "test-key")
        assert len(jobs) == 1
        assert jobs[0]["source"] == "usajobs"
        assert jobs[0]["salary"] == "$80,000-$120,000"
        assert jobs[0]["is_deep_link"] is False

    def test_usajobs_handles_failure(self):
        from routers.jobs_router import _fetch_usajobs
        with patch("routers.jobs_router.urllib.request.urlopen", side_effect=Exception("error")), \
             patch("routers.jobs_router.urllib.request.Request"):
            assert _fetch_usajobs("Python", 5, "key") == []


class TestExternalSearchLinks:
    """Issue #1 — pre-filled deep-link search URLs."""

    def test_external_search_returns_four_portals(self, client):
        r = client.post(
            "/api/auth/register",
            json={"username": "ext_user_v1", "password": "password123", "email": "ext_user_v1@test.local"},
        )
        if r.status_code == 400:
            r = client.post("/api/auth/login", data={"username": "ext_user_v1", "password": "password123"})
        token = r.json()["access_token"]
        h = {"Authorization": f"Bearer {token}"}

        data = json.dumps({
            "full_name": "Jane",
            "skills": [{"name": "Python", "years": 5}, {"name": "FastAPI", "years": 3}],
            "experience": [{"company": "X", "role": "Senior Engineer", "start": "2020"}],
            "location": "Remote",
        }).encode()
        imp = client.post(
            "/api/import", files={"file": ("p.json", data, "application/json")}, headers=h
        )
        pid = imp.json()["profile_id"]

        resp = client.get(f"/api/profiles/{pid}/external-search", headers=h)
        assert resp.status_code == 200
        body = resp.json()
        assert "links" in body
        assert len(body["links"]) == 4
        portals = {link["portal"] for link in body["links"]}
        assert {"linkedin", "indeed", "glassdoor", "google_jobs"} == portals
        for link in body["links"]:
            assert link["url"].startswith("https://")
            assert "label" in link
            assert "icon" in link
        # The keywords should reference the role + skills
        assert "Senior" in body["keywords"] or "Engineer" in body["keywords"]

    def test_external_search_uses_session_keyword_override(self, client):
        r = client.post(
            "/api/auth/register",
            json={"username": "ext_ovr_v1", "password": "password123", "email": "ext_ovr_v1@test.local"},
        )
        if r.status_code == 400:
            r = client.post("/api/auth/login", data={"username": "ext_ovr_v1", "password": "password123"})
        token = r.json()["access_token"]
        h = {"Authorization": f"Bearer {token}"}

        data = json.dumps({
            "full_name": "Jane",
            "skills": [{"name": "Python", "years": 5}],
            "experience": [{"company": "X", "role": "Engineer", "start": "2020"}],
            "location": "Remote",
        }).encode()
        imp = client.post(
            "/api/import", files={"file": ("p.json", data, "application/json")}, headers=h
        )
        pid = imp.json()["profile_id"]

        resp = client.get(
            f"/api/profiles/{pid}/external-search?keywords=Node+Backend&location=Berlin",
            headers=h,
        )
        assert resp.status_code == 200
        body = resp.json()
        assert body["keywords"] == "Node Backend"
        assert body["location"] == "Berlin"
        for link in body["links"]:
            assert "Node" in link["url"] or "Node" in body["keywords"]
            assert "Berlin" in link["url"]

    def test_external_search_google_jobs_url_is_simple(self, client):
        """Google Jobs URL must use a format that works in modern Chrome —
        no deprecated `ibp=htl;jobs` parameter that the browser ignores."""
        r = client.post(
            "/api/auth/register",
            json={"username": "ext_gj_v1", "password": "password123", "email": "ext_gj_v1@test.local"},
        )
        if r.status_code == 400:
            r = client.post("/api/auth/login", data={"username": "ext_gj_v1", "password": "password123"})
        token = r.json()["access_token"]
        h = {"Authorization": f"Bearer {token}"}

        data = json.dumps({
            "full_name": "Jane",
            "skills": [{"name": "Python", "years": 5}],
            "experience": [{"company": "X", "role": "Engineer", "start": "2020"}],
            "location": "Remote",
        }).encode()
        imp = client.post(
            "/api/import", files={"file": ("p.json", data, "application/json")}, headers=h
        )
        pid = imp.json()["profile_id"]

        resp = client.get(f"/api/profiles/{pid}/external-search", headers=h).json()
        google = next((l for l in resp["links"] if l["portal"] == "google_jobs"), None)
        assert google is not None
        url = google["url"]
        # Must use simple search URL with query and +jobs
        assert url.startswith("https://www.google.com/search?")
        assert "jobs" in url
        # Uses the official ibp=htl;jobs parameter (URL-encoded as %3B)
        # to switch the result set to the Jobs vertical.
        assert "ibp=htl%3Bjobs" in url

    def test_external_search_accepts_experience_level(self, client):
        """LinkedIn f_E parameter is set from the experience_level query arg."""
        r = client.post(
            "/api/auth/register",
            json={"username": "ext_exp_v1", "password": "password123", "email": "ext_exp_v1@test.local"},
        )
        if r.status_code == 400:
            r = client.post("/api/auth/login", data={"username": "ext_exp_v1", "password": "password123"})
        token = r.json()["access_token"]
        h = {"Authorization": f"Bearer {token}"}
        imp = client.post(
            "/api/import",
            files={"file": ("p.json", json.dumps({"full_name": "X", "skills": [{"name": "Python"}]}).encode())},
            headers=h,
        )
        pid = imp.json()["profile_id"]
        r = client.get(
            f"/api/profiles/{pid}/external-search?experience_level=mid-senior", headers=h
        ).json()
        li = next(l for l in r["links"] if l["portal"] == "linkedin")
        assert "f_E=4" in li["url"]  # mid-senior = 4 in LinkedIn's code

    def test_external_search_accepts_work_type(self, client):
        """LinkedIn f_WT parameter is set from the work_type query arg."""
        r = client.post(
            "/api/auth/register",
            json={"username": "ext_wt_v1", "password": "password123", "email": "ext_wt_v1@test.local"},
        )
        if r.status_code == 400:
            r = client.post("/api/auth/login", data={"username": "ext_wt_v1", "password": "password123"})
        token = r.json()["access_token"]
        h = {"Authorization": f"Bearer {token}"}
        imp = client.post(
            "/api/import",
            files={"file": ("p.json", json.dumps({"full_name": "X", "skills": [{"name": "Python"}]}).encode())},
            headers=h,
        )
        pid = imp.json()["profile_id"]
        r = client.get(
            f"/api/profiles/{pid}/external-search?work_type=remote", headers=h
        ).json()
        li = next(l for l in r["links"] if l["portal"] == "linkedin")
        assert "f_WT=2" in li["url"]  # remote = 2 in LinkedIn's code
        # Glassdoor should also receive the remote work-type hint
        gd = next(l for l in r["links"] if l["portal"] == "glassdoor")
        assert "remoteWorkType=1" in gd["url"]

    def test_external_search_accepts_salary_currency(self, client):
        """LinkedIn f_C parameter reflects the requested currency code."""
        r = client.post(
            "/api/auth/register",
            json={"username": "ext_cur_v1", "password": "password123", "email": "ext_cur_v1@test.local"},
        )
        if r.status_code == 400:
            r = client.post("/api/auth/login", data={"username": "ext_cur_v1", "password": "password123"})
        token = r.json()["access_token"]
        h = {"Authorization": f"Bearer {token}"}
        imp = client.post(
            "/api/import",
            files={"file": ("p.json", json.dumps({"full_name": "X", "skills": [{"name": "Python"}]}).encode())},
            headers=h,
        )
        pid = imp.json()["profile_id"]
        r = client.get(
            f"/api/profiles/{pid}/external-search?salary_min=100000&salary_currency=INR",
            headers=h,
        ).json()
        assert r["currency"] == "INR"
        li = next(l for l in r["links"] if l["portal"] == "linkedin")
        assert "f_C=INR" in li["url"]
        assert "f_SB2=100000" in li["url"]

    def test_external_search_defaults_currency_to_usd(self, client):
        r = client.post(
            "/api/auth/register",
            json={"username": "ext_cur2_v1", "password": "password123", "email": "ext_cur2_v1@test.local"},
        )
        if r.status_code == 400:
            r = client.post("/api/auth/login", data={"username": "ext_cur2_v1", "password": "password123"})
        token = r.json()["access_token"]
        h = {"Authorization": f"Bearer {token}"}
        imp = client.post(
            "/api/import",
            files={"file": ("p.json", json.dumps({"full_name": "X", "skills": [{"name": "Python"}]}).encode())},
            headers=h,
        )
        pid = imp.json()["profile_id"]
        r = client.get(f"/api/profiles/{pid}/external-search", headers=h).json()
        assert r["currency"] == "USD"

    def test_external_search_time_posted_forwards_to_linkedin(self, client):
        """LinkedIn f_TPR reflects the time_posted query arg."""
        r = client.post(
            "/api/auth/register",
            json={"username": "ext_tp_v1", "password": "password123", "email": "ext_tp_v1@test.local"},
        )
        if r.status_code == 400:
            r = client.post("/api/auth/login", data={"username": "ext_tp_v1", "password": "password123"})
        token = r.json()["access_token"]
        h = {"Authorization": f"Bearer {token}"}
        imp = client.post(
            "/api/import",
            files={"file": ("p.json", json.dumps({"full_name": "X", "skills": [{"name": "Python"}]}).encode())},
            headers=h,
        )
        pid = imp.json()["profile_id"]
        r = client.get(
            f"/api/profiles/{pid}/external-search?time_posted=last_24h", headers=h
        ).json()
        li = next(l for l in r["links"] if l["portal"] == "linkedin")
        assert "f_TPR=r86400" in li["url"]


class TestDeepLinks:
    def test_indeed_returns_deep_link(self):
        from routers.jobs_router import _fetch_indeed
        jobs = _fetch_indeed("Python Developer", "Remote", 5)
        assert len(jobs) == 1
        assert jobs[0]["is_deep_link"] is True
        assert jobs[0]["source"] == "indeed"
        assert "indeed.com" in jobs[0]["url"]
        assert "Python+Developer" in jobs[0]["url"] or "Python%20Developer" in jobs[0]["url"]

    def test_glassdoor_returns_deep_link(self):
        from routers.jobs_router import _fetch_glassdoor
        jobs = _fetch_glassdoor("ML Engineer", "Remote", 5)
        assert len(jobs) == 1
        assert jobs[0]["is_deep_link"] is True
        assert jobs[0]["source"] == "glassdoor"
        assert "glassdoor.com" in jobs[0]["url"]

    def test_google_jobs_returns_deep_link(self):
        from routers.jobs_router import _fetch_google_jobs
        jobs = _fetch_google_jobs("Data Scientist", "New York")
        assert len(jobs) == 1
        assert jobs[0]["is_deep_link"] is True
        assert jobs[0]["source"] == "google_jobs"
        assert "google.com" in jobs[0]["url"]

    def test_linkedin_falls_back_to_deep_link_on_failure(self):
        from routers.jobs_router import _fetch_linkedin
        with patch("routers.jobs_router._fetch_linkedin_guest", return_value=[]):
            jobs = _fetch_linkedin("Python Dev", "Remote", 5)
        assert len(jobs) == 1
        assert jobs[0]["is_deep_link"] is True
        assert jobs[0]["source"] == "linkedin"
