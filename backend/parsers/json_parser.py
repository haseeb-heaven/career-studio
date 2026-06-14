import json
from parsers.base import ParseResult
from parsers import register
from models import (Profile, Skill, Experience, ExperienceBullet,
                    Project, Education, Certification, ContactLink)


@register("json")
class JsonParser:
    def parse(self, data: bytes) -> ParseResult:
        d = json.loads(data.decode())
        profile = Profile(
            full_name=d.get("full_name", ""),
            email=d.get("email", ""),
            phone=d.get("phone", ""),
            location=d.get("location", ""),
            summary=d.get("summary", ""),
            availability=d.get("availability", ""),
            compensation=d.get("compensation", ""),
        )
        profile.links = [ContactLink(label=l["label"], url=l["url"])
                         for l in d.get("links", [])]
        profile.skills = [Skill(name=s["name"], category=s.get("category", ""),
                                years=float(s.get("years", 0)))
                          for s in d.get("skills", [])]
        profile.experience = []
        for e in d.get("experience", []):
            exp = Experience(company=e["company"], role=e.get("role", ""),
                             start=e.get("start", ""), end=e.get("end", ""),
                             location=e.get("location", ""))
            exp.bullets = [ExperienceBullet(text=b) for b in e.get("bullets", [])]
            profile.experience.append(exp)
        profile.projects = []
        for p in d.get("projects", []):
            proj = Project(name=p["name"], description=p.get("description", ""),
                           link=p.get("link", ""))
            proj.set_tech(p.get("tech", []))
            profile.projects.append(proj)
        profile.education = [
            Education(institution=e["institution"], degree=e.get("degree", ""),
                      field=e.get("field", ""), start=e.get("start", ""), end=e.get("end", ""))
            for e in d.get("education", [])
        ]
        profile.certifications = [
            Certification(name=c["name"], issuer=c.get("issuer", ""), date=c.get("date", ""))
            for c in d.get("certifications", [])
        ]
        return ParseResult(profile=profile)
