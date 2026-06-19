"""Job matching — multi-source job board integration with parallel fetching.

Issue #7: profile-aware weighted match scoring, advanced filters, sort,
pagination, missing-skill gap, saved filter presets.
"""
import asyncio
import json
import re
import urllib.request
import urllib.parse
import xml.etree.ElementTree as ET
from datetime import datetime, timedelta, timezone
from fastapi import APIRouter, HTTPException, Query, Depends
from pydantic import BaseModel
from sqlmodel import Session, select
import db
from models import Profile, JobMatch, Settings, User, SavedFilter
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
                "date_posted": (j.get("publication_date") or "")[:10],
                "job_type": j.get("job_type", "") or "",
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


def _fetch_reed(query: str, limit: int, api_key: str) -> list[dict]:
    """Reed.co.uk API — UK-focused job board, free dev key required."""
    if not api_key:
        return []
    try:
        encoded = urllib.parse.quote(query)
        url = f"https://www.reed.co.uk/api/1.0/search?keywords={encoded}&resultsToTake={limit}"
        req = urllib.request.Request(
            url,
            headers={
                "Authorization": f"Basic {api_key}",
                "User-Agent": _BROWSER_UA,
            },
        )
        with urllib.request.urlopen(req, timeout=12) as resp:
            data = json.loads(resp.read())
        jobs = []
        for j in data.get("results", [])[:limit]:
            sal_min = int(j.get("minimumSalary") or 0)
            sal_max = int(j.get("maximumSalary") or 0)
            salary = None
            if sal_min and sal_max:
                salary = f"£{sal_min:,}-£{sal_max:,}"
            elif sal_min:
                salary = f"£{sal_min:,}+"
            jobs.append({
                "title": j.get("jobTitle", ""),
                "company": j.get("employerName", ""),
                "location": j.get("locationName", "UK") or "UK",
                "url": j.get("jobUrl", ""),
                "description": (j.get("jobDescription", "") or "")[:500],
                "source": "reed",
                "salary": salary,
                "is_deep_link": False,
                "date_posted": (j.get("datePosted") or "")[:10],
            })
        return jobs
    except Exception as e:
        logger.warning("Reed fetch failed: %s", e)
        return []


def _fetch_usajobs(query: str, limit: int, api_key: str) -> list[dict]:
    """USAJOBS API — US federal government jobs, free key required."""
    if not api_key:
        return []
    try:
        encoded = urllib.parse.quote(query)
        url = f"https://data.usajobs.gov/api/search?Keyword={encoded}&ResultsPerPage={limit}"
        req = urllib.request.Request(
            url,
            headers={
                "Authorization-Key": api_key,
                "User-Agent": "career-studio-ai/1.0",
            },
        )
        with urllib.request.urlopen(req, timeout=12) as resp:
            data = json.loads(resp.read())
        jobs = []
        for j in data.get("SearchResult", {}).get("SearchResultItems", [])[:limit]:
            pd = j.get("MatchedObjectDescriptor", {})
            sal_min = int(pd.get("PositionRemuneration", [{}])[0].get("MinimumRange", "0") or 0)
            sal_max = int(pd.get("PositionRemuneration", [{}])[0].get("MaximumRange", "0") or 0)
            salary = None
            if sal_min and sal_max:
                salary = f"${sal_min:,}-${sal_max:,}"
            locations = [loc.get("LocationName", "") for loc in pd.get("PositionLocation", [])]
            jobs.append({
                "title": pd.get("PositionTitle", ""),
                "company": pd.get("OrganizationName", "US Federal Government"),
                "location": ", ".join(filter(None, locations)) or "US",
                "url": pd.get("PositionURI", ""),
                "description": (pd.get("QualificationSummary", "") or "")[:500],
                "source": "usajobs",
                "salary": salary,
                "is_deep_link": False,
                "date_posted": (pd.get("PublicationStartDate") or "")[:10],
            })
        return jobs
    except Exception as e:
        logger.warning("USAJOBS fetch failed: %s", e)
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


# ── Scoring engine (Issue #7 — weighted 6-factor) ────────────────────────────

_REQUIRED_YEARS_RE = re.compile(
    r"(\d+)\+?\s*(?:years?|yrs?)\s+(?:of\s+)?experience", re.IGNORECASE
)
_DEGREE_KEYWORDS = (
    "bachelor", "master", "phd", "doctorate",
    "bs", "ms", "b.sc", "m.sc", "degree",
)
_CERT_KEYWORDS = (
    "aws", "gcp", "azure", "kubernetes", "cka", "ckad",
    "pmp", "scrum", "cissp", "terraform", "certified",
)

