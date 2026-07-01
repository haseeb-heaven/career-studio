"""Comprehensive integration tests for the Job search filters, sort, and pagination.

Uses pytest's `monkeypatch` fixture to replace the external source fetchers
with deterministic stubs. The patches are automatically reverted after each
test by pytest, so there are no cleanup issues across multiple /jobs calls
within the same test.
"""
import json
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))


def _days_ago(n: int) -> str:
    """ISO date string for n days before today (date-robust fixtures)."""
    return (datetime.now(timezone.utc) - timedelta(days=n)).date().isoformat()


def _auth(client, username):
    r = client.post(
        "/api/auth/register",
        json={"username": username, "password": "password123", "email": f"{username}@test.local"},
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
            {"name": "AWS", "years": 2},
        ],
        "experience": [{"company": "AI Corp", "role": "Senior Engineer", "start": "2020"}],
        "education": [{"institution": "MIT", "degree": "BSc", "field": "CS", "start": "2014", "end": "2018"}],
        "certifications": [{"name": "AWS Solutions Architect", "issuer": "Amazon", "date": "2023"}],
    }).encode()
    return client.post(
        "/api/import", files={"file": ("p.json", data, "application/json")}, headers=headers
    ).json()["profile_id"]


# â”€â”€ Fixture jobs covering every filter dimension â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
def _build_fixture_jobs():
    return [
        {
            "title": "Senior Python Developer", "company": "TechCorp",
            "location": "Remote", "source": "remotive",
            "description": "Python FastAPI AWS required. 5+ years experience.",
            "salary": "$120k-$150k", "is_deep_link": False,
            "date_posted": _days_ago(2), "job_type": "remote",
            "is_remote": True, "industry": "tech",
            "match_score": 92.0, "salary_min": 120000, "salary_max": 150000,
            "match_breakdown": "{}", "matched_skills": "[]", "missing_skills": "[]",
            "url": "https://example.com/senior-python",
        },
        {
            "title": "Junior Java Developer", "company": "OldCorp",
            "location": "New York, NY", "source": "arbeitnow",
            "description": "Entry level Java developer.",
            "salary": None, "is_deep_link": False,
            "date_posted": _days_ago(200), "job_type": "full-time",
            "is_remote": False, "industry": "finance",
            "match_score": 22.0, "salary_min": 0, "salary_max": 0,
            "match_breakdown": "{}", "matched_skills": "[]", "missing_skills": "[]",
            "url": "https://example.com/junior-java",
        },
        {
            "title": "ML Engineer", "company": "AIStartup",
            "location": "Remote", "source": "himalayas",
            "description": "Machine Learning and Python expert. AWS required. 3+ years experience.",
            "salary": "$140k-$180k", "is_deep_link": False,
            "date_posted": _days_ago(4), "job_type": "contract",
            "is_remote": True, "industry": "tech",
            "match_score": 85.0, "salary_min": 140000, "salary_max": 180000,
            "match_breakdown": "{}", "matched_skills": "[]", "missing_skills": "[]",
            "url": "https://example.com/ml-engineer",
        },
        {
            "title": "Data Scientist", "company": "DataCo",
            "location": "San Francisco, CA", "source": "themuse",
            "description": "Python and data analysis. 3+ years experience.",
            "salary": "$100k", "is_deep_link": False,
            "date_posted": _days_ago(6), "job_type": "full-time",
            "is_remote": False, "industry": "tech",
            "match_score": 70.0, "salary_min": 100000, "salary_max": 100000,
            "match_breakdown": "{}", "matched_skills": "[]", "missing_skills": "[]",
            "url": "https://example.com/data-scientist",
        },
        {
            "title": "Backend Node Developer", "company": "WebCo",
            "location": "Berlin", "source": "remoteok",
            "description": "Node.js backend development.",
            "salary": None, "is_deep_link": False,
            "date_posted": _days_ago(9), "job_type": "",
            "is_remote": True, "industry": "",
            "match_score": 55.0, "salary_min": 0, "salary_max": 0,
            "match_breakdown": "{}", "matched_skills": "[]", "missing_skills": "[]",
            "url": "https://example.com/backend-node",
        },
        {
            "title": "Full-Stack Engineer", "company": "StartupX",
            "location": "Remote", "source": "jobicy",
            "description": "Full-Stack role with React and Python.",
            "salary": "$80k-$110k", "is_deep_link": False,
            "date_posted": _days_ago(5), "job_type": "remote",
            "is_remote": True, "industry": "",
            "match_score": 60.0, "salary_min": 80000, "salary_max": 110000,
            "match_breakdown": "{}", "matched_skills": "[]", "missing_skills": "[]",
            "url": "https://example.com/full-stack",
        },
    ]


import pytest


