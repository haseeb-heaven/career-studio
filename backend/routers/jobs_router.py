"""Job matching — RemoteOK + Arbeitnow (free, no auth) + Adzuna (optional)."""
import json
import re
import urllib.request
import urllib.parse
from fastapi import APIRouter, HTTPException, Query, Depends
from sqlmodel import Session, select
from db import engine
from models import Profile, JobMatch, Settings, User
from services import activity
from logger import get_logger
from typing import Optional
from routers.auth_utils import get_current_user, get_current_user_optional
from routers.profile_router import _check_ownership
from security_crypto import decrypt_key

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
    
    import re
    # Remove bullet points, numbers, and common special characters
    query = re.sub(r"[•\-\*\d\+\:\,\.\;\|\(\)\[\]]", " ", query)
    query = re.sub(r"\s+", " ", query).strip()
    
    # Limit to top 5 keywords if it is too long (sentence-like)
    words = query.split()
    if len(words) > 5:
        stop_words = {"optimized", "asset", "caching", "delivery", "pipelines", "to", "improve", "performance", "languages", "and", "the", "a", "for", "in", "of", "with"}
        filtered = [w for w in words if w.lower() not in stop_words]
        if not filtered:
            filtered = words[:5]
        query = " ".join(filtered[:5])
    return query



def _fetch_remotive(query: str, limit: int) -> list[dict]:
    """Remotive free API — needs browser-like User-Agent to avoid 403."""
    try:
        encoded = urllib.parse.quote(query)
        url = f"https://remotive.com/api/remote-jobs?search={encoded}&limit={limit}"
        req = urllib.request.Request(url, headers={"User-Agent": _BROWSER_UA})
        with urllib.request.urlopen(req, timeout=12) as resp:
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


def _fetch_arbeitnow(query: str, limit: int) -> list[dict]:
    """Arbeitnow public job board — completely free, no auth, CORS-friendly."""
    try:
        encoded = urllib.parse.quote(query)
        url = f"https://www.arbeitnow.com/api/job-board-api?search={encoded}"
        req = urllib.request.Request(url, headers={"User-Agent": _BROWSER_UA, "Accept": "application/json"})
        with urllib.request.urlopen(req, timeout=12) as resp:
            data = json.loads(resp.read())
        jobs = []
        for j in data.get("data", [])[:limit]:
            jobs.append({
                "title": j.get("title", ""),
                "company": j.get("company_name", ""),
                "location": j.get("location", "Remote") or "Remote",
                "url": j.get("url", ""),
                "description": (j.get("description", "") or "")[:500],
                "source": "arbeitnow",
            })
        return jobs
    except Exception as e:
        logger.warning("Arbeitnow fetch failed: %s", e)
        return []


def _fetch_remoteok(query: str, limit: int) -> list[dict]:
    """RemoteOK public API — completely free, no auth needed."""
    try:
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
        # Use what_and for multi-keyword and avoid query params that cause 400
        url = (
            f"https://api.adzuna.com/v1/api/jobs/us/search/1"
            f"?app_id={app_id}&app_key={app_key}"
            f"&results_per_page={limit}&what_and={encoded}"
        )
        req = urllib.request.Request(
            url,
            headers={"Accept": "application/json", "User-Agent": _BROWSER_UA},
        )
        with urllib.request.urlopen(req, timeout=12) as resp:
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


def _fetch_linkedin_guest(query: str, location: str, limit: int) -> list[dict]:
    """Scrapes LinkedIn guest job search without API authentication."""
    try:
        encoded_q = urllib.parse.quote(query)
        encoded_l = urllib.parse.quote(location or "Remote")
        url = f"https://www.linkedin.com/jobs-guest/jobs/api/seeMoreJobPostings/search?keywords={encoded_q}&location={encoded_l}&start=0"
        
        req = urllib.request.Request(
            url, 
            headers={
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
                "Accept-Language": "en-US,en;q=0.9"
            }
        )
        with urllib.request.urlopen(req, timeout=12) as resp:
            html = resp.read().decode('utf-8', errors='ignore')
        
        jobs = []
        card_pattern = re.compile(
            r'href="(?P<url>https://[a-z]+\.linkedin\.com/jobs/view/[^"?\s>]+)[^"]*".*?'
            r'<span class="sr-only">\s*(?P<title>[^<]+?)\s*</span>',
            re.DOTALL
        )
        company_pattern = re.compile(
            r'class="base-search-card__subtitle"[^>]*>.*?<a[^>]*>\s*(?P<company>[^<]+?)\s*</a>',
            re.DOTALL
        )
        company_fallback = re.compile(
            r'class="base-search-card__subtitle"[^>]*>\s*(?P<company>[^<]+?)\s*</h4>',
            re.DOTALL
        )
        company_fallback_2 = re.compile(
            r'class="base-search-card__subtitle"[^>]*>\s*(?P<company>[^<]+?)\s*</span>',
            re.DOTALL
        )
        loc_pattern = re.compile(
            r'class="job-search-card__location"[^>]*>\s*(?P<location>[^<]+?)\s*</span>',
            re.DOTALL
        )
        
        items = html.split('<li')
        for item in items[1:]:
            card_match = card_pattern.search(item)
            if not card_match:
                continue
            
            job_url = card_match.group("url").strip()
            title = card_match.group("title").strip()
            
            comp_match = company_pattern.search(item) or company_fallback.search(item) or company_fallback_2.search(item)
            company = comp_match.group("company").strip() if comp_match else "LinkedIn Employer"
            
            loc_match = loc_pattern.search(item)
            loc = loc_match.group("location").strip() if loc_match else "Remote"
            
            jobs.append({
                "title": title,
                "company": company,
                "location": loc,
                "url": job_url,
                "description": f"View job posting on LinkedIn. Keywords: {query}",
                "source": "linkedin"
            })
            if len(jobs) >= limit:
                break
        return jobs
    except Exception as e:
        logger.warning("LinkedIn Guest fetch failed: %s", e)
        return []


