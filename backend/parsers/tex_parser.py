import re
from parsers.base import ParseResult
from parsers import register
from models import Profile, Skill, Experience, ExperienceBullet, Education, Project, Certification

@register("tex")
class TexParser:
    """Best-effort LaTeX resume parser using regex. Handles moderncv, deedy-resume, and custom formats."""

    def parse(self, data: bytes) -> ParseResult:
        text = data.decode("utf-8", errors="replace")
        warnings = ["LaTeX import is best-effort — please review and correct each section."]

        profile = Profile(full_name="")
        profile.skills = []
        profile.experience = []
        profile.projects = []
        profile.education = []
        profile.certifications = []
        profile.links = []

        # --- Name ---
        # Try \name{First}{Last} (moderncv), \name{Full Name}, \author{Name}
        m = re.search(r'\\name\{([^}]+)\}\{([^}]+)\}', text)
        if m:
            profile.full_name = f"{m.group(1).strip()} {m.group(2).strip()}"
        if not profile.full_name:
            m = re.search(r'\\(?:name|author|fullname)\{([^}]+)\}', text)
            if m:
                profile.full_name = m.group(1).strip()

        # --- Email ---
        m = re.search(r'\\(?:email|Email)\{([^}]+)\}', text)
        if m:
            profile.email = m.group(1).strip()
        if not profile.email:
            m = re.search(r'href\{mailto:([^}]+)\}', text)
            if m:
                profile.email = m.group(1).strip()
        if not profile.email:
            m = re.search(r'[\w.+-]+@[\w-]+\.\w+', text)
            if m:
                profile.email = m.group()

        # --- Phone ---
        m = re.search(r'\\(?:phone|mobile|Phone)\{([^}]+)\}', text)
        if m:
            profile.phone = m.group(1).strip()
        if not profile.phone:
            m = re.search(r'[\+\d][\d\s\-().]{7,}', text)
            if m:
                profile.phone = m.group().strip()

        # --- Location ---
        m = re.search(r'\\(?:address|location)\{([^}]+)\}(?:\{([^}]*)\})?', text)
        if m:
            parts = [p for p in [m.group(1), m.group(2)] if p]
            profile.location = ", ".join(parts)

        # --- Summary/Objective ---
        m = re.search(r'\\(?:summary|objective|quote)\{([^}]+)\}', text, re.DOTALL)
        if m:
            profile.summary = re.sub(r'\s+', ' ', m.group(1)).strip()

        # --- Skills ---
        # Look for \cvskill{name}{level} or \skill{name} or itemize under Skills section
        skill_section = re.search(
            r'\\section\{Skills?\}(.*?)(?:\\section|\\end\{document\})',
            text, re.DOTALL | re.IGNORECASE
        )
        if skill_section:
            skill_text = skill_section.group(1)
            # \cvskill{Python}{5} or \cvitem{Languages}{Python, C++}
            for m in re.finditer(r'\\cvskill\{([^}]+)\}\{([^}]*)\}', skill_text):
                profile.skills.append(Skill(name=m.group(1).strip()))
            for m in re.finditer(r'\\cvitem\{([^}]+)\}\{([^}]+)\}', skill_text):
                for skill in re.split(r'[,;]', m.group(2)):
                    name = skill.strip()
                    if name:
                        profile.skills.append(Skill(name=name, category=m.group(1).strip()))
            # plain \item entries
            if not profile.skills:
                for m in re.finditer(r'\\item\s+([^\n\\]+)', skill_text):
                    for skill in re.split(r'[,;]', m.group(1)):
                        name = re.sub(r'\{[^}]*\}', '', skill).strip()
                        if name:
                            profile.skills.append(Skill(name=name))

        # --- Experience ---
        exp_section = re.search(
            r'\\section\{(?:Experience|Work Experience|Employment)\}(.*?)(?:\\section|\\end\{document\})',
            text, re.DOTALL | re.IGNORECASE
        )
        if exp_section:
            exp_text = exp_section.group(1)
            # \cventry{dates}{role}{company}{location}{grade}{description}
            for m in re.finditer(
                r'\\cventry\{([^}]*)\}\{([^}]*)\}\{([^}]*)\}\{([^}]*)\}\{[^}]*\}\{([^}]*)\}',
                exp_text, re.DOTALL
            ):
                dates, role, company, location, desc = m.group(1), m.group(2), m.group(3), m.group(4), m.group(5)
                # parse start/end from dates like "2020--2022" or "Jan 2020 -- Present"
                date_parts = re.split(r'\s*--+\s*', dates)
                start = date_parts[0].strip() if date_parts else ""
                end = date_parts[1].strip() if len(date_parts) > 1 else ""
                exp = Experience(role=role.strip(), company=company.strip(),
                                 start=start, end=end, location=location.strip())
                exp.bullets = []
                for bullet in re.finditer(r'\\item\s+([^\n\\]+)', desc):
                    exp.bullets.append(ExperienceBullet(text=bullet.group(1).strip()))
                profile.experience.append(exp)

        # --- Education ---
        edu_section = re.search(
            r'\\section\{Education\}(.*?)(?:\\section|\\end\{document\})',
            text, re.DOTALL | re.IGNORECASE
        )
        if edu_section:
            edu_text = edu_section.group(1)
            for m in re.finditer(
                r'\\cventry\{([^}]*)\}\{([^}]*)\}\{([^}]*)\}\{[^}]*\}\{[^}]*\}\{[^}]*\}',
                edu_text
            ):
                dates, degree, institution = m.group(1), m.group(2), m.group(3)
                date_parts = re.split(r'\s*--+\s*', dates)
                start = date_parts[0].strip() if date_parts else ""
                end = date_parts[1].strip() if len(date_parts) > 1 else ""
                profile.education.append(Education(
                    institution=institution.strip(), degree=degree.strip(),
                    start=start, end=end
                ))

        # --- Projects ---
        proj_section = re.search(
            r'\\section\{Projects?\}(.*?)(?:\\section|\\end\{document\})',
            text, re.DOTALL | re.IGNORECASE
        )
        if proj_section:
            proj_text = proj_section.group(1)
            for m in re.finditer(r'\\cvitem\{([^}]+)\}\{([^}]+)\}', proj_text):
                profile.projects.append(Project(
                    name=m.group(1).strip(),
                    description=re.sub(r'\{[^}]*\}|\\[a-z]+', ' ', m.group(2)).strip()
                ))
            if not profile.projects:
                for m in re.finditer(r'\\item\s+([^\n\\]+)', proj_text):
                    name = re.sub(r'\{[^}]*\}|\\[a-z]+', ' ', m.group(1)).strip()
                    if name:
                        profile.projects.append(Project(name=name))

        if not profile.full_name:
            warnings.append("Could not extract name from LaTeX. Please edit manually.")

        return ParseResult(profile=profile, warnings=warnings)
