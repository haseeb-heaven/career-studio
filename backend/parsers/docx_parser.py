import io, re
from docx import Document
from parsers.base import ParseResult
from parsers import register
from models import Profile, Skill, Experience, ExperienceBullet, Education


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

        for style, text in paragraphs:
            lower = text.lower()
            # heading detection
            if "Heading 1" in style or style == "Title":
                if not profile.full_name and not any(kw in lower for kw in
                        ["summary", "skill", "experience", "education", "project", "cert",
                         "availability", "compensation"]):
                    profile.full_name = text
                elif "summary" in lower:
                    current_section = "summary"
                elif "skill" in lower:
                    current_section = "skills"
                elif "experience" in lower:
                    current_section = "experience"
                elif "education" in lower:
                    current_section = "education"
                elif "project" in lower:
                    current_section = "projects"
                elif "cert" in lower:
                    current_section = "certifications"
                elif "availability" in lower or "compensation" in lower:
                    current_section = "meta"
            elif "Heading 2" in style and current_section == "experience":
                parts = text.split("—")
                role = parts[0].strip() if parts else text
                company = parts[1].strip() if len(parts) > 1 else ""
                current_exp = Experience(company=company, role=role, start="", end="")
                current_exp.bullets = []
                profile.experience.append(current_exp)
            elif current_section == "summary":
                profile.summary = (profile.summary + " " + text).strip()
            elif current_section == "skills":
                # "Python (Language) — 6 yrs" format from our exporter
                m = re.match(r"(.+?)\s*\((.+?)\)\s*—\s*([\d.]+)", text)
                if m:
                    profile.skills.append(Skill(name=m.group(1).strip(),
                                                category=m.group(2).strip(),
                                                years=float(m.group(3))))
                else:
                    profile.skills.append(Skill(name=text))
            elif current_section == "experience" and current_exp:
                if text.startswith("•"):
                    current_exp.bullets.append(ExperienceBullet(text=text[1:].strip()))
            elif current_section == "education":
                m = re.match(r"(.+?)\s+(.+?)\s+—\s+(.+?)\s+\((.+?)–(.+?)\)", text)
                if m:
                    profile.education.append(Education(
                        degree=m.group(1), field=m.group(2), institution=m.group(3),
                        start=m.group(4), end=m.group(5)))
            elif current_section == "meta":
                if "|" in text:
                    parts = [p.strip() for p in text.split("|")]
                    for part in parts:
                        if "available" in part.lower():
                            profile.availability = part.split(":")[-1].strip()
                        elif "compensation" in part.lower():
                            profile.compensation = part.split(":")[-1].strip()

        # extract email/phone from second paragraph (contact line)
        for _, text in paragraphs[1:3]:
            email_m = re.search(r"[\w.+-]+@[\w-]+\.\w+", text)
            phone_m = re.search(r"[\+\d][\d\s\-().]{6,}", text)
            if email_m:
                profile.email = email_m.group()
            if phone_m:
                profile.phone = phone_m.group().strip()

        return ParseResult(profile=profile, warnings=warnings)
