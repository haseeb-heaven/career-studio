import pytest
from sqlalchemy.exc import IntegrityError
from sqlmodel import SQLModel, Session, create_engine, select

import db  # noqa: F401 - registers SQLite foreign key pragma listener
from models import ActivityLog, CoverLetter, JobMatch, Profile, Settings, Skill, User


@pytest.fixture(name="db_engine")
def db_engine_fixture():
    engine = create_engine("sqlite:///:memory:")
    SQLModel.metadata.create_all(engine)
    yield engine
    SQLModel.metadata.drop_all(engine)


def test_user_email_is_unique(db_engine):
    with Session(db_engine) as session:
        session.add(User(username="one", email="same@example.com", password_hash="x"))
        session.add(User(username="two", email="same@example.com", password_hash="x"))

        with pytest.raises(IntegrityError):
            session.commit()


def test_deleting_user_cascades_owned_data(db_engine):
    with Session(db_engine) as session:
        user = User(username="owner", email="owner@example.com", password_hash="x")
        session.add(user)
        session.commit()
        session.refresh(user)

        settings = Settings(user_id=user.id)
        profile = Profile(user_id=user.id, full_name="Owner")
        session.add(settings)
        session.add(profile)
        session.commit()
        session.refresh(profile)

        session.add(Skill(profile_id=profile.id, name="Python"))
        session.add(ActivityLog(action="import", profile_id=profile.id))
        session.add(CoverLetter(profile_id=profile.id, job_title="Engineer"))
        session.add(JobMatch(profile_id=profile.id, title="Engineer"))
        session.commit()

        session.delete(user)
        session.commit()

        assert session.exec(select(Settings)).all() == []
        assert session.exec(select(Profile)).all() == []
        assert session.exec(select(Skill)).all() == []
        assert session.exec(select(ActivityLog)).all() == []
        assert session.exec(select(CoverLetter)).all() == []
        assert session.exec(select(JobMatch)).all() == []


def test_settings_are_one_row_per_user(db_engine):
    with Session(db_engine) as session:
        user = User(username="owner", email="owner@example.com", password_hash="x")
        session.add(user)
        session.commit()
        session.refresh(user)

        session.add(Settings(user_id=user.id))
        session.add(Settings(user_id=user.id))

        with pytest.raises(IntegrityError):
            session.commit()
