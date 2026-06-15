"""CRUD endpoints for profile sub-sections: skills, experience, bullets, projects, education, certifications."""
from fastapi import APIRouter, HTTPException
from sqlmodel import Session, select
from db import engine
from models import (
    Profile, Skill, Experience, ExperienceBullet,
    Project, Education, Certification
)
from services.activity import log_activity
from logger import get_logger
import json

logger = get_logger(__name__)
router = APIRouter(prefix="/profiles", tags=["sections"])


def _profile_or_404(session: Session, profile_id: int) -> Profile:
    p = session.get(Profile, profile_id)
    if not p:
        raise HTTPException(404, f"Profile {profile_id} not found")
    return p


# ──────────────────────────────────────────────
# SKILLS
# ──────────────────────────────────────────────

@router.post("/{profile_id}/skills", status_code=201)
def add_skill(profile_id: int, body: dict):
    with Session(engine) as s:
        _profile_or_404(s, profile_id)
        skill = Skill(
            profile_id=profile_id,
            name=body.get("name", ""),
            category=body.get("category", ""),
            years=float(body.get("years", 0) or 0),
        )
        s.add(skill)
        s.commit()
        s.refresh(skill)
        log_activity("patch", f"added skill '{skill.name}' to profile #{profile_id}", profile_id)
        return {"id": skill.id, "name": skill.name, "category": skill.category, "years": skill.years}


@router.patch("/{profile_id}/skills/{skill_id}")
def update_skill(profile_id: int, skill_id: int, body: dict):
    with Session(engine) as s:
        _profile_or_404(s, profile_id)
        skill = s.get(Skill, skill_id)
        if not skill or skill.profile_id != profile_id:
            raise HTTPException(404, "Skill not found")
        if "name" in body:
            skill.name = body["name"]
        if "category" in body:
            skill.category = body["category"]
        if "years" in body:
            skill.years = float(body["years"] or 0)
        s.add(skill)
        s.commit()
        s.refresh(skill)
        return {"id": skill.id, "name": skill.name, "category": skill.category, "years": skill.years}


@router.delete("/{profile_id}/skills/{skill_id}", status_code=204)
def delete_skill(profile_id: int, skill_id: int):
    with Session(engine) as s:
        _profile_or_404(s, profile_id)
        skill = s.get(Skill, skill_id)
        if not skill or skill.profile_id != profile_id:
            raise HTTPException(404, "Skill not found")
        s.delete(skill)
        s.commit()


# ──────────────────────────────────────────────
# EXPERIENCE
# ──────────────────────────────────────────────

def _exp_dict(e: Experience) -> dict:
    return {
        "id": e.id, "company": e.company, "role": e.role,
        "start": e.start, "end": e.end, "location": e.location,
        "bullets": [{"id": b.id, "text": b.text} for b in (e.bullets or [])],
    }


@router.post("/{profile_id}/experience", status_code=201)
def add_experience(profile_id: int, body: dict):
    with Session(engine) as s:
        _profile_or_404(s, profile_id)
        exp = Experience(
            profile_id=profile_id,
            company=body.get("company", ""),
            role=body.get("role", ""),
            start=body.get("start", ""),
            end=body.get("end", ""),
            location=body.get("location", ""),
        )
        s.add(exp)
        s.flush()
        for b in body.get("bullets", []):
            s.add(ExperienceBullet(experience_id=exp.id, text=b if isinstance(b, str) else b.get("text", "")))
        s.commit()
        s.refresh(exp)
        log_activity("patch", f"added experience '{exp.role}' to profile #{profile_id}", profile_id)
        return _exp_dict(exp)


@router.patch("/{profile_id}/experience/{exp_id}")
def update_experience(profile_id: int, exp_id: int, body: dict):
    with Session(engine) as s:
        _profile_or_404(s, profile_id)
        exp = s.get(Experience, exp_id)
        if not exp or exp.profile_id != profile_id:
            raise HTTPException(404, "Experience not found")
        for field in ("company", "role", "start", "end", "location"):
            if field in body:
                setattr(exp, field, body[field])
        s.add(exp)
        s.commit()
        s.refresh(exp)
        return _exp_dict(exp)


