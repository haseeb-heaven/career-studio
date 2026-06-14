import json
import pytest
from sqlmodel import create_engine, SQLModel, Session
from models import Profile, Skill, Experience, ExperienceBullet, Education, Certification
from exporters import exporter_for


@pytest.fixture(name="session")
def session_fixture():
    engine = create_engine("sqlite:///:memory:")
    SQLModel.metadata.create_all(engine)
    with Session(engine) as s:
        yield s


@pytest.fixture(name="profile")
def profile_fixture(session):
    p = Profile(full_name="Jane Doe", email="jane@example.com", summary="Senior engineer.",
                availability="Immediate", compensation="£90k+")
    session.add(p)
    session.commit()
    session.refresh(p)
    session.add(Skill(profile_id=p.id, name="Python", category="Language", years=6.0))
    exp = Experience(profile_id=p.id, company="Acme", role="Engineer", start="2020-01", end="2024-06")
    session.add(exp)
    session.commit()
    session.refresh(exp)
    session.add(ExperienceBullet(experience_id=exp.id, text="Built microservices."))
    session.add(Education(profile_id=p.id, institution="MIT", degree="BSc", field="CS",
                          start="2014", end="2018"))
    session.add(Certification(profile_id=p.id, name="AWS SAA", issuer="Amazon", date="2023-03"))
    session.commit()
    session.refresh(p)
    return p


def test_json_exporter_produces_valid_json(profile):
    exp = exporter_for("json")
    result = exp.export(profile)
    data = json.loads(result)
    assert data["full_name"] == "Jane Doe"
    assert data["email"] == "jane@example.com"
    assert len(data["skills"]) == 1
    assert data["skills"][0]["name"] == "Python"
    assert len(data["experience"]) == 1
    assert data["experience"][0]["bullets"] == ["Built microservices."]
    assert len(data["education"]) == 1
    assert len(data["certifications"]) == 1
    assert data["availability"] == "Immediate"


def test_csv_exporter_produces_skill_rows(profile):
    import csv, io
    exp = exporter_for("csv")
    result = exp.export(profile)
    reader = csv.DictReader(io.StringIO(result.decode()))
    rows = list(reader)
    # CSV exports skills section as rows
    skill_rows = [r for r in rows if r.get("section") == "skill"]
    assert len(skill_rows) == 1
    assert skill_rows[0]["name"] == "Python"
    assert skill_rows[0]["category"] == "Language"


def test_xml_exporter_produces_valid_xml(profile):
    import xml.etree.ElementTree as ET
    exp = exporter_for("xml")
    result = exp.export(profile)
    root = ET.fromstring(result.decode())
    assert root.tag == "profile"
    assert root.find("full_name").text == "Jane Doe"
    skills = root.findall("skills/skill")
    assert len(skills) == 1
    assert skills[0].find("name").text == "Python"


def test_docx_exporter_produces_valid_docx(profile):
    from docx import Document
    import io
    exp = exporter_for("docx")
    result = exp.export(profile)
    doc = Document(io.BytesIO(result))
    full_text = " ".join(p.text for p in doc.paragraphs)
    assert "Jane Doe" in full_text
    assert "Python" in full_text
    assert "Acme" in full_text


def test_pdf_exporter_produces_pdf_bytes(profile):
    exp = exporter_for("pdf")
    result = exp.export(profile)
    assert result[:4] == b"%PDF"
    assert len(result) > 1000


def test_json_round_trip(profile):
    from parsers import parser_for as pfr
    exp = exporter_for("json")
    exported = exp.export(profile)
    result = pfr("json").parse(exported)
    assert result.profile.full_name == profile.full_name
    assert len(result.profile.skills) == len(profile.skills)
    assert len(result.profile.experience) == len(profile.experience)
