"""PDF parser — 3-tier extraction chain with coordinate-based section detection.

Pipeline:
1. Extract text + word layout via pdfplumber (Tier 1)
2. Fallback to pymupdf span extraction if chars < 50 (Tier 2)
3. Fallback to pytesseract OCR if chars < 100 (Tier 3)
4. Coordinate/font-based section detection → deterministic Profile
5. Optional AI refinement pass (offline-safe)
"""
import io
import json
import re
from collections import defaultdict
from dataclasses import dataclass, field as dc_field
from typing import Any

import pdfplumber

from logger import get_logger
from models import (
    Profile, Skill, Experience, ExperienceBullet,
    Project, Education, Certification, ContactLink,
)
from parsers.base import ParseResult
from parsers import register

logger = get_logger(__name__)


# ── TierResult ────────────────────────────────────────────────────────────────

@dataclass
class TierResult:
    text: str
    words: list[dict]
    tables: list[list]
    tier: int
    meta: dict = dc_field(default_factory=dict)


# ── Tier 1: pdfplumber ────────────────────────────────────────────────────────

def _extract_tier1(data: bytes) -> TierResult:
    words_all: list[dict] = []
    tables_all: list[list] = []
    pages_text: list[str] = []
    page_chars: list[int] = []
    try:
        with pdfplumber.open(io.BytesIO(data)) as pdf:
            page_count = len(pdf.pages)
            for page in pdf.pages:
                w = page.extract_words(extra_attrs=["size", "fontname"]) or []
                words_all.extend(w)
                tables_all.extend(page.extract_tables() or [])
                page_text = " ".join(wd["text"] for wd in w)
                pages_text.append(page_text)
                page_chars.append(len(page_text))
    except Exception as exc:
        logger.warning("Tier 1 extraction failed: %s", exc)
        return TierResult(
            text="", words=[], tables=[], tier=1,
            meta={"page_count": 0, "page_chars": [], "tier_name": "pdfplumber", "error": str(exc)},
        )
    full_text = "\n".join(pages_text)
    return TierResult(
        text=full_text, words=words_all, tables=tables_all, tier=1,
        meta={"page_count": page_count, "page_chars": page_chars, "tier_name": "pdfplumber"},
    )


# ── Tier 2: pymupdf ───────────────────────────────────────────────────────────

def _extract_tier2(data: bytes) -> TierResult:
    try:
        import fitz  # pymupdf
    except ImportError as exc:
        logger.warning("pymupdf not installed: %s", exc)
        return TierResult(text="", words=[], tables=[], tier=2,
                         meta={"page_count": 0, "page_chars": [], "tier_name": "pymupdf",
                               "error": str(exc)})
    words_all: list[dict] = []
    pages_text: list[str] = []
    page_chars: list[int] = []
    try:
        doc = fitz.open(stream=data, filetype="pdf")
        page_count = len(doc)
        for page in doc:
            d = page.get_text("dict")
            page_words: list[dict] = []
            for block in d.get("blocks", []):
                for line in block.get("lines", []):
                    for span in line.get("spans", []):
                        for raw_word in span["text"].split():
                            page_words.append({
                                "text": raw_word,
                                "x0": float(span["bbox"][0]),
                                "top": float(span["bbox"][1]),
                                "size": float(span["size"]),
                                "fontname": span["font"],
                            })
            words_all.extend(page_words)
            page_text = " ".join(w["text"] for w in page_words)
            pages_text.append(page_text)
            page_chars.append(len(page_text))
        doc.close()
    except Exception as exc:
        logger.warning("Tier 2 extraction failed: %s", exc)
        return TierResult(text="", words=[], tables=[], tier=2,
                         meta={"page_count": 0, "page_chars": [], "tier_name": "pymupdf",
                               "error": str(exc)})
    return TierResult(
        text="\n".join(pages_text), words=words_all, tables=[], tier=2,
        meta={"page_count": page_count, "page_chars": page_chars, "tier_name": "pymupdf"},
    )


# ── Tier 3: pytesseract OCR ───────────────────────────────────────────────────

def _extract_tier3(data: bytes) -> TierResult:
    try:
        from pdf2image import convert_from_bytes
        import pytesseract
        images = convert_from_bytes(data, dpi=200)
        pages_text: list[str] = []
        page_chars: list[int] = []
        for img in images:
            text = pytesseract.image_to_string(img)
            pages_text.append(text)
            page_chars.append(len(text))
        return TierResult(
            text="\n".join(pages_text), words=[], tables=[], tier=3,
            meta={"page_count": len(images), "page_chars": page_chars, "tier_name": "tesseract"},
        )
    except Exception as exc:
        logger.warning("Tier 3 OCR failed: %s", exc)
        return TierResult(text="", words=[], tables=[], tier=3,
                         meta={"page_count": 0, "page_chars": [], "tier_name": "tesseract",
                               "error": str(exc)})


