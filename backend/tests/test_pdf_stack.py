"""Focused tests for the 3-tier PDF extraction chain and heuristic parser."""
import io
import pytest
from fpdf import FPDF


# ── Fixtures ─────────────────────────────────────────────────────────────────

@pytest.fixture
def simple_pdf_bytes():
    """A minimal text-based PDF pdfplumber can extract from."""
    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Helvetica", "B", 18)
    pdf.cell(0, 10, "Jane Smith", new_x="LMARGIN", new_y="NEXT")
    pdf.set_font("Helvetica", size=10)
    pdf.cell(0, 8, "jane@example.com | +1 555-0100 | London, UK", new_x="LMARGIN", new_y="NEXT")
    pdf.set_font("Helvetica", "B", 12)
    pdf.cell(0, 10, "EXPERIENCE", new_x="LMARGIN", new_y="NEXT")
    pdf.set_font("Helvetica", size=10)
    pdf.cell(0, 8, "Senior Engineer - Acme Corp | 2021 - Present", new_x="LMARGIN", new_y="NEXT")
    pdf.cell(0, 6, "- Built microservices at scale.", new_x="LMARGIN", new_y="NEXT")
    pdf.set_font("Helvetica", "B", 12)
    pdf.cell(0, 10, "SKILLS", new_x="LMARGIN", new_y="NEXT")
    pdf.set_font("Helvetica", size=10)
    pdf.cell(0, 8, "Python, Docker, PostgreSQL", new_x="LMARGIN", new_y="NEXT")
    return bytes(pdf.output())


@pytest.fixture
def empty_pdf_bytes():
    """A PDF with no text content (all whitespace / blank pages)."""
    pdf = FPDF()
    pdf.add_page()
    return bytes(pdf.output())


# ── TierResult ────────────────────────────────────────────────────────────────

def test_tier_result_has_required_fields(simple_pdf_bytes):
    from parsers.pdf_parser import _extract_tier1
    r = _extract_tier1(simple_pdf_bytes)
    assert hasattr(r, "text")
    assert hasattr(r, "words")
    assert hasattr(r, "tables")
    assert hasattr(r, "tier")
    assert hasattr(r, "meta")


def test_tier1_returns_tier_number_1(simple_pdf_bytes):
    from parsers.pdf_parser import _extract_tier1
    r = _extract_tier1(simple_pdf_bytes)
    assert r.tier == 1


def test_tier1_extracts_text(simple_pdf_bytes):
    from parsers.pdf_parser import _extract_tier1
    r = _extract_tier1(simple_pdf_bytes)
    assert len(r.text) >= 50
    assert "Jane" in r.text


def test_tier1_extracts_word_dicts(simple_pdf_bytes):
    from parsers.pdf_parser import _extract_tier1
    r = _extract_tier1(simple_pdf_bytes)
    assert len(r.words) > 0
    word = r.words[0]
    assert "text" in word
    assert "x0" in word
    assert "top" in word
    assert "size" in word
    assert "fontname" in word


def test_tier1_meta_has_page_count(simple_pdf_bytes):
    from parsers.pdf_parser import _extract_tier1
    r = _extract_tier1(simple_pdf_bytes)
    assert r.meta["page_count"] == 1
    assert isinstance(r.meta["page_chars"], list)
    assert len(r.meta["page_chars"]) == 1
    assert r.meta["tier_name"] == "pdfplumber"


def test_tier1_returns_empty_result_on_corrupt_bytes():
    from parsers.pdf_parser import _extract_tier1
    r = _extract_tier1(b"not a pdf")
    assert r.text == ""
    assert r.tier == 1
    assert "error" in r.meta


# ── Tier 2 ────────────────────────────────────────────────────────────────────

def test_tier2_extracts_text(simple_pdf_bytes):
    from parsers.pdf_parser import _extract_tier2
    r = _extract_tier2(simple_pdf_bytes)
    assert r.tier == 2
    assert len(r.text) >= 50
    assert "Jane" in r.text


def test_tier2_word_model_matches_tier1_schema(simple_pdf_bytes):
    from parsers.pdf_parser import _extract_tier2
    r = _extract_tier2(simple_pdf_bytes)
    assert len(r.words) > 0
    for word in r.words:
        assert "text" in word
        assert "x0" in word
        assert "top" in word
        assert "size" in word
        assert "fontname" in word


