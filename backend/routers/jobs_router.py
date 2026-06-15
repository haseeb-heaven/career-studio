"""Job matching — RemoteOK + Arbeitnow (free, no auth) + Adzuna (optional)."""
import json
import urllib.request
import urllib.parse
from fastapi import APIRouter, HTTPException, Query
from sqlmodel import Session, select
from db import engine
from models import Profile, JobMatch, Settings
from services import activity
from logger import get_logger

logger = get_logger(__name__)
router = APIRouter(prefix="/profiles", tags=["jobs"])

_BROWSER_UA = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/120.0.0.0 Safari/537.36"
)


def _build_keywords(profile: Profile) -> str:
    """Build a targeted job search query from profile skills and roles."""
    # Collect top skill names (up to 6, prefer longer/specific ones)
    skills = sorted(
        [s.name for s in (profile.skills or []) if s.name],
        key=lambda x: -len(x)
    )[:6]

    # Most recent/relevant role
    roles = [e.role for e in (profile.experience or []) if e.role]
    role = roles[0] if roles else ""

    # Build query: role first, then top skills
    parts = []
    if role:
        parts.append(role)
    # Add top 4 skills that aren't substrings of role
    for s in skills:
        if not any(s.lower() in p.lower() for p in parts):
            parts.append(s)
        if len(parts) >= 5:
            break

    query = " ".join(dict.fromkeys(parts))[:120].strip()
    if not query:
        query = profile.summary[:80].strip() if profile.summary else "software developer"
    return query


def _match_score(job_title: str, job_desc: str, skill_names: list[str], query: str) -> float:
    """Score 0–100 based on how well job matches the profile skills and query."""
    if not skill_names and not query:
        return 0.0

    score = 0.0
    title_lower = job_title.lower()
    desc_lower = job_desc.lower()

    # Title match (weighted 50%)
    query_words = [w for w in query.lower().split() if len(w) > 2]
    title_hits = sum(1 for w in query_words if w in title_lower)
    if query_words:
        score += (title_hits / len(query_words)) * 50

    # Skills in description (weighted 50%)
    if skill_names:
        skill_hits = sum(1 for s in skill_names if s.lower() in desc_lower)
        score += (skill_hits / len(skill_names)) * 50

    return round(min(100.0, score), 1)




@router.get("/{profile_id}/jobs")
def search_jobs(profile_id: int, limit: int = Query(default=20, le=50)):
    with Session(engine) as s:
        p = s.get(Profile, profile_id)
        if not p:
            raise HTTPException(status_code=404, detail="Profile not found")
        s.refresh(p)
        skill_names = [sk.name for sk in (p.skills or [])]
        query = _build_keywords(p)
        cfg = s.exec(select(Settings)).first() or Settings()
        adzuna_id = cfg.adzuna_app_id or ""
        adzuna_key = cfg.adzuna_app_key or ""

    logger.info("Job search for profile %d: %r", profile_id, query)

    third = max(1, limit // 3)
    half = max(1, limit // 2)

    arbeitnow_jobs = _fetch_arbeitnow(query, half)
    remoteok_jobs = _fetch_remoteok(query, third)
    remotive_jobs = _fetch_remotive(query, third)
    adzuna_jobs = _fetch_adzuna(query, third, adzuna_id, adzuna_key)

    all_jobs = arbeitnow_jobs + remoteok_jobs + remotive_jobs + adzuna_jobs

    with Session(engine) as s:
        old = s.exec(select(JobMatch).where(JobMatch.profile_id == profile_id)).all()
        for o in old:
            s.delete(o)
        s.commit()

        for j in all_jobs:
            score = _match_score(j["title"], j["description"], skill_names, query)
            s.add(JobMatch(
                profile_id=profile_id,
                title=j["title"],
                company=j["company"],
                location=j["location"],
                url=j["url"],
                description=j["description"],
                source=j["source"],
                match_score=score,
            ))
        s.commit()

        results = s.exec(
            select(JobMatch)
            .where(JobMatch.profile_id == profile_id)
            .order_by(JobMatch.match_score.desc())
        ).all()

        saved = [
            {
                "id": r.id, "title": r.title, "company": r.company,
                "location": r.location, "url": r.url, "description": r.description,
                "source": r.source, "match_score": r.match_score,
            }
            for r in results
        ]

    activity.log_activity("jobs_search", f"query={query}, found={len(saved)}", profile_id)
    return {"query": query, "jobs": saved}