@pytest.fixture
def patched_sources(monkeypatch):
    """Pytest fixture that replaces every _fetch_* source function and the
    scoring engine with deterministic stubs. The fixture is function-scoped
    and monkeypatch auto-undoes everything after the test â€” no manual
    cleanup, no race conditions across multiple /jobs calls in one test.
    Returns the list of fixture jobs so a test can customise them."""
    import routers.jobs_router as rj
    jobs = _build_fixture_jobs()

    def _one_source(query, limit):
        return [dict(j) for j in jobs]

    def _zero2(query, limit):
        return []

    def _zero3(query, location, limit, api_key=""):
        return []

    def _zero_gj(query, location):
        return []

    def fake_scoring(profile, job, search_loc=""):
        return {
            "score": float(job.get("match_score", 0.0)),
            "breakdown": json.loads(job.get("match_breakdown", "{}") or "{}"),
            "matched": json.loads(job.get("matched_skills", "[]") or "[]"),
            "missing": json.loads(job.get("missing_skills", "[]") or "[]"),
            "skill_details": [],
            "gaps": {},
            "partials": [],
            "insight": "",
            "confidence": "",
        }

    monkeypatch.setattr(rj, "_fetch_remotive", _one_source)
    monkeypatch.setattr(rj, "_fetch_arbeitnow", _zero2)
    monkeypatch.setattr(rj, "_fetch_remoteok", _zero2)
    monkeypatch.setattr(rj, "_fetch_himalayas", _zero2)
    monkeypatch.setattr(rj, "_fetch_the_muse", _zero2)
    monkeypatch.setattr(rj, "_fetch_jobicy", _zero2)
    monkeypatch.setattr(rj, "_fetch_weworkremotely", _zero2)
    monkeypatch.setattr(rj, "_fetch_linkedin", _zero3)
    monkeypatch.setattr(rj, "_fetch_indeed", _zero3)
    monkeypatch.setattr(rj, "_fetch_glassdoor", _zero3)
    monkeypatch.setattr(rj, "_fetch_google_jobs", _zero_gj)
    monkeypatch.setattr(rj, "_fetch_adzuna", _zero2)
    monkeypatch.setattr(rj, "_fetch_findwork", _zero2)
    monkeypatch.setattr(rj, "_fetch_jooble", _zero2)
    monkeypatch.setattr(rj, "_fetch_reed", _zero2)
    monkeypatch.setattr(rj, "_fetch_usajobs", _zero2)
    monkeypatch.setattr(rj, "_profile_match_score", fake_scoring)
    return jobs


# --- Tests -----------------------------------------------------------------

def test_no_filter_returns_all_jobs(client, patched_sources):
    h = _auth(client, "flt_all_v1")
    pid = _profile(client, h)
    r = client.get(f"/api/profiles/{pid}/jobs?limit=100", headers=h).json()
    assert r["total"] == 6


def test_filter_min_match_score(client, patched_sources):
    h = _auth(client, "flt_score_v1")
    pid = _profile(client, h)
    r = client.get(f"/api/profiles/{pid}/jobs?min_match_score=70&limit=100", headers=h).json()
    assert r["total"] == 3
    scores = sorted(j["match_score"] for j in r["jobs"])
    assert scores == [70.0, 85.0, 92.0]


def test_filter_min_match_score_zero_is_no_filter(client, patched_sources):
    h = _auth(client, "flt_score_zero_v1")
    pid = _profile(client, h)
    r = client.get(f"/api/profiles/{pid}/jobs?min_match_score=0&limit=100", headers=h).json()
    assert r["total"] == 6


def test_filter_date_posted_last_7d(client, patched_sources):
    h = _auth(client, "flt_date_v1")
    pid = _profile(client, h)
    r = client.get(f"/api/profiles/{pid}/jobs?date_posted=last_7d&limit=100", headers=h).json()
    # last_7d keeps jobs dated within the past 7 days (or untagged). With the
    # dynamic fixtures, 4 jobs are within 7d (2/4/5/6 days ago) and 2 are
    # older (9 and 200 days ago) — so this now asserts a non-vacuous set.
    cutoff = _days_ago(7)
    titles = {j["title"] for j in r["jobs"]}
    assert "Senior Python Developer" in titles   # 2 days ago
    assert "ML Engineer" in titles               # 4 days ago
    assert "Full-Stack Engineer" in titles       # 5 days ago
    assert "Data Scientist" in titles            # 6 days ago
    assert "Backend Node Developer" not in titles  # 9 days ago → filtered
    assert "Junior Java Developer" not in titles   # 200 days ago → filtered
    for job in r["jobs"]:
        assert job["date_posted"] == "" or job["date_posted"] >= cutoff


def test_filter_date_posted_any_returns_all(client, patched_sources):
    h = _auth(client, "flt_date_any_v1")
    pid = _profile(client, h)
    r = client.get(f"/api/profiles/{pid}/jobs?date_posted=any&limit=100", headers=h).json()
    assert r["total"] == 6


def test_filter_job_type_includes_untagged_jobs(client, patched_sources):
    h = _auth(client, "flt_jt_v1")
    pid = _profile(client, h)
    r = client.get(f"/api/profiles/{pid}/jobs?job_type=remote&limit=100", headers=h).json()
    titles = {j["title"] for j in r["jobs"]}
    assert "Senior Python Developer" in titles  # job_type=remote
    assert "Full-Stack Engineer" in titles      # job_type=remote
    assert "Backend Node Developer" in titles   # job_type="" (untagged → kept)
    # Jobs with a DIFFERENT non-empty job_type are excluded
    assert "ML Engineer" not in titles          # job_type=contract
    assert "Junior Java Developer" not in titles # job_type=full-time
    assert "Data Scientist" not in titles        # job_type=full-time


def test_filter_job_type_multiple(client, patched_sources):
    h = _auth(client, "flt_jt2_v1")
    pid = _profile(client, h)
    r = client.get(f"/api/profiles/{pid}/jobs?job_type=remote,full-time&limit=100", headers=h).json()
    titles = {j["title"] for j in r["jobs"]}
    assert "ML Engineer" not in titles
    assert len(titles) == 5


def test_filter_industry_includes_untagged_jobs(client, patched_sources):
    h = _auth(client, "flt_ind_v1")
    pid = _profile(client, h)
    r = client.get(f"/api/profiles/{pid}/jobs?industries=tech&limit=100", headers=h).json()
    titles = {j["title"] for j in r["jobs"]}
    assert "Senior Python Developer" in titles
    assert "ML Engineer" in titles
    assert "Data Scientist" in titles
    assert "Backend Node Developer" in titles
    assert "Full-Stack Engineer" in titles
    assert "Junior Java Developer" not in titles


def test_filter_industry_no_match(client, patched_sources):
    h = _auth(client, "flt_ind_hc_v1")
    pid = _profile(client, h)
    r = client.get(f"/api/profiles/{pid}/jobs?industries=healthcare&limit=100", headers=h).json()
    # No healthcare jobs, but 2 jobs have empty industry (Backend Node, Full-Stack)
    # which are included by the "don't hide untagged" policy.
    assert r["total"] == 2
    titles = {j["title"] for j in r["jobs"]}
    assert "Backend Node Developer" in titles
    assert "Full-Stack Engineer" in titles