@router.delete("/{profile_id}/experience/{exp_id}", status_code=204)
def delete_experience(profile_id: int, exp_id: int):
    with Session(engine) as s:
        _profile_or_404(s, profile_id)
        exp = s.get(Experience, exp_id)
        if not exp or exp.profile_id != profile_id:
            raise HTTPException(404, "Experience not found")
        for b in list(exp.bullets or []):
            s.delete(b)
        s.delete(exp)
        s.commit()


# ──────────────────────────────────────────────
# EXPERIENCE BULLETS
# ──────────────────────────────────────────────

@router.post("/{profile_id}/experience/{exp_id}/bullets", status_code=201)
def add_bullet(profile_id: int, exp_id: int, body: dict):
    with Session(engine) as s:
        _profile_or_404(s, profile_id)
        exp = s.get(Experience, exp_id)
        if not exp or exp.profile_id != profile_id:
            raise HTTPException(404, "Experience not found")
        bullet = ExperienceBullet(experience_id=exp_id, text=body.get("text", ""))
        s.add(bullet)
        s.commit()
        s.refresh(bullet)
        return {"id": bullet.id, "text": bullet.text}


@router.patch("/{profile_id}/experience/{exp_id}/bullets/{bullet_id}")
def update_bullet(profile_id: int, exp_id: int, bullet_id: int, body: dict):
    with Session(engine) as s:
        _profile_or_404(s, profile_id)
        bullet = s.get(ExperienceBullet, bullet_id)
        if not bullet or bullet.experience_id != exp_id:
            raise HTTPException(404, "Bullet not found")
        bullet.text = body.get("text", bullet.text)
        s.add(bullet)
        s.commit()
        s.refresh(bullet)
        return {"id": bullet.id, "text": bullet.text}


@router.delete("/{profile_id}/experience/{exp_id}/bullets/{bullet_id}", status_code=204)
def delete_bullet(profile_id: int, exp_id: int, bullet_id: int):
    with Session(engine) as s:
        bullet = s.get(ExperienceBullet, bullet_id)
        if not bullet or bullet.experience_id != exp_id:
            raise HTTPException(404, "Bullet not found")
        s.delete(bullet)
        s.commit()


# ──────────────────────────────────────────────
# PROJECTS
# ──────────────────────────────────────────────

def _proj_dict(p: Project) -> dict:
    return {
        "id": p.id, "name": p.name, "description": p.description,
        "link": p.link, "tech": p.get_tech(),
    }


@router.post("/{profile_id}/projects", status_code=201)
def add_project(profile_id: int, body: dict):
    with Session(engine) as s:
        _profile_or_404(s, profile_id)
        proj = Project(
            profile_id=profile_id,
            name=body.get("name", ""),
            description=body.get("description", ""),
            link=body.get("link", ""),
        )
        proj.set_tech(body.get("tech", []))
        s.add(proj)
        s.commit()
        s.refresh(proj)
        log_activity("patch", f"added project '{proj.name}' to profile #{profile_id}", profile_id)
        return _proj_dict(proj)


@router.patch("/{profile_id}/projects/{proj_id}")
def update_project(profile_id: int, proj_id: int, body: dict):
    with Session(engine) as s:
        _profile_or_404(s, profile_id)
        proj = s.get(Project, proj_id)
        if not proj or proj.profile_id != profile_id:
            raise HTTPException(404, "Project not found")
        for field in ("name", "description", "link"):
            if field in body:
                setattr(proj, field, body[field])
        if "tech" in body:
            proj.set_tech(body["tech"])
        s.add(proj)
        s.commit()
        s.refresh(proj)
        return _proj_dict(proj)


