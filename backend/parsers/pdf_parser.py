import io, re
import pdfplumber
from parsers.base import ParseResult
from parsers import register
from models import Profile, Skill, Experience, ExperienceBullet, Education


# Section headers emitted by pdf_exporter in UPPERCASE
SECTION_KEYWORDS = {
    "summary": "summary",
    "skills": "skills",
    "experience": "experience",
    "education": "education",
    "projects": "projects",
    "certifications": "certifications",
    "availability": "meta",
    "compensation": "meta",
}

# em-dash U+2014 used by pdf_exporter between role and company
EM_DASH = "—"
# en-dash U+2013 used inside date ranges (2014–2018)
EN_DASH = "–"


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

        with pdfplumber.open(io.BytesIO(data)) as pdf:
            lines = []
            for page in pdf.pages:
                text = page.extract_text() or ""
                lines.extend(text.splitlines())

        lines = [line.strip() for line in lines if line.strip()]
        if not lines:
            warnings.append("Could not extract any text from PDF.")
            return ParseResult(profile=profile, warnings=warnings)

        # First non-empty line = name (heuristic)
        profile.full_name = lines[0]

        # email / phone from first 5 lines
        for line in lines[:5]:
            email_m = re.search(r"[\w.+-]+@[\w-]+\.\w+", line)
            phone_m = re.search(r"[\+\d][\d\s\-().]{6,}", line)
            if email_m:
                profile.email = email_m.group()
            if phone_m:
                profile.phone = phone_m.group().strip()

        current_section = None
        current_exp = None

        for line in lines[1:]:
            low = line.lower()
            # section header detection — headers are ALL CAPS single words/phrases
            matched_section = None
            for kw, sec in SECTION_KEYWORDS.items():
                # match lines that are exactly the keyword (uppercased) or start with it
                if low.strip(" —–:").startswith(kw):
                    matched_section = sec
                    break
            if matched_section:
                current_section = matched_section
                continue

            if current_section == "summary":
                profile.summary = (profile.summary + " " + line).strip()

            elif current_section == "skills":
                # PDF exporter format: "Python (6.0y)" or " • skill1 • skill2"
                # Handle bullet-separated list on one line
                if " • " in line or " • " in line:
                    sep = " • " if " • " in line else " • "
                    for item in line.split(sep):
                        item = item.strip()
                        if item:
                            m = re.match(r"(.+?)\s*\(([\d.]+)y\)", item)
                            if m:
                                profile.skills.append(Skill(name=m.group(1).strip(),
                                                            years=float(m.group(2))))
                            else:
                                profile.skills.append(Skill(name=item))
                else:
                    m = re.match(r"(.+?)\s*\(([\d.]+)y\)", line)
                    if m:
                        profile.skills.append(Skill(name=m.group(1).strip(),
                                                    years=float(m.group(2))))
                    elif line:
                        profile.skills.append(Skill(name=line))

            elif current_section == "experience":
                # "Role — Company" heading (em-dash)
                if EM_DASH in line and not line.startswith("(cid:"):
                    parts = line.split(EM_DASH, 1)
                    current_exp = Experience(role=parts[0].strip(),
                                             company=parts[1].strip(), start="", end="")
                    current_exp.bullets = []
                    profile.experience.append(current_exp)
                elif line.startswith("(cid:") and current_exp:
                    # bullet: "(cid:127) text..."
                    bullet_text = re.sub(r"^\(cid:\d+\)\s*", "", line).strip()
                    current_exp.bullets.append(ExperienceBullet(text=bullet_text))
                # date/location line — skip (not stored separately in model)

            elif current_section == "education":
                # "BSc Computer Science — MIT (2014–2018)"
                m = re.match(
                    r"(.+?)\s+(.+?)\s+" + re.escape(EM_DASH) + r"\s+(.+?)\s+\((.+?)" +
                    re.escape(EN_DASH) + r"(.+?)\)",
                    line
                )
                if m:
                    profile.education.append(Education(
                        degree=m.group(1), field=m.group(2), institution=m.group(3),
                        start=m.group(4), end=m.group(5)))

            elif current_section == "meta":
                # "Available: Immediate  |  Compensation: £90k+"
                if "|" in line:
                    parts = [p.strip() for p in line.split("|")]
                    for part in parts:
                        if "available" in part.lower():
                            profile.availability = part.split(":", 1)[-1].strip()
                        elif "compensation" in part.lower():
                            profile.compensation = part.split(":", 1)[-1].strip()

        return ParseResult(profile=profile, warnings=warnings)
