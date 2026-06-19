import pytest
from sqlmodel import create_engine, SQLModel, Session
from fastapi.testclient import TestClient
from models import Profile, Skill, Experience, ExperienceBullet, Education, Certification, Project, ContactLink


@pytest.fixture(name="engine")
def engine_fixture():
    engine = create_engine("sqlite:///:memory:")
    SQLModel.metadata.create_all(engine)
    yield engine
    SQLModel.metadata.drop_all(engine)


@pytest.fixture(name="session")
def session_fixture(engine):
    with Session(engine) as session:
        yield session


@pytest.fixture(name="sample_profile")
def sample_profile_fixture(session):
    profile = Profile(full_name="Jane Doe", email="jane@example.com", phone="+1 555 0100",
                      location="London, UK", summary="Senior backend engineer.")
    session.add(profile)
    session.commit()
    session.refresh(profile)
    skill = Skill(profile_id=profile.id, name="Python", category="Language", years=6.0)
    session.add(skill)
    exp = Experience(profile_id=profile.id, company="Acme Corp", role="Backend Engineer",
                     start="2020-01", end="2024-06")
    session.add(exp)
    session.commit()
    session.refresh(exp)
    bullet = ExperienceBullet(experience_id=exp.id, text="Built microservices handling 1M req/day.")
    session.add(bullet)
    edu = Education(profile_id=profile.id, institution="MIT", degree="BSc", field="Computer Science",
                    start="2014", end="2018")
    session.add(edu)
    session.commit()
    session.refresh(profile)
    return profile


@pytest.fixture(name="client")
def client_fixture():
    """TestClient wired to a fresh in-memory SQLite DB. Patches `db.engine`
    in place and re-creates tables so the routers see the test schema."""
    from sqlalchemy.pool import StaticPool
    test_engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    SQLModel.metadata.create_all(test_engine)

    import db
    original_engine = db.engine
    db.engine = test_engine

    # Re-import main so that create_app() picks up the new engine. The routers
    # already bound to the old engine are not used because we register fresh
    # router instances via create_app.
    import sys
    for mod in (
        "routers.jobs_router", "routers.profile_router", "routers.analysis_router",
        "routers.sections_router", "routers.auth_router", "routers.settings_router",
        "routers.import_router", "routers.export_router", "routers.logs_router",
        "main",
    ):
        if mod in sys.modules:
            del sys.modules[mod]

    from main import create_app
    app = create_app()
    with TestClient(app) as c:
        yield c

    db.engine = original_engine
    SQLModel.metadata.drop_all(test_engine)

