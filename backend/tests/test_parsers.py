import json
import pytest
from pathlib import Path
from parsers import parser_for

FIXTURES = Path(__file__).parent / "fixtures"


def test_json_parser_extracts_full_name():
    p = parser_for("json")
    data = (FIXTURES / "sample.json").read_bytes()
    result = p.parse(data)
    assert result.profile.full_name == "Jane Doe"
    assert result.profile.email == "jane@example.com"
    assert result.warnings == []


def test_json_parser_extracts_skills():
    p = parser_for("json")
    data = (FIXTURES / "sample.json").read_bytes()
    result = p.parse(data)
    assert len(result.profile.skills) == 1
    assert result.profile.skills[0].name == "Python"
    assert result.profile.skills[0].years == 6.0


def test_json_parser_extracts_experience_with_bullets():
    p = parser_for("json")
    data = (FIXTURES / "sample.json").read_bytes()
    result = p.parse(data)
    assert len(result.profile.experience) == 1
    exp = result.profile.experience[0]
    assert exp.company == "Acme Corp"
    assert len(exp.bullets) == 1
    assert "microservices" in exp.bullets[0].text


def test_csv_parser_extracts_contact():
    p = parser_for("csv")
    data = (FIXTURES / "sample.csv").read_bytes()
    result = p.parse(data)
    assert result.profile.full_name == "Jane Doe"
    assert result.profile.email == "jane@example.com"


def test_csv_parser_extracts_skills():
    p = parser_for("csv")
    data = (FIXTURES / "sample.csv").read_bytes()
    result = p.parse(data)
    assert len(result.profile.skills) == 1
    assert result.profile.skills[0].name == "Python"


def test_xml_parser_extracts_full_name():
    p = parser_for("xml")
    data = (FIXTURES / "sample.xml").read_bytes()
    result = p.parse(data)
    assert result.profile.full_name == "Jane Doe"


def test_xml_parser_extracts_skills():
    p = parser_for("xml")
    data = (FIXTURES / "sample.xml").read_bytes()
    result = p.parse(data)
    assert any(s.name == "Python" for s in result.profile.skills)


def test_docx_parser_extracts_name():
    p = parser_for("docx")
    data = (FIXTURES / "sample.docx").read_bytes()
    result = p.parse(data)
    assert "Jane" in result.profile.full_name or result.profile.full_name != ""


def test_docx_parser_returns_warnings_for_ambiguous_content():
    p = parser_for("docx")
    data = (FIXTURES / "sample.docx").read_bytes()
    result = p.parse(data)
    # DOCX always adds a best-effort warning
    assert isinstance(result.warnings, list)
    assert len(result.warnings) >= 1


def test_pdf_parser_extracts_name():
    p = parser_for("pdf")
    data = (FIXTURES / "sample.pdf").read_bytes()
    result = p.parse(data)
    assert result.profile.full_name != ""
    assert "Jane" in result.profile.full_name


def test_pdf_parser_returns_warnings():
    p = parser_for("pdf")
    data = (FIXTURES / "sample.pdf").read_bytes()
    result = p.parse(data)
    assert len(result.warnings) >= 1
