import csv, io
from exporters.base import Exporter
from exporters import register
from models import Profile


@register("csv")
class CsvExporter(Exporter):
    mime_type = "text/csv"
    extension = "csv"

    def export(self, profile: Profile) -> bytes:
        output = io.StringIO()
        writer = csv.DictWriter(output, fieldnames=["section", "name", "value1", "value2", "value3", "value4", "category"])
        writer.writeheader()
        writer.writerow({"section": "contact", "name": "full_name", "value1": profile.full_name})
        writer.writerow({"section": "contact", "name": "email", "value1": profile.email})
        writer.writerow({"section": "contact", "name": "phone", "value1": profile.phone})
        writer.writerow({"section": "contact", "name": "location", "value1": profile.location})
        writer.writerow({"section": "summary", "name": "summary", "value1": profile.summary})
        for l in (profile.links or []):
            writer.writerow({"section": "link", "name": l.label, "value1": l.url})
        for s in (profile.skills or []):
            writer.writerow({"section": "skill", "name": s.name, "category": s.category,
                             "value1": str(s.years)})
        for e in (profile.experience or []):
            writer.writerow({"section": "experience", "name": e.company, "value1": e.role,
                             "value2": e.start, "value3": e.end, "value4": e.location})
            for b in (e.bullets or []):
                writer.writerow({"section": "experience_bullet", "name": e.company, "value1": b.text})
        for p in (profile.projects or []):
            writer.writerow({"section": "project", "name": p.name, "value1": p.description,
                             "value2": p.link, "value3": ",".join(p.get_tech())})
        for ed in (profile.education or []):
            writer.writerow({"section": "education", "name": ed.institution, "value1": ed.degree,
                             "value2": ed.field, "value3": ed.start, "value4": ed.end})
        for c in (profile.certifications or []):
            writer.writerow({"section": "certification", "name": c.name,
                             "value1": c.issuer, "value2": c.date})
        writer.writerow({"section": "meta", "name": "availability", "value1": profile.availability})
        writer.writerow({"section": "meta", "name": "compensation", "value1": profile.compensation})
        return output.getvalue().encode()
