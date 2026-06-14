from exporters.base import Exporter
from exporters import register
from models import Profile


@register("html")
@register("portfolio")
class PortfolioExporter(Exporter):
    mime_type = "text/html"
    extension = "html"

    def export(self, profile: Profile) -> bytes:
        skills_html = ""
        if profile.skills:
            tags = "".join(
                f'<span class="tag">{s.name}</span>'
                for s in profile.skills
            )
            skills_html = f'<section><h2>Skills</h2><div class="tags">{tags}</div></section>'

        exp_html = ""
        if profile.experience:
            items = ""
            for e in profile.experience:
                bullets = "".join(f"<li>{b.text}</li>" for b in (e.bullets or []))
                items += f"""
                <div class="card">
                  <div class="card-header">
                    <strong>{e.role}</strong> — {e.company}
                    <span class="meta">{e.start} – {e.end}{(' · ' + e.location) if e.location else ''}</span>
                  </div>
                  {'<ul>' + bullets + '</ul>' if bullets else ''}
                </div>"""
            exp_html = f"<section><h2>Experience</h2>{items}</section>"

        proj_html = ""
        if profile.projects:
            items = ""
            for p in profile.projects:
                tech = "".join(f'<span class="tag">{t}</span>' for t in p.get_tech())
                link = f'<a href="{p.link}" target="_blank">View Project →</a>' if p.link else ""
                items += f"""
                <div class="card">
                  <div class="card-header"><strong>{p.name}</strong> {link}</div>
                  {f'<p>{p.description}</p>' if p.description else ''}
                  <div class="tags">{tech}</div>
                </div>"""
            proj_html = f"<section><h2>Projects</h2>{items}</section>"

        edu_html = ""
        if profile.education:
            items = "".join(
                f'<div class="card"><strong>{ed.degree} {ed.field}</strong> — {ed.institution} <span class="meta">({ed.start}–{ed.end})</span></div>'
                for ed in profile.education
            )
            edu_html = f"<section><h2>Education</h2>{items}</section>"

        cert_html = ""
        if profile.certifications:
            items = "".join(
                f'<div class="card">{c.name} — <em>{c.issuer}</em> ({c.date})</div>'
                for c in profile.certifications
            )
            cert_html = f"<section><h2>Certifications</h2>{items}</section>"

        links_html = "".join(
            f'<a href="{lnk.url}" target="_blank">{lnk.label}</a>'
            for lnk in (profile.links or [])
        )

        html = f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>{profile.full_name} — Portfolio</title>
<style>
  *{{box-sizing:border-box;margin:0;padding:0}}
  body{{font-family:system-ui,sans-serif;background:#f8fafc;color:#1e293b;line-height:1.6}}
  header{{background:linear-gradient(135deg,#1e3a8a,#3b82f6);color:white;padding:3rem 2rem;text-align:center}}
  header h1{{font-size:2.5rem;margin-bottom:.5rem}}
  header .contact{{opacity:.85;font-size:.95rem}}
  header .links{{margin-top:1rem;display:flex;justify-content:center;gap:1rem;flex-wrap:wrap}}
  header .links a{{color:#bfdbfe;text-decoration:none;border:1px solid #93c5fd;padding:.25rem .75rem;border-radius:999px;font-size:.85rem}}
  header .links a:hover{{background:rgba(255,255,255,.1)}}
  main{{max-width:860px;margin:2rem auto;padding:0 1rem}}
  section{{margin-bottom:2.5rem}}
  h2{{font-size:1.2rem;font-weight:700;color:#1e3a8a;border-bottom:2px solid #e2e8f0;padding-bottom:.4rem;margin-bottom:1rem;text-transform:uppercase;letter-spacing:.05em}}
  .card{{background:white;border:1px solid #e2e8f0;border-radius:12px;padding:1.25rem;margin-bottom:.75rem}}
  .card-header{{display:flex;justify-content:space-between;align-items:baseline;flex-wrap:wrap;gap:.5rem;margin-bottom:.5rem}}
  .meta{{font-size:.85rem;color:#64748b}}
  .tags{{display:flex;flex-wrap:wrap;gap:.4rem;margin-top:.5rem}}
  .tag{{background:#dbeafe;color:#1e40af;padding:.2rem .65rem;border-radius:999px;font-size:.8rem;font-weight:500}}
  ul{{padding-left:1.25rem;margin-top:.5rem}}
  li{{margin-bottom:.25rem;font-size:.95rem;color:#374151}}
  .summary{{background:white;border-left:4px solid #3b82f6;padding:1.25rem;border-radius:0 12px 12px 0;color:#374151;font-size:1rem}}
  p{{margin-top:.5rem;color:#475569;font-size:.95rem}}
  footer{{text-align:center;padding:2rem;color:#94a3b8;font-size:.85rem}}
  a{{color:#3b82f6}}
</style>
</head>
<body>
<header>
  <h1>{profile.full_name}</h1>
  <div class="contact">{' · '.join(filter(None,[profile.email,profile.phone,profile.location]))}</div>
  <div class="links">{links_html}</div>
</header>
<main>
  {f'<section><div class="summary">{profile.summary}</div></section>' if profile.summary else ''}
  {skills_html}
  {exp_html}
  {proj_html}
  {edu_html}
  {cert_html}
</main>
<footer>Generated by Career Studio · {profile.full_name}</footer>
</body>
</html>"""
        return html.encode("utf-8")
