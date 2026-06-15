import json
from parsers.base import ParseResult
from parsers import register
from models import (Profile, Skill, Experience, ExperienceBullet,
                    Project, Education, Certification, ContactLink)


def _parse_experience_list(raw: list) -> list[Experience]:
    result = []
    for e in raw:
        if not isinstance(e, dict):
            continue
        exp = Experience(
            company=e.get("company", e.get("employer", "")),
            role=e.get("role", e.get("title", e.get("position", ""))),
            start=e.get("start", e.get("start_date", e.get("from", ""))),
            end=e.get("end", e.get("end_date", e.get("to", ""))),
            location=e.get("location", ""),
        )
        exp.bullets = [ExperienceBullet(text=b if isinstance(b, str) else b.get("text", ""))
                       for b in e.get("bullets", e.get("responsibilities", e.get("highlights", [])))]
        result.append(exp)
    return result


@register("json")
class JsonParser:
    def parse(self, data: bytes) -> ParseResult:
        warnings = []
        raw = json.loads(data.decode())

        # Case 1: root is a list — treat as experience array
        if isinstance(raw, list):
            warnings.append("JSON contains only an experience list — name and other fields left blank. Please fill in manually.")
            profile = Profile(full_name="Unknown")
            profile.links = []
            profile.skills = []
            profile.experience = _parse_experience_list(raw)
            profile.projects = []
            profile.education = []
            profile.certifications = []
            return ParseResult(profile=profile, warnings=warnings)

        # Case 2: dict — full or partial profile
        d = raw
        # flexible name field
        name = d.get("full_name") or d.get("name") or d.get("fullName") or ""
        if not name:
            warnings.append("No name found in JSON (expected 'full_name' or 'name'). Please edit manually.")
            name = "Unknown"

        profile = Profile(
            full_name=name,
            email=d.get("email", ""),
            phone=d.get("phone", ""),
            location=d.get("location", ""),
            summary=d.get("summary", d.get("about", d.get("objective", ""))),
            availability=d.get("availability", ""),
            compensation=d.get("compensation", ""),
        )

        profile.links = [
            ContactLink(label=l.get("label", l.get("type", "")), url=l.get("url", l.get("href", "")))
            for l in d.get("links", d.get("contact_links", []))
            if isinstance(l, dict)
        ]
        profile.skills = []
        for s in d.get("skills", []):
            if isinstance(s, str):
                profile.skills.append(Skill(name=s))
            elif isinstance(s, dict):
                profile.skills.append(Skill(
                    name=s.get("name", s.get("skill", "")),
                    category=s.get("category", s.get("type", "")),
                    years=float(s.get("years", s.get("experience_years", 0)) or 0),
                ))

        exp_raw = d.get("experience", d.get("work_experience", d.get("work", [])))
        profile.experience = _parse_experience_list(exp_raw) if isinstance(exp_raw, list) else []

        profile.projects = []
        for p in d.get("projects", []):
            if not isinstance(p, dict):
                continue
            proj = Project(
                name=p.get("name", p.get("title", "")),
                description=p.get("description", p.get("summary", "")),
                link=p.get("link", p.get("url", p.get("github", ""))),
            )
            tech = p.get("tech", p.get("technologies", p.get("stack", [])))
            proj.set_tech(tech if isinstance(tech, list) else [])
            profile.projects.append(proj)

        profile.education = [
            Education(
                institution=e.get("institution", e.get("school", e.get("university", ""))),
                degree=e.get("degree", e.get("qualification", "")),
                field=e.get("field", e.get("major", e.get("subject", ""))),
                start=e.get("start", e.get("start_date", e.get("from", ""))),
                end=e.get("end", e.get("end_date", e.get("to", e.get("graduation_year", "")))),
            )
            for e in d.get("education", []) if isinstance(e, dict)
        ]

        profile.certifications = [
            Certification(
                name=c.get("name", c.get("title", c.get("certification", ""))),
                issuer=c.get("issuer", c.get("issued_by", c.get("organization", ""))),
                date=c.get("date", c.get("issued_date", c.get("year", ""))),
            )
            for c in d.get("certifications", d.get("certificates", [])) if isinstance(c, dict)
        ]

        return ParseResult(profile=profile, warnings=warnings)
