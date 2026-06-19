"""Tests for new JobMatch columns and SavedFilter table."""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from models import JobMatch, SavedFilter, Profile, Skill
from sqlmodel import Session, select


def test_jobmatch_has_new_columns(session, sample_profile):
    jm = JobMatch(
        profile_id=sample_profile.id, title="Dev", company="Co",
        match_score=80.0, date_posted="2026-06-15", job_type="remote",
        industry="tech", is_remote=True, is_expired=False,
        salary_min=100000, salary_max=150000,
        match_breakdown='{"skills": 40}', matched_skills='["Python"]',
        missing_skills='["Docker"]',
    )
    session.add(jm)
    session.commit()
    session.refresh(jm)
    assert jm.date_posted == "2026-06-15"
    assert jm.job_type == "remote"
    assert jm.is_remote is True
    assert jm.salary_min == 100000
    assert jm.salary_max == 150000
    assert jm.matched_skills == '["Python"]'
    assert jm.missing_skills == '["Docker"]'


def test_saved_filter_persists(session, sample_profile):
    sf = SavedFilter(
        user_id=None, profile_id=sample_profile.id, name="Senior Remote",
        filters='{"min_years": 5}', sort="best_match",
    )
    session.add(sf)
    session.commit()
    sf_id = sf.id
    session.expire_all()
    found = session.get(SavedFilter, sf_id)
    assert found is not None
    assert found.name == "Senior Remote"
    assert found.sort == "best_match"
    assert "min_years" in found.filters


def test_jobmatch_defaults_are_safe(session, sample_profile):
    """A new JobMatch with no extra fields should be valid (Issue #7 migration defaults)."""
    jm = JobMatch(profile_id=sample_profile.id, title="X")
    session.add(jm)
    session.commit()
    session.refresh(jm)
    assert jm.date_posted == ""
    assert jm.job_type == ""
    assert jm.is_remote is False
    assert jm.salary_min == 0
    assert jm.salary_max == 0
    assert jm.matched_skills == "[]"
    assert jm.missing_skills == "[]"
    assert jm.match_breakdown == ""


def test_certification_has_cert_id_column(session, sample_profile):
    """Certifications carry an optional alphanumeric cert_id (license / serial)."""
    from models import Certification
    cert = Certification(
        profile_id=sample_profile.id,
        name="AWS Solutions Architect",
        cert_id="AWS-SAA-12345",
        issuer="Amazon",
        date="2024-06",
    )
    session.add(cert)
    session.commit()
    session.refresh(cert)
    assert cert.cert_id == "AWS-SAA-12345"
    assert cert.name == "AWS Solutions Architect"


def test_certification_cert_id_defaults_to_empty(session, sample_profile):
    from models import Certification
    cert = Certification(profile_id=sample_profile.id, name="PMP")
    session.add(cert)
    session.commit()
    session.refresh(cert)
    assert cert.cert_id == ""
