"""Job matching endpoint — searches Remotive (free, no key) + Adzuna (free tier)."""
import json
import math
import urllib.request
import urllib.parse
from fastapi import APIRouter, HTTPException, Query
from sqlmodel import Session, select
from db import engine
from models import Profile, JobMatch, Skill
from services import activity
from logger import get_logger

logger = get_logger(__name__)
router = APIRouter(prefix="/profiles", tags=["jobs"])


def _build_keywords(profile: Profile) -> str:
    """Extract top skills + role title as a search query."""
    skill_names = [s.name for s in (profile.skills or [])][:6]
    # Try to infer current role from latest experience
    role = ""
    if profile.experience:
        role = profile.experience[0].role
    terms = ([role] if role else []) + skill_names
    return " ".join(dict.fromkeys(terms))[:120]  # deduplicate, cap length


def _fetch_remotive(query: str, limit: int) -> list[dict]:
    """Remotive public API — free, no auth."""
    try:
        encoded = urllib.parse.quote(query)
        url = f"https://remotive.com/api/remote-jobs?search={encoded}&limit={limit}"
        with urllib.request.urlopen(url, timeout=8) as resp:
            data = json.loads(resp.read())
        jobs = []
        for j in data.get("jobs", []):
            jobs.append({
                "title": j.get("title", ""),
                "company": j.get("company_name", ""),
                "location": j.get("candidate_required_location", "Remote"),
                "url": j.get("url", ""),
                "description": j.get("description", "")[:500],
                "source": "remotive",
            })
        return jobs
    except Exception as e:
        logger.warning("Remotive fetch failed: %s", e)
        return []


def _fetch_adzuna(query: str, limit: int) -> list[dict]:
    """Adzuna public API — free tier, no key needed for basic search."""
    try:
        encoded = urllib.parse.quote(query)
        url = (
            f"https://api.adzuna.com/v1/api/jobs/us/search/1"
            f"?app_id=&app_key=&results_per_page={limit}&what={encoded}&content-type=application/json"
        )
        with urllib.request.urlopen(url, timeout=8) as resp:
            data = json.loads(resp.read())
        jobs = []
        for j in data.get("results", []):
            jobs.append({
                "title": j.get("title", ""),
                "company": j.get("company", {}).get("display_name", ""),
                "location": j.get("location", {}).get("display_name", ""),
                "url": j.get("redirect_url", ""),
                "description": j.get("description", "")[:500],
                "source": "adzuna",
            })
        return jobs
    except Exception as e:
        logger.warning("Adzuna fetch failed: %s", e)
        return []


def _match_score(job_desc: str, skill_names: list[str]) -> float:
    """Simple keyword-overlap score 0–100."""
    if not skill_names or not job_desc:
        return 0.0
    desc_lower = job_desc.lower()
    hits = sum(1 for s in skill_names if s.lower() in desc_lower)
    return round(min(100.0, (hits / len(skill_names)) * 100), 1)


@router.get("/{profile_id}/jobs")
def search_jobs(profile_id: int, limit: int = Query(default=20, le=50)):
    with Session(engine) as s:
        p = s.get(Profile, profile_id)
        if not p:
            raise HTTPException(status_code=404, detail="Profile not found")
        s.refresh(p)
        skill_names = [sk.name for sk in (p.skills or [])]
        query = _build_keywords(p)

    logger.info("Job search for profile %d: %r", profile_id, query)

    half = max(1, limit // 2)
    remotive_jobs = _fetch_remotive(query, half)
    adzuna_jobs = _fetch_adzuna(query, half)

    all_jobs = remotive_jobs + adzuna_jobs

    # Score and save to DB
    saved = []
    with Session(engine) as s:
        # Clear old matches for this profile
        old = s.exec(select(JobMatch).where(JobMatch.profile_id == profile_id)).all()
        for o in old:
            s.delete(o)
        s.commit()

        for j in all_jobs:
            score = _match_score(j["description"], skill_names)
            jm = JobMatch(
                profile_id=profile_id,
                title=j["title"],
                company=j["company"],
                location=j["location"],
                url=j["url"],
                description=j["description"],
                source=j["source"],
                match_score=score,
            )
            s.add(jm)
        s.commit()

        results = s.exec(
            select(JobMatch)
            .where(JobMatch.profile_id == profile_id)
            .order_by(JobMatch.match_score.desc())
        ).all()

        saved = [
            {
                "id": r.id,
                "title": r.title,
                "company": r.company,
                "location": r.location,
                "url": r.url,
                "description": r.description,
                "source": r.source,
                "match_score": r.match_score,
            }
            for r in results
        ]

    activity.log_activity("jobs_search", f"query={query}, found={len(saved)}", profile_id)
    return {"query": query, "jobs": saved}
