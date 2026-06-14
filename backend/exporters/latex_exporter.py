import re
from exporters.base import Exporter
from exporters import register
from models import Profile


def _esc(s: str) -> str:
    """Escape LaTeX special characters."""
    if not s:
        return ""
    replacements = [
        ("\\", r"\textbackslash{}"),
        ("&", r"\&"), ("%", r"\%"), ("$", r"\$"), ("#", r"\#"),
        ("_", r"\_"), ("{", r"\{"), ("}", r"\}"),
        ("~", r"\textasciitilde{}"), ("^", r"\textasciicircum{}"),
    ]
    for old, new in replacements:
        s = s.replace(old, new)
    return s


@register("latex")
@register("tex")
class LatexExporter(Exporter):
    mime_type = "application/x-latex"
    extension = "tex"

    def export(self, profile: Profile) -> bytes:
        lines = [
            r"\documentclass[11pt,a4paper]{article}",
            r"\usepackage[margin=2cm]{geometry}",
            r"\usepackage{hyperref}",
            r"\usepackage{titlesec}",
            r"\usepackage{enumitem}",
            r"\usepackage{parskip}",
            r"\titleformat{\section}{\large\bfseries}{}{0em}{}[\titlerule]",
            r"\setlist[itemize]{leftmargin=*,noitemsep,topsep=2pt}",
            r"\hypersetup{colorlinks=true,urlcolor=blue}",
            r"\pagestyle{empty}",
            r"\begin{document}",
            "",
            r"{\LARGE\bfseries " + _esc(profile.full_name) + r"}\\[4pt]",
        ]

        contact_parts = list(filter(None, [
            profile.email and r"\href{mailto:" + profile.email + r"}{" + _esc(profile.email) + r"}",
            _esc(profile.phone) if profile.phone else None,
            _esc(profile.location) if profile.location else None,
        ]))
        if contact_parts:
            lines.append(" $|$ ".join(contact_parts) + r"\\")

        for lnk in (profile.links or []):
            lines.append(r"\href{" + lnk.url + r"}{" + _esc(lnk.label) + r"} ")
        lines.append("")

        if profile.summary:
            lines += [r"\section*{Summary}", _esc(profile.summary), ""]

        if profile.skills:
            lines.append(r"\section*{Skills}")
            lines.append(r"\begin{itemize}")
            for s in profile.skills:
                lines.append(r"  \item " + _esc(s.name) +
                             (f" ({_esc(s.category)})" if s.category else "") +
                             (f" --- {s.years} yrs" if s.years else ""))
            lines.append(r"\end{itemize}")
            lines.append("")

        if profile.experience:
            lines.append(r"\section*{Experience}")
            for e in profile.experience:
                lines.append(r"\textbf{" + _esc(e.role) + r"} \hfill " + _esc(e.company))
                lines.append(r"\textit{" + _esc(e.start) + r" -- " + _esc(e.end) + r"}" +
                             (r" \hfill \textit{" + _esc(e.location) + r"}" if e.location else ""))
                if e.bullets:
                    lines.append(r"\begin{itemize}")
                    for b in e.bullets:
                        lines.append(r"  \item " + _esc(b.text))
                    lines.append(r"\end{itemize}")
                lines.append("")

        if profile.projects:
            lines.append(r"\section*{Projects}")
            for p in profile.projects:
                link_part = (r" \href{" + p.link + r"}{[link]}" if p.link else "")
                lines.append(r"\textbf{" + _esc(p.name) + r"}" + link_part)
                if p.description:
                    lines.append(_esc(p.description))
                if p.get_tech():
                    lines.append(r"\textit{Tech: " + _esc(", ".join(p.get_tech())) + r"}")
                lines.append("")

        if profile.education:
            lines.append(r"\section*{Education}")
            for ed in profile.education:
                lines.append(r"\textbf{" + _esc(ed.degree) + " " + _esc(ed.field) + r"} \hfill " + _esc(ed.institution))
                lines.append(r"\textit{" + _esc(ed.start) + r" -- " + _esc(ed.end) + r"}")
                lines.append("")

        if profile.certifications:
            lines.append(r"\section*{Certifications}")
            lines.append(r"\begin{itemize}")
            for c in profile.certifications:
                lines.append(r"  \item \textbf{" + _esc(c.name) + r"} --- " + _esc(c.issuer) + " (" + _esc(c.date) + ")")
            lines.append(r"\end{itemize}")
            lines.append("")

        if profile.availability or profile.compensation:
            lines.append(r"\section*{Availability \& Compensation}")
            parts = []
            if profile.availability:
                parts.append("Available: " + _esc(profile.availability))
            if profile.compensation:
                parts.append("Compensation: " + _esc(profile.compensation))
            lines.append(" $|$ ".join(parts))
            lines.append("")

        lines.append(r"\end{document}")
        return "\n".join(lines).encode("utf-8")