def test_filter_salary_min_includes_unspecified(client, patched_sources):
    h = _auth(client, "flt_sal_v1")
    pid = _profile(client, h)
    r = client.get(f"/api/profiles/{pid}/jobs?min_salary=100000&limit=100", headers=h).json()
    titles = {j["title"] for j in r["jobs"]}
    assert "Senior Python Developer" in titles
    assert "ML Engineer" in titles
    assert "Data Scientist" in titles
    assert "Junior Java Developer" in titles
    assert "Backend Node Developer" in titles
    assert "Full-Stack Engineer" in titles


def test_filter_salary_max_excludes_high(client, patched_sources):
    h = _auth(client, "flt_sal_max_v1")
    pid = _profile(client, h)
    r = client.get(f"/api/profiles/{pid}/jobs?max_salary=110000&limit=100", headers=h).json()
    titles = {j["title"] for j in r["jobs"]}
    assert "ML Engineer" not in titles
    assert "Data Scientist" in titles
    assert "Full-Stack Engineer" in titles


def test_filter_salary_range_overlap(client, patched_sources):
    h = _auth(client, "flt_sal_range_v1")
    pid = _profile(client, h)
    r = client.get(f"/api/profiles/{pid}/jobs?min_salary=100000&max_salary=120000&limit=100", headers=h).json()
    titles = {j["title"] for j in r["jobs"]}
    assert "Senior Python Developer" in titles
    assert "Data Scientist" in titles
    assert "ML Engineer" not in titles


def test_filter_salary_zero_zero_is_no_filter(client, patched_sources):
    h = _auth(client, "flt_sal_zero_v1")
    pid = _profile(client, h)
    r = client.get(f"/api/profiles/{pid}/jobs?min_salary=0&max_salary=0&limit=100", headers=h).json()
    assert r["total"] == 6


def test_filter_salary_blank_inputs_via_zero(client, patched_sources):
    h = _auth(client, "flt_sal_blank_v1")
    pid = _profile(client, h)
    r = client.get(f"/api/profiles/{pid}/jobs?min_salary=100000&max_salary=0&limit=100", headers=h).json()
    titles = {j["title"] for j in r["jobs"]}
    assert "Senior Python Developer" in titles
    assert "ML Engineer" in titles
    assert "Data Scientist" in titles
    assert "Junior Java Developer" in titles
    assert "Backend Node Developer" in titles
    r2 = client.get(f"/api/profiles/{pid}/jobs?min_salary=0&max_salary=110000&limit=100", headers=h).json()
    titles2 = {j["title"] for j in r2["jobs"]}
    assert "ML Engineer" not in titles2
    assert "Data Scientist" in titles2
    assert "Junior Java Developer" in titles2
    assert "Backend Node Developer" in titles2


def test_filter_years_min_keeps_untagged(client, patched_sources):
    h = _auth(client, "flt_yrs_v1")
    pid = _profile(client, h)
    r = client.get(f"/api/profiles/{pid}/jobs?min_years=3&max_years=50&limit=100", headers=h).json()
    titles = {j["title"] for j in r["jobs"]}
    assert "Senior Python Developer" in titles
    assert "Data Scientist" in titles
    assert "ML Engineer" in titles
    assert "Backend Node Developer" in titles


def test_filter_years_excludes_high_min(client, patched_sources):
    h = _auth(client, "flt_yrs_high_v1")
    pid = _profile(client, h)
    r = client.get(f"/api/profiles/{pid}/jobs?min_years=10&max_years=50&limit=100", headers=h).json()
    titles = {j["title"] for j in r["jobs"]}
    assert "Senior Python Developer" not in titles
    assert "Data Scientist" not in titles
    assert "ML Engineer" not in titles
    assert "Backend Node Developer" in titles
    assert "Junior Java Developer" in titles


def test_filter_years_handles_range_phrasing(client, patched_sources, monkeypatch):
    """Regression: a description phrased as "3-5 years of experience" (not
    the flat "N years" pattern) must still be excluded when it falls outside
    the requested range — the old filter only matched exact "N years"/"N yrs"
    substrings and silently let range-phrased postings through."""
    import routers.jobs_router as rj
    jobs = [{
        "title": "Range Phrased Role", "company": "RangeCo",
        "location": "Remote", "source": "remotive",
        "description": "Backend role. 3-5 years of experience required.",
        "salary": None, "is_deep_link": False,
        "date_posted": _days_ago(1), "job_type": "remote",
        "is_remote": True, "industry": "tech",
        "match_score": 80.0, "salary_min": 0, "salary_max": 0,
        "match_breakdown": "{}", "matched_skills": "[]", "missing_skills": "[]",
        "url": "https://example.com/range-phrased",
    }]
    monkeypatch.setattr(rj, "_fetch_remotive", lambda query, limit: [dict(j) for j in jobs])

    h = _auth(client, "flt_yrs_range_v1")
    pid = _profile(client, h)
    r = client.get(f"/api/profiles/{pid}/jobs?min_years=10&max_years=50&limit=100", headers=h).json()
    titles = {j["title"] for j in r["jobs"]}
    assert "Range Phrased Role" not in titles


def test_filter_location_excludes_mismatched_city(client, patched_sources):
    """Setting location=India should exclude onsite jobs tagged with an
    unrelated city/country, while remote jobs (via is_remote) still show up
    regardless of their location text."""
    h = _auth(client, "flt_loc_v1")
    pid = _profile(client, h)
    r = client.get(f"/api/profiles/{pid}/jobs?location=India&limit=100", headers=h).json()
    titles = {j["title"] for j in r["jobs"]}
    # Onsite jobs in unrelated cities are excluded
    assert "Junior Java Developer" not in titles       # New York, NY
    assert "Data Scientist" not in titles               # San Francisco, CA
    # Remote jobs pass regardless of location text (Backend Node Developer
    # is tagged "Berlin" but is_remote=True)
    assert "Senior Python Developer" in titles
    assert "Backend Node Developer" in titles