# ── Tier selector ─────────────────────────────────────────────────────────────

def _pick_tier(data: bytes) -> tuple[TierResult, list[str]]:
    r = _extract_tier1(data)
    if len(r.text) < 50:
        logger.info("Tier 1 yielded %d chars — falling back to Tier 2 (pymupdf)", len(r.text))
        r = _extract_tier2(data)
    if len(r.text) < 100:
        logger.info("Tier 2 yielded %d chars — falling back to Tier 3 (OCR)", len(r.text))
        r = _extract_tier3(data)
    warnings = [
        f"Extracted {len(r.text)} chars via Tier {r.tier} ({r.meta.get('tier_name', '?')})"
    ]
    return r, warnings


# ── Section header aliases ────────────────────────────────────────────────────

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


# ── Helpers ───────────────────────────────────────────────────────────────────

def _is_section_header(line: str) -> str | None:
    """Return the canonical section name if line is a header, else None."""
    stripped = line.strip(" :–—_•\t").lower()
    if stripped in _SECTION_MAP:
        return _SECTION_MAP[stripped]
    for kw, sec in _SECTION_MAP.items():
        if stripped.startswith(kw) and len(stripped) <= len(kw) + 4:
            return sec
    return None


def _strip_bullet(line: str) -> str:
    line = line.strip()
    if line and line[0] in _BULLET_CHARS:
        line = line[1:].lstrip()
    line = re.sub(r"^[-*+]\s+", "", line)
    return line.strip()


def _extract_date_range(text: str):
    """Return (start, end) strings from text like '2020 – Present'."""
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
    hits = _DATE_RE.findall(line)
    if not hits:
        return False
    words = line.split()
    return len(hits) / max(len(words), 1) > 0.3


def _looks_like_email_or_phone(line: str) -> bool:
    return bool(_EMAIL_RE.search(line)) or bool(_PHONE_RE.search(line))


# ── Section detection ─────────────────────────────────────────────────────────

def _detect_sections(words: list[dict], text: str) -> list[tuple[int, str]]:
    """Return [(line_index, section_name)] sorted by position in text.splitlines()."""
    if not text:
        return []

    lines = text.splitlines()
    results: list[tuple[int, str]] = []

    if words:
        line_words: dict[int, list[dict]] = defaultdict(list)
        for w in words:
            bucket = round(w.get("top", 0) / 2) * 2
            line_words[bucket].append(w)

        size_map: dict[str, float] = {}
        for bucket_words in line_words.values():
            line_text = " ".join(w["text"] for w in sorted(bucket_words, key=lambda x: x.get("x0", 0)))
            max_size = max(w.get("size", 0) for w in bucket_words)
            size_map[line_text.strip()] = max_size

        for i, line in enumerate(lines):
            stripped = line.strip()
            if not stripped:
                continue
            size = size_map.get(stripped, 0.0)
            if size >= 11.5:
                sec = _is_section_header(stripped)
                if sec:
                    results.append((i, sec))

    if not results:
        for i, line in enumerate(lines):
            sec = _is_section_header(line)
            if sec:
                results.append((i, sec))

    results.sort(key=lambda x: x[0])
    return results


# ── Heuristic parse ───────────────────────────────────────────────────────────

