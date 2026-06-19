"""Unit tests for the weighted profile match scoring engine (Issue #7)."""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from models import Profile, Skill, Experience, Education, Certification
from routers.jobs_router import _profile_match_score, _parse_required_years, _parse_salary_range, _extract_job_type, _is_remote_job


def _build_profile(**kw):
    p = Profile(full_name=kw.get("name", "Jane"), location=kw.get("location", "Remote"))
    p.skills = [Skill(name=n, years=y) for n, y in kw.get("skills", [])]
    p.experience = [
        Experience(company="A", role=r, start="2020", end="")
        for r in kw.get("roles", [])
    ]
    p.education = [
        Education(institution=i, degree=d, field=f, start="", end="")
        for i, d, f in kw.get("education", [])
    ]
    p.certifications = [
        Certification(name=str(n), issuer="", date="")
        for n in kw.get("certs", [])
    ]
    return p


def test_full_match_returns_high_score():
    p = _build_profile(
        location="Remote",
        skills=[("Python", 5), ("FastAPI", 3)],
        roles=["Senior Engineer"],
        education=[("MIT", "BSc", "CS")],
        certs=["AWS"],
    )
    job = {
        "title": "Senior Engineer Python FastAPI",
        "description": "Python FastAPI AWS needed. 3+ years of experience. Bachelor degree required.",
        "location": "Remote", "is_remote": True,
    }
    r = _profile_match_score(p, job)
    assert r["score"] >= 80
    assert "Python" in r["matched"]


def test_missing_skill_appears_in_gap():
    p = _build_profile(skills=[("Python", 5)])
    job = {"title": "Dev", "description": "Python and Kubernetes required", "location": "Remote", "is_remote": True}
    r = _profile_match_score(p, job)
    assert any(s.lower() == "kubernetes" for s in r["missing"])
    assert "Python" in r["matched"]


def test_no_profile_data_returns_valid_score():
    p = Profile(full_name="X")
    p.skills = []; p.experience = []; p.education = []; p.certifications = []
    job = {"title": "Dev", "description": "x", "location": ""}
    r = _profile_match_score(p, job)
    assert 0 <= r["score"] <= 100


def test_required_years_regex():
    assert _parse_required_years("5+ years of experience needed") == 5
    assert _parse_required_years("Must have 3 yrs experience") == 3
    assert _parse_required_years("No experience needed") == 0
    assert _parse_required_years("") == 0
    assert _parse_required_years("10 years of experience preferred") == 10


def test_breakdown_has_all_six_factors():
    p = _build_profile(skills=[("Python", 5)])
    job = {"title": "Python Dev", "description": "Python", "location": "Remote", "is_remote": True}
    r = _profile_match_score(p, job)
    for k in ("skills", "years", "education", "location", "certifications", "title"):
        assert k in r["breakdown"]


def test_remote_match_without_location():
    p = _build_profile(skills=[("Python", 5)])
    p.location = ""
    job = {"title": "Dev", "description": "x", "is_remote": True, "location": "Remote"}
    r = _profile_match_score(p, job)
    assert r["breakdown"]["location"] == 100


def test_title_similarity_low_when_no_overlap():
    p = _build_profile(roles=["Senior Engineer"], skills=[("Python", 5)])
    job = {"title": "Completely Different Role", "description": "Python needed", "location": "Remote", "is_remote": True}
    r = _profile_match_score(p, job)
    assert r["breakdown"]["title"] < 50


def test_title_similarity_high_when_overlap():
    p = _build_profile(roles=["Senior Backend Engineer"], skills=[("Python", 5)])
    job = {"title": "Senior Backend Engineer", "description": "Python", "location": "Remote", "is_remote": True}
    r = _profile_match_score(p, job)
    assert r["breakdown"]["title"] >= 90


def test_education_required_but_missing_penalized():
    p = _build_profile(skills=[("Python", 5)])
    job = {"title": "Dev", "description": "Bachelor degree required, Python needed", "location": "Remote", "is_remote": True}
    r = _profile_match_score(p, job)
    assert r["breakdown"]["education"] <= 50


def test_education_matched_when_both_have_it():
    p = _build_profile(skills=[("Python", 5)], education=[("MIT", "BS", "CS")])
    job = {"title": "Dev", "description": "Bachelor degree, Python", "location": "Remote", "is_remote": True}
    r = _profile_match_score(p, job)
    assert r["breakdown"]["education"] == 100