def test_tier2_meta_has_tier_name(simple_pdf_bytes):
    from parsers.pdf_parser import _extract_tier2
    r = _extract_tier2(simple_pdf_bytes)
    assert r.meta["tier_name"] == "pymupdf"


def test_tier2_handles_corrupt_bytes():
    from parsers.pdf_parser import _extract_tier2
    r = _extract_tier2(b"garbage")
    assert r.text == ""
    assert "error" in r.meta


# ── Tier 3 ────────────────────────────────────────────────────────────────────

def test_tier3_meta_has_tier_name(simple_pdf_bytes):
    from parsers.pdf_parser import _extract_tier3
    r = _extract_tier3(simple_pdf_bytes)
    assert r.tier == 3
    assert r.meta["tier_name"] == "tesseract"
    # words and tables are always empty for OCR tier
    assert r.words == []
    assert r.tables == []


def test_tier3_handles_missing_tesseract(simple_pdf_bytes, monkeypatch):
    import parsers.pdf_parser as mod
    monkeypatch.setattr(mod, "_extract_tier3",
        lambda data: mod.TierResult(text="", words=[], tables=[], tier=3,
            meta={"page_count": 0, "page_chars": [], "tier_name": "tesseract",
                  "error": "tesseract not found"}))
    from parsers.pdf_parser import _extract_tier3
    r = _extract_tier3(simple_pdf_bytes)
    assert r.text == ""
    assert "error" in r.meta


# ── _pick_tier ────────────────────────────────────────────────────────────────

def test_pick_tier_uses_tier1_for_text_pdf(simple_pdf_bytes):
    from parsers.pdf_parser import _pick_tier
    r, warnings = _pick_tier(simple_pdf_bytes)
    assert r.tier == 1
    assert any("Tier 1" in w for w in warnings)


def test_pick_tier_falls_back_to_tier2(simple_pdf_bytes, monkeypatch):
    import parsers.pdf_parser as mod
    monkeypatch.setattr(mod, "_extract_tier1",
        lambda data: mod.TierResult(text="x" * 49, words=[], tables=[], tier=1,
            meta={"page_count": 1, "page_chars": [49], "tier_name": "pdfplumber"}))
    r, warnings = mod._pick_tier(simple_pdf_bytes)
    assert r.tier == 2


def test_pick_tier_falls_back_to_tier3(simple_pdf_bytes, monkeypatch):
    import parsers.pdf_parser as mod
    monkeypatch.setattr(mod, "_extract_tier1",
        lambda data: mod.TierResult(text="x" * 49, words=[], tables=[], tier=1,
            meta={"page_count": 1, "page_chars": [49], "tier_name": "pdfplumber"}))
    monkeypatch.setattr(mod, "_extract_tier2",
        lambda data: mod.TierResult(text="x" * 99, words=[], tables=[], tier=2,
            meta={"page_count": 1, "page_chars": [99], "tier_name": "pymupdf"}))
    r, warnings = mod._pick_tier(simple_pdf_bytes)
    assert r.tier == 3


def test_pick_tier_warning_contains_tier_name(simple_pdf_bytes):
    from parsers.pdf_parser import _pick_tier
    _, warnings = _pick_tier(simple_pdf_bytes)
    assert len(warnings) == 1
    assert "pdfplumber" in warnings[0] or "pymupdf" in warnings[0] or "tesseract" in warnings[0]


# ── _detect_sections ──────────────────────────────────────────────────────────

def test_detect_sections_finds_experience_by_keyword_fallback():
    from parsers.pdf_parser import _detect_sections
    text = "Jane Smith\njane@example.com\nExperience\nSenior Engineer"
    result = _detect_sections(words=[], text=text)
    secs = [s for _, s in result]
    assert "experience" in secs


def test_detect_sections_finds_skills_by_font_size():
    from parsers.pdf_parser import _detect_sections
    words = [
        {"text": "Jane", "x0": 50.0, "top": 50.0, "size": 18.0, "fontname": "Helvetica-Bold"},
        {"text": "Smith", "x0": 90.0, "top": 50.0, "size": 18.0, "fontname": "Helvetica-Bold"},
        {"text": "SKILLS", "x0": 50.0, "top": 120.0, "size": 12.0, "fontname": "Helvetica-Bold"},
    ]
    text = "Jane Smith\njane@example.com\nSKILLS\nPython, Docker"
    result = _detect_sections(words=words, text=text)
    secs = [s for _, s in result]
    assert "skills" in secs


