import csv, io
from parsers.base import ParseResult
from parsers import register
from models import (Profile, Skill, Experience, ExperienceBullet,
                    Project, Education, Certification, ContactLink)

_CONTACT_FIELDS = {"full_name", "email", "phone", "location"}
_META_FIELDS = {"availability", "compensation"}


@register("csv")
class CsvParser:
    def parse(self, data: bytes) -> ParseResult:
        reader = csv.DictReader(io.StringIO(data.decode()))
        rows = list(reader)
        profile = Profile(full_name="")
        profile.skills = []
        profile.experience = []
        profile.projects = []
        profile.education = []
        profile.certifications = []
        profile.links = []

        exp_map: dict[str, Experience] = {}

        for row in rows:
            section = row.get("section", "")
            name = row.get("name", "")
            v1 = row.get("value1", "")
            v2 = row.get("value2", "")
            v3 = row.get("value3", "")
            v4 = row.get("value4", "")
            cat = row.get("category", "")

            if section == "contact" and name in _CONTACT_FIELDS:
                setattr(profile, name, v1)
            elif section == "link":
                profile.links.append(ContactLink(label=name, url=v1))
            elif section == "summary":
                profile.summary = v1
            elif section == "skill":
                profile.skills.append(Skill(name=name, category=cat,
                                            years=float(v1) if v1 else 0.0))
            elif section == "experience":
                e = Experience(company=name, role=v1, start=v2, end=v3, location=v4)
                e.bullets = []
                exp_map[name] = e
                profile.experience.append(e)
            elif section == "experience_bullet":
                if name in exp_map:
                    exp_map[name].bullets.append(ExperienceBullet(text=v1))
            elif section == "project":
                proj = Project(name=name, description=v1, link=v2)
                proj.set_tech([t.strip() for t in v3.split(",") if t.strip()] if v3 else [])
                profile.projects.append(proj)
            elif section == "education":
                profile.education.append(Education(institution=name, degree=v1,
                                                   field=v2, start=v3, end=v4))
            elif section == "certification":
                profile.certifications.append(Certification(name=name, issuer=v1, date=v2))
            elif section == "meta" and name in _META_FIELDS:
                setattr(profile, name, v1)

        return ParseResult(profile=profile)
