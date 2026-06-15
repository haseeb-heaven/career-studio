"""PDF parser — best-effort heuristic extraction for real-world resumes.

Strategy:
1. Extract raw text via pdfplumber
2. Attempt AI-enhanced structured extraction (when AI is configured)
3. Fall back to regex heuristics if AI is unavailable
"""
import io
import json
import re
import pdfplumber
from parsers.base import ParseResult
from parsers import register
from models import Profile, Skill, Experience, ExperienceBullet, Project, Education, Certification


# ── Section header aliases ──────────────────────────────────────────────────

_SECTION_MAP = {
    # summary / objective
    "summary": "summary",
    "professional summary": "summary",
    "career summary": "summary",
    "profile": "summary",
    "about": "summary",
    "objective": "summary",
    "career objective": "summary",
    "personal statement": "summary",
    # skills
    "skills": "skills",
    "technical skills": "skills",
    "core skills": "skills",
    "key skills": "skills",
    "competencies": "skills",
    "technologies": "skills",
    "tech stack": "skills",
    "tools": "skills",
    "expertise": "skills",
    "areas of expertise": "skills",
    "programming languages": "skills",
    # experience
    "experience": "experience",
    "work experience": "experience",
    "professional experience": "experience",
    "employment history": "experience",
    "career history": "experience",
    "work history": "experience",
    "relevant experience": "experience",
    "internships": "experience",
    # education
    "education": "education",
    "academic background": "education",
    "academic qualifications": "education",
    "qualifications": "education",
    "degrees": "education",
    # projects
    "projects": "projects",
    "personal projects": "projects",
    "side projects": "projects",
    "portfolio": "projects",
    "open source": "projects",
    # certifications
    "certifications": "certifications",
    "certificates": "certifications",
    "licenses": "certifications",
    "awards": "certifications",
    "achievements": "certifications",
    "honours": "certifications",
    "honors": "certifications",
}

# Date patterns  e.g. "Jan 2020", "2020", "01/2020", "January 2020"
_DATE_RE = re.compile(
    r"(Jan(?:uary)?|Feb(?:ruary)?|Mar(?:ch)?|Apr(?:il)?|May|Jun(?:e)?|"
    r"Jul(?:y)?|Aug(?:ust)?|Sep(?:tember)?|Oct(?:ober)?|Nov(?:ember)?|Dec(?:ember)?)"
    r"\s*[,']?\s*\d{2,4}|\b\d{4}\b|Present|Current|Now|Ongoing|Till\s*Date",
    re.IGNORECASE,
)

_BULLET_CHARS = set("•·▪▸►▶◆●○◦–-*›❖")
_EMAIL_RE = re.compile(r"[\w.+\-]+@[\w.\-]+\.\w{2,}")
_PHONE_RE = re.compile(r"(?:\+?\d[\d\s\-().]{7,}\d)")
_URL_RE = re.compile(r"https?://[^\s]+|linkedin\.com/[^\s]+|github\.com/[^\s]+", re.IGNORECASE)


# ── Helpers ─────────────────────────────────────────────────────────────────

def _is_section_header(line: str) -> str | None:
    """Return the canonical section name if line is a header, else None."""
    stripped = line.strip(" :–—_•\t").lower()
    # exact match
    if stripped in _SECTION_MAP:
        return _SECTION_MAP[stripped]
    # starts-with match for longer headers
    for kw, sec in _SECTION_MAP.items():
        if stripped.startswith(kw) and len(stripped) <= len(kw) + 4:
            return sec
    return None


def _strip_bullet(line: str) -> str:
    line = line.strip()
    if line and line[0] in _BULLET_CHARS:
        line = line[1:].lstrip()
    # Remove markdown-style bullets
    line = re.sub(r"^[-*+]\s+", "", line)
    return line.strip()


def _extract_date_range(text: str):
    """Return (start, end) strings from text like '2020 – Present' or 'Jan 2019 - Dec 2021'."""
    dates = _DATE_RE.findall(text)
    if len(dates) >= 2:
        return str(dates[0]), str(dates[-1])
    elif len(dates) == 1:
        lower = text.lower()
        if any(w in lower for w in ["present", "current", "now", "ongoing"]):
            return str(dates[0]), "Present"
        return str(dates[0]), ""
    return "", ""


def _looks_like_date_line(line: str) -> bool:
    """True if line is primarily dates / location (not a bullet or job title)."""
    hits = _DATE_RE.findall(line)
    if not hits:
        return False
    words = line.split()
    # If more than half the tokens are dates / separators it's a date line
    return len(hits) / max(len(words), 1) > 0.3


def _looks_like_email_or_phone(line: str) -> bool:
    return bool(_EMAIL_RE.search(line)) or bool(_PHONE_RE.search(line))


# ── AI-assisted parse ────────────────────────────────────────────────────────

