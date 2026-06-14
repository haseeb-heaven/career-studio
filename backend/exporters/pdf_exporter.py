import io
from reportlab.lib.pagesizes import letter
from reportlab.lib import colors
from reportlab.lib.units import inch
from reportlab.lib.styles import ParagraphStyle
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, HRFlowable
from exporters.base import Exporter
from exporters import register
from models import Profile

BLUE = colors.HexColor('#1e3a8a')
MID = colors.HexColor('#475569')
DARK = colors.HexColor('#0f172a')


def _styles():
    # Prefix names with "cs-" to avoid colliding with ReportLab's global style registry
    # on repeated calls within the same process.
    return {
        'name':      ParagraphStyle('cs-name', fontName='Helvetica-Bold', fontSize=20,
                                    textColor=BLUE, spaceAfter=2),
        'contact':   ParagraphStyle('cs-contact', fontName='Helvetica', fontSize=9,
                                    textColor=MID, spaceAfter=6),
        'section':   ParagraphStyle('cs-section', fontName='Helvetica-Bold', fontSize=10,
                                    textColor=BLUE, spaceBefore=10, spaceAfter=4,
                                    textTransform='uppercase'),
        'body':      ParagraphStyle('cs-body', fontName='Helvetica', fontSize=9,
                                    textColor=DARK, leading=14, spaceAfter=3),
        'bullet':    ParagraphStyle('cs-bullet', fontName='Helvetica', fontSize=9,
                                    textColor=DARK, leading=13, leftIndent=14, spaceAfter=2),
        'job_title': ParagraphStyle('cs-job_title', fontName='Helvetica-Bold', fontSize=10,
                                    textColor=DARK),
        'job_meta':  ParagraphStyle('cs-job_meta', fontName='Helvetica-Oblique', fontSize=8.5,
                                    textColor=MID, spaceAfter=2),
    }


@register("pdf")
class PdfExporter(Exporter):
    mime_type = "application/pdf"
    extension = "pdf"

    def export(self, profile: Profile) -> bytes:
        buf = io.BytesIO()
        doc = SimpleDocTemplate(buf, pagesize=letter,
                                leftMargin=0.75*inch, rightMargin=0.75*inch,
                                topMargin=0.75*inch, bottomMargin=0.75*inch)
        st = _styles()
        story = []

        story.append(Paragraph(profile.full_name, st['name']))
        contact = " | ".join(filter(None, [profile.email, profile.phone, profile.location]))
        story.append(Paragraph(contact, st['contact']))

        def section(title):
            story.append(HRFlowable(width="100%", thickness=1, color=BLUE, spaceAfter=4))
            story.append(Paragraph(title, st['section']))

        if profile.summary:
            section("Summary")
            story.append(Paragraph(profile.summary, st['body']))

        if profile.skills:
            section("Skills")
            skill_text = " • ".join(f"{s.name} ({s.years}y)" for s in profile.skills)
            story.append(Paragraph(skill_text, st['body']))

        if profile.experience:
            section("Experience")
            for e in profile.experience:
                story.append(Paragraph(f"{e.role} — {e.company}", st['job_title']))
                story.append(Paragraph(f"{e.start} – {e.end}  {e.location}".strip(), st['job_meta']))
                for b in (e.bullets or []):
                    story.append(Paragraph(f"• {b.text}", st['bullet']))
                story.append(Spacer(1, 4))

        if profile.projects:
            section("Projects")
            for p in profile.projects:
                story.append(Paragraph(p.name, st['job_title']))
                if p.description:
                    story.append(Paragraph(p.description, st['body']))
                if p.get_tech():
                    story.append(Paragraph("Tech: " + ", ".join(p.get_tech()), st['body']))
                story.append(Spacer(1, 4))

        if profile.education:
            section("Education")
            for ed in profile.education:
                story.append(Paragraph(
                    f"{ed.degree} {ed.field} — {ed.institution} ({ed.start}–{ed.end})",
                    st['body']))

        if profile.certifications:
            section("Certifications")
            for c in profile.certifications:
                story.append(Paragraph(f"• {c.name} — {c.issuer} ({c.date})", st['bullet']))

        if profile.availability or profile.compensation:
            section("Availability & Compensation")
            story.append(Paragraph(
                f"Available: {profile.availability}  |  Compensation: {profile.compensation}",
                st['body']))

        doc.build(story)
        return buf.getvalue()
