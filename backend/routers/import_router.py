import os
import db
from fastapi import APIRouter, UploadFile, HTTPException
from sqlmodel import Session
from sqlalchemy.orm import make_transient
from parsers import parser_for
from models import Profile, Skill, Experience, ExperienceBullet, Project, Education, Certification, ContactLink

router = APIRouter(tags=["import"])


def _persist(session: Session, profile: Profile) -> Profile:
    """Persist a parsed (transient) Profile with all its children manually."""
    # Snapshot children before clearing relationships
    skills_data = [
        {"name": s.name, "category": s.category, "years": s.years}
        for s in (profile.skills or [])
    ]
    exp_data = [
        {
            "company": e.company, "role": e.role, "start": e.start,
            "end": e.end, "location": e.location,
            "bullets": [b.text for b in (e.bullets or [])],
        }
        for e in (profile.experience or [])
    ]
    proj_data = [
        {"name": p.name, "description": p.description, "link": p.link, "tech": p.tech}
        for p in (profile.projects or [])
    ]
    edu_data = [
        {"institution": ed.institution, "degree": ed.degree, "field": ed.field,
         "start": ed.start, "end": ed.end}
        for ed in (profile.education or [])
    ]
    cert_data = [
        {"name": c.name, "issuer": c.issuer, "date": c.date}
        for c in (profile.certifications or [])
    ]
    link_data = [
        {"label": lnk.label, "url": lnk.url}
        for lnk in (profile.links or [])
    ]

    # Insert only the profile row first
    bare = Profile(
        full_name=profile.full_name,
        email=profile.email,
        phone=profile.phone,
        location=profile.location,
        summary=profile.summary,
        availability=profile.availability,
        compensation=profile.compensation,
    )
    session.add(bare)
    session.flush()  # assigns bare.id
    pid = bare.id

    for s in skills_data:
        session.add(Skill(profile_id=pid, **s))

    for e in exp_data:
        bullets_text = e.pop("bullets")
        exp_row = Experience(profile_id=pid, **e)
        session.add(exp_row)
        session.flush()
        for text in bullets_text:
            session.add(ExperienceBullet(experience_id=exp_row.id, text=text))

    for p in proj_data:
        session.add(Project(profile_id=pid, **p))

    for ed in edu_data:
        session.add(Education(profile_id=pid, **ed))

    for c in cert_data:
        session.add(Certification(profile_id=pid, **c))

    for lnk in link_data:
        session.add(ContactLink(profile_id=pid, **lnk))

    session.commit()
    session.refresh(bare)
    return bare


@router.post("/import", status_code=201)
async def import_file(file: UploadFile):
    filename = file.filename or ""
    ext = os.path.splitext(filename)[-1].lstrip(".").lower()
    if not ext:
        raise HTTPException(400, "Cannot determine file extension")
    try:
        parser = parser_for(ext)
    except ValueError:
        raise HTTPException(400, f"Unsupported file type: {ext}")

    data = await file.read()
    result = parser.parse(data)

    with Session(db.engine) as session:
        profile = _persist(session, result.profile)
        return {"profile_id": profile.id, "warnings": result.warnings}