def _ai_parse(text: str) -> dict | None:
    """Call AI to extract structured resume data. Returns dict or None."""
    try:
        from services.ai_service import complete_simple
        system = (
            "You are a resume parser. Extract structured information from the resume text below.\n"
            "Return ONLY a valid JSON object with these exact keys (omit sections with no data):\n"
            '{"full_name":"","email":"","phone":"","location":"","summary":"",'
            '"skills":["Python","Docker"],'
            '"experience":[{"company":"","role":"","start":"","end":"","location":"",'
            '"bullets":["Achieved X by doing Y"]}],'
            '"education":[{"institution":"","degree":"","field":"","start":"","end":""}],'
            '"projects":[{"name":"","description":"","tech":["React","Node"]}],'
            '"certifications":[{"name":"","issuer":"","date":""}]}\n'
            "Rules: skills must be a flat list of strings. bullets must be plain strings. "
            "Return ONLY JSON, no markdown, no explanation."
        )
        raw = complete_simple(system, f"Resume text (first 5000 chars):\n{text[:5000]}")
        raw = raw.strip()
        if raw.startswith("```"):
            lines = raw.splitlines()
            raw = "\n".join(lines[1:-1] if lines[-1].startswith("```") else lines[1:])
        return json.loads(raw)
    except Exception:
        return None


def _build_profile_from_ai(d: dict) -> Profile:
    """Build a Profile from AI-parsed dict (same key aliases as json_parser)."""
    from parsers.json_parser import JsonParser
    return JsonParser().parse(json.dumps(d).encode()).profile


# ── Heuristic parse ──────────────────────────────────────────────────────────

def _heuristic_parse(lines: list[str]) -> Profile:
    profile = Profile(full_name="")
    profile.skills = []
    profile.experience = []
    profile.projects = []
    profile.education = []
    profile.certifications = []
    profile.links = []

    # ── Pass 1: extract contact info from first 10 lines ──
    header_end = min(10, len(lines))
    for i, line in enumerate(lines[:header_end]):
        em = _EMAIL_RE.search(line)
        if em and not profile.email:
            profile.email = em.group()
        ph = _PHONE_RE.search(line)
        if ph and not profile.phone:
            profile.phone = ph.group().strip()
        for u in _URL_RE.finditer(line):
            url = u.group()
            if not profile.links:
                from models import ContactLink
                profile.links = []
            from models import ContactLink
            label = "LinkedIn" if "linkedin" in url.lower() else "GitHub" if "github" in url.lower() else "Web"
            profile.links.append(ContactLink(label=label, url=url))

    # First non-blank line without @, phone or URL is likely the name
    for line in lines[:5]:
        if not _EMAIL_RE.search(line) and not _PHONE_RE.search(line) and not _URL_RE.search(line):
            candidate = re.sub(r"[|/\\,]+", " ", line).strip()
            # Skip if it looks like a section header
            if not _is_section_header(candidate) and len(candidate.split()) <= 6 and len(candidate) > 1:
                profile.full_name = candidate
                break

    # ── Pass 2: section detection + content parsing ──
    current_section = None
    current_exp: Experience | None = None
    current_proj: Project | None = None
    summary_lines: list[str] = []

    for line in lines:
        sec = _is_section_header(line)
        if sec:
            current_section = sec
            current_exp = None
            current_proj = None
            continue

        clean = line.strip()
        if not clean:
            continue

        # Skip contact/header info already extracted
        if _looks_like_email_or_phone(clean):
            continue

        if current_section == "summary":
            summary_lines.append(clean)

        elif current_section == "skills":
            # Skills may be: comma-separated, pipe-separated, bulleted, or one per line
            text = _strip_bullet(clean)
            # Try splitting on various delimiters
            for sep in (",", "|", "•", "·", "/", ";"):
                if sep in text:
                    for part in text.split(sep):
                        part = part.strip()
                        if 2 <= len(part) <= 40 and not _DATE_RE.search(part):
                            profile.skills.append(Skill(name=part))
                    break
            else:
                # Single skill or "Category: skill1, skill2"
                if ":" in text:
                    _, rest = text.split(":", 1)
                    parts = [p.strip() for p in rest.split(",") if p.strip()]
                    for p in parts:
                        if 2 <= len(p) <= 40:
                            profile.skills.append(Skill(name=p))
                elif 2 <= len(text) <= 40 and not _looks_like_date_line(text):
                    profile.skills.append(Skill(name=text))

        elif current_section == "experience":
            text = clean
            # Detect em-dash or | separator between role and company
            role, company = "", ""
            for sep in (" — ", " – ", " | ", " @ ", " at "):
                if sep in text:
                    parts = text.split(sep, 1)
                    role, company = parts[0].strip(), parts[1].strip()
                    break

            # Check if it's a bullet
            is_bullet = clean[0] in _BULLET_CHARS or re.match(r"^[-*+]\s", clean)

            if is_bullet and current_exp is not None:
                bullet_text = _strip_bullet(clean)
                if bullet_text:
                    current_exp.bullets.append(ExperienceBullet(text=bullet_text))
            elif (role and company) or (not _looks_like_date_line(text) and not is_bullet and len(text.split()) <= 8):
                # New experience entry
                if not role:
                    role = text  # treat as role title
                    company = ""
                start, end = _extract_date_range(text)
                exp = Experience(company=company, role=role, start=start, end=end)
                exp.bullets = []
                profile.experience.append(exp)
                current_exp = exp
            elif _looks_like_date_line(text) and current_exp and not current_exp.start:
                s, e = _extract_date_range(text)
                current_exp.start = s
                current_exp.end = e
            elif current_exp is not None and not _looks_like_date_line(text):
                # Treat as bullet if no bullet char but it's descriptive text
                if len(text) > 20 and text[0].islower() or len(text.split()) > 5:
                    current_exp.bullets.append(ExperienceBullet(text=text))

        elif current_section == "education":
            text = clean
            if _looks_like_date_line(text) and profile.education:
                s, e = _extract_date_range(text)
                if not profile.education[-1].start:
                    profile.education[-1].start = s
                    profile.education[-1].end = e
            elif not _is_section_header(text):
                start, end = _extract_date_range(text)
                # Try to separate degree/institution
                deg, inst, field = "", text, ""
                for sep in (" — ", " – ", " | ", ", "):
                    if sep in text:
                        parts = text.split(sep, 1)
                        deg, inst = parts[0].strip(), parts[1].strip()
                        # Remove dates from inst
                        inst = _DATE_RE.sub("", inst).strip(" -–—(),")
                        break
                # Check for "in <field>" in degree
                m = re.match(r"(.+?)\s+in\s+(.+)", deg, re.IGNORECASE)
                if m:
                    deg, field = m.group(1).strip(), m.group(2).strip()
                profile.education.append(Education(
                    institution=inst, degree=deg, field=field, start=start, end=end
                ))

        elif current_section == "projects":
            text = clean
            is_bullet = clean[0] in _BULLET_CHARS or re.match(r"^[-*+]\s", clean)
            if is_bullet and current_proj is not None:
                desc_addition = _strip_bullet(clean)
                current_proj.description = (current_proj.description + " " + desc_addition).strip()
            elif not _looks_like_date_line(text):
                from models import Project as Proj
                # New project
                name = text.split("|")[0].split("—")[0].split("–")[0].strip()
                proj = Proj(name=name, description="", link="", tech="[]")
                proj.set_tech([])
                profile.projects.append(proj)
                current_proj = proj

        elif current_section == "certifications":
            text = _strip_bullet(clean)
            if text and not _looks_like_date_line(text):
                start, _ = _extract_date_range(text)
                name = _DATE_RE.sub("", text).strip(" -–—|,")
                if name:
                    profile.certifications.append(Certification(name=name, issuer="", date=start))

    if summary_lines:
        profile.summary = " ".join(summary_lines)

    # Deduplicate skills
    seen = set()
    unique_skills = []
    for s in profile.skills:
        key = s.name.lower().strip()
        if key not in seen and len(key) > 1:
            seen.add(key)
            unique_skills.append(s)
    profile.skills = unique_skills

    return profile


