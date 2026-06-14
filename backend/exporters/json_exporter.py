import json
from exporters.base import Exporter
from exporters import register
from models import Profile


@register("json")
class JsonExporter(Exporter):
    mime_type = "application/json"
    extension = "json"

    def export(self, profile: Profile) -> bytes:
        data = {
            "full_name": profile.full_name,
            "email": profile.email,
            "phone": profile.phone,
            "location": profile.location,
            "summary": profile.summary,
            "availability": profile.availability,
            "compensation": profile.compensation,
            "links": [{"label": l.label, "url": l.url} for l in (profile.links or [])],
            "skills": [{"name": s.name, "category": s.category, "years": s.years}
                       for s in (profile.skills or [])],
            "experience": [
                {
                    "company": e.company,
                    "role": e.role,
                    "start": e.start,
                    "end": e.end,
                    "location": e.location,
                    "bullets": [b.text for b in (e.bullets or [])],
                }
                for e in (profile.experience or [])
            ],
            "projects": [
                {"name": p.name, "description": p.description, "link": p.link, "tech": p.get_tech()}
                for p in (profile.projects or [])
            ],
            "education": [
                {"institution": e.institution, "degree": e.degree, "field": e.field,
                 "start": e.start, "end": e.end}
                for e in (profile.education or [])
            ],
            "certifications": [
                {"name": c.name, "issuer": c.issuer, "date": c.date}
                for c in (profile.certifications or [])
            ],
        }
        return json.dumps(data, indent=2, ensure_ascii=False).encode()
