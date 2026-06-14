import xml.etree.ElementTree as ET
from parsers.base import ParseResult
from parsers import register
from models import (Profile, Skill, Experience, ExperienceBullet,
                    Project, Education, Certification, ContactLink)


def _t(el, tag, default=""):
    child = el.find(tag)
    return child.text if child is not None and child.text else default


@register("xml")
class XmlParser:
    def parse(self, data: bytes) -> ParseResult:
        root = ET.fromstring(data.decode())
        profile = Profile(
            full_name=_t(root, "full_name"),
            email=_t(root, "email"),
            phone=_t(root, "phone"),
            location=_t(root, "location"),
            summary=_t(root, "summary"),
            availability=_t(root, "availability"),
            compensation=_t(root, "compensation"),
        )
        profile.links = [ContactLink(label=_t(lnk, "label"), url=_t(lnk, "url"))
                         for lnk in root.findall("links/link")]
        profile.skills = [Skill(name=_t(s, "name"), category=_t(s, "category"),
                                years=float(_t(s, "years") or 0))
                          for s in root.findall("skills/skill")]
        profile.experience = []
        for job in root.findall("experience/job"):
            e = Experience(company=_t(job, "company"), role=_t(job, "role"),
                           start=_t(job, "start"), end=_t(job, "end"),
                           location=_t(job, "location"))
            e.bullets = [ExperienceBullet(text=b.text or "")
                         for b in job.findall("bullets/bullet")]
            profile.experience.append(e)
        profile.projects = []
        for proj in root.findall("projects/project"):
            p = Project(name=_t(proj, "name"), description=_t(proj, "description"),
                        link=_t(proj, "link"))
            p.set_tech([i.text or "" for i in proj.findall("tech/item")])
            profile.projects.append(p)
        profile.education = [
            Education(institution=_t(ed, "institution"), degree=_t(ed, "degree"),
                      field=_t(ed, "field"), start=_t(ed, "start"), end=_t(ed, "end"))
            for ed in root.findall("education/degree")
        ]
        profile.certifications = [
            Certification(name=_t(c, "name"), issuer=_t(c, "issuer"), date=_t(c, "date"))
            for c in root.findall("certifications/certification")
        ]
        return ParseResult(profile=profile)