def test_detect_sections_ignores_small_font_headers():
    from parsers.pdf_parser import _detect_sections
    words = [
        {"text": "EXPERIENCE", "x0": 50.0, "top": 100.0, "size": 9.0, "fontname": "Helvetica"},
    ]
    text = "Jane Smith\nEXPERIENCE\nSenior Engineer"
    result = _detect_sections(words=words, text=text)
    secs = [s for _, s in result]
    assert "experience" in secs


def test_detect_sections_returns_sorted_by_line_index():
    from parsers.pdf_parser import _detect_sections
    text = "Jane Smith\nSummary\nI am great\nExperience\nEngineer at Acme"
    result = _detect_sections(words=[], text=text)
    indices = [i for i, _ in result]
    assert indices == sorted(indices)


def test_detect_sections_empty_text_returns_empty():
    from parsers.pdf_parser import _detect_sections
    assert _detect_sections(words=[], text="") == []


# ── _heuristic_parse ──────────────────────────────────────────────────────────

def _make_words(entries):
    """Helper: build word dicts from (text, x0, top, size) tuples."""
    return [{"text": t, "x0": x, "top": y, "size": s, "fontname": "Helvetica"}
            for t, x, y, s in entries]


def test_heuristic_parse_extracts_name_from_largest_font():
    from parsers.pdf_parser import _heuristic_parse
    words = _make_words([
        ("Jane", 50, 30, 18), ("Smith", 90, 30, 18),
        ("jane@example.com", 50, 60, 9),
        ("EXPERIENCE", 50, 100, 12),
    ])
    text = "Jane Smith\njane@example.com\nEXPERIENCE\nEngineer"
    profile = _heuristic_parse(words=words, tables=[], text=text)
    assert "Jane" in profile.full_name
    assert "Smith" in profile.full_name


def test_heuristic_parse_extracts_email():
    from parsers.pdf_parser import _heuristic_parse
    text = "Jane Smith\njane@example.com | +1 555-0100\nSKILLS\nPython"
    profile = _heuristic_parse(words=[], tables=[], text=text)
    assert profile.email == "jane@example.com"


def test_heuristic_parse_extracts_skills_from_text():
    from parsers.pdf_parser import _heuristic_parse
    text = "Jane Smith\nSKILLS\nPython, Docker, PostgreSQL"
    profile = _heuristic_parse(words=[], tables=[], text=text)
    skill_names = [s.name for s in profile.skills]
    assert "Python" in skill_names
    assert "Docker" in skill_names


def test_heuristic_parse_extracts_skills_from_table():
    from parsers.pdf_parser import _heuristic_parse
    tables = [[["Python", "Docker"], ["PostgreSQL", "Redis"]]]
    text = "Jane Smith\nSKILLS"
    profile = _heuristic_parse(words=[], tables=tables, text=text)
    skill_names = [s.name for s in profile.skills]
    assert "Python" in skill_names
    assert "Docker" in skill_names
    assert "PostgreSQL" in skill_names


def test_heuristic_parse_deduplicates_skills():
    from parsers.pdf_parser import _heuristic_parse
    tables = [[["Python", "Docker"]]]
    text = "Jane Smith\nSKILLS\nPython, React"
    profile = _heuristic_parse(words=[], tables=tables, text=text)
    python_count = sum(1 for s in profile.skills if s.name.lower() == "python")
    assert python_count == 1


def test_heuristic_parse_extracts_summary():
    from parsers.pdf_parser import _heuristic_parse
    text = "Jane Smith\nSUMMARY\nSenior backend engineer with 8 years experience.\nEXPERIENCE\nEngineer"
    profile = _heuristic_parse(words=[], tables=[], text=text)
    assert "Senior" in profile.summary


def test_heuristic_parse_extracts_experience():
    from parsers.pdf_parser import _heuristic_parse
    text = "Jane Smith\nEXPERIENCE\nSenior Engineer — Acme Corp\n2021 - Present\n- Built microservices."
    profile = _heuristic_parse(words=[], tables=[], text=text)
    assert len(profile.experience) >= 1


def test_heuristic_parse_returns_empty_profile_on_empty_text():
    from parsers.pdf_parser import _heuristic_parse
    profile = _heuristic_parse(words=[], tables=[], text="")
    assert profile.full_name == ""
    assert profile.skills == []


# ── _merge_ai ─────────────────────────────────────────────────────────────────

