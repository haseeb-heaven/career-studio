import io, re
from docx import Document
from parsers.base import ParseResult
from parsers import register
from models import Profile, Skill, Experience, ExperienceBullet, Education, Project, Certification, ContactLink


_SECTION_MAP = {
    "summary": "summary", "professional summary": "summary", "career summary": "summary",
    "profile": "summary", "about": "summary", "objective": "summary",
    "skills": "skills", "technical skills": "skills", "core skills": "skills",
    "technologies": "skills", "tech stack": "skills", "tools": "skills",
    "experience": "experience", "work experience": "experience",
    "professional experience": "experience", "employment history": "experience",
    "education": "education", "academic background": "education",
    "projects": "projects", "personal projects": "projects",
    "certifications": "certifications", "certificates": "certifications",
    "awards": "certifications", "achievements": "certifications",
}


def _is_section_header(text: str) -> str | None:
    stripped = text.strip(" :–—_•\t").lower()
    if stripped in _SECTION_MAP:
        return _SECTION_MAP[stripped]
    for kw, sec in _SECTION_MAP.items():
        if stripped.startswith(kw) and len(stripped) <= len(kw) + 4:
            return sec
    return None


@register("docx")
@register("doc")
class DocxParser:
    """Best-effort DOCX -> Profile. Returns warnings for unresolved sections."""

    def parse(self, data: bytes) -> ParseResult:
        doc = Document(io.BytesIO(data))
        paragraphs = [(p.style.name, p.text.strip()) for p in doc.paragraphs if p.text.strip()]
        warnings = ["DOCX import is best-effort — please review and correct each section."]

        profile = Profile(full_name="")
        profile.skills = []
        profile.experience = []
        profile.projects = []
        profile.education = []
        profile.certifications = []
        profile.links = []

        current_section = None
        current_exp = None
        current_proj = None

        for style, text in paragraphs:
            is_heading = "Heading" in style or style == "Title"

            text_section = _is_section_header(text)
            if text_section:
                current_section = text_section
                current_exp = None
                current_proj = None
                continue

            if is_heading and not profile.full_name and not text_section:
                profile.full_name = text
                continue

            if current_section == "summary":
                profile.summary = (profile.summary + " " + text).strip()
            elif current_section == "skills":
                m = re.match(r"(.+?)\s*\((.+?)\)\s*—\s*([\d.]+)", text)
                if m:
                    profile.skills.append(Skill(name=m.group(1).strip(),
                                                category=m.group(2).strip(),
                                                years=float(m.group(3))))
                else:
                    for sep in (",", "|", "•", "·", ";"):
                        if sep in text:
                            for part in text.split(sep):
                                part = part.strip()
                                if 2 <= len(part) <= 60:
                                    profile.skills.append(Skill(name=part))
                            break
                    else:
                        if 2 <= len(text) <= 60:
                            profile.skills.append(Skill(name=text))
            elif current_section == "experience":
                if text.startswith("•"):
                    if current_exp:
                        current_exp.bullets.append(ExperienceBullet(text=text[1:].strip()))
                else:
                    for sep in (" — ", " – ", " - ", " | ", " @ "):
                        if sep in text:
                            parts = text.split(sep, 1)
                            role = parts[0].strip()
                            company = parts[1].strip()
                            current_exp = Experience(company=company, role=role, start="", end="")
                            current_exp.bullets = []
                            profile.experience.append(current_exp)
                            break
                    else:
                        current_exp = Experience(company="", role=text, start="", end="")
                        current_exp.bullets = []
                        profile.experience.append(current_exp)
            elif current_section == "education":
                m = re.match(r"(.+?)\s+(.+?)\s+—\s+(.+?)\s+\((.+?)–(.+?)\)", text)
                if m:
                    profile.education.append(Education(
                        degree=m.group(1), field=m.group(2), institution=m.group(3),
                        start=m.group(4), end=m.group(5)))
                else:
                    profile.education.append(Education(institution=text, degree="", field="", start="", end=""))
            elif current_section == "projects":
                if text.startswith("•"):
                    if current_proj:
                        current_proj.description = (current_proj.description + " " + text[1:].strip()).strip()
                else:
                    current_proj = Project(name=text, description="", link="", tech="[]")
                    current_proj.set_tech([])
                    profile.projects.append(current_proj)
            elif current_section == "certifications":
                clean = text.lstrip("•").strip()
                if clean:
                    profile.certifications.append(Certification(name=clean, issuer="", date=""))

        for _, text in paragraphs[:3]:
            email_m = re.search(r"[\w.+-]+@[\w-]+\.\w+", text)
            phone_m = re.search(r"[\+\d][\d\s\-().]{6,}", text)
            if email_m and not profile.email:
                profile.email = email_m.group()
            if phone_m and not profile.phone:
                profile.phone = phone_m.group().strip()
            url_m = re.search(r"https?://[^\s]+|linkedin\.com/[^\s]+|github\.com/[^\s]+", text, re.IGNORECASE)
            if url_m and not any(l.url == url_m.group() for l in profile.links):
                label = "LinkedIn" if "linkedin" in url_m.group().lower() else "GitHub" if "github" in url_m.group().lower() else "Web"
                profile.links.append(ContactLink(label=label, url=url_m.group()))

        return ParseResult(profile=profile, warnings=warnings)