# A small, opinionated vocabulary used to surface "missing skills" from the
# job description. This is intentionally a short list to keep false positives
# low — a longer list makes the gap analysis noisy. Single-word tokens are
# matched with word boundaries to avoid substring false positives (e.g. "go"
# inside "google").
_JOB_SKILL_VOCAB = (
    # Languages
    "python", "java", "javascript", "typescript", "golang", "rust", "ruby", "php",
    "swift", "kotlin", "scala", "perl", "matlab", "c++", "c#", "r lang",
    # Frontend
    "react", "vue", "angular", "svelte", "next.js", "nuxt", "redux",
    "html", "css", "sass", "tailwind", "webpack", "vite",
    "frontend", "front-end", "front end",
    # Backend / runtimes
    "node", "nodejs", "node.js", "express", "expressjs", "fastapi", "django",
    "flask", "spring", "spring boot", "springboot", "rails", "laravel",
    "nestjs", "graphql", "grpc", ".net", "dotnet",
    "backend", "back-end", "back end", "fullstack", "full-stack", "full stack",
    # Databases
    "postgresql", "postgres", "mysql", "mongodb", "redis", "elasticsearch",
    "dynamodb", "kafka", "rabbitmq", "sqlite", "cassandra", "clickhouse",
    "nosql", "sql",
    # DevOps / cloud
    "docker", "kubernetes", "k8s", "terraform", "ansible", "jenkins",
    "github actions", "helm", "prometheus", "grafana", "datadog",
    "aws", "gcp", "azure", "cloudfront", "lambda", "ec2", "rds",
    "ci/cd", "devops",
    # Data / ML
    "machine learning", "deep learning", "nlp", "computer vision",
    "tensorflow", "pytorch", "scikit-learn", "pandas", "numpy", "spark",
    "hadoop", "airflow", "dbt", "snowflake", "bigquery", "redshift",
    "data science", "data engineering", "data analyst",
    # Tools / practices
    "git", "agile", "scrum", "kanban", "jira",
    "microservices", "rest api", "restful", "soap",
    "linux", "bash", "powershell", "unix",
    "tdd", "ci/cd",
    # Design
    "figma", "sketch", "adobe xd",
    # Testing
    "jest", "pytest", "junit", "selenium", "cypress", "playwright",
    # Roles / domains
    "devops", "sre", "qa", "etl", "api", "saas", "b2b", "b2c",
    "microservice", "monolith", "serverless", "edge",
    "security", "owasp", "penetration testing",
    "android", "ios", "mobile", "react native", "flutter",
)


def _contains_token(haystack_l: str, token: str) -> bool:
    """Word-boundary-aware substring check. Multi-word tokens use plain substring
    matching because the word-boundary check is too strict for phrases like
    'machine learning' inside 'state-of-the-art machine learning pipelines'."""
    if " " in token or "." in token or "/" in token or "-" in token:
        return token in haystack_l
    pattern = r"(?<![a-z0-9])" + re.escape(token) + r"(?![a-z0-9])"
    return re.search(pattern, haystack_l) is not None

_WEIGHTS = {
    "skills": 0.40,
    "years": 0.20,
    "education": 0.15,
    "location": 0.10,
    "certifications": 0.10,
    "title": 0.05,
}


def _parse_required_years(text: str) -> int:
    if not text:
        return 0
    m = _REQUIRED_YEARS_RE.search(text)
    return int(m.group(1)) if m else 0


def _profile_years(profile: Profile) -> int:
    """Total years across all skill records. Best-effort heuristic."""
    if not profile or not getattr(profile, "skills", None):
        return 0
    return int(round(sum(float(s.years or 0) for s in profile.skills)))


def _skills_factor(profile: Profile, haystack: str) -> tuple[float, list[str], list[str]]:
    skills = [s.name for s in (profile.skills or []) if s.name]
    haystack_l = (haystack or "").lower()
    if not skills:
        return 50.0, [], []
    matched: list[str] = []
    missing_user_skills: list[str] = []
    for s in skills:
        if s.lower() in haystack_l:
            matched.append(s)
        else:
            missing_user_skills.append(s)
    score = (len(matched) / max(len(skills), 1)) * 100
    # Identify "missing" — job-required skills not in the profile. We do this
    # by extracting known skill tokens from the job description via the
    # JOB_SKILL_VOCAB list and reporting the ones the user doesn't have.
    profile_lc = {s.lower() for s in skills}
    seen: set[str] = set()
    missing_job_skills: list[str] = []
    for token in _JOB_SKILL_VOCAB:
        if token in profile_lc:
            continue
        if token in seen:
            continue
        if _contains_token(haystack_l, token):
            missing_job_skills.append(token)
            seen.add(token)
    return score, matched, missing_job_skills


def _years_factor(profile: Profile, required: int) -> float:
    if required <= 0:
        return 100.0
    have = _profile_years(profile)
    if have <= 0:
        return 30.0
    return min(have / required, 1.0) * 100