def test_filter_location_blank_returns_all(client, patched_sources):
    h = _auth(client, "flt_loc_blank_v1")
    pid = _profile(client, h)
    r = client.get(f"/api/profiles/{pid}/jobs?limit=100", headers=h).json()
    assert r["total"] == 6


def test_filter_combined_realistic(client, patched_sources):
    h = _auth(client, "flt_combo_v1")
    pid = _profile(client, h)
    r = client.get(
        f"/api/profiles/{pid}/jobs?job_type=remote&min_match_score=60"
        f"&date_posted=last_7d&min_salary=80000&sort=best_match&limit=100",
        headers=h,
    ).json()
    titles = {j["title"] for j in r["jobs"]}
    assert "Senior Python Developer" in titles
    assert "ML Engineer" not in titles
    assert "Backend Node Developer" not in titles
    assert "Data Scientist" not in titles
    assert "Full-Stack Engineer" in titles


def test_sort_recent(client, patched_sources):
    h = _auth(client, "sort_recent_v1")
    pid = _profile(client, h)
    r = client.get(f"/api/profiles/{pid}/jobs?sort=recent&limit=100", headers=h).json()
    dates = [j["date_posted"] for j in r["jobs"] if j["date_posted"]]
    assert dates == sorted(dates, reverse=True)


def test_sort_salary(client, patched_sources):
    h = _auth(client, "sort_salary_v1")
    pid = _profile(client, h)
    r = client.get(f"/api/profiles/{pid}/jobs?sort=salary&limit=100", headers=h).json()
    max_salaries = [j["salary_max"] for j in r["jobs"]]
    assert max_salaries == sorted(max_salaries, reverse=True)


def test_sort_best_match_default(client, patched_sources):
    h = _auth(client, "sort_match_v1")
    pid = _profile(client, h)
    r = client.get(f"/api/profiles/{pid}/jobs?limit=100", headers=h).json()
    scores = [j["match_score"] for j in r["jobs"]]
    assert scores == sorted(scores, reverse=True)


def test_pagination_offset_limit(client, patched_sources):
    h = _auth(client, "page_v1")
    pid = _profile(client, h)
    first = client.get(f"/api/profiles/{pid}/jobs?limit=2&offset=0", headers=h).json()
    second = client.get(f"/api/profiles/{pid}/jobs?limit=2&offset=2", headers=h).json()
    third = client.get(f"/api/profiles/{pid}/jobs?limit=2&offset=4", headers=h).json()
    assert first["total"] == 6
    assert len(first["jobs"]) == 2
    assert len(second["jobs"]) == 2
    assert len(third["jobs"]) == 2
    assert first["has_more"] is True
    assert second["has_more"] is True
    assert third["has_more"] is False
    all_ids = [j["id"] for j in first["jobs"] + second["jobs"] + third["jobs"]]
    assert len(all_ids) == len(set(all_ids))


def test_response_shape_includes_all_filter_metadata(client, patched_sources):
    h = _auth(client, "shape_v1")
    pid = _profile(client, h)
    r = client.get(f"/api/profiles/{pid}/jobs?limit=100", headers=h).json()
    for j in r["jobs"]:
        for k in (
            "id", "title", "company", "location", "match_score", "salary",
            "date_posted", "job_type", "industry", "is_remote", "is_deep_link",
            "salary_min", "salary_max", "match_breakdown", "matched_skills",
            "missing_skills", "source", "url", "description", "is_expired",
            "skill_details", "gaps", "hire_chance", "hire_chance_label",
            "insight", "confidence",
        ):
            assert k in j, f"Missing key {k} in job response"


# ── Advanced ML matchmaking: semantic, per-skill detail, gaps (real engine) ────
#
# These tests use the REAL _profile_match_score (not the stubbed one) so the
# new advanced signals — semantic partial matches, per-skill confidence, and
# the structured gaps analysis — are exercised end-to-end through the API.

def _patch_only_remotive_with(monkeypatch, jobs):
    """Patch every source so only Remotive returns ``jobs``; keep real scoring."""
    import routers.jobs_router as rj
    monkeypatch.setattr(rj, "_fetch_remotive", lambda q, l: [dict(j) for j in jobs])
    for name in ("_fetch_arbeitnow", "_fetch_remoteok", "_fetch_himalayas",
                 "_fetch_the_muse", "_fetch_jobicy", "_fetch_weworkremotely",
                 "_fetch_adzuna", "_fetch_findwork", "_fetch_jooble",
                 "_fetch_reed", "_fetch_usajobs"):
        monkeypatch.setattr(rj, name, lambda q, l: [])
    for name in ("_fetch_linkedin", "_fetch_indeed", "_fetch_glassdoor"):
        monkeypatch.setattr(rj, name, lambda q, loc, l, k="": [])
    monkeypatch.setattr(rj, "_fetch_google_jobs", lambda q, loc: [])


