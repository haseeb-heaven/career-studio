import xml.etree.ElementTree as ET
from exporters.base import Exporter
from exporters import register
from models import Profile


def _sub(parent, tag, text=""):
    el = ET.SubElement(parent, tag)
    el.text = str(text) if text is not None else ""
    return el


@register("xml")
class XmlExporter(Exporter):
    mime_type = "application/xml"
    extension = "xml"

    def export(self, profile: Profile) -> bytes:
        root = ET.Element("profile")
        _sub(root, "full_name", profile.full_name)
        _sub(root, "email", profile.email)
        _sub(root, "phone", profile.phone)
        _sub(root, "location", profile.location)
        _sub(root, "summary", profile.summary)
        _sub(root, "availability", profile.availability)
        _sub(root, "compensation", profile.compensation)

        links_el = ET.SubElement(root, "links")
        for lnk in (profile.links or []):
            le = ET.SubElement(links_el, "link")
            _sub(le, "label", lnk.label)
            _sub(le, "url", lnk.url)

        skills_el = ET.SubElement(root, "skills")
        for s in (profile.skills or []):
            se = ET.SubElement(skills_el, "skill")
            _sub(se, "name", s.name)
            _sub(se, "category", s.category)
            _sub(se, "years", s.years)

        exp_el = ET.SubElement(root, "experience")
        for e in (profile.experience or []):
            ee = ET.SubElement(exp_el, "job")
            _sub(ee, "company", e.company)
            _sub(ee, "role", e.role)
            _sub(ee, "start", e.start)
            _sub(ee, "end", e.end)
            _sub(ee, "location", e.location)
            bullets_el = ET.SubElement(ee, "bullets")
            for b in (e.bullets or []):
                _sub(bullets_el, "bullet", b.text)

        projects_el = ET.SubElement(root, "projects")
        for p in (profile.projects or []):
            pe = ET.SubElement(projects_el, "project")
            _sub(pe, "name", p.name)
            _sub(pe, "description", p.description)
            _sub(pe, "link", p.link)
            tech_el = ET.SubElement(pe, "tech")
            for t in p.get_tech():
                _sub(tech_el, "item", t)

        edu_el = ET.SubElement(root, "education")
        for ed in (profile.education or []):
            ede = ET.SubElement(edu_el, "degree")
            _sub(ede, "institution", ed.institution)
            _sub(ede, "degree", ed.degree)
            _sub(ede, "field", ed.field)
            _sub(ede, "start", ed.start)
            _sub(ede, "end", ed.end)

        certs_el = ET.SubElement(root, "certifications")
        for c in (profile.certifications or []):
            ce = ET.SubElement(certs_el, "certification")
            _sub(ce, "name", c.name)
            _sub(ce, "issuer", c.issuer)
            _sub(ce, "date", c.date)

        ET.indent(root)
        return ET.tostring(root, encoding="unicode", xml_declaration=False).encode()
