from models import Profile, Skill, Experience, ExperienceBullet, Education, Project
from sqlmodel import Session, select


def test_profile_persists(session):
    p = Profile(full_name="Test User")
    session.add(p)
    session.commit()
    result = session.exec(select(Profile)).first()
    assert result.full_name == "Test User"


def test_skill_links_to_profile(session, sample_profile):
    skills = session.exec(select(Skill).where(Skill.profile_id == sample_profile.id)).all()
    assert len(skills) == 1
    assert skills[0].name == "Python"


def test_experience_with_bullets(session, sample_profile):
    exps = session.exec(select(Experience).where(Experience.profile_id == sample_profile.id)).all()
    assert len(exps) == 1
    bullets = session.exec(select(ExperienceBullet).where(ExperienceBullet.experience_id == exps[0].id)).all()
    assert len(bullets) == 1
    assert "microservices" in bullets[0].text


def test_project_tech_json_roundtrip(session):
    p = Profile(full_name="Dev")
    session.add(p)
    session.commit()
    proj = Project(profile_id=p.id, name="My App")
    proj.set_tech(["Python", "FastAPI", "React"])
    session.add(proj)
    session.commit()
    session.refresh(proj)
    assert proj.get_tech() == ["Python", "FastAPI", "React"]