# ── Main parser ──────────────────────────────────────────────────────────────

@register("pdf")
class PdfParser:
    def parse(self, data: bytes) -> ParseResult:
        warnings = ["PDF import is best-effort — please review and correct each section."]
        profile = Profile(full_name="")
        profile.skills = []
        profile.experience = []
        profile.projects = []
        profile.education = []
        profile.certifications = []
        profile.links = []

        # Extract text
        try:
            with pdfplumber.open(io.BytesIO(data)) as pdf:
                pages_text = []
                for page in pdf.pages:
                    text = page.extract_text(x_tolerance=3, y_tolerance=3) or ""
                    pages_text.append(text)
                full_text = "\n".join(pages_text)
        except Exception as e:
            warnings.append(f"Could not open PDF: {e}")
            return ParseResult(profile=profile, warnings=warnings)

        lines = [ln.strip() for ln in full_text.splitlines() if ln.strip()]
        if not lines:
            warnings.append("Could not extract any text from PDF.")
            return ParseResult(profile=profile, warnings=warnings)

        # Try AI-assisted parse first
        ai_result = _ai_parse(full_text)
        if ai_result and ai_result.get("full_name"):
            try:
                profile = _build_profile_from_ai(ai_result)
                warnings.append("AI-assisted PDF extraction completed — verify all sections.")
                return ParseResult(profile=profile, warnings=warnings)
            except Exception:
                pass  # fall through to heuristic

        # Heuristic parse
        profile = _heuristic_parse(lines)
        if not profile.full_name:
            warnings.append("Could not detect name — please fill in manually.")

        return ParseResult(profile=profile, warnings=warnings)