def test_merge_ai_never_overwrites_non_empty_email():
    from parsers.pdf_parser import _merge_ai
    from models import Profile
    baseline = Profile(full_name="Jane Smith", email="jane@example.com")
    baseline.skills = []
    baseline.experience = []
    baseline.projects = []
    baseline.education = []
    baseline.certifications = []
    baseline.links = []
    ai_dict = {"full_name": "Jane Smith", "email": "wrong@ai.com", "skills": []}
    result = _merge_ai(baseline, ai_dict)
    assert result.email == "jane@example.com"


def test_merge_ai_never_overwrites_non_empty_name():
    from parsers.pdf_parser import _merge_ai
    from models import Profile
    baseline = Profile(full_name="Jane Smith", email="")
    baseline.skills = []
    baseline.experience = []
    baseline.projects = []
    baseline.education = []
    baseline.certifications = []
    baseline.links = []
    ai_dict = {"full_name": "WRONG NAME", "skills": []}
    result = _merge_ai(baseline, ai_dict)
    assert result.full_name == "Jane Smith"


def test_merge_ai_fills_empty_summary_from_ai():
    from parsers.pdf_parser import _merge_ai
    from models import Profile
    baseline = Profile(full_name="Jane Smith", email="", summary="")
    baseline.skills = []
    baseline.experience = []
    baseline.projects = []
    baseline.education = []
    baseline.certifications = []
    baseline.links = []
    ai_dict = {"full_name": "Jane Smith", "summary": "Senior backend engineer.", "skills": []}
    result = _merge_ai(baseline, ai_dict)
    assert result.summary == "Senior backend engineer."


def test_merge_ai_overwrites_shorter_summary_with_longer_ai_summary():
    from parsers.pdf_parser import _merge_ai
    from models import Profile
    baseline = Profile(full_name="Jane", email="", summary="Short.")
    baseline.skills = []
    baseline.experience = []
    baseline.projects = []
    baseline.education = []
    baseline.certifications = []
    baseline.links = []
    ai_dict = {"full_name": "Jane", "summary": "Senior backend engineer with 8 years of experience.", "skills": []}
    result = _merge_ai(baseline, ai_dict)
    assert "8 years" in result.summary


def test_merge_ai_returns_baseline_on_none():
    from parsers.pdf_parser import _merge_ai
    from models import Profile
    baseline = Profile(full_name="Jane Smith", email="jane@example.com")
    baseline.skills = []
    baseline.experience = []
    baseline.projects = []
    baseline.education = []
    baseline.certifications = []
    baseline.links = []
    result = _merge_ai(baseline, None)
    assert result.full_name == "Jane Smith"
    assert result.email == "jane@example.com"


def test_merge_ai_appends_ai_skills_not_in_baseline():
    from parsers.pdf_parser import _merge_ai
    from models import Profile, Skill
    baseline = Profile(full_name="Jane", email="")
    baseline.skills = [Skill(name="Python", profile_id=0)]
    baseline.experience = []
    baseline.projects = []
    baseline.education = []
    baseline.certifications = []
    baseline.links = []
    ai_dict = {"full_name": "Jane", "skills": ["Python", "Docker", "React"]}
    result = _merge_ai(baseline, ai_dict)
    names = [s.name for s in result.skills]
    assert "Docker" in names
    assert "React" in names


# ── PdfParser.parse integration ───────────────────────────────────────────────

def test_pdf_parser_parse_returns_parse_result(simple_pdf_bytes):
    from parsers import parser_for
    result = parser_for("pdf").parse(simple_pdf_bytes)
    from parsers.base import ParseResult
    assert isinstance(result, ParseResult)


def test_pdf_parser_parse_extracts_name(simple_pdf_bytes):
    from parsers import parser_for
    result = parser_for("pdf").parse(simple_pdf_bytes)
    assert result.profile.full_name != ""
    assert "Jane" in result.profile.full_name


def test_pdf_parser_parse_has_warnings(simple_pdf_bytes):
    from parsers import parser_for
    result = parser_for("pdf").parse(simple_pdf_bytes)
    assert isinstance(result.warnings, list)
    assert len(result.warnings) >= 1


def test_pdf_parser_parse_survives_corrupt_bytes():
    from parsers import parser_for
    result = parser_for("pdf").parse(b"not a pdf")
    assert result.profile is not None
    assert any("Extracted" in w or "Tier" in w or "Could not" in w or "chars" in w
               for w in result.warnings)


# ── Golden tests: heuristic parser field extraction ───────────────────────────