def _heuristic_parse(words: list[dict], tables: list[list], text: str) -> Profile:
    """Build a Profile from layout data. Always returns a valid Profile; never raises."""
    profile = Profile(full_name="")
    profile.skills = []
    profile.experience = []
    profile.projects = []
    profile.education = []
    profile.certifications = []
    profile.links = []

    if not text:
        return profile

    all_lines = text.splitlines()
    lines = [ln.strip() for ln in all_lines if ln.strip()]

    # Collect raw skill names during parsing to avoid SQLAlchemy instrumentation
    # issues when deduplicating; Skill objects are created once at the end.
    _skill_names: list[str] = []

    # ── Name: largest-font word cluster in top 20% of first-page y-extent ──
    if words:
        tops = [w.get("top", 0) for w in words]
        if tops:
            min_top, max_top = min(tops), max(tops)
            threshold = min_top + (max_top - min_top) * 0.20
            header_words = [w for w in words if w.get("top", 0) <= threshold]
            if header_words:
                max_size = max(w.get("size", 0) for w in header_words)
                name_words = [w for w in header_words if w.get("size", 0) >= max_size - 0.5]
                by_line: dict[int, list[dict]] = defaultdict(list)
                for w in name_words:
                    by_line[round(w.get("top", 0) / 2) * 2].append(w)
                for key in sorted(by_line.keys()):
                    candidate = " ".join(
                        w["text"] for w in sorted(by_line[key], key=lambda x: x.get("x0", 0))
                    )
                    candidate = re.sub(r"[|/\\,]+", " ", candidate).strip()
                    if (
                        not _is_section_header(candidate)
                        and not _EMAIL_RE.search(candidate)
                        and not _PHONE_RE.search(candidate)
                        and not _URL_RE.search(candidate)
                        and 1 < len(candidate.split()) <= 6
                        and len(candidate) > 1
                    ):
                        profile.full_name = candidate
                        break

    if not profile.full_name:
        for line in lines[:5]:
            if not _EMAIL_RE.search(line) and not _PHONE_RE.search(line) and not _URL_RE.search(line):
                candidate = re.sub(r"[|/\\,]+", " ", line).strip()
                if not _is_section_header(candidate) and len(candidate.split()) <= 6 and len(candidate) > 1:
                    profile.full_name = candidate
                    break

    # ── Contact: regex scan of first 10 lines ──
    for line in lines[:10]:
        em = _EMAIL_RE.search(line)
        if em and not profile.email:
            profile.email = em.group()
        ph = _PHONE_RE.search(line)
        if ph and not profile.phone:
            profile.phone = ph.group().strip()
        for u in _URL_RE.finditer(line):
            url = u.group()
            label = "LinkedIn" if "linkedin" in url.lower() else "GitHub" if "github" in url.lower() else "Web"
            profile.links.append(ContactLink(label=label, url=url))

    # ── Skills from tables ──
    for table in (tables or []):
        for row in (table or []):
            for cell in (row or []):
                cell = (cell or "").strip()
                if 2 <= len(cell) <= 40 and not _DATE_RE.search(cell) and not _is_section_header(cell):
                    _skill_names.append(cell)

    # ── Section detection + line-by-line parsing ──
    section_markers = _detect_sections(words, text)
    line_to_section: dict[int, str] = {idx: sec for idx, sec in section_markers}

    current_section: str | None = None
    current_exp: Experience | None = None
    current_proj: Project | None = None
    summary_lines: list[str] = []

    for i, line in enumerate(all_lines):
        if i in line_to_section:
            current_section = line_to_section[i]
            current_exp = None
            current_proj = None
            continue

        sec = _is_section_header(line)
        if sec:
            current_section = sec
            current_exp = None
            current_proj = None
            continue

        clean = line.strip()
        if not clean:
            continue
        if _looks_like_email_or_phone(clean):
            continue

        if current_section == "summary":
            summary_lines.append(clean)

        elif current_section == "skills":
            text_part = _strip_bullet(clean)
            for sep in (",", "|", "•", "·", "/", ";"):
                if sep in text_part:
                    for part in text_part.split(sep):
                        part = part.strip()
                        if 2 <= len(part) <= 40 and not _DATE_RE.search(part):
                            _skill_names.append(part)
                    break
            else:
                if ":" in text_part:
                    _, rest = text_part.split(":", 1)
                    for p in [x.strip() for x in rest.split(",") if x.strip()]:
                        if 2 <= len(p) <= 40:
                            _skill_names.append(p)
                elif 2 <= len(text_part) <= 40 and not _looks_like_date_line(text_part):
                    _skill_names.append(text_part)

        elif current_section == "experience":
            role, company = "", ""
            for sep in (" — ", " – ", " | ", " @ ", " at "):
                if sep in clean:
                    parts = clean.split(sep, 1)
                    role, company = parts[0].strip(), parts[1].strip()
                    break
            is_bullet = clean[0] in _BULLET_CHARS or bool(re.match(r"^[-*+]\s", clean))
            if is_bullet and current_exp is not None:
                bullet_text = _strip_bullet(clean)
                if bullet_text:
                    current_exp.bullets.append(ExperienceBullet(text=bullet_text))
            elif (role and company) or (
                not _looks_like_date_line(clean) and not is_bullet and len(clean.split()) <= 8
            ):
                if not role:
                    role = clean
                    company = ""
                start, end = _extract_date_range(clean)
                exp = Experience(company=company, role=role, start=start, end=end)
                exp.bullets = []
                profile.experience.append(exp)
                current_exp = exp
            elif _looks_like_date_line(clean) and current_exp and not current_exp.start:
                s, e = _extract_date_range(clean)
                current_exp.start = s
                current_exp.end = e
            elif current_exp is not None and not _looks_like_date_line(clean):
                if (len(clean) > 20 and clean[0].islower()) or len(clean.split()) > 5:
                    current_exp.bullets.append(ExperienceBullet(text=clean))

        elif current_section == "education":
            if _looks_like_date_line(clean) and profile.education:
                s, e = _extract_date_range(clean)
                if not profile.education[-1].start:
                    profile.education[-1].start = s
                    profile.education[-1].end = e
            elif not _is_section_header(clean):
                start, end = _extract_date_range(clean)
                deg, inst, field = "", clean, ""
                for sep in (" — ", " – ", " | ", ", "):
                    if sep in clean:
                        parts = clean.split(sep, 1)
                        deg, inst = parts[0].strip(), parts[1].strip()
                        inst = _DATE_RE.sub("", inst).strip(" -–—(),")
                        break
                m = re.match(r"(.+?)\s+in\s+(.+)", deg, re.IGNORECASE)
                if m:
                    deg, field = m.group(1).strip(), m.group(2).strip()
                profile.education.append(Education(
                    institution=inst, degree=deg, field=field, start=start, end=end
                ))

        elif current_section == "projects":
            is_bullet = clean[0] in _BULLET_CHARS or bool(re.match(r"^[-*+]\s", clean))
            if is_bullet and current_proj is not None:
                current_proj.description = (current_proj.description + " " + _strip_bullet(clean)).strip()
            elif not _looks_like_date_line(clean):
                name = clean.split("|")[0].split("—")[0].split("–")[0].strip()
                proj = Project(name=name, description="", link="", tech="[]")
                proj.set_tech([])
                profile.projects.append(proj)
                current_proj = proj

        elif current_section == "certifications":
            text_part = _strip_bullet(clean)
            if text_part and not _looks_like_date_line(text_part):
                start, _ = _extract_date_range(text_part)
                name = _DATE_RE.sub("", text_part).strip(" -–—|,")
                if name:
                    profile.certifications.append(Certification(name=name, issuer="", date=start))

    if summary_lines:
        profile.summary = " ".join(summary_lines)

    # Build deduplicated skills from collected names (avoids SQLAlchemy list issues)
    seen: set[str] = set()
    for name in _skill_names:
        key = name.lower().strip()
        if key not in seen and len(key) > 1:
            seen.add(key)
            profile.skills.append(Skill(name=name))

    return profile