def _education_factor(profile: Profile, desc: str) -> float:
    desc_l = (desc or "").lower()
    job_requires_degree = any(k in desc_l for k in _DEGREE_KEYWORDS)
    has_degree = bool(profile.education and any(
        (e.degree or e.field) for e in profile.education
    ))
    if job_requires_degree and has_degree:
        return 100.0
    if job_requires_degree and not has_degree:
        return 40.0
    return 100.0


def _location_factor(profile: Profile, job: dict) -> float:
    if job.get("is_remote") or job.get("job_type") == "remote":
        return 100.0
    if not profile or not (profile.location or "").strip():
        return 50.0
    profile_tokens = {t.lower() for t in re.split(r"[,\s]+", profile.location) if t}
    job_loc = (job.get("location") or "").lower()
    if any(t in job_loc for t in profile_tokens if len(t) > 2):
        return 100.0
    return 60.0


def _certifications_factor(profile: Profile, desc: str) -> float:
    certs = [c.name for c in (profile.certifications or []) if c.name]
    desc_l = (desc or "").lower()
    job_mentions_cert = any(k in desc_l for k in _CERT_KEYWORDS)
    if not certs:
        return 30.0 if job_mentions_cert else 80.0
    matched = sum(1 for c in certs if c.lower() in desc_l)
    return (matched / len(certs)) * 100


def _title_factor(profile: Profile, job_title: str) -> float:
    roles = [e.role for e in (profile.experience or []) if e.role]
    if not roles or not job_title:
        return 0.0
    role_tokens = {t.lower() for t in re.split(r"\W+", roles[0]) if len(t) > 2}
    title_tokens = {t.lower() for t in re.split(r"\W+", job_title) if len(t) > 2}
    if not role_tokens or not title_tokens:
        return 0.0
    overlap = role_tokens & title_tokens
    return (len(overlap) / max(len(role_tokens), 1)) * 100


def _profile_match_score(profile: Profile, job: dict) -> dict:
    """Weighted 6-factor match score. Returns score, breakdown, matched, missing."""
    title = (job.get("title") or "")
    desc = (job.get("description") or "")
    haystack = f"{title}\n{desc}"
    required_years = _parse_required_years(desc)

    skills_score, matched, missing = _skills_factor(profile, haystack)
    factors = {
        "skills": skills_score,
        "years": _years_factor(profile, required_years),
        "education": _education_factor(profile, desc),
        "location": _location_factor(profile, job),
        "certifications": _certifications_factor(profile, desc),
        "title": _title_factor(profile, title),
    }
    score = sum(_WEIGHTS[k] * factors[k] for k in _WEIGHTS)
    return {
        "score": round(min(100.0, max(0.0, score)), 1),
        "breakdown": {k: round(v, 1) for k, v in factors.items()},
        "matched": matched,
        "missing": missing,
    }


# ── Backwards-compatible simple scorer (kept for legacy callers/tests) ────────

def _match_score(job_title: str, job_desc: str, skill_names: list[str], query: str) -> float:
    """Legacy flat scorer: 50% title overlap + 50% skills in description."""
    if not skill_names and not query:
        return 0.0
    score = 0.0
    title_lower = (job_title or "").lower()
    desc_lower = (job_desc or "").lower()
    query_words = [w for w in (query or "").lower().split() if len(w) > 2]
    title_hits = sum(1 for w in query_words if w in title_lower)
    if query_words:
        score += (title_hits / len(query_words)) * 50
    if skill_names:
        skill_hits = sum(1 for s in skill_names if s.lower() in desc_lower)
        score += (skill_hits / len(skill_names)) * 50
    return round(min(100.0, score), 1)


# ── Helpers for new fields ────────────────────────────────────────────────────

def _extract_date_posted(j: dict) -> str:
    raw = j.get("date_posted") or j.get("publication_date") or ""
    return str(raw)[:10] if raw else ""


def _extract_job_type(j: dict) -> str:
    raw = (j.get("job_type") or "").lower().strip()
    if raw in ("full_time", "full-time", "full time"):
        return "full-time"
    if raw in ("part_time", "part-time", "part time"):
        return "part-time"
    if "contract" in raw:
        return "contract"
    if "remote" in raw:
        return "remote"
    if "hybrid" in raw:
        return "hybrid"
    return ""


def _is_remote_job(j: dict) -> bool:
    if j.get("is_remote") is True:
        return True
    if (j.get("job_type") or "").lower() == "remote":
        return True
    loc = (j.get("location") or "").lower()
    return "remote" in loc or "anywhere" in loc


def _parse_salary_range(salary_str: str) -> tuple[int, int]:
    """Best-effort: extract min/max from "$120k-$150k", "$120,000", etc."""
    if not salary_str:
        return 0, 0
    nums = re.findall(r"(\d[\d,]*(?:\.\d+)?)\s*([kKmM]?)", str(salary_str))
    parsed = []
    for n, suffix in nums:
        v = float(n.replace(",", ""))
        if suffix.lower() == "k":
            v *= 1000
        elif suffix.lower() == "m":
            v *= 1_000_000
        parsed.append(int(v))
    if not parsed:
        return 0, 0
    if len(parsed) == 1:
        return parsed[0], parsed[0]
    return min(parsed[0], parsed[1]), max(parsed[0], parsed[1])


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
    "adzuna", "findwork", "jooble", "reed", "usajobs",
}


