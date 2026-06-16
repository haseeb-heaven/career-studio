"""Job matching — multi-source job board integration with parallel fetching."""
import asyncio
import json
import re
import urllib.request
import urllib.parse
import xml.etree.ElementTree as ET
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
    skills = sorted(
        [s.name for s in (profile.skills or []) if s.name],
        key=lambda x: -len(x)
    )[:6]

    roles = [e.role for e in (profile.experience or []) if e.role]
    role = roles[0] if roles else ""

    parts = []
    if role:
        parts.append(role)
    for s in skills:
        if not any(s.lower() in p.lower() for p in parts):
            parts.append(s)
        if len(parts) >= 5:
            break

    query = " ".join(dict.fromkeys(parts))[:120].strip()
    if not query:
        query = profile.summary[:80].strip() if profile.summary else "software developer"

    query = re.sub(r"[•\-\*\d\+\:\,\.\;\|\(\)\[\]]", " ", query)
    query = re.sub(r"\s+", " ", query).strip()

    words = query.split()
    if len(words) > 5:
        stop_words = {"optimized", "asset", "caching", "delivery", "pipelines", "to", "improve",
                      "performance", "languages", "and", "the", "a", "for", "in", "of", "with"}
        filtered = [w for w in words if w.lower() not in stop_words]
        if not filtered:
            filtered = words[:5]
        query = " ".join(filtered[:5])
    return query


# ── Tier 1 sources (no auth) ──────────────────────────────────────────────────

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
                "salary": None,
                "is_deep_link": False,
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
                "salary": None,
                "is_deep_link": False,
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
                "salary": None,
                "is_deep_link": False,
            })
        return jobs[:limit]
    except Exception as e:
        logger.warning("RemoteOK fetch failed: %s", e)
        return []


def _fetch_himalayas(query: str, limit: int) -> list[dict]:
    """Himalayas remote jobs API — free, no auth, includes salary data."""
    try:
        encoded = urllib.parse.quote(query)
        url = f"https://himalayas.app/jobs/api?q={encoded}&limit={limit}"
        req = urllib.request.Request(url, headers={"User-Agent": _BROWSER_UA, "Accept": "application/json"})
        with urllib.request.urlopen(req, timeout=12) as resp:
            data = json.loads(resp.read())
        jobs = []
        for j in data.get("jobs", [])[:limit]:
            locs = j.get("locationRestrictions") or []
            loc = locs[0] if locs else "Remote"
            raw_salary = j.get("salary") or j.get("salaryRange") or j.get("salaryMin")
            jobs.append({
                "title": j.get("title", ""),
                "company": j.get("companyName", ""),
                "location": loc,
                "url": j.get("applicationUrl", j.get("url", "")),
                "description": (j.get("description", "") or "")[:500],
                "source": "himalayas",
                "salary": str(raw_salary) if raw_salary else None,
                "is_deep_link": False,
            })
        return jobs
    except Exception as e:
        logger.warning("Himalayas fetch failed: %s", e)
        return []


def _fetch_the_muse(query: str, limit: int) -> list[dict]:
    """The Muse public jobs API — free, no auth."""
    try:
        encoded = urllib.parse.quote(query)
        url = f"https://www.themuse.com/api/public/jobs?category={encoded}&page=0&descending=true"
        req = urllib.request.Request(url, headers={"User-Agent": _BROWSER_UA, "Accept": "application/json"})
        with urllib.request.urlopen(req, timeout=12) as resp:
            data = json.loads(resp.read())
        jobs = []
        for j in data.get("results", [])[:limit]:
            locs = j.get("locations", [])
            loc = locs[0].get("name", "Remote") if locs else "Remote"
            jobs.append({
                "title": j.get("name", ""),
                "company": j.get("company", {}).get("name", ""),
                "location": loc,
                "url": j.get("refs", {}).get("landing_page", ""),
                "description": (j.get("contents", "") or "")[:500],
                "source": "themuse",
                "salary": None,
                "is_deep_link": False,
            })
        return jobs
    except Exception as e:
        logger.warning("The Muse fetch failed: %s", e)
        return []


def _fetch_jobicy(query: str, limit: int) -> list[dict]:
    """Jobicy remote jobs JSON feed — free, no auth."""
    try:
        url = f"https://jobicy.com/?feed=job_feed&search={urllib.parse.quote(query)}"
        req = urllib.request.Request(url, headers={"User-Agent": _BROWSER_UA, "Accept": "application/json"})
        with urllib.request.urlopen(req, timeout=12) as resp:
            data = json.loads(resp.read())
        raw = data.get("jobs") if isinstance(data, dict) else data if isinstance(data, list) else []
        jobs = []
        for j in (raw or [])[:limit]:
            if not isinstance(j, dict):
                continue
            jobs.append({
                "title": j.get("jobTitle", j.get("title", "")),
                "company": j.get("companyName", j.get("company", "")),
                "location": j.get("jobGeo", j.get("location", "Remote")) or "Remote",
                "url": j.get("url", ""),
                "description": (j.get("jobExcerpt", j.get("description", "")) or "")[:500],
                "source": "jobicy",
                "salary": None,
                "is_deep_link": False,
            })
        return jobs
    except Exception as e:
        logger.warning("Jobicy fetch failed: %s", e)
        return []