@pytest.fixture
def golden_pdf_bytes():
    """Known resume PDF with specific skills, experience, and certifications.
    These golden tests verify that the heuristic parser extracts named fields
    rather than just confirming the parser doesn't crash."""
    pdf = FPDF()
    pdf.add_page()
    # Name / contact block
    pdf.set_font("Helvetica", "B", 18)
    pdf.cell(0, 10, "Alex Rivera", new_x="LMARGIN", new_y="NEXT")
    pdf.set_font("Helvetica", size=10)
    pdf.cell(0, 6, "alex@example.com | +1 555-9999 | New York, NY", new_x="LMARGIN", new_y="NEXT")

    # Skills section
    pdf.set_font("Helvetica", "B", 13)
    pdf.cell(0, 9, "SKILLS", new_x="LMARGIN", new_y="NEXT")
    pdf.set_font("Helvetica", size=10)
    pdf.cell(0, 6, "Python | JavaScript | Docker | Kubernetes | PostgreSQL", new_x="LMARGIN", new_y="NEXT")

    # Experience section
    pdf.set_font("Helvetica", "B", 13)
    pdf.cell(0, 9, "EXPERIENCE", new_x="LMARGIN", new_y="NEXT")
    pdf.set_font("Helvetica", "B", 11)
    pdf.cell(0, 7, "Staff Engineer", new_x="LMARGIN", new_y="NEXT")
    pdf.set_font("Helvetica", size=10)
    pdf.cell(0, 6, "CloudBase Inc  |  2019 - Present", new_x="LMARGIN", new_y="NEXT")
    pdf.cell(0, 5, "- Designed multi-region deployment pipeline.", new_x="LMARGIN", new_y="NEXT")
    pdf.cell(0, 5, "- Reduced p99 latency by 40%.", new_x="LMARGIN", new_y="NEXT")

    # Certifications section
    pdf.set_font("Helvetica", "B", 13)
    pdf.cell(0, 9, "CERTIFICATIONS", new_x="LMARGIN", new_y="NEXT")
    pdf.set_font("Helvetica", size=10)
    pdf.cell(0, 6, "AWS Solutions Architect | Amazon Web Services", new_x="LMARGIN", new_y="NEXT")
    pdf.cell(0, 6, "Certified Kubernetes Administrator | CNCF", new_x="LMARGIN", new_y="NEXT")

    return bytes(pdf.output())


class TestHeuristicParserGolden:
    """Golden tests: parse a known synthetic PDF and assert specific fields are extracted.
    These catch regressions where the parser silently drops sections."""

    def setup_method(self):
        from parsers import parser_for
        self.parse = lambda data: parser_for("pdf").parse(data)

    def test_golden_name(self, golden_pdf_bytes):
        result = self.parse(golden_pdf_bytes)
        assert "Alex" in result.profile.full_name, (
            f"Expected 'Alex' in full_name, got {result.profile.full_name!r}"
        )

    def test_golden_skills_extracted(self, golden_pdf_bytes):
        result = self.parse(golden_pdf_bytes)
        names = [s.name.lower() for s in result.profile.skills]
        assert any("python" in n for n in names), f"Expected Python in skills, got: {names}"
        assert any("docker" in n for n in names), f"Expected Docker in skills, got: {names}"

    def test_golden_skills_split_on_pipe(self, golden_pdf_bytes):
        result = self.parse(golden_pdf_bytes)
        # If splitting fails we'd get one giant skill name with pipes in it
        for skill in result.profile.skills:
            assert "|" not in skill.name, (
                f"Skill not split correctly: {skill.name!r} — delimiter '|' still present"
            )

    def test_golden_experience_extracted(self, golden_pdf_bytes):
        result = self.parse(golden_pdf_bytes)
        assert len(result.profile.experience) >= 1, (
            f"Expected at least 1 experience entry, got {len(result.profile.experience)}"
        )
        roles = [e.role for e in result.profile.experience]
        assert any("Engineer" in r or "engineer" in r for r in roles), (
            f"Expected 'Engineer' role, got: {roles}"
        )

    def test_golden_certifications_extracted(self, golden_pdf_bytes):
        result = self.parse(golden_pdf_bytes)
        assert len(result.profile.certifications) >= 1, (
            f"Expected at least 1 certification, got {len(result.profile.certifications)}"
        )
        cert_names = [c.name for c in result.profile.certifications]
        assert any("AWS" in n or "Kubernetes" in n for n in cert_names), (
            f"Expected AWS or Kubernetes cert, got: {cert_names}"
        )
