"""Unit tests for the weighted profile match scoring engine (Issue #7)."""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from models import Profile, Skill, Experience, Education, Certification
from routers.jobs_router import (
    _profile_match_score,
    _parse_required_years,
    _parse_salary_range,
    _extract_job_type,
    _is_remote_job,
    _confidence_band,
    _weights_with_neural,
    _WEIGHTS,
)


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
    assert r["breakdown"]["location"] == 90


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
    assert r["breakdown"]["years"] == 25.0  # no profile years → 25


def test_years_factor_full_when_job_has_no_requirement():
    p = _build_profile(skills=[("Python", 1)])
    job = {"title": "Dev", "description": "Python needed", "location": "Remote"}
    r = _profile_match_score(p, job)
    assert r["breakdown"]["years"] == 70


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


# ── Advanced matching tests (fuzzy + cosine + insight + confidence) ──────────

def test_fuzzy_skill_match_nodejs_variant():
    """User with 'Node.js' skill should fuzzy-match a job saying 'nodejs'."""
    p = _build_profile(skills=[("Node.js", 5)])
    job = {
        "title": "Node Developer",
        "description": "Looking for a nodejs developer with strong backend experience",
        "location": "Remote", "is_remote": True,
    }
    r = _profile_match_score(p, job)
    # Fuzzy match should surface the skill
    assert "Node.js" in r["matched"]


def test_synonym_normalization_reactjs():
    """User with 'ReactJS' skill should match a job mentioning 'React'."""
    p = _build_profile(skills=[("ReactJS", 4)])
    job = {
        "title": "Frontend Engineer",
        "description": "React frontend application with modern tooling",
        "location": "Remote", "is_remote": True,
    }
    r = _profile_match_score(p, job)
    assert "ReactJS" in r["matched"]


def test_cosine_keyword_density_high_for_overlap():
    """Heavy skill overlap should produce a meaningful keyword_density score."""
    p = _build_profile(skills=[("Python", 5), ("FastAPI", 3), ("AWS", 2)])
    job = {
        "title": "Python FastAPI Developer",
        "description": "Python FastAPI AWS cloud backend development",
        "location": "Remote", "is_remote": True,
    }
    r = _profile_match_score(p, job)
    assert r["breakdown"]["keyword_density"] >= 30  # cosine + fuzzy coverage


def test_insight_string_present_in_result():
    """Every scored job should include an insight string."""
    p = _build_profile(skills=[("Python", 5)])
    job = {"title": "Python Dev", "description": "Python", "location": "Remote", "is_remote": True}
    r = _profile_match_score(p, job)
    assert "insight" in r
    assert isinstance(r["insight"], str)
    assert len(r["insight"]) > 0


def test_confidence_band_for_high_score():
    """A high score should produce 'Excellent' or 'Strong' confidence."""
    p = _build_profile(
        skills=[("Python", 5), ("FastAPI", 3)],
        roles=["Senior Engineer"],
        education=[("MIT", "BSc", "CS")],
    )
    job = {
        "title": "Senior Engineer Python FastAPI",
        "description": "Python FastAPI AWS needed. 3+ years of experience. Bachelor degree required.",
        "location": "Remote", "is_remote": True,
    }
    r = _profile_match_score(p, job)
    assert r["score"] >= 70
    assert r["confidence"] in ("Excellent", "Strong")


def test_confidence_band_helper():
    assert _confidence_band(90) == "Excellent"
    assert _confidence_band(72) == "Strong"
    assert _confidence_band(55) == "Moderate"
    assert _confidence_band(35) == "Weak"
    assert _confidence_band(10) == "Poor"


def test_result_has_confidence_key():
    """Every _profile_match_score result must include 'confidence'."""
    p = _build_profile(skills=[("Python", 5)])
    job = {"title": "Dev", "description": "Python", "location": "Remote"}
    r = _profile_match_score(p, job)
    assert "confidence" in r
    assert r["confidence"] in ("Excellent", "Strong", "Moderate", "Weak", "Poor")


# ── Advanced ML matchmaking: semantic, per-skill detail, gaps ─────────────────

def test_breakdown_includes_semantic_factor():
    """The 9-factor breakdown must include the new semantic category signal."""
    p = _build_profile(skills=[("Python", 5)])
    job = {"title": "Dev", "description": "Python", "location": "Remote", "is_remote": True}
    r = _profile_match_score(p, job)
    assert "semantic" in r["breakdown"]
    assert 0 <= r["breakdown"]["semantic"] <= 100


def test_semantic_factor_rewards_same_category():
    """React (profile) vs Angular (job) — no exact match, but the semantic
    signal must be > 0 because both are frontend skills."""
    p = _build_profile(skills=[("React", 3), ("Vue", 2)])
    job = {
        "title": "Frontend Engineer",
        "description": "Angular and TypeScript frontend framework required",
        "location": "Remote", "is_remote": True,
    }
    r = _profile_match_score(p, job)
    assert r["breakdown"]["semantic"] > 0
    # Angular must show up as a partial match (via React/Vue), not just missing
    partials = [d for d in r["skill_details"] if d["status"] == "partial"]
    assert any(d["skill"].lower() == "angular" for d in partials)