def _date_cutoff(date_posted: str) -> str:
    """Return ISO date string for 'last 24h', 'last 7d', 'last 30d' cutoff."""
    now = datetime.now(timezone.utc)
    if date_posted == "last_24h":
        return (now - timedelta(hours=24)).date().isoformat()
    if date_posted == "last_7d":
        return (now - timedelta(days=7)).date().isoformat()
    if date_posted == "last_30d":
        return (now - timedelta(days=30)).date().isoformat()
    return ""


@router.get("/{profile_id}/jobs")
async def search_jobs(
    profile_id: int,
    limit: int = Query(default=20, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    job_title: str = Query(default=""),
    location: str = Query(default=""),
    portal: str = Query(default="all"),
    min_years: int = Query(default=0, ge=0, le=50),
    max_years: int = Query(default=50, ge=0, le=50),
    date_posted: str = Query(default="any"),
    min_match_score: float = Query(default=0.0, ge=0.0, le=100.0),
    job_type: str = Query(default=""),
    min_salary: int = Query(default=0, ge=0),
    max_salary: int = Query(default=0, ge=0),
    industries: str = Query(default=""),
    sort: str = Query(default="best_match"),
    user: Optional[User] = Depends(get_current_user_optional),
):
    # ---- 1. Load profile, build query, get API keys ----
    with Session(db.engine) as s:
        p = s.get(Profile, profile_id)
        if not p:
            raise HTTPException(status_code=404, detail="Profile not found")
        if user:
            _check_ownership(s, p, user)
        elif p.user_id is not None:
            raise HTTPException(status_code=403, detail="Forbidden")
        s.refresh(p)
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
        reed_key = decrypt_key(cfg.reed_api_key or "")
        usajobs_key = decrypt_key(cfg.usajobs_api_key or "")

    logger.info(
        "Job search for profile %d: query=%r, location=%r, portal=%r, sort=%r",
        profile_id, query, search_loc, portal, sort,
    )

    p_lower = portal.lower().strip()
    if p_lower not in _SUPPORTED_PORTALS:
        raise HTTPException(
            status_code=400,
            detail=f"Unsupported portal '{portal}'. Supported: {', '.join(sorted(_SUPPORTED_PORTALS))}"
        )

    if sort not in ("best_match", "recent", "salary", "location"):
        raise HTTPException(status_code=400, detail=f"Unsupported sort '{sort}'")

    # ---- 2. Fetch from sources in parallel ----
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
    if reed_key and p_lower in ("all", "reed"):
        tasks.append(asyncio.to_thread(_fetch_reed, query, limit, reed_key))
    elif p_lower == "reed":
        tasks.append(asyncio.to_thread(_fetch_reed, query, limit, reed_key))
    if usajobs_key and p_lower in ("all", "usajobs"):
        tasks.append(asyncio.to_thread(_fetch_usajobs, query, limit, usajobs_key))
    elif p_lower == "usajobs":
        tasks.append(asyncio.to_thread(_fetch_usajobs, query, limit, usajobs_key))

    results = await asyncio.gather(*tasks, return_exceptions=True)

    all_jobs = []
    for result in results:
        if isinstance(result, Exception):
            logger.warning("Source fetch raised: %s", result)
            continue
        all_jobs.extend(result)

    all_jobs = _deduplicate(all_jobs)

    # ---- 2b. Strict query + location filtering ----
    # External sources are fuzzy: Remotive's free-text search will return
    # loosely-related jobs (e.g. searching "Backend Developer" can return
    # "Frontend Web Developer" because the description shares generic
    # keywords like "Developer"). To honour the user's intent we
    # post-filter results:
    #   * Job title: ALL of the user's query tokens (split on whitespace)
    #     must appear in either the job's title or description. This
    #     means "Backend Developer" excludes a "Frontend Web Developer"
    #     job (the "Backend" token is missing) but keeps a "Senior Backend
    #     Developer" job (both tokens present).
    #   * Location: at least one of the user's location tokens must
    #     appear in the job's location field. Jobs with empty location
    #     are kept (don't hide untagged jobs).
    if job_title and job_title.strip():
        title_keywords = [
            t.lower() for t in re.split(r"[\s,/]+", job_title.strip())
            if len(t) > 1
        ]
        if title_keywords:
            def _matches_query(j: dict) -> bool:
                title_l = (j.get("title") or "").lower()
                desc_l = (j.get("description") or "").lower()
                return all(
                    kw in title_l or kw in desc_l for kw in title_keywords
                )
            before = len(all_jobs)
            all_jobs = [j for j in all_jobs if _matches_query(j)]
            logger.info(
                "Strict title filter '%s' kept %d / %d jobs",
                job_title, len(all_jobs), before,
            )
    if location and location.strip():
        loc_tokens = [
            t.lower() for t in re.split(r"[\s,/]+", location.strip())
            if len(t) > 2
        ]
        if loc_tokens:
            def _matches_loc(j: dict) -> bool:
                jl = (j.get("location") or "").lower()
                if not jl:
                    return True  # untagged → keep
                return any(tok in jl for tok in loc_tokens)
            before = len(all_jobs)
            all_jobs = [j for j in all_jobs if _matches_loc(j)]
            logger.info(
                "Strict location filter '%s' kept %d / %d jobs",
                location, len(all_jobs), before,
            )

    # ---- 3. Score & persist all fetched jobs ----
    # Profile must remain attached so the scoring engine can read its
    # relationships (skills, experience, education, certifications). We do
    # the whole scoring + persistence inside one session block.
    with Session(db.engine) as s:
        # Re-attach the profile inside this new session
        p = s.get(Profile, profile_id)
        s.refresh(p)

        old = s.exec(select(JobMatch).where(JobMatch.profile_id == profile_id)).all()
        for o in old:
            s.delete(o)
        s.commit()

        for j in all_jobs:
            result = _profile_match_score(p, j)
            j["_score"] = result["score"]
            j["_breakdown"] = json.dumps(result["breakdown"])
            j["_matched"] = json.dumps(result["matched"])
            j["_missing"] = json.dumps(result["missing"])
            if not j.get("date_posted"):
                j["date_posted"] = _extract_date_posted(j)
            if not j.get("job_type"):
                j["job_type"] = _extract_job_type(j)
            if not j.get("is_remote"):
                j["is_remote"] = _is_remote_job(j)
            sal_min, sal_max = _parse_salary_range(j.get("salary") or "")
            s.add(JobMatch(
                profile_id=profile_id,
                title=j["title"],
                company=j["company"],
                location=j["location"],
                url=j["url"],
                description=j["description"],
                source=j["source"],
                match_score=j["_score"],
                salary=j.get("salary"),
                is_deep_link=j.get("is_deep_link", False),
                date_posted=j.get("date_posted", ""),
                job_type=j.get("job_type", ""),
                industry=j.get("industry", ""),
                is_remote=j.get("is_remote", False),
                salary_min=sal_min,
                salary_max=sal_max,
                match_breakdown=j["_breakdown"],
                matched_skills=j["_matched"],
                missing_skills=j["_missing"],
            ))
        s.commit()

    # ---- 4. Apply filters / sort / pagination in SQLModel ----
    # Treat blank / 0 salary bounds as "no filter" — the frontend sends
    # 0 for empty inputs. Negative or absurd values are clamped to 0 here.
    min_salary = max(0, int(min_salary or 0))
    max_salary = max(0, int(max_salary or 0))
    min_years = max(0, int(min_years or 0))
    max_years = min(50, max(0, int(max_years or 50)))
    min_match_score = max(0.0, min(100.0, float(min_match_score or 0)))

    job_type_set = {t.strip() for t in (job_type or "").split(",") if t.strip()}
    industry_set = {t.strip() for t in (industries or "").split(",") if t.strip()}
    cutoff = _date_cutoff(date_posted) if date_posted != "any" else ""

    with Session(db.engine) as s:
        stmt = select(JobMatch).where(JobMatch.profile_id == profile_id)
        if min_match_score > 0:
            stmt = stmt.where(JobMatch.match_score >= min_match_score)
        # Multi-select filters: keep a job if (a) it has an empty field
        # (we don't know its actual type/industry so we don't drop it)
        # OR (b) its field matches one of the user-selected values.
        # This avoids hiding jobs because the upstream API didn't tag them.
        if job_type_set:
            stmt = stmt.where(
                (JobMatch.job_type == "") | (JobMatch.job_type.in_(job_type_set))
            )
        if industry_set:
            stmt = stmt.where(
                (JobMatch.industry == "") | (JobMatch.industry.in_(industry_set))
            )
        # Salary: if no salary info, keep the job. Otherwise require the
        # stated range to overlap [min_salary, max_salary].
        if min_salary > 0 and max_salary > 0 and min_salary > max_salary:
            min_salary, max_salary = max_salary, min_salary
        if min_salary > 0:
            stmt = stmt.where(
                (JobMatch.salary_max == 0) | (JobMatch.salary_max >= min_salary)
            )
        if max_salary > 0:
            stmt = stmt.where(
                (JobMatch.salary_min == 0) | (JobMatch.salary_min <= max_salary)
            )
        if cutoff:
            stmt = stmt.where(
                (JobMatch.date_posted == "") | (JobMatch.date_posted >= cutoff)
            )
        # Years filter: exclude jobs whose description mentions a years
        # requirement BELOW min_years (too junior) or ABOVE max_years (too
        # senior). Jobs with no years mention are kept — better to over-show
        # than to silently drop postings the upstream API didn't tag.
        if min_years > 0 or max_years < 50:
            from sqlalchemy import or_
            exclude_clauses = []
            # Exclude "N+ years" / "N years" / "N yrs" for N below min_years
            for n in range(1, max(1, min_years)):
                exclude_clauses.append(
                    JobMatch.description.contains(f"{n}+ years")
                    | JobMatch.description.contains(f"{n} years")
                    | JobMatch.description.contains(f"{n} yrs")
                )
            # Exclude years above max_years
            if max_years < 50:
                for n in range(max_years + 1, 51):
                    exclude_clauses.append(
                        JobMatch.description.contains(f"{n}+ years")
                        | JobMatch.description.contains(f"{n} years")
                        | JobMatch.description.contains(f"{n} yrs")
                    )
            if exclude_clauses:
                stmt = stmt.where(~or_(*exclude_clauses))

        if sort == "recent":
            stmt = stmt.order_by(JobMatch.date_posted.desc(), JobMatch.match_score.desc())
        elif sort == "salary":
            stmt = stmt.order_by(JobMatch.salary_max.desc(), JobMatch.match_score.desc())
        else:  # best_match (default)
            stmt = stmt.order_by(JobMatch.match_score.desc(), JobMatch.created_at.desc())

        all_rows = s.exec(stmt).all()
        total = len(all_rows)
        rows = all_rows[offset : offset + limit]

        saved = [
            {
                "id": r.id, "title": r.title, "company": r.company,
                "location": r.location, "url": r.url, "description": r.description,
                "source": r.source, "match_score": r.match_score,
                "salary": r.salary, "is_deep_link": r.is_deep_link,
                "date_posted": r.date_posted, "job_type": r.job_type,
                "industry": r.industry, "is_remote": r.is_remote,
                "is_expired": r.is_expired,
                "salary_min": r.salary_min, "salary_max": r.salary_max,
                "match_breakdown": json.loads(r.match_breakdown or "{}"),
                "matched_skills": json.loads(r.matched_skills or "[]"),
                "missing_skills": json.loads(r.missing_skills or "[]"),
            }
            for r in rows
        ]

    activity.log_activity(
        "jobs_search",
        f"query={query}, location={search_loc}, sort={sort}, found={len(saved)}/{total}",
        profile_id,
    )
    return {
        "query": query,
        "total": total,
        "offset": offset,
        "limit": limit,
        "has_more": (offset + limit) < total,
        "jobs": saved,
    }


# ── Saved filter presets (Issue #7) ──────────────────────────────────────────

class SavedFilterIn(BaseModel):
    name: str
    filters: dict = {}
    sort: str = "best_match"


@router.get("/{profile_id}/saved-filters")
def list_saved_filters(
    profile_id: int,
    user: User = Depends(get_current_user),
):
    with Session(db.engine) as s:
        rows = s.exec(
            select(SavedFilter)
            .where(SavedFilter.user_id == user.id)
            .order_by(SavedFilter.created_at.desc())
        ).all()
        return [
            {
                "id": r.id,
                "name": r.name,
                "filters": json.loads(r.filters or "{}"),
                "sort": r.sort,
                "created_at": r.created_at.isoformat(),
            }
            for r in rows
        ]


@router.post("/{profile_id}/saved-filters", status_code=201)
def create_saved_filter(
    profile_id: int,
    body: SavedFilterIn,
    user: User = Depends(get_current_user),
):
    with Session(db.engine) as s:
        p = s.get(Profile, profile_id)
        if not p:
            raise HTTPException(404, "Profile not found")
        _check_ownership(s, p, user)
        sf = SavedFilter(
            user_id=user.id,
            profile_id=profile_id,
            name=body.name,
            filters=json.dumps(body.filters or {}),
            sort=body.sort or "best_match",
        )
        s.add(sf)
        s.commit()
        s.refresh(sf)
        return {
            "id": sf.id,
            "name": sf.name,
            "filters": json.loads(sf.filters or "{}"),
            "sort": sf.sort,
            "created_at": sf.created_at.isoformat(),
        }


@router.delete("/{profile_id}/saved-filters/{sf_id}", status_code=204)
def delete_saved_filter(
    profile_id: int,
    sf_id: int,
    user: User = Depends(get_current_user),
):
    with Session(db.engine) as s:
        sf = s.get(SavedFilter, sf_id)
        if not sf or sf.user_id != user.id:
            raise HTTPException(404, "Saved filter not found")
        s.delete(sf)
        s.commit()


@router.patch("/{profile_id}/saved-filters/{sf_id}")
def update_saved_filter(
    profile_id: int,
    sf_id: int,
    body: dict,
    user: User = Depends(get_current_user),
):
    """Edit a saved filter preset (rename + override filters / sort)."""
    with Session(db.engine) as s:
        sf = s.get(SavedFilter, sf_id)
        if not sf or sf.user_id != user.id:
            raise HTTPException(404, "Saved filter not found")
        if "name" in body and body["name"]:
            sf.name = str(body["name"]).strip()
        if "filters" in body and isinstance(body["filters"], dict):
            sf.filters = json.dumps(body["filters"])
        if "sort" in body and body["sort"]:
            sf.sort = str(body["sort"])
        s.add(sf)
        s.commit()
        s.refresh(sf)
        return {
            "id": sf.id,
            "name": sf.name,
            "filters": json.loads(sf.filters or "{}"),
            "sort": sf.sort,
            "created_at": sf.created_at.isoformat(),
        }


# ── External search deep links (Issue #1) ────────────────────────────────────

# Map our internal filter values to LinkedIn's `f_E` experience-level codes.
# LinkedIn's standard: 1=Internship, 2=Entry, 3=Associate, 4=Mid-Senior,
# 5=Director, 6=Executive.
_LINKEDIN_EXP_LEVELS = {
    "internship": "1",
    "entry": "2",
    "associate": "3",
    "mid-senior": "4",
    "director": "5",
    "executive": "6",
}

# Map our job_type tokens to LinkedIn's `f_WT` work-type codes.
# LinkedIn: 1=On-site, 2=Remote, 3=Hybrid.
_LINKEDIN_WORK_TYPES = {
    "full-time": "1",
    "remote": "2",
    "hybrid": "3",
}

# Map our date_posted tokens to LinkedIn's `f_TPR` (time posted, recency
# in seconds). r86400 = 24h, r604800 = 7d, r2592000 = 30d.
_LINKEDIN_TIME_POSTED = {
    "last_24h": "r86400",
    "last_7d": "r604800",
    "last_30d": "r2592000",
}


@router.get("/{profile_id}/external-search")
def external_search_links(
    profile_id: int,
    user: Optional[User] = Depends(get_current_user_optional),
    keywords: str = Query(default="", description="Override the keyword string used in deep links"),
    location: str = Query(default="", description="Override the location used in deep links"),
    experience_level: str = Query(
        default="",
        description="LinkedIn experience level: internship|entry|associate|mid-senior|director|executive",
    ),
    work_type: str = Query(
        default="",
        description="LinkedIn work type: full-time|remote|hybrid",
    ),
    time_posted: str = Query(
        default="",
        description="Recency filter: last_24h|last_7d|last_30d",
    ),
    salary_min: int = Query(default=0, ge=0),
    salary_currency: str = Query(
        default="USD",
        description="3-letter currency code (USD, INR, GBP, EUR, CAD, AUD, SGD, JPY)",
    ),
):
    """Generate pre-filled external search URLs (LinkedIn, Indeed, Glassdoor,
    Google Jobs). The `keywords` and `location` query params let the frontend
    pass the current session's inputs (so the links reflect the Job Title
    and Location fields the user is currently editing) instead of the stale
    profile defaults. The advanced filters — experience level, work type,
    time posted, salary + currency — are forwarded to the deep links as
    platform-specific parameters so the external site opens with the same
    filtering the user applied in the in-app search."""
    with Session(db.engine) as s:
        p = s.get(Profile, profile_id)
        if not p:
            raise HTTPException(404, "Profile not found")
        if user:
            _check_ownership(s, p, user)
        elif p.user_id is not None:
            raise HTTPException(403, "Forbidden")
        s.refresh(p)
        # Read relationships inside the session so they don't detach
        role = ""
        if p.experience and p.experience[0] and p.experience[0].role:
            role = p.experience[0].role
        all_skills = [
            sk.name for sk in (p.skills or []) if sk.name
        ]
        default_location = p.location or "Remote"

    if not role:
        role = "Software Engineer"

    if keywords and keywords.strip():
        kw = keywords.strip()
    else:
        kw = " ".join([role] + all_skills) if all_skills else role
    loc = location.strip() or default_location
    encoded_kw = urllib.parse.quote(kw)
    encoded_loc = urllib.parse.quote(loc)

    # Normalise the currency to a 3-letter uppercase code. Default to USD
    # when the frontend sends something blank or invalid.
    cur = (salary_currency or "USD").strip().upper()[:3] or "USD"

    # LinkedIn deep-link parameters
    linkedin_f_E = _LINKEDIN_EXP_LEVELS.get(experience_level, "")
    linkedin_f_WT = _LINKEDIN_WORK_TYPES.get(work_type, "")
    linkedin_f_TPR = _LINKEDIN_TIME_POSTED.get(time_posted, "r86400")

    # Build the LinkedIn query string. LinkedIn accepts these as separate
    # `&f_` parameters and combines them server-side.
    linkedin_extra = []
    if linkedin_f_E:
        linkedin_extra.append(f"f_E={linkedin_f_E}")
    if linkedin_f_WT:
        linkedin_extra.append(f"f_WT={linkedin_f_WT}")
    if linkedin_f_TPR:
        linkedin_extra.append(f"f_TPR={linkedin_f_TPR}")
    if salary_min > 0:
        linkedin_extra.append(f"f_SB2={salary_min}")
        linkedin_extra.append(f"f_C={cur}")
    linkedin_extra_str = "&" + "&".join(linkedin_extra) if linkedin_extra else ""

    # Indeed: fromage = days since posting. 1=last day, 3=3 days, 7=7 days,
    # 14=14 days. salary param format varies; we use the simple "Salary
    # min" with currency encoded into the label.
    indeed_fromage_map = {"last_24h": "1", "last_7d": "7", "last_30d": "14"}
    indeed_fromage = indeed_fromage_map.get(time_posted, "")
    indeed_extra = []
    if indeed_fromage:
        indeed_extra.append(f"fromage={indeed_fromage}")
    if salary_min > 0:
        indeed_extra.append(f"salary={salary_min}")
    if linkedin_f_WT == "2":
        indeed_extra.append("remotejob=032b3046-708a-4bbf-8c5e-60b0c4e87b1a")
    indeed_extra_str = "&" + "&".join(indeed_extra) if indeed_extra else ""

    # Glassdoor: param name varies; includeSalary=true and fromAge as days.
    glassdoor_extra = []
    if time_posted == "last_24h":
        glassdoor_extra.append("fromAge=1")
    elif time_posted == "last_7d":
        glassdoor_extra.append("fromAge=7")
    elif time_posted == "last_30d":
        glassdoor_extra.append("fromAge=30")
    if linkedin_f_WT == "2":
        glassdoor_extra.append("remoteWorkType=1")
    elif linkedin_f_WT == "3":
        glassdoor_extra.append("remoteWorkType=2")
    if salary_min > 0:
        glassdoor_extra.append(f"minSalary={salary_min}")
    glassdoor_extra_str = "&" + "&".join(glassdoor_extra) if glassdoor_extra else ""

    # Google Jobs: time_posted via `since` param (d_ = days, h_ = hours,
    # w_ = weeks, m_ = months; default = no limit).
    google_since_map = {
        "last_24h": "d_1",
        "last_7d": "w_1",
        "last_30d": "m_1",
    }
    google_since = google_since_map.get(time_posted, "")
    google_extra = []
    if google_since:
        google_extra.append(f"since={google_since}")
    if linkedin_f_WT == "2":
        google_extra.append("q=remote+work")
    google_extra_str = "&" + "&".join(google_extra) if google_extra else ""

    return {
        "keywords": kw,
        "location": loc,
        "currency": cur,
        "links": [
            {
                "portal": "linkedin",
                "label": "LinkedIn",
                # LinkedIn: f_TPR=time posted, f_E=experience level,
                # f_WT=work type (1=on-site, 2=remote, 3=hybrid),
                # f_SB2=salary min, f_C=currency code, sortBy=R = relevance
                "url": (
                    f"https://www.linkedin.com/jobs/search/?"
                    f"keywords={encoded_kw}"
                    f"&location={encoded_loc}"
                    f"&f_TPR={linkedin_f_TPR}"
                    f"{linkedin_extra_str}"
                    f"&sortBy=R"
                ),
                "icon": "💼",
            },
            {
                "portal": "indeed",
                "label": "Indeed",
                # Indeed: fromage=days since posted, salary=min salary
                "url": (
                    f"https://www.indeed.com/jobs?"
                    f"q={encoded_kw}"
                    f"&l={encoded_loc}"
                    f"&sort=date"
                    f"{indeed_extra_str}"
                ),
                "icon": "🔎",
            },
            {
                "portal": "glassdoor",
                "label": "Glassdoor",
                "url": (
                    f"https://www.glassdoor.com/Job/jobs.htm?"
                    f"sc.keyword={encoded_kw}"
                    f"&locT=C&locN={encoded_loc}"
                    f"{glassdoor_extra_str}"
                ),
                "icon": "🏢",
            },
            {
                "portal": "google_jobs",
                "label": "Google Jobs",
                # Google Jobs aggregator URL. Uses the official
                # `ibp=htl;jobs` parameter (URL-encoded as %3B) to
                # switch the result set to the Jobs vertical so the
                # search opens directly in Jobs mode, not regular
                # web search.
                "url": (
                    f"https://www.google.com/search?"
                    f"q={encoded_kw}+jobs+{encoded_loc}"
                    f"&ibp=htl%3Bjobs"
                    f"{google_extra_str}"
                ),
                "icon": "🌐",
            },
        ],
    }