def _fetch_weworkremotely(query: str, limit: int) -> list[dict]:
    """We Work Remotely RSS feed — parsed from XML."""
    try:
        url = "https://weworkremotely.com/remote-jobs.rss"
        req = urllib.request.Request(url, headers={"User-Agent": _BROWSER_UA})
        with urllib.request.urlopen(req, timeout=12) as resp:
            xml_data = resp.read()
        root = ET.fromstring(xml_data)
        query_words = [w for w in query.lower().split() if len(w) > 2]
        jobs = []
        for item in root.iter("item"):
            title_el = item.find("title")
            link_el = item.find("link")
            desc_el = item.find("description")
            if title_el is None:
                continue
            title = title_el.text or ""
            if query_words and not any(w in title.lower() for w in query_words):
                continue
            jobs.append({
                "title": title,
                "company": "",
                "location": "Remote",
                "url": link_el.text if link_el is not None else "",
                "description": (desc_el.text or "")[:500] if desc_el is not None else "",
                "source": "weworkremotely",
                "salary": None,
                "is_deep_link": False,
            })
            if len(jobs) >= limit:
                break
        return jobs
    except Exception as e:
        logger.warning("We Work Remotely fetch failed: %s", e)
        return []


# ── Tier 2 sources (API key required) ────────────────────────────────────────

def _fetch_adzuna(query: str, limit: int, app_id: str, app_key: str) -> list[dict]:
    """Adzuna API — only called when app_id and app_key are configured."""
    if not app_id or not app_key:
        return []
    try:
        encoded = urllib.parse.quote(query)
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
                "salary": None,
                "is_deep_link": False,
            }
            for j in data.get("results", [])
        ]
    except Exception as e:
        logger.warning("Adzuna fetch failed: %s", e)
        return []


def _fetch_findwork(query: str, limit: int, api_key: str) -> list[dict]:
    """Findwork.dev API — developer-focused jobs, requires free API key."""
    if not api_key:
        return []
    try:
        encoded = urllib.parse.quote(query)
        url = f"https://findwork.dev/api/jobs/?search={encoded}"
        req = urllib.request.Request(
            url,
            headers={"Authorization": f"Token {api_key}", "User-Agent": _BROWSER_UA}
        )
        with urllib.request.urlopen(req, timeout=12) as resp:
            data = json.loads(resp.read())
        jobs = []
        for j in data.get("results", [])[:limit]:
            jobs.append({
                "title": j.get("role", ""),
                "company": j.get("company_name", ""),
                "location": j.get("location", "Remote") or "Remote",
                "url": j.get("url", ""),
                "description": (j.get("text", "") or "")[:500],
                "source": "findwork",
                "salary": None,
                "is_deep_link": False,
            })
        return jobs
    except Exception as e:
        logger.warning("Findwork fetch failed: %s", e)
        return []


def _fetch_jooble(query: str, limit: int, api_key: str) -> list[dict]:
    """Jooble API — global aggregator across 140k+ job sites, requires API key."""
    if not api_key:
        return []
    try:
        url = f"https://jooble.org/api/{api_key}"
        payload = json.dumps({"keywords": query, "location": "", "count": limit}).encode()
        req = urllib.request.Request(
            url,
            data=payload,
            headers={"Content-Type": "application/json", "User-Agent": _BROWSER_UA}
        )
        with urllib.request.urlopen(req, timeout=12) as resp:
            data = json.loads(resp.read())
        jobs = []
        for j in data.get("jobs", [])[:limit]:
            jobs.append({
                "title": j.get("title", ""),
                "company": j.get("company", ""),
                "location": j.get("location", "Remote") or "Remote",
                "url": j.get("link", ""),
                "description": (j.get("snippet", "") or "")[:500],
                "source": "jooble",
                "salary": j.get("salary") or None,
                "is_deep_link": False,
            })
        return jobs
    except Exception as e:
        logger.warning("Jooble fetch failed: %s", e)
        return []


# ── Tier 3 deep links (open browser, no data fetched) ────────────────────────

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
                "source": "linkedin",
                "salary": None,
                "is_deep_link": False,
            })
            if len(jobs) >= limit:
                break
        return jobs
    except Exception as e:
        logger.warning("LinkedIn Guest fetch failed: %s", e)
        return []