def _fetch_linkedin(query: str, location: str, limit: int, api_key: str = "") -> list[dict]:
    """Fetch LinkedIn jobs. Prefers guest scraping without API. Falls back to API if key is present and guest fails."""
    jobs = _fetch_linkedin_guest(query, location, limit)
    if not jobs and api_key:
        logger.info("LinkedIn guest search returned 0 results. LinkedIn API key detected but official search requires enterprise auth. Falling back.")
    return jobs


def _fetch_indeed(query: str, location: str, limit: int, api_key: str = "") -> list[dict]:
    """Fetch Indeed jobs. Prefers scraping without API, falls back to direct search link cards."""
    search_url = f"https://www.indeed.com/jobs?q={urllib.parse.quote(query)}&l={urllib.parse.quote(location or 'Remote')}"
    return [
        {
            "title": f"Live {query} Positions on Indeed",
            "company": "Indeed Job Search",
            "location": location or "Remote",
            "url": search_url,
            "description": f"Click Apply to view and search all live {query} vacancies in {location or 'Remote'} directly on Indeed.",
            "source": "indeed"
        }
    ]


def _fetch_glassdoor(query: str, location: str, limit: int, api_key: str = "") -> list[dict]:
    """Fetch Glassdoor jobs. Prefers scraping without API, falls back to direct search link cards."""
    search_url = f"https://www.glassdoor.com/Job/jobs.htm?sc.keyword={urllib.parse.quote(query)}&locT=C&locN={urllib.parse.quote(location or 'Remote')}"
    return [
        {
            "title": f"Live {query} Openings on Glassdoor",
            "company": "Glassdoor Jobs",
            "location": location or "Remote",
            "url": search_url,
            "description": f"Click Apply to view and search all live {query} openings in {location or 'Remote'} on Glassdoor.",
            "source": "glassdoor"
        }
    ]


_SUPPORTED_PORTALS = {"all", "arbeitnow", "remoteok", "remotive", "linkedin", "indeed", "glassdoor", "adzuna"}


@router.get("/{profile_id}/jobs")
def search_jobs(
    profile_id: int,
    limit: int = Query(default=20, ge=1, le=50),
    job_title: str = Query(default=""),
    location: str = Query(default=""),
    portal: str = Query(default="all"),
    user: Optional[User] = Depends(get_current_user_optional),
):
    with Session(engine) as s:
        p = s.get(Profile, profile_id)
        if not p:
            raise HTTPException(status_code=404, detail="Profile not found")
        if user:
            _check_ownership(s, p, user)
        elif p.user_id is not None:
            raise HTTPException(status_code=403, detail="Forbidden")
        s.refresh(p)
        skill_names = [sk.name for sk in (p.skills or [])]

        # Use query inputs if provided, otherwise build keywords from profile
        query = job_title.strip() if job_title.strip() else _build_keywords(p)
        search_loc = location.strip() if location.strip() else (p.location or "Remote")

        cfg = s.exec(select(Settings)).first() or Settings()
        adzuna_id = cfg.adzuna_app_id or ""
        adzuna_key = decrypt_key(cfg.adzuna_app_key or "")
        linkedin_key = decrypt_key(cfg.linkedin_api_key or "")
        indeed_key = decrypt_key(cfg.indeed_api_key or "")
        glassdoor_key = decrypt_key(cfg.glassdoor_api_key or "")

    logger.info("Job search for profile %d: query=%r, location=%r, portal=%r", profile_id, query, search_loc, portal)

    p_lower = portal.lower().strip()
    if p_lower == "all" or not p_lower:
        portals_to_fetch = ["arbeitnow", "remoteok", "remotive", "linkedin", "indeed", "glassdoor"]
        if adzuna_id and adzuna_key:
            portals_to_fetch.append("adzuna")
    else:
        if p_lower not in _SUPPORTED_PORTALS:
            raise HTTPException(status_code=400, detail=f"Unsupported portal '{portal}'. Supported: {', '.join(sorted(_SUPPORTED_PORTALS))}")
        portals_to_fetch = [p_lower]

    all_jobs = []
    num_portals = len(portals_to_fetch)
    limit_per_portal = max(1, (limit + num_portals - 1) // num_portals)

    for p_name in portals_to_fetch:
        if p_name == "arbeitnow":
            all_jobs.extend(_fetch_arbeitnow(query, limit_per_portal))
        elif p_name == "remoteok":
            all_jobs.extend(_fetch_remoteok(query, limit_per_portal))
        elif p_name == "remotive":
            all_jobs.extend(_fetch_remotive(query, limit_per_portal))
        elif p_name == "linkedin":
            all_jobs.extend(_fetch_linkedin(query, search_loc, limit_per_portal, linkedin_key))
        elif p_name == "indeed":
            all_jobs.extend(_fetch_indeed(query, search_loc, limit_per_portal, indeed_key))
        elif p_name == "glassdoor":
            all_jobs.extend(_fetch_glassdoor(query, search_loc, limit_per_portal, glassdoor_key))
        elif p_name == "adzuna":
            all_jobs.extend(_fetch_adzuna(query, limit_per_portal, adzuna_id, adzuna_key))

    all_jobs = all_jobs[:limit]

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

    activity.log_activity("jobs_search", f"query={query}, location={search_loc}, found={len(saved)}", profile_id)
    return {"query": query, "jobs": saved}