# ── AI refinement ─────────────────────────────────────────────────────────────

def _ai_refine(text: str) -> dict | None:
    """Call AI to get normalized/gap-filled JSON. Returns dict or None on any failure."""
    if len(text) < 200:
        logger.debug("Skipping AI refinement: text too short (%d chars)", len(text))
        return None
    try:
        from services.ai_service import complete_simple
    except ImportError:
        return None
    try:
        system = (
            "You are a resume parser. The following resume text has already been parsed. "
            "Return a corrected and normalized JSON object with these keys (omit empty sections):\n"
            '{"full_name":"","email":"","phone":"","location":"","summary":"",'
            '"skills":["Python","Docker"],'
            '"experience":[{"company":"","role":"","start":"","end":"","location":"",'
            '"bullets":["Achieved X"]}],'
            '"education":[{"institution":"","degree":"","field":"","start":"","end":""}],'
            '"projects":[{"name":"","description":"","tech":["React"]}],'
            '"certifications":[{"name":"","issuer":"","date":""}]}\n'
            "Rules: do not invent data not in the text. Return ONLY JSON."
        )
        raw = complete_simple(system, f"Resume text:\n{text[:5000]}")
        raw = raw.strip()
        if raw.startswith("```"):
            raw_lines = raw.splitlines()
            raw = "\n".join(raw_lines[1:-1] if raw_lines[-1].startswith("```") else raw_lines[1:])
        return json.loads(raw)
    except Exception as exc:
        logger.warning("AI refinement failed: %s", exc)
        return None


# ── Conservative merge ────────────────────────────────────────────────────────