def _fetch_linkedin(query: str, location: str, limit: int, api_key: str = "") -> list[dict]:
    """Fetch LinkedIn jobs via guest scraping, fall back to deep link."""
    jobs = _fetch_linkedin_guest(query, location, limit)
    if not jobs:
        search_url = (
            f"https://www.linkedin.com/jobs/search/?keywords={urllib.parse.quote(query)}"
            f"&location={urllib.parse.quote(location or 'Remote')}&f_TPR=r86400"
        )
        jobs = [{
            "title": f"Search '{query}' on LinkedIn",
            "company": "LinkedIn Jobs",
            "location": location or "Remote",
            "url": search_url,
            "description": f"Search live {query} postings on LinkedIn (last 24 hours). Opens in browser.",
            "source": "linkedin",
            "salary": None,
            "is_deep_link": True,
        }]
    return jobs


def _fetch_indeed(query: str, location: str, limit: int, api_key: str = "") -> list[dict]:
    """Indeed deep link — opens pre-filled search in browser."""
    search_url = (
        f"https://www.indeed.com/jobs?q={urllib.parse.quote(query)}"
        f"&l={urllib.parse.quote(location or 'Remote')}&sort=date"
    )
    return [{
        "title": f"Search '{query}' on Indeed",
        "company": "Indeed Job Search",
        "location": location or "Remote",
        "url": search_url,
        "description": f"Search live {query} postings on Indeed sorted by date. Opens in browser.",
        "source": "indeed",
        "salary": None,
        "is_deep_link": True,
    }]


def _fetch_glassdoor(query: str, location: str, limit: int, api_key: str = "") -> list[dict]:
    """Glassdoor deep link — opens pre-filled search in browser."""
    search_url = (
        f"https://www.glassdoor.com/Job/jobs.htm?sc.keyword={urllib.parse.quote(query)}"
        f"&locT=C&locN={urllib.parse.quote(location or 'Remote')}"
    )
    return [{
        "title": f"Search '{query}' on Glassdoor",
        "company": "Glassdoor Jobs",
        "location": location or "Remote",
        "url": search_url,
        "description": f"Search live {query} postings on Glassdoor. Opens in browser.",
        "source": "glassdoor",
        "salary": None,
        "is_deep_link": True,
    }]


def _fetch_google_jobs(query: str, location: str) -> list[dict]:
    """Google Jobs deep link — aggregates LinkedIn, Indeed, Glassdoor, company pages."""
    search_url = (
        f"https://www.google.com/search?q={urllib.parse.quote(query + ' jobs')}"
        f"&ibp=htl;jobs"
    )
    return [{
        "title": f"Search '{query}' on Google Jobs",
        "company": "Google Jobs",
        "location": location or "Multiple Sources",
        "url": search_url,
        "description": "Google Jobs aggregates postings from LinkedIn, Indeed, Glassdoor and company pages. Opens in browser.",
        "source": "google_jobs",
        "salary": None,
        "is_deep_link": True,
    }]


# ── Scoring & deduplication ───────────────────────────────────────────────────

def _match_score(job_title: str, job_desc: str, skill_names: list[str], query: str) -> float:
    """Score 0–100 based on how well job matches the profile skills and query."""
    if not skill_names and not query:
        return 0.0

    score = 0.0
    title_lower = job_title.lower()
    desc_lower = job_desc.lower()

    query_words = [w for w in query.lower().split() if len(w) > 2]
    title_hits = sum(1 for w in query_words if w in title_lower)
    if query_words:
        score += (title_hits / len(query_words)) * 50

    if skill_names:
        skill_hits = sum(1 for s in skill_names if s.lower() in desc_lower)
        score += (skill_hits / len(skill_names)) * 50

    return round(min(100.0, score), 1)


def _deduplicate(jobs: list[dict]) -> list[dict]:
    """Deduplicate by (title, company), keeping first occurrence."""
    seen: set[tuple[str, str]] = set()
    result = []
    for j in jobs:
        key = (j.get("title", "").lower().strip(), j.get("company", "").lower().strip())
        if key not in seen:
            seen.add(key)
            result.append(j)
    return result


# ── Supported portals registry ────────────────────────────────────────────────

_SUPPORTED_PORTALS = {
    "all", "arbeitnow", "remoteok", "remotive",
    "himalayas", "themuse", "jobicy", "weworkremotely",
    "linkedin", "indeed", "glassdoor", "google_jobs",
    "adzuna", "findwork", "jooble",
}