def test_years_factor_zero_when_no_profile_years():
    p = _build_profile()  # no skills
    job = {"title": "Dev", "description": "5+ years experience", "location": "Remote"}
    r = _profile_match_score(p, job)
    assert r["breakdown"]["years"] == 30.0  # no profile years → 30


def test_years_factor_full_when_job_has_no_requirement():
    p = _build_profile(skills=[("Python", 1)])
    job = {"title": "Dev", "description": "Python needed", "location": "Remote"}
    r = _profile_match_score(p, job)
    assert r["breakdown"]["years"] == 100


def test_certifications_penalized_when_job_mentions_them():
    p = _build_profile(skills=[("Python", 5)])  # no certs
    job = {"title": "Dev", "description": "AWS Python", "location": "Remote"}
    r = _profile_match_score(p, job)
    assert r["breakdown"]["certifications"] <= 40


def test_nodejs_skill_matches_nodejs_in_description():
    """User with Node.js skill should match a Node.js job description."""
    p = _build_profile(skills=[("Node.js", 5)])
    job = {
        "title": "Node Developer",
        "description": "Looking for a Node.js developer with strong backend experience",
        "location": "Remote", "is_remote": True,
    }
    r = _profile_match_score(p, job)
    assert "Node.js" in r["matched"]


def test_backend_skill_recognised():
    """User with 'Backend' skill should match backend job descriptions."""
    p = _build_profile(skills=[("Backend", 5), ("Python", 3)])
    job = {
        "title": "Backend Engineer",
        "description": "Backend Python developer wanted",
        "location": "Remote", "is_remote": True,
    }
    r = _profile_match_score(p, job)
    assert "Backend" in r["matched"]


def test_frontend_role_matches_frontend_skill():
    """Frontend skill in profile should match a Frontend job."""
    p = _build_profile(skills=[("Frontend", 4), ("React", 3)])
    job = {
        "title": "Frontend Engineer",
        "description": "Frontend React developer for SaaS platform",
        "location": "Remote", "is_remote": True,
    }
    r = _profile_match_score(p, job)
    assert "Frontend" in r["matched"]


def test_fullstack_role_matches_fullstack_skill():
    p = _build_profile(skills=[("Fullstack", 5), ("Node", 3), ("React", 3)])
    job = {
        "title": "Fullstack Engineer",
        "description": "Fullstack role with React and Node",
        "location": "Remote", "is_remote": True,
    }
    r = _profile_match_score(p, job)
    assert any(s.lower() == "fullstack" for s in r["matched"])


def test_score_is_weighted_sum():
    """Manually verify the weighted sum against the WEIGHTS dict."""
    from routers.jobs_router import _WEIGHTS
    p = _build_profile(skills=[("Python", 5)])
    job = {"title": "Python Dev", "description": "Python", "location": "Remote", "is_remote": True}
    r = _profile_match_score(p, job)
    expected = sum(_WEIGHTS[k] * r["breakdown"][k] for k in _WEIGHTS)
    assert abs(r["score"] - round(min(100.0, max(0.0, expected)), 1)) < 0.2


# ── Helper tests ──────────────────────────────────────────────────────────────

def test_parse_salary_range_k_format():
    assert _parse_salary_range("$120k-$150k") == (120000, 150000)


def test_parse_salary_range_full_numbers():
    assert _parse_salary_range("$120,000 - $150,000") == (120000, 150000)


def test_parse_salary_range_single_value():
    assert _parse_salary_range("$100k") == (100000, 100000)


def test_parse_salary_range_empty():
    assert _parse_salary_range("") == (0, 0)
    assert _parse_salary_range(None) == (0, 0)


def test_extract_job_type_recognises_remote():
    assert _extract_job_type({"job_type": "remote"}) == "remote"
    assert _extract_job_type({"job_type": "Full Time"}) == "full-time"
    assert _extract_job_type({"job_type": "Contract"}) == "contract"
    assert _extract_job_type({"job_type": ""}) == ""


def test_is_remote_job_by_location():
    assert _is_remote_job({"location": "Remote"}) is True
    assert _is_remote_job({"location": "Anywhere in US"}) is True
    assert _is_remote_job({"location": "New York, NY"}) is False
    assert _is_remote_job({"location": "Remote", "is_remote": True}) is True