def _merge_ai(baseline: Profile, ai_dict: dict | None) -> Profile:
    """Merge AI-parsed dict into baseline using conservative rules. Returns baseline."""
    if not ai_dict or not isinstance(ai_dict, dict):
        return baseline

    if not baseline.full_name and ai_dict.get("full_name"):
        baseline.full_name = str(ai_dict["full_name"])
    if not baseline.email and ai_dict.get("email"):
        baseline.email = str(ai_dict["email"])
    if not baseline.phone and ai_dict.get("phone"):
        baseline.phone = str(ai_dict["phone"])
    if not baseline.location and ai_dict.get("location"):
        baseline.location = str(ai_dict["location"])

    ai_summary = str(ai_dict.get("summary") or "").strip()
    if ai_summary and len(ai_summary) > len(baseline.summary):
        baseline.summary = ai_summary

    ai_skills = [s for s in (ai_dict.get("skills") or []) if isinstance(s, str) and s.strip()]
    if ai_skills and len(ai_skills) > len(baseline.skills):
        baseline.skills = [Skill(name=s.strip()) for s in ai_skills]
    elif ai_skills:
        existing = {s.name.lower() for s in baseline.skills}
        for name in ai_skills:
            if name.lower() not in existing:
                baseline.skills.append(Skill(name=name))
                existing.add(name.lower())

    existing_exp = {(e.company.lower(), e.role.lower()) for e in baseline.experience}
    for ai_exp in (ai_dict.get("experience") or []):
        if not isinstance(ai_exp, dict):
            continue
        company = str(ai_exp.get("company") or "")
        role = str(ai_exp.get("role") or "")
        if (company.lower(), role.lower()) not in existing_exp:
            exp = Experience(
                company=company, role=role,
                start=str(ai_exp.get("start") or ""),
                end=str(ai_exp.get("end") or ""),
                location=str(ai_exp.get("location") or ""),
            )
            exp.bullets = [
                ExperienceBullet(text=b)
                for b in (ai_exp.get("bullets") or [])
                if isinstance(b, str)
            ]
            baseline.experience.append(exp)
            existing_exp.add((company.lower(), role.lower()))

    existing_proj = {p.name.lower() for p in baseline.projects}
    for ai_proj in (ai_dict.get("projects") or []):
        if not isinstance(ai_proj, dict):
            continue
        name = str(ai_proj.get("name") or "")
        if name.lower() in existing_proj:
            for p in baseline.projects:
                if p.name.lower() == name.lower():
                    ai_desc = str(ai_proj.get("description") or "").strip()
                    if ai_desc and len(ai_desc) > len(p.description):
                        p.description = ai_desc
        else:
            tech = [t for t in (ai_proj.get("tech") or []) if isinstance(t, str)]
            proj = Project(name=name, description=str(ai_proj.get("description") or ""),
                           link="", tech="[]")
            proj.set_tech(tech)
            baseline.projects.append(proj)
            existing_proj.add(name.lower())

    existing_edu = {e.institution.lower() for e in baseline.education}
    for ai_edu in (ai_dict.get("education") or []):
        if not isinstance(ai_edu, dict):
            continue
        inst = str(ai_edu.get("institution") or "")
        if inst.lower() not in existing_edu:
            baseline.education.append(Education(
                institution=inst,
                degree=str(ai_edu.get("degree") or ""),
                field=str(ai_edu.get("field") or ""),
                start=str(ai_edu.get("start") or ""),
                end=str(ai_edu.get("end") or ""),
            ))
            existing_edu.add(inst.lower())

    existing_cert = {c.name.lower() for c in baseline.certifications}
    for ai_cert in (ai_dict.get("certifications") or []):
        if not isinstance(ai_cert, dict):
            continue
        name = str(ai_cert.get("name") or "")
        if name.lower() not in existing_cert:
            baseline.certifications.append(Certification(
                name=name,
                issuer=str(ai_cert.get("issuer") or ""),
                date=str(ai_cert.get("date") or ""),
            ))
            existing_cert.add(name.lower())

    return baseline


# ── Main parser ───────────────────────────────────────────────────────────────

@register("pdf")
class PdfParser:
    def parse(self, data: bytes) -> ParseResult:
        warnings: list[str] = [
            "PDF import is best-effort — please review and correct each section."
        ]

        tier_result, tier_warnings = _pick_tier(data)
        warnings.extend(tier_warnings)

        if not tier_result.text.strip():
            warnings.append("Could not extract any text from this PDF.")
            profile = Profile(full_name="")
            profile.skills = []
            profile.experience = []
            profile.projects = []
            profile.education = []
            profile.certifications = []
            profile.links = []
            return ParseResult(profile=profile, warnings=warnings)

        baseline = _heuristic_parse(
            words=tier_result.words,
            tables=tier_result.tables,
            text=tier_result.text,
        )

        if not baseline.full_name:
            warnings.append("Could not detect name — please fill in manually.")

        ai_dict = _ai_refine(tier_result.text)
        if ai_dict:
            baseline = _merge_ai(baseline, ai_dict)
            warnings.append("AI-assisted refinement applied — verify all sections.")
        else:
            logger.debug("AI refinement skipped or failed; using deterministic result.")

        return ParseResult(profile=baseline, warnings=warnings)