@router.get("/{profile_id}/jobs")
async def search_jobs(
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

        query = job_title.strip() if job_title.strip() else _build_keywords(p)
        search_loc = location.strip() if location.strip() else (p.location or "Remote")

        cfg = s.exec(select(Settings)).first() or Settings()
        adzuna_id = cfg.adzuna_app_id or ""
        adzuna_key = decrypt_key(cfg.adzuna_app_key or "")
        linkedin_key = decrypt_key(cfg.linkedin_api_key or "")
        indeed_key = decrypt_key(cfg.indeed_api_key or "")
        glassdoor_key = decrypt_key(cfg.glassdoor_api_key or "")
        findwork_key = decrypt_key(cfg.findwork_api_key or "")
        jooble_key = decrypt_key(cfg.jooble_api_key or "")

    logger.info("Job search for profile %d: query=%r, location=%r, portal=%r", profile_id, query, search_loc, portal)

    p_lower = portal.lower().strip()
    if p_lower not in _SUPPORTED_PORTALS:
        raise HTTPException(
            status_code=400,
            detail=f"Unsupported portal '{portal}'. Supported: {', '.join(sorted(_SUPPORTED_PORTALS))}"
        )

    # Build list of coroutines to run concurrently
    tasks: list = []
    if p_lower in ("all", "remotive"):
        tasks.append(asyncio.to_thread(_fetch_remotive, query, limit))
    if p_lower in ("all", "arbeitnow"):
        tasks.append(asyncio.to_thread(_fetch_arbeitnow, query, limit))
    if p_lower in ("all", "remoteok"):
        tasks.append(asyncio.to_thread(_fetch_remoteok, query, limit))
    if p_lower in ("all", "himalayas"):
        tasks.append(asyncio.to_thread(_fetch_himalayas, query, limit))
    if p_lower in ("all", "themuse"):
        tasks.append(asyncio.to_thread(_fetch_the_muse, query, limit))
    if p_lower in ("all", "jobicy"):
        tasks.append(asyncio.to_thread(_fetch_jobicy, query, limit))
    if p_lower in ("all", "weworkremotely"):
        tasks.append(asyncio.to_thread(_fetch_weworkremotely, query, limit))
    if p_lower in ("all", "linkedin"):
        tasks.append(asyncio.to_thread(_fetch_linkedin, query, search_loc, limit, linkedin_key))
    if p_lower in ("all", "indeed"):
        tasks.append(asyncio.to_thread(_fetch_indeed, query, search_loc, limit, indeed_key))
    if p_lower in ("all", "glassdoor"):
        tasks.append(asyncio.to_thread(_fetch_glassdoor, query, search_loc, limit, glassdoor_key))
    if p_lower in ("all", "google_jobs"):
        tasks.append(asyncio.to_thread(_fetch_google_jobs, query, search_loc))
    if p_lower in ("all",) and adzuna_id and adzuna_key:
        tasks.append(asyncio.to_thread(_fetch_adzuna, query, limit, adzuna_id, adzuna_key))
    elif p_lower == "adzuna":
        tasks.append(asyncio.to_thread(_fetch_adzuna, query, limit, adzuna_id, adzuna_key))
    if findwork_key and p_lower in ("all", "findwork"):
        tasks.append(asyncio.to_thread(_fetch_findwork, query, limit, findwork_key))
    elif p_lower == "findwork":
        tasks.append(asyncio.to_thread(_fetch_findwork, query, limit, findwork_key))
    if jooble_key and p_lower in ("all", "jooble"):
        tasks.append(asyncio.to_thread(_fetch_jooble, query, limit, jooble_key))
    elif p_lower == "jooble":
        tasks.append(asyncio.to_thread(_fetch_jooble, query, limit, jooble_key))

    results = await asyncio.gather(*tasks, return_exceptions=True)

    all_jobs = []
    for result in results:
        if isinstance(result, Exception):
            logger.warning("Source fetch raised: %s", result)
            continue
        all_jobs.extend(result)

    all_jobs = _deduplicate(all_jobs)[:limit]

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
                salary=j.get("salary"),
                is_deep_link=j.get("is_deep_link", False),
            ))
        s.commit()

        results_db = s.exec(
            select(JobMatch)
            .where(JobMatch.profile_id == profile_id)
            .order_by(JobMatch.match_score.desc())
        ).all()

        saved = [
            {
                "id": r.id, "title": r.title, "company": r.company,
                "location": r.location, "url": r.url, "description": r.description,
                "source": r.source, "match_score": r.match_score,
                "salary": r.salary, "is_deep_link": r.is_deep_link,
            }
            for r in results_db
        ]

    activity.log_activity("jobs_search", f"query={query}, location={search_loc}, found={len(saved)}", profile_id)
    return {"query": query, "jobs": saved}