@router.delete("/{profile_id}/projects/{proj_id}", status_code=204)
def delete_project(profile_id: int, proj_id: int):
    with Session(engine) as s:
        _profile_or_404(s, profile_id)
        proj = s.get(Project, proj_id)
        if not proj or proj.profile_id != profile_id:
            raise HTTPException(404, "Project not found")
        s.delete(proj)
        s.commit()


# ──────────────────────────────────────────────
# EDUCATION
# ──────────────────────────────────────────────

def _edu_dict(ed: Education) -> dict:
    return {
        "id": ed.id, "institution": ed.institution, "degree": ed.degree,
        "field": ed.field, "start": ed.start, "end": ed.end,
    }


@router.post("/{profile_id}/education", status_code=201)
def add_education(profile_id: int, body: dict):
    with Session(engine) as s:
        _profile_or_404(s, profile_id)
        ed = Education(
            profile_id=profile_id,
            institution=body.get("institution", ""),
            degree=body.get("degree", ""),
            field=body.get("field", ""),
            start=body.get("start", ""),
            end=body.get("end", ""),
        )
        s.add(ed)
        s.commit()
        s.refresh(ed)
        log_activity("patch", f"added education '{ed.institution}' to profile #{profile_id}", profile_id)
        return _edu_dict(ed)


@router.patch("/{profile_id}/education/{edu_id}")
def update_education(profile_id: int, edu_id: int, body: dict):
    with Session(engine) as s:
        _profile_or_404(s, profile_id)
        ed = s.get(Education, edu_id)
        if not ed or ed.profile_id != profile_id:
            raise HTTPException(404, "Education not found")
        for field in ("institution", "degree", "field", "start", "end"):
            if field in body:
                setattr(ed, field, body[field])
        s.add(ed)
        s.commit()
        s.refresh(ed)
        return _edu_dict(ed)


@router.delete("/{profile_id}/education/{edu_id}", status_code=204)
def delete_education(profile_id: int, edu_id: int):
    with Session(engine) as s:
        _profile_or_404(s, profile_id)
        ed = s.get(Education, edu_id)
        if not ed or ed.profile_id != profile_id:
            raise HTTPException(404, "Education not found")
        s.delete(ed)
        s.commit()


# ──────────────────────────────────────────────
# CERTIFICATIONS
# ──────────────────────────────────────────────

def _cert_dict(c: Certification) -> dict:
    return {"id": c.id, "name": c.name, "issuer": c.issuer, "date": c.date}


@router.post("/{profile_id}/certifications", status_code=201)
def add_certification(profile_id: int, body: dict):
    with Session(engine) as s:
        _profile_or_404(s, profile_id)
        cert = Certification(
            profile_id=profile_id,
            name=body.get("name", ""),
            issuer=body.get("issuer", ""),
            date=body.get("date", ""),
        )
        s.add(cert)
        s.commit()
        s.refresh(cert)
        log_activity("patch", f"added cert '{cert.name}' to profile #{profile_id}", profile_id)
        return _cert_dict(cert)


@router.patch("/{profile_id}/certifications/{cert_id}")
def update_certification(profile_id: int, cert_id: int, body: dict):
    with Session(engine) as s:
        _profile_or_404(s, profile_id)
        cert = s.get(Certification, cert_id)
        if not cert or cert.profile_id != profile_id:
            raise HTTPException(404, "Certification not found")
        for field in ("name", "issuer", "date"):
            if field in body:
                setattr(cert, field, body[field])
        s.add(cert)
        s.commit()
        s.refresh(cert)
        return _cert_dict(cert)


@router.delete("/{profile_id}/certifications/{cert_id}", status_code=204)
def delete_certification(profile_id: int, cert_id: int):
    with Session(engine) as s:
        _profile_or_404(s, profile_id)
        cert = s.get(Certification, cert_id)
        if not cert or cert.profile_id != profile_id:
            raise HTTPException(404, "Certification not found")
        s.delete(cert)
        s.commit()
