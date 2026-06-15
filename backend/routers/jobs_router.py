"""Job matching — Remotive (free) + RemoteOK (free) + Adzuna (optional, needs keys)."""
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


def _build_keywords(profile: Profile) -> str:
    skill_names = [s.name for s in (profile.skills or [])][:6]
    role = profile.experience[0].role if profile.experience else ""
    terms = ([role] if role else []) + skill_names
    return " ".join(dict.fromkeys(terms))[:120]


def _fetch_remotive(query: str, limit: int) -> list[dict]:
    try:
        encoded = urllib.parse.quote(query)
        url = f"https://remotive.com/api/remote-jobs?search={encoded}&limit={limit}"
        with urllib.request.urlopen(url, timeout=10) as resp:
            data = json.loads(resp.read())
        return [
            {
                "title": j.get("title", ""),
                "company": j.get("company_name", ""),
                "location": j.get("candidate_required_location", "Remote"),
                "url": j.get("url", ""),
                "description": (j.get("description", "") or "")[:500],
                "source": "remotive",
            }
            for j in data.get("jobs", [])
        ]
    except Exception as e:
        logger.warning("Remotive fetch failed: %s", e)
        return []


def _fetch_remoteok(query: str, limit: int) -> list[dict]:
    """RemoteOK public API — completely free, no auth needed."""
    try:
        # RemoteOK takes comma-separated tags
        tags = urllib.parse.quote(query.replace(" ", ","))
        url = f"https://remoteok.com/api?tags={tags}"
        req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0 (career-studio/1.0)"})
        with urllib.request.urlopen(req, timeout=10) as resp:
            data = json.loads(resp.read())
        jobs = []
        for j in data:
            if not isinstance(j, dict) or "position" not in j:
                continue
            jobs.append({
                "title": j.get("position", ""),
                "company": j.get("company", ""),
                "location": j.get("location", "Remote"),
                "url": j.get("url", ""),
                "description": (j.get("description", "") or "")[:500],
                "source": "remoteok",
            })
        return jobs[:limit]
    except Exception as e:
        logger.warning("RemoteOK fetch failed: %s", e)
        return []


def _fetch_adzuna(query: str, limit: int, app_id: str, app_key: str) -> list[dict]:
    """Adzuna API — only called when app_id and app_key are configured."""
    if not app_id or not app_key:
        return []
    try:
        encoded = urllib.parse.quote(query)
        url = (
            f"https://api.adzuna.com/v1/api/jobs/us/search/1"
            f"?app_id={app_id}&app_key={app_key}&results_per_page={limit}"
            f"&what={encoded}&content-type=application/json"
        )
        with urllib.request.urlopen(url, timeout=10) as resp:
            data = json.loads(resp.read())
        return [
            {
                "title": j.get("title", ""),
                "company": j.get("company", {}).get("display_name", ""),
                "location": j.get("location", {}).get("display_name", ""),
                "url": j.get("redirect_url", ""),
                "description": (j.get("description", "") or "")[:500],
                "source": "adzuna",
            }
            for j in data.get("results", [])
        ]
    except Exception as e:
        logger.warning("Adzuna fetch failed: %s", e)
        return []


def _match_score(job_desc: str, skill_names: list[str]) -> float:
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
        cfg = s.exec(select(Settings)).first() or Settings()
        adzuna_id = cfg.adzuna_app_id or ""
        adzuna_key = cfg.adzuna_app_key or ""

    logger.info("Job search for profile %d: %r", profile_id, query)

    third = max(1, limit // 3)
    half = max(1, limit // 2)

    remotive_jobs = _fetch_remotive(query, half)
    remoteok_jobs = _fetch_remoteok(query, third)
    adzuna_jobs = _fetch_adzuna(query, third, adzuna_id, adzuna_key)

    all_jobs = remotive_jobs + remoteok_jobs + adzuna_jobs

    with Session(engine) as s:
        old = s.exec(select(JobMatch).where(JobMatch.profile_id == profile_id)).all()
        for o in old:
            s.delete(o)
        s.commit()

        for j in all_jobs:
            score = _match_score(j["description"], skill_names)
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