def test_semantic_partial_match_appears_in_skill_details(client, monkeypatch):
    """A candidate with React/Vue should get PARTIAL credit (not "missing")
    for a job requiring Angular, because all three are frontend skills — the
    semantic category-embedding signal rewards same-category overlap."""
    jobs = [{
        "title": "Frontend Engineer",
        "company": "UI Co",
        "location": "Remote",
        "source": "remotive",
        "description": "We need Angular and TypeScript. Frontend framework experience required.",
        "salary": None, "is_deep_link": False, "url": "https://example.com/fe",
    }]
    _patch_only_remotive_with(monkeypatch, jobs)

    h = _auth(client, "sem_partial_v1")
    # Custom profile with React + Vue (frontend) so Angular gets partial credit
    # via the semantic category-embedding signal.
    data = json.dumps({
        "full_name": "FE Dev",
        "skills": [{"name": "React", "years": 3}, {"name": "Vue", "years": 2}],
        "experience": [{"company": "UI Inc", "role": "Frontend Engineer", "start": "2021"}],
    }).encode()
    pid = client.post(
        "/api/import", files={"file": ("p.json", data, "application/json")}, headers=h,
    ).json()["profile_id"]
    r = client.get(f"/api/profiles/{pid}/jobs?limit=100", headers=h).json()
    assert r["total"] == 1
    job = r["jobs"][0]
    # The breakdown must include the new semantic factor
    assert "semantic" in job["match_breakdown"]
    assert job["match_breakdown"]["semantic"] > 0
    # skill_details must contain a "partial" entry for Angular (via React/Vue)
    partials = [d for d in job["skill_details"] if d["status"] == "partial"]
    assert len(partials) > 0
    partial_skills = {d["skill"].lower() for d in partials}
    assert "angular" in partial_skills
    # Each partial entry must name the covering resume skill and carry confidence
    for d in partials:
        assert d["via"]
        assert 0 < d["confidence"] <= 100
        assert d["category"]


def test_gaps_panel_reports_location_mismatch(client, monkeypatch):
    """When the candidate's effective location is Remote but the job is in
    Berlin, the gaps panel must surface a location "gap" with a human message.
    (We use a Remote profile location so the strict location filter doesn't
    drop the Berlin job before the scoring engine can evaluate it.)"""
    jobs = [{
        "title": "Backend Engineer",
        "company": "DE Co",
        "location": "Berlin, Germany",
        "source": "remotive",
        "description": "Python backend developer. 3+ years experience.",
        "salary": None, "is_deep_link": False, "url": "https://example.com/de",
    }]
    _patch_only_remotive_with(monkeypatch, jobs)

    h = _auth(client, "gap_loc_v1")
    # Profile with no location → effective search location defaults to Remote,
    # so the strict location filter is skipped and the Berlin job survives to
    # be scored (and penalized on the location factor).
    data = json.dumps({
        "full_name": "Remote Dev",
        "skills": [{"name": "Python", "years": 4}],
        "experience": [{"company": "X", "role": "Backend Engineer", "start": "2022"}],
    }).encode()
    pid = client.post(
        "/api/import", files={"file": ("p.json", data, "application/json")}, headers=h,
    ).json()["profile_id"]
    r = client.get(f"/api/profiles/{pid}/jobs?limit=100", headers=h).json()
    assert r["total"] == 1
    gaps = r["jobs"][0]["gaps"]
    assert gaps["location"]["status"] == "gap"
    assert "Berlin" in gaps["location"]["message"]


def test_gaps_panel_reports_experience_gap(client, monkeypatch):
    """A junior candidate (0 profile years) vs a 5+ year requirement must
    surface an experience "gap"."""
    jobs = [{
        "title": "Senior Engineer",
        "company": "S Co",
        "location": "Remote",
        "source": "remotive",
        "description": "Python developer. 5+ years of experience required.",
        "salary": None, "is_deep_link": False, "url": "https://example.com/sr",
    }]
    _patch_only_remotive_with(monkeypatch, jobs)

    # Build a profile with skills but no years, so _profile_years ≈ 0
    h = _auth(client, "gap_exp_v1")
    data = json.dumps({
        "full_name": "Junior Dev",
        "skills": [{"name": "Python", "years": 0}],
        "experience": [{"company": "School", "role": "Intern", "start": "2026"}],
    }).encode()
    pid = client.post(
        "/api/import", files={"file": ("p.json", data, "application/json")}, headers=h,
    ).json()["profile_id"]
    r = client.get(f"/api/profiles/{pid}/jobs?limit=100", headers=h).json()
    assert r["total"] == 1
    gaps = r["jobs"][0]["gaps"]
    assert gaps["experience"]["status"] == "gap"
    assert "5" in gaps["experience"]["message"]


def test_location_alias_sf_matches_san_francisco(client, monkeypatch):
    """Alias-aware location matching: a candidate location of "SF" must align
    with a job tagged "San Francisco" (previously these would NOT match)."""
    jobs = [{
        "title": "Python Developer",
        "company": "SF Co",
        "location": "San Francisco, CA",
        "source": "remotive",
        "description": "Python developer.",
        "salary": None, "is_deep_link": False, "url": "https://example.com/sf",
    }]
    _patch_only_remotive_with(monkeypatch, jobs)

    h = _auth(client, "alias_sf_v1")
    pid = _profile(client, h)
    r = client.get(
        f"/api/profiles/{pid}/jobs?location=SF&limit=100", headers=h,
    ).json()
    assert r["total"] == 1
    # The location factor should be high (canonical-city equality)
    assert r["jobs"][0]["match_breakdown"]["location"] >= 75
    assert r["jobs"][0]["gaps"]["location"]["status"] != "gap"


def test_skill_details_matched_have_high_confidence(client, monkeypatch):
    """Exactly-matched skills must appear with status "matched" and confidence
    >= 85 in the per-skill detail list."""
    jobs = [{
        "title": "Python Developer",
        "company": "Py Co",
        "location": "Remote",
        "source": "remotive",
        "description": "Python FastAPI developer needed.",
        "salary": None, "is_deep_link": False, "url": "https://example.com/py",
    }]
    _patch_only_remotive_with(monkeypatch, jobs)

    h = _auth(client, "detail_match_v1")
    pid = _profile(client, h)  # profile has Python, FastAPI, ML, AWS
    r = client.get(f"/api/profiles/{pid}/jobs?limit=100", headers=h).json()
    details = r["jobs"][0]["skill_details"]
    matched = [d for d in details if d["status"] == "matched"]
    matched_skills = {d["skill"].lower() for d in matched}
    assert "python" in matched_skills
    assert "fastapi" in matched_skills
    for d in matched:
        assert d["confidence"] >= 85