def test_result_includes_skill_details():
    """_profile_match_score must return a per-skill detail list."""
    p = _build_profile(skills=[("Python", 5), ("FastAPI", 3)])
    job = {"title": "Python Dev", "description": "Python FastAPI", "location": "Remote", "is_remote": True}
    r = _profile_match_score(p, job)
    assert "skill_details" in r
    assert isinstance(r["skill_details"], list)
    # Matched skills must appear with status "matched" and high confidence
    matched = [d for d in r["skill_details"] if d["status"] == "matched"]
    assert any(d["skill"].lower() == "python" for d in matched)
    for d in matched:
        assert d["confidence"] >= 85
        assert d["severity"] in ("required", "nice_to_have")


def test_result_includes_structured_gaps():
    """_profile_match_score must return a structured gaps object covering all
    six dimensions, each with a status and a human message."""
    p = _build_profile(skills=[("Python", 5)])
    job = {"title": "Senior Dev", "description": "Python. 5+ years experience.", "location": "Berlin"}
    r = _profile_match_score(p, job)
    assert "gaps" in r
    gaps = r["gaps"]
    for dim in ("skills", "experience", "location", "seniority", "education", "certifications"):
        assert dim in gaps
        assert gaps[dim]["status"] in ("ok", "weak", "gap")
        assert isinstance(gaps[dim]["message"], str) and gaps[dim]["message"]


def test_gaps_location_gap_for_mismatch():
    """A Remote candidate vs a Berlin job → location gap."""
    p = _build_profile(skills=[("Python", 5)])
    p.location = "Remote"
    job = {"title": "Dev", "description": "Python", "location": "Berlin, Germany"}
    r = _profile_match_score(p, job)
    assert r["gaps"]["location"]["status"] == "gap"


def test_gaps_experience_gap_for_junior():
    """0 profile years vs 5+ required → experience gap."""
    p = _build_profile(skills=[("Python", 0)])
    job = {"title": "Senior Dev", "description": "Python. 5+ years of experience required.", "location": "Remote"}
    r = _profile_match_score(p, job)
    assert r["gaps"]["experience"]["status"] == "gap"


def test_location_factor_sf_alias_matches_san_francisco():
    """The alias-aware location factor: 'SF' on the profile must align with a
    job tagged 'San Francisco' (score >= 75), which the legacy naive token
    matcher would have missed."""
    p = _build_profile(skills=[("Python", 5)])
    p.location = "SF"
    job = {"title": "Dev", "description": "Python", "location": "San Francisco, CA"}
    r = _profile_match_score(p, job, "SF")
    assert r["breakdown"]["location"] >= 75
    assert r["gaps"]["location"]["status"] != "gap"


def test_location_factor_same_region_partial_credit():
    """City vs country granularity: 'Berlin' profile vs 'Germany' job tag
    should get region-level partial credit (>= 70), not a hard gap."""
    p = _build_profile(skills=[("Python", 5)])
    p.location = "Berlin"
    job = {"title": "Dev", "description": "Python", "location": "Germany"}
    r = _profile_match_score(p, job, "Berlin")
    assert r["breakdown"]["location"] >= 70


def test_partials_list_present_when_semantic_covers_gap():
    """When a missing skill is semantically covered, the 'partials' list must
    record the covering resume skill and the confidence."""
    p = _build_profile(skills=[("React", 3)])
    job = {
        "title": "Frontend Engineer",
        "description": "Angular frontend required",
        "location": "Remote", "is_remote": True,
    }
    r = _profile_match_score(p, job)
    assert "partials" in r
    assert any(p_["required"].lower() == "angular" for p_ in r["partials"])
    ang = next(p_ for p_ in r["partials"] if p_["required"].lower() == "angular")
    assert ang["via"].lower() == "react"
    assert ang["confidence"] >= 60


def test_profile_match_score_returns_single_well_formed_result():
    """Regression test for a dead-code bug: _profile_match_score used to have
    an unreachable duplicate return block after the real one. This asserts
    the function returns exactly one well-formed dict with the full key set
    (including skill_details/partials/gaps, which the dead block omitted)."""
    p = _build_profile(
        location="Remote",
        skills=[("Python", 5), ("FastAPI", 3)],
        roles=["Senior Engineer"],
    )
    job = {
        "title": "Senior Engineer Python FastAPI",
        "description": "Python FastAPI needed. 3+ years of experience.",
        "location": "Remote", "is_remote": True,
    }
    r = _profile_match_score(p, job)
    assert set(r.keys()) == {
        "score", "breakdown", "matched", "missing", "skill_details",
        "partials", "gaps", "insight", "confidence",
    }
    assert isinstance(r["score"], float)


def test_weights_with_neural_disabled_returns_original_weights():
    assert _weights_with_neural(False) is _WEIGHTS


def test_weights_with_neural_enabled_sums_to_one_and_includes_factor():
    w = _weights_with_neural(True)
    assert "neural_semantic" in w
    assert abs(sum(w.values()) - 1.0) < 1e-9


def test_neural_score_raises_match_score_when_provided():
    """A job with no shared keywords gets a low score normally; providing a
    high neural_score must raise the result (the factor contributes to the
    weighted sum and appears in the breakdown)."""
    p = _build_profile(skills=[("Python", 5)])
    job = {"title": "Role", "description": "Completely unrelated requirements text", "location": "Remote", "is_remote": True}
    without = _profile_match_score(p, job)
    with_neural = _profile_match_score(p, job, neural_score=95.0)
    assert with_neural["score"] > without["score"]
    assert with_neural["breakdown"]["neural_semantic"] == 95.0
    assert "neural_semantic" not in without["breakdown"]
