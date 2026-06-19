import db
from fastapi import APIRouter, HTTPException, Depends
from sqlmodel import Session, select
from typing import Optional
from models import (
    Profile, Skill, Experience, ExperienceBullet,
    Project, Education, Certification, ContactLink, User,
)
from logger import get_logger
from services.activity import log_activity
from routers.auth_utils import get_current_user, get_current_user_optional

logger = get_logger(__name__)
router = APIRouter(prefix="/profiles", tags=["profiles"])


def _get_or_404(session: Session, profile_id: int) -> Profile:
    profile = session.get(Profile, profile_id)
    if not profile:
        raise HTTPException(404, f"Profile {profile_id} not found")
    return profile


def _check_ownership(session: Session, profile: Profile, user: User) -> None:
    """Enforce ownership. Unclaimed profiles (user_id=NULL) are claimed by the first
    authenticated user who touches them, preventing the global-shared-bucket problem."""
    if profile.user_id is None:
        profile.user_id = user.id
        session.add(profile)
        session.commit()
        session.refresh(profile)
    elif profile.user_id != user.id:
        raise HTTPException(status_code=403, detail="Forbidden")


@router.get("")
def list_profiles(user: User = Depends(get_current_user)):
    with Session(db.engine) as session:
        profiles = session.exec(
            select(Profile).where(
                (Profile.user_id == user.id) | (Profile.user_id == None)  # noqa: E711
            )
        ).all()
        return [{"id": p.id, "full_name": p.full_name, "email": p.email} for p in profiles]


@router.get("/{profile_id}")
def get_profile(profile_id: int, user: Optional[User] = Depends(get_current_user_optional)):
    logger.info(f"GET profile {profile_id}")
    with Session(db.engine) as session:
        p = _get_or_404(session, profile_id)
        if user:
            _check_ownership(session, p, user)
        elif p.user_id is not None:
            raise HTTPException(status_code=403, detail="Forbidden")
        skills = list(p.skills or [])
        experience = list(p.experience or [])
        projects = list(p.projects or [])
        education = list(p.education or [])
        certifications = list(p.certifications or [])
        links = list(p.links or [])
        return {
            "id": p.id,
            "full_name": p.full_name,
            "email": p.email,
            "phone": p.phone,
            "location": p.location,
            "summary": p.summary,
            "availability": p.availability,
            "compensation": p.compensation,
            "skills": [
                {"id": s.id, "name": s.name, "category": s.category, "years": s.years}
                for s in skills
            ],
            "experience": [
                {
                    "id": e.id, "company": e.company, "role": e.role,
                    "start": e.start, "end": e.end, "location": e.location,
                    "bullets": [{"id": b.id, "text": b.text} for b in (e.bullets or [])],
                }
                for e in experience
            ],
            "projects": [
                {
                    "id": pr.id, "name": pr.name, "description": pr.description,
                    "link": pr.link, "tech": pr.get_tech(),
                }
                for pr in projects
            ],
            "education": [
                {
                    "id": ed.id, "institution": ed.institution, "degree": ed.degree,
                    "field": ed.field, "start": ed.start, "end": ed.end,
                }
                for ed in education
            ],
            "certifications": [
                {"id": c.id, "cert_id": c.cert_id, "name": c.name, "issuer": c.issuer, "date": c.date}
                for c in certifications
            ],
            "links": [{"id": lnk.id, "label": lnk.label, "url": lnk.url} for lnk in links],
        }


@router.patch("/{profile_id}")
def patch_profile(profile_id: int, body: dict, user: Optional[User] = Depends(get_current_user_optional)):
    ALLOWED = {"full_name", "email", "phone", "location", "summary", "availability", "compensation"}
    logger.info(f"PATCH profile {profile_id}: {list(body.keys())}")
    with Session(db.engine) as session:
        p = _get_or_404(session, profile_id)
        if user:
            _check_ownership(session, p, user)
        elif p.user_id is not None:
            raise HTTPException(status_code=403, detail="Forbidden")
        # else: unclaimed profile + no auth → allow edit
        for k, v in body.items():
            if k in ALLOWED:
                setattr(p, k, v)
        session.add(p)
        session.commit()
        session.refresh(p)
        log_activity("patch", f"profile #{profile_id} fields={list(body.keys())}", profile_id)
        return {"id": p.id, "full_name": p.full_name}


@router.delete("/{profile_id}", status_code=204)
def delete_profile(profile_id: int, user: User = Depends(get_current_user)):
    logger.info(f"DELETE profile {profile_id}")
    with Session(db.engine) as session:
        p = _get_or_404(session, profile_id)
        _check_ownership(session, p, user)
        session.delete(p)
        session.commit()
        log_activity("delete", f"profile #{profile_id}", profile_id)