def test_invalid_sort_returns_400(client, patched_sources):
    h = _auth(client, "bad_sort_v1")
    pid = _profile(client, h)
    r = client.get(f"/api/profiles/{pid}/jobs?sort=bogus", headers=h)
    assert r.status_code == 400


def test_invalid_portal_returns_400(client, patched_sources):
    h = _auth(client, "bad_portal_v1")
    pid = _profile(client, h)
    r = client.get(f"/api/profiles/{pid}/jobs?portal=bogus_source", headers=h)
    assert r.status_code == 400


def test_nonexistent_profile_returns_404(client, patched_sources):
    h = _auth(client, "no_profile_v1")
    r = client.get("/api/profiles/999999/jobs", headers=h)
    assert r.status_code == 404


def test_dedupe_collapses_same_title_company(client, monkeypatch):
    """Deduplication by (title, company) keeps only the first occurrence."""
    import routers.jobs_router as rj
    jobs = _build_fixture_jobs()
    jobs.append(dict(jobs[0]))
    jobs[-1]["url"] = "https://example.com/different-url"

    monkeypatch.setattr(rj, "_fetch_remotive", lambda q, l: [dict(j) for j in jobs])
    for name in ("_fetch_arbeitnow", "_fetch_remoteok", "_fetch_himalayas",
                 "_fetch_the_muse", "_fetch_jobicy", "_fetch_weworkremotely",
                 "_fetch_adzuna", "_fetch_findwork", "_fetch_jooble",
                 "_fetch_reed", "_fetch_usajobs"):
        monkeypatch.setattr(rj, name, lambda q, l: [])
    for name in ("_fetch_linkedin", "_fetch_indeed", "_fetch_glassdoor"):
        monkeypatch.setattr(rj, name, lambda q, loc, l, k="": [])
    monkeypatch.setattr(rj, "_fetch_google_jobs", lambda q, loc: [])
    monkeypatch.setattr(rj, "_profile_match_score", lambda p, j, sl="": {
        "score": float(j.get("match_score", 0.0)),
        "breakdown": {}, "matched": [], "missing": [],
        "skill_details": [], "gaps": {}, "partials": [],
        "insight": "", "confidence": "",
    })

    h = _auth(client, "dedup_v1")
    pid = _profile(client, h)
    r = client.get(f"/api/profiles/{pid}/jobs?limit=100", headers=h).json()
    assert r["total"] == 6
    urls = [j["url"] for j in r["jobs"]]
    assert len(set(urls)) == 6


# ── Issue: strict query + location filtering ─────────────────────────────────

def test_strict_query_filter_keeps_only_matching_jobs(client, monkeypatch):
    """When the user types a Job Title, only jobs whose title or description
    contains ALL query tokens are kept. The previous behaviour returned
    loosely-related jobs (e.g. searching "Backend Developer" returned
    "Frontend Web Developer" because generic keywords overlapped)."""
    import routers.jobs_router as rj
    # Inject a Frontend job alongside the Backend fixture jobs so we can
    # verify it gets filtered out when the user searches "Backend".
    jobs = [
        {
            "title": "Senior Backend Python Developer",
            "company": "TechCorp",
            "location": "Remote", "source": "remotive",
            "description": "Python FastAPI AWS required. 5+ years of backend experience.",
            "salary": "$120k-$150k", "is_deep_link": False,
            "date_posted": "2026-06-15", "job_type": "remote",
            "is_remote": True, "industry": "tech",
            "match_score": 92.0, "salary_min": 120000, "salary_max": 150000,
            "match_breakdown": "{}", "matched_skills": "[]", "missing_skills": "[]",
            "url": "https://example.com/senior-backend",
        },
        {
            "title": "ML Backend Developer",
            "company": "AIStartup",
            "location": "Remote", "source": "himalayas",
            "description": "Machine Learning and Python expert. Backend systems.",
            "salary": "$140k-$180k", "is_deep_link": False,
            "date_posted": "2026-06-18", "job_type": "contract",
            "is_remote": True, "industry": "tech",
            "match_score": 85.0, "salary_min": 140000, "salary_max": 180000,
            "match_breakdown": "{}", "matched_skills": "[]", "missing_skills": "[]",
            "url": "https://example.com/ml-backend",
        },
        {
            "title": "Frontend Web Developer React/Typescript",
            "company": "FakeCorp",
            "location": "Remote, USA",
            "source": "remotive",
            "description": "React TypeScript frontend role. CSS HTML only. UI work.",
            "salary": "$90k-$120k", "is_deep_link": False,
            "date_posted": "2026-06-15", "job_type": "remote",
            "is_remote": True, "industry": "tech",
            "match_score": 70.0, "salary_min": 90000, "salary_max": 120000,
            "match_breakdown": "{}", "matched_skills": "[]", "missing_skills": "[]",
            "url": "https://example.com/frontend-react",
        },
    ]

    monkeypatch.setattr(rj, "_fetch_remotive", lambda q, l: [dict(j) for j in jobs])
    for name in ("_fetch_arbeitnow", "_fetch_remoteok", "_fetch_himalayas",
                 "_fetch_the_muse", "_fetch_jobicy", "_fetch_weworkremotely",
                 "_fetch_adzuna", "_fetch_findwork", "_fetch_jooble",
                 "_fetch_reed", "_fetch_usajobs"):
        monkeypatch.setattr(rj, name, lambda q, l: [])
    for name in ("_fetch_linkedin", "_fetch_indeed", "_fetch_glassdoor"):
        monkeypatch.setattr(rj, name, lambda q, loc, l, k="": [])
    monkeypatch.setattr(rj, "_fetch_google_jobs", lambda q, loc: [])
    monkeypatch.setattr(rj, "_profile_match_score", lambda p, j, sl="": {
        "score": float(j.get("match_score", 0.0)),
        "breakdown": {}, "matched": [], "missing": [],
        "skill_details": [], "gaps": {}, "partials": [],
        "insight": "", "confidence": "",
    })

    h = _auth(client, "strict_q_v1")
    pid = _profile(client, h)
    r = client.get(
        f"/api/profiles/{pid}/jobs?job_title=Backend+Developer&limit=100",
        headers=h,
    ).json()
    titles = {j["title"] for j in r["jobs"]}
    # Strict filter must remove the Frontend job even though it scored
    # well against the Python-heavy profile.
    assert "Frontend Web Developer React/Typescript" not in titles
    # And keep the actual Backend-flavoured jobs.
    assert "Senior Backend Python Developer" in titles
    assert "ML Backend Developer" in titles


