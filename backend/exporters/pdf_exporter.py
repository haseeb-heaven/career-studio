"""PDF exporter using fpdf2 — Unicode-capable, no global style registry."""
from pathlib import Path

from fpdf import FPDF

from exporters.base import Exporter
from exporters import register
from logger import get_logger
from models import Profile

logger = get_logger(__name__)

_FONTS_DIR = Path(__file__).parent.parent / "assets" / "fonts"
_FONT_REGULAR = _FONTS_DIR / "DejaVuSans.ttf"
_FONT_BOLD = _FONTS_DIR / "DejaVuSans-Bold.ttf"

_BLUE = (30, 58, 138)
_SLATE = (71, 85, 105)
_DARK = (15, 23, 42)


def _load_fonts(pdf: FPDF) -> None:
    if not _FONT_REGULAR.exists():
        raise FileNotFoundError(
            f"Required font not found: {_FONT_REGULAR}. "
            "Run the font setup step in the deployment guide."
        )
    if not _FONT_BOLD.exists():
        raise FileNotFoundError(
            f"Required font not found: {_FONT_BOLD}. "
            "Run the font setup step in the deployment guide."
        )
    pdf.add_font("DejaVu", style="", fname=str(_FONT_REGULAR))
    pdf.add_font("DejaVu", style="B", fname=str(_FONT_BOLD))


@register("pdf")
class PdfExporter(Exporter):
    mime_type = "application/pdf"
    extension = "pdf"

    def export(self, profile: Profile) -> bytes:
        pdf = FPDF()
        pdf.set_auto_page_break(auto=True, margin=19)
        pdf.add_page()
        pdf.set_margins(19, 19, 19)
        _load_fonts(pdf)

        # ── Name ──────────────────────────────────────────────────────────────
        pdf.set_font("DejaVu", style="B", size=20)
        pdf.set_text_color(*_BLUE)
        pdf.cell(0, 10, profile.full_name, new_x="LMARGIN", new_y="NEXT")

        # ── Contact line ──────────────────────────────────────────────────────
        contact_parts = [x for x in [profile.email, profile.phone, profile.location] if x]
        if contact_parts:
            pdf.set_font("DejaVu", size=9)
            pdf.set_text_color(*_SLATE)
            pdf.multi_cell(0, 6, " | ".join(contact_parts), new_x="LMARGIN", new_y="NEXT")
        pdf.ln(2)

        if profile.summary:
            self._section_title(pdf, "Summary")
            self._body_line(pdf, profile.summary)

        if profile.skills:
            self._section_title(pdf, "Skills")
            skill_text = " • ".join(
                f"{s.name} ({s.years}y)" if s.years else s.name
                for s in profile.skills
            )
            self._body_line(pdf, skill_text)

        if profile.experience:
            self._section_title(pdf, "Experience")
            for e in profile.experience:
                pdf.set_font("DejaVu", style="B", size=10)
                pdf.set_text_color(*_DARK)
                role_company_parts = [p for p in [e.role, e.company] if p]
                pdf.multi_cell(0, 7, " — ".join(role_company_parts), new_x="LMARGIN", new_y="NEXT")
                date_parts = [p for p in [e.start, e.end] if p]
                meta_str = " – ".join(date_parts)
                if e.location:
                    meta_str = (meta_str + "  " + e.location).strip()
                if meta_str:
                    self._job_meta(pdf, meta_str)
                for b in (e.bullets or []):
                    self._bullet(pdf, b.text)
                pdf.ln(2)

        if profile.projects:
            self._section_title(pdf, "Projects")
            for p in profile.projects:
                pdf.set_font("DejaVu", style="B", size=10)
                pdf.set_text_color(*_DARK)
                pdf.multi_cell(0, 7, p.name, new_x="LMARGIN", new_y="NEXT")
                if p.description:
                    self._body_line(pdf, p.description)
                tech = p.get_tech()
                if tech:
                    self._body_line(pdf, "Tech: " + ", ".join(tech))
                pdf.ln(2)

        if profile.education:
            self._section_title(pdf, "Education")
            for ed in profile.education:
                degree_field = " ".join(p for p in [ed.degree, ed.field] if p)
                dates = "–".join(p for p in [ed.start, ed.end] if p)
                institution_dates = ed.institution or ""
                if dates:
                    institution_dates = f"{institution_dates} ({dates})" if institution_dates else dates
                parts = [p for p in [degree_field, institution_dates] if p]
                self._body_line(pdf, " — ".join(parts))

        if profile.certifications:
            self._section_title(pdf, "Certifications")
            for c in profile.certifications:
                cert_parts = [p for p in [c.name, c.issuer] if p]
                cert_line = " — ".join(cert_parts)
                if c.date:
                    cert_line = f"{cert_line} ({c.date})" if cert_line else c.date
                if cert_line:
                    self._bullet(pdf, cert_line)

        if profile.availability or profile.compensation:
            self._section_title(pdf, "Availability & Compensation")
            parts = []
            if profile.availability:
                parts.append(f"Available: {profile.availability}")
            if profile.compensation:
                parts.append(f"Compensation: {profile.compensation}")
            self._body_line(pdf, "  |  ".join(parts))

        return bytes(pdf.output())

    def _section_title(self, pdf: FPDF, title: str) -> None:
        pdf.set_draw_color(*_BLUE)
        pdf.set_line_width(0.4)
        pdf.line(pdf.l_margin, pdf.get_y(), pdf.w - pdf.r_margin, pdf.get_y())
        pdf.ln(1)
        pdf.set_font("DejaVu", style="B", size=10)
        pdf.set_text_color(*_BLUE)
        pdf.cell(0, 7, title.upper(), new_x="LMARGIN", new_y="NEXT")

    def _body_line(self, pdf: FPDF, text: str) -> None:
        pdf.set_font("DejaVu", size=9)
        pdf.set_text_color(*_DARK)
        pdf.multi_cell(0, 6, text, new_x="LMARGIN", new_y="NEXT")
        pdf.ln(1)

    def _bullet(self, pdf: FPDF, text: str) -> None:
        pdf.set_font("DejaVu", size=9)
        pdf.set_text_color(*_DARK)
        pdf.set_x(pdf.l_margin + 5)
        pdf.multi_cell(0, 6, f"• {text}", new_x="LMARGIN", new_y="NEXT")
        pdf.ln(0.5)

    def _job_meta(self, pdf: FPDF, text: str) -> None:
        if not text.strip():
            return
        pdf.set_font("DejaVu", style="", size=8)
        pdf.set_text_color(*_SLATE)
        pdf.multi_cell(0, 5, text, new_x="LMARGIN", new_y="NEXT")
        pdf.ln(1)