def test_strict_query_filter_matches_description_too(client, monkeypatch):
    """A job whose TITLE doesn't contain the keyword but whose description
    does (e.g. 'Hiring a Senior Engineer to build our backend') is kept."""
    import routers.jobs_router as rj
    jobs = [{
        "title": "Software Engineer",
        "company": "Co",
        "location": "Remote",
        "source": "remotive",
        "description": "Join us to build a backend service in Python.",
        "salary": None, "is_deep_link": False,
        "date_posted": "2026-06-15", "job_type": "remote",
        "is_remote": True, "industry": "tech",
        "match_score": 80.0, "salary_min": 0, "salary_max": 0,
        "match_breakdown": "{}", "matched_skills": "[]", "missing_skills": "[]",
        "url": "https://example.com/se",
    }, {
        "title": "Marketing Manager",
        "company": "Co2",
        "location": "Remote",
        "source": "remotive",
        "description": "Looking for a marketing manager with SEO skills.",
        "salary": None, "is_deep_link": False,
        "date_posted": "2026-06-15", "job_type": "full-time",
        "is_remote": True, "industry": "marketing",
        "match_score": 5.0, "salary_min": 0, "salary_max": 0,
        "match_breakdown": "{}", "matched_skills": "[]", "missing_skills": "[]",
        "url": "https://example.com/mm",
    }]
    monkeypatch.setattr(rj, "_fetch_remotive", lambda q, l: [dict(j) for j in jobs])
    for name in ("_fetch_arbeitnow", "_fetch_remoteok", "_fetch_himalayas",
                 "_fetch_the_muse", "_fetch_jobicy", "_fetch_weworkremotely",
                 "_fetch_adzuna", "_fetch_findwork", "_fetch_jooble",
                 "_fetch_reed", "_fetch_usajobs"):
        monkeypatch.setattr(rj, name, lambda q, l: [])
    for name in ("_fetch_linkedin", "_fetch_indeed", "_fetch_glassdoor"):
        monkeypatch.setattr(rj, name, lambda q, loc, l, k="": [])
    monkeypatch.setattr(rj, "_fetch_google_jobs", lambda q, loc: [])
    monkeypatch.setattr(rj, "_profile_match_score", lambda p, j, sl="": {
        "score": float(j.get("match_score", 0.0)),
        "breakdown": {}, "matched": [], "missing": [],
        "skill_details": [], "gaps": {}, "partials": [],
        "insight": "", "confidence": "",
    })

    h = _auth(client, "strict_q2_v1")
    pid = _profile(client, h)
    r = client.get(
        f"/api/profiles/{pid}/jobs?job_title=backend&limit=100", headers=h,
    ).json()
    titles = {j["title"] for j in r["jobs"]}
    # "backend" in the description → keep
    assert "Software Engineer" in titles
    # No backend mention at all → drop
    assert "Marketing Manager" not in titles


def test_strict_location_filter_excludes_other_regions(client, monkeypatch):
    """When the user types a Location, only jobs whose location field
    contains a location token are kept. Previously a "Remote" profile
    location was used as a fallback and overrode the user's input."""
    import routers.jobs_router as rj
    jobs = [
        {
            "title": "Backend Engineer", "company": "IndianCo",
            "location": "Bangalore, India", "source": "remotive",
            "description": "Backend in Python.",
            "salary": None, "is_deep_link": False,
            "date_posted": "2026-06-15", "job_type": "full-time",
            "is_remote": False, "industry": "tech",
            "match_score": 85.0, "salary_min": 0, "salary_max": 0,
            "match_breakdown": "{}", "matched_skills": "[]", "missing_skills": "[]",
            "url": "https://example.com/in",
        },
        {
            "title": "Backend Engineer", "company": "USCo",
            "location": "San Francisco, USA", "source": "remotive",
            "description": "Backend in Python.",
            "salary": None, "is_deep_link": False,
            "date_posted": "2026-06-15", "job_type": "full-time",
            "is_remote": False, "industry": "tech",
            "match_score": 85.0, "salary_min": 0, "salary_max": 0,
            "match_breakdown": "{}", "matched_skills": "[]", "missing_skills": "[]",
            "url": "https://example.com/us",
        },
    ]
    monkeypatch.setattr(rj, "_fetch_remotive", lambda q, l: [dict(j) for j in jobs])
    for name in ("_fetch_arbeitnow", "_fetch_remoteok", "_fetch_himalayas",
                 "_fetch_the_muse", "_fetch_jobicy", "_fetch_weworkremotely",
                 "_fetch_adzuna", "_fetch_findwork", "_fetch_jooble",
                 "_fetch_reed", "_fetch_usajobs"):
        monkeypatch.setattr(rj, name, lambda q, l: [])
    for name in ("_fetch_linkedin", "_fetch_indeed", "_fetch_glassdoor"):
        monkeypatch.setattr(rj, name, lambda q, loc, l, k="": [])
    monkeypatch.setattr(rj, "_fetch_google_jobs", lambda q, loc: [])
    monkeypatch.setattr(rj, "_profile_match_score", lambda p, j, sl="": {
        "score": float(j.get("match_score", 0.0)),
        "breakdown": {}, "matched": [], "missing": [],
        "skill_details": [], "gaps": {}, "partials": [],
        "insight": "", "confidence": "",
    })

    h = _auth(client, "strict_loc_v1")
    pid = _profile(client, h)
    r = client.get(
        f"/api/profiles/{pid}/jobs?location=India&limit=100", headers=h,
    ).json()
    companies = {j["company"] for j in r["jobs"]}
    assert "IndianCo" in companies
    assert "USCo" not in companies


def test_strict_location_keeps_untagged_jobs(client, monkeypatch):
    """Jobs with empty location (upstream didn't tag) are kept even when
    the user filters by a specific location — same policy as the
    job_type and industry filters."""
    import routers.jobs_router as rj
    jobs = [
        {"title": "Backend Engineer", "company": "A", "location": "India",
         "description": "Backend", "source": "remotive",
         "date_posted": "2026-06-15", "job_type": "remote",
         "match_score": 80.0, "salary_min": 0, "salary_max": 0,
         "match_breakdown": "{}", "matched_skills": "[]", "missing_skills": "[]",
         "url": "https://example.com/a"},
        {"title": "Backend Engineer", "company": "B", "location": "",
         "description": "Backend", "source": "remotive",
         "date_posted": "2026-06-15", "job_type": "remote",
         "match_score": 80.0, "salary_min": 0, "salary_max": 0,
         "match_breakdown": "{}", "matched_skills": "[]", "missing_skills": "[]",
         "url": "https://example.com/b"},
    ]
    monkeypatch.setattr(rj, "_fetch_remotive", lambda q, l: [dict(j) for j in jobs])
    for name in ("_fetch_arbeitnow", "_fetch_remoteok", "_fetch_himalayas",
                 "_fetch_the_muse", "_fetch_jobicy", "_fetch_weworkremotely",
                 "_fetch_adzuna", "_fetch_findwork", "_fetch_jooble",
                 "_fetch_reed", "_fetch_usajobs"):
        monkeypatch.setattr(rj, name, lambda q, l: [])
    for name in ("_fetch_linkedin", "_fetch_indeed", "_fetch_glassdoor"):
        monkeypatch.setattr(rj, name, lambda q, loc, l, k="": [])
    monkeypatch.setattr(rj, "_fetch_google_jobs", lambda q, loc: [])
    monkeypatch.setattr(rj, "_profile_match_score", lambda p, j, sl="": {
        "score": float(j.get("match_score", 0.0)),
        "breakdown": {}, "matched": [], "missing": [],
        "skill_details": [], "gaps": {}, "partials": [],
        "insight": "", "confidence": "",
    })

    h = _auth(client, "strict_loc2_v1")
    pid = _profile(client, h)
    r = client.get(
        f"/api/profiles/{pid}/jobs?location=India&limit=100", headers=h,
    ).json()
    companies = {j["company"] for j in r["jobs"]}
    # India job kept
    assert "A" in companies
    # Untagged job kept (empty location)
    assert "B" in companies


# ── Deep semantic matching settings toggle ────────────────────────────────

def test_deep_semantic_matching_toggle_appears_in_breakdown(client, monkeypatch):
    """When use_deep_semantic_matching is on, the neural_semantic factor must
    appear in match_breakdown (using the real scoring engine, with only the
    embedding model mocked out); when off, it must not."""
    from unittest.mock import patch

    jobs = [{
        "title": "Python Developer",
        "company": "Py Co",
        "location": "Remote",
        "source": "remotive",
        "description": "Python FastAPI developer needed.",
        "salary": None, "is_deep_link": False, "url": "https://example.com/py-deep-sem",
    }]
    _patch_only_remotive_with(monkeypatch, jobs)

    h = _auth(client, "deep_sem_v1")
    pid = _profile(client, h)

    r = client.put("/api/settings", json={"use_deep_semantic_matching": True}, headers=h)
    assert r.status_code == 200

    with patch(
        "routers.jobs_router.embedding_engine.neural_semantic_scores",
        return_value=[88.5],
    ):
        r = client.get(f"/api/profiles/{pid}/jobs?limit=100", headers=h)
    assert r.status_code == 200
    jobs_resp = r.json()["jobs"]
    assert len(jobs_resp) == 1
    assert jobs_resp[0]["match_breakdown"].get("neural_semantic") == 88.5

    r = client.put("/api/settings", json={"use_deep_semantic_matching": False}, headers=h)
    assert r.status_code == 200
    r = client.get(f"/api/profiles/{pid}/jobs?limit=100", headers=h)
    assert r.status_code == 200
    jobs_resp = r.json()["jobs"]
    assert "neural_semantic" not in jobs_resp[0]["match_breakdown"]


def test_external_search_google_jobs_uses_ibp_format(client, patched_sources):
    """Google Jobs deep link must use the official `ibp=htl;jobs` parameter
    (URL-encoded as %3B) to switch the result set to the Jobs vertical so
    the search opens directly in Jobs mode, not regular web search."""
    h = _auth(client, "ext_gj_v2")
    pid = _profile(client, h)
    r = client.get(
        f"/api/profiles/{pid}/external-search?keywords=Backend+Developer&location=India",
        headers=h,
    ).json()
    google = next((l for l in r["links"] if l["portal"] == "google_jobs"), None)
    assert google is not None
    url = google["url"]
    # Must be a Google search URL with the query and +jobs and location
    assert url.startswith("https://www.google.com/search?")
    assert "Backend" in url
    assert "jobs" in url
    assert "India" in url
    # Must use the official ibp=htl;jobs parameter (URL-encoded)
    assert "ibp=htl%3Bjobs" in url
    # Must NOT use the deprecated uibp parameter
    assert "uibp=" not in url
