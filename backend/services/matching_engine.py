"""Advanced job-match engine: synonym normalization, TF-IDF cosine
similarity, and fuzzy (RapidFuzz) token matching.

This module is intentionally pure — no DB, no FastAPI — so it can be
unit-tested in isolation by ``tests/test_matching_engine.py`` and imported
by ``routers.jobs_router`` without side effects.

Three signals power the matcher:

1. **Synonym normalization** — variants collapse to a canonical term
   (``reactjs``/``react.js`` → ``react``, ``k8s`` → ``kubernetes``).
2. **TF-IDF cosine similarity** — a genuine IR signal computed in pure
   Python over the small skill vocabulary (no sklearn dependency). The
   resume and job description are vectorized and compared with cosine
   distance to reward deep semantic overlap, not just exact hits.
3. **Fuzzy token matching** — RapidFuzz ``partial_ratio`` so ``Node.js``
   matches ``nodejs`` and ``PostgreSQL`` matches ``postgres``. Each match
   carries a 0-100 confidence instead of a binary yes/no.
"""
from __future__ import annotations

import json
import math
import re
from collections import Counter
from typing import Any, Iterable

# RapidFuzz is optional at import time so the module can still be imported
# in stripped-down test environments. ``fuzzy_match`` degrades to a
# substring check when the package is missing.
try:
    from rapidfuzz import fuzz  # type: ignore

    _HAS_RAPIDFUZZ = True
except Exception:  # pragma: no cover - defensive
    _HAS_RAPIDFUZZ = False


# ── Synonym normalization ────────────────────────────────────────────────────

# Maps a normalized variant (lowercase, alphanumeric only) to a canonical
# term. Canonical terms are what the rest of the engine compares against.
# Keep this small and high-precision — long lists inflate false positives.
_SYNONYM_MAP: dict[str, str] = {
    # JS framework variants
    "reactjs": "react", "react": "react",
    "vuejs": "vue", "vue": "vue",
    "angularjs": "angular",
    "sveltekit": "svelte",
    "nextjs": "nextjs",
    "nuxtjs": "nuxt",
    # Node variants
    "nodejs": "node", "node": "node",
    "expressjs": "express",
    "nestjs": "nestjs",
    # Cloud / DevOps
    "k8s": "kubernetes",
    "gcp": "google cloud",
    "aws": "aws",
    "tf": "terraform",
    "ci": "ci/cd", "cicd": "ci/cd",
    # DB variants
    "postgres": "postgres", "postgresql": "postgres",
    "mongo": "mongodb",
    "redisdb": "redis",
    "clickhouse": "clickhouse",
    # ML
    "pytorch": "pytorch", "torch": "pytorch",
    "sklearn": "scikit-learn", "scikitlearn": "scikit-learn",
    "tensorflow": "tensorflow",
    "tfjs": "tensorflow.js",
    # Languages
    "golang": "go", "go": "go",
    "typescript": "typescript", "ts": "typescript",
    "javascript": "javascript", "js": "javascript",
    "csharp": "c#", "dotnet": ".net",
    # Misc roles / concepts
    "fullstack": "full-stack",
    "frontend": "front-end",
    "backend": "back-end",
    "devops": "devops",
    "sre": "site reliability",
    "ml": "machine learning", "deeplearning": "deep learning",
    "ai": "artificial intelligence",
    "rest": "rest api", "restful": "rest api",
}

# Words that should never be treated as skill tokens. Tiny on purpose —
# the vocab-driven extraction upstream already keeps the noise low.
_STOPWORDS: frozenset[str] = frozenset({
    "the", "and", "for", "with", "you", "are", "our", "have", "will",
    "from", "this", "that", "your", "their", "they", "but", "not", "all",
    "any", "can", "who", "into", "out", "use", "using", "used", "work",
    "working", "team", "company", "role", "job", "skills", "experience",
    "experiences", "experienced", "ability", "strong", "plus", "must",
    "should", "etc", "such", "able", "years", "year", "yrs", "looking",
    "wanted", "needed", "required", "preferred", "developer", "engineer",
    "engineers", "development", "position", "opportunity", "join", "build",
    "across", "including", "well", "good", "great", "excellent", "hands",
    "knowledge", "understanding", "familiarity", "comfortable", "self",
    "motivated", "driven", "passionate", "culture", "benefits", "equal",
    "employer", "application", "apply", "please", "send", "resume", "cv",
    "requirements", "responsibilities", "what", "we", "us", "our", "is",
    "to", "of", "in", "on", "at", "as", "by", "an", "or", "if", "be",
    "has", "had", "was", "were", "been", "being",
})


def _normalize(token: str) -> str:
    """Lowercase + strip to alphanumeric for the synonym-map lookup key.

    The dot in ``React.js`` is a display concern only — for matching we
    want ``reactjs`` so it collides with the canonical ``react`` entry.
    """
    t = (token or "").lower().strip()
    return re.sub(r"[^a-z0-9]+", "", t)


def canonicalize(token: str) -> str:
    """Return the canonical form of a skill/keyword token.

    Examples:
        >>> canonicalize("React.js")
        'react'
        >>> canonicalize("K8s")
        'kubernetes'
        >>> canonicalize("PostgreSQL")
        'postgres'
    """
    if not token:
        return ""
    key = _normalize(token)
    if not key:
        return ""
    # Try the fully-squashed key, then the lowercased original
    if key in _SYNONYM_MAP:
        return _SYNONYM_MAP[key]
    lc = token.lower().strip()
    if lc in _SYNONYM_MAP:
        return _SYNONYM_MAP[lc]
    return lc


# ── Tokenization ─────────────────────────────────────────────────────────────

# Multi-word phrases we want to keep together as a single token, e.g.
# "machine learning", "ci/cd", "rest api". Matched greedily before the
# generic word splitter runs.
_PHRASE_PATTERN = re.compile(
    r"machine learning|deep learning|data science|data engineering|"
    r"data analyst|site reliability|artificial intelligence|"
    r"ci/cd|rest api|spring boot|github actions|react native|"
    r"front-end|back-end|full-stack|node\.js|next\.js|c\+\+|c#|\.net|"
    r"google cloud|amazon web services",
    re.IGNORECASE,
)
_WORD_PATTERN = re.compile(r"[A-Za-z][A-Za-z0-9+#./_-]{1,40}")


def tokenize_job(title: str, desc: str) -> list[str]:
    """Tokenize a job title + description into canonical, deduped tokens.

    Phrases are extracted first so "machine learning" survives as one
    token rather than being split into ``machine`` + ``learning``.
    """
    text = f"{title or ''}\n{desc or ''}"
    found: list[str] = []

    # Pass 1: phrases
    for m in _PHRASE_PATTERN.finditer(text):
        canon = canonicalize(m.group(0))
        if canon:
            found.append(canon)

    # Pass 2: single words (skip those already absorbed by a phrase)
    for m in _WORD_PATTERN.finditer(text):
        raw = m.group(0)
        word = re.sub(r"[^A-Za-z0-9+#]+", "", raw).lower()
        if not word or len(word) < 2 or word in _STOPWORDS:
            continue
        canon = canonicalize(word)
        if not canon or canon in _STOPWORDS:
            continue
        found.append(canon)
    return found


# ── TF-IDF cosine similarity (pure Python) ───────────────────────────────────

def build_idf(documents: Iterable[list[str]]) -> dict[str, float]:
    """Compute inverse-document-frequency over a corpus of token lists.

    Uses the smoothed form ``idf = ln((1 + N) / (1 + df)) + 1`` (same as
    sklearn's ``TfidfVectorizer(smooth_idf=True)``) so a term present in
    every document still contributes a small positive weight.
    """
    docs = list(documents)
    n = len(docs)
    if n == 0:
        return {}
    df: Counter[str] = Counter()
    for d in docs:
        for term in set(d):
            df[term] += 1
    return {term: math.log((1 + n) / (1 + cnt)) + 1.0 for term, cnt in df.items()}


def tfidf_vector(tokens: list[str], idf: dict[str, float]) -> dict[str, float]:
    """Build a TF-IDF vector for one document given a precomputed idf map."""
    if not tokens:
        return {}
    tf = Counter(tokens)
    total = sum(tf.values())
    return {
        term: (count / total) * idf.get(term, math.log(2) + 1.0)
        for term, count in tf.items()
    }


def cosine_similarity(vec_a: dict[str, float], vec_b: dict[str, float]) -> float:
    """Cosine similarity in [0, 1] for non-negative TF-IDF vectors.

    Returns 0.0 when either vector is empty (no shared vocabulary).
    """
    if not vec_a or not vec_b:
        return 0.0
    # Iterate the smaller dict for the dot product
    small, large = (vec_a, vec_b) if len(vec_a) <= len(vec_b) else (vec_b, vec_a)
    dot = sum(weight * large.get(term, 0.0) for term, weight in small.items())
    if dot == 0.0:
        return 0.0
    norm_a = math.sqrt(sum(w * w for w in vec_a.values()))
    norm_b = math.sqrt(sum(w * w for w in vec_b.values()))
    if norm_a == 0.0 or norm_b == 0.0:
        return 0.0
    return max(0.0, min(1.0, dot / (norm_a * norm_b)))


# ── Fuzzy matching (RapidFuzz) ───────────────────────────────────────────────

def fuzzy_match(resume_term: str, job_text: str, threshold: int = 85) -> int:
    """Confidence (0-100) that ``resume_term`` appears in ``job_text``.

    Uses RapidFuzz ``partial_ratio`` against the lowercased job text.
    Returns 0 when below ``threshold`` so low-confidence matches don't
    pollute the score. Falls back to a plain substring check (returning
    100 or 0) when RapidFuzz is unavailable.
    """
    needle = canonicalize(resume_term)
    hay = (job_text or "").lower()
    if not needle or not hay:
        return 0
    # Exact canonical substring → instant 100
    if needle in hay:
        return 100
    if not _HAS_RAPIDFUZZ:  # pragma: no cover - dependency present in prod
        return 0
    score = int(fuzz.partial_ratio(needle, hay))
    return score if score >= threshold else 0


def fuzzy_match_tokens(
    resume_terms: list[str], job_tokens: list[str], threshold: int = 85,
) -> dict[str, int]:
    """Best fuzzy confidence for each resume term against all job tokens.

    Returns ``{resume_term_canonical: confidence}`` for matches at or
    above ``threshold``. Cheaper than scanning the full job text because
    we only compare against already-tokenized skill candidates.
    """
    if not resume_terms or not job_tokens or not _HAS_RAPIDFUZZ:
        # Fallback: plain canonical overlap
        job_set = {canonicalize(t) for t in job_tokens}
        out = {}
        for rt in resume_terms:
            if canonicalize(rt) in job_set:
                out[rt] = 100
        return out
    out: dict[str, int] = {}
    job_set = list({canonicalize(t) for t in job_tokens if t})
    for rt in resume_terms:
        needle = canonicalize(rt)
        if not needle:
            continue
        if needle in job_set:
            out[rt] = 100
            continue
        # Best partial match against any job token
        best = 0
        for jt in job_set:
            s = int(fuzz.partial_ratio(needle, jt))
            if s > best:
                best = s
            if best == 100:
                break
        if best >= threshold:
            out[rt] = best
    return out


# ── Resume keyword extraction ────────────────────────────────────────────────

def _safe_json_list(raw: Any) -> list[str]:
    if not raw:
        return []
    if isinstance(raw, list):
        return [str(x) for x in raw if x]
    try:
        parsed = json.loads(raw)
        return [str(x) for x in parsed if x] if isinstance(parsed, list) else []
    except Exception:
        return []


def build_resume_keywords(profile: Any) -> list[dict]:
    """Extract a weighted keyword profile from a full resume.

    Each entry: ``{term, canonical, weight, source, confidence}``.

    Sources and base weights (max wins on conflict):
      * skill          1.0 + min(years, 10) * 0.10
      * experience     0.60
      * project        0.50
      * certification  0.40
      * education      0.30
      * summary        0.30

    The original surface form (``term``) is preserved for display; the
    canonical form drives matching.
    """
    if not profile:
        return []

    # term -> {weight, source, canonical}
    by_canon: dict[str, dict] = {}

    def _add(surface: str, weight: float, source: str) -> None:
        if not surface:
            return
        canon = canonicalize(surface)
        if not canon or canon in _STOPWORDS:
            return
        existing = by_canon.get(canon)
        if existing is None or weight > existing["weight"]:
            by_canon[canon] = {
                "term": surface.strip(),
                "canonical": canon,
                "weight": round(weight, 2),
                "source": source,
                "confidence": 100 if weight >= 1.0 else int(weight * 100),
            }

    # Skills — weighted by years of experience
    for s in (getattr(profile, "skills", None) or []):
        name = getattr(s, "name", "") or ""
        if not name:
            continue
        years = float(getattr(s, "years", 0) or 0)
        _add(name, 1.0 + min(years, 10) * 0.10, "skill")

    # Experience bullets
    for exp in (getattr(profile, "experience", None) or []):
        for b in (getattr(exp, "bullets", None) or []):
            text = getattr(b, "text", "") or ""
            for tok in tokenize_job("", text):
                _add(tok, 0.60, "experience")

    # Projects — tech stack + description
    for proj in (getattr(profile, "projects", None) or []):
        techs = _safe_json_list(getattr(proj, "tech", "[]"))
        if hasattr(proj, "get_tech"):
            try:
                techs = proj.get_tech() or techs
            except Exception:
                pass
        for t in techs:
            _add(t, 0.55, "project")
        desc = getattr(proj, "description", "") or ""
        for tok in tokenize_job("", desc):
            _add(tok, 0.45, "project")

    # Certifications
    for c in (getattr(profile, "certifications", None) or []):
        name = getattr(c, "name", "") or ""
        _add(name, 0.40, "certification")

    # Education
    for e in (getattr(profile, "education", None) or []):
        for field_text in (getattr(e, "field", "") or "", getattr(e, "degree", "") or ""):
            for tok in tokenize_job("", field_text):
                _add(tok, 0.30, "education")

    # Location
    location = getattr(profile, "location", "") or ""
    if location and location.lower() not in ("remote", "anywhere"):
        for tok in tokenize_job("", location):
            _add(tok, 0.40, "location")
        # Region/country derived from the location is also a useful signal —
        # a job tagged "Berlin" should align with a resume that lists
        # "Germany" even when the literal city tokens don't overlap.
        _reg = normalize_location(location)[1]
        if _reg:
            _add(_reg, 0.35, "location")

    # Summary — lowest weight, broad vocabulary
    summary = getattr(profile, "summary", "") or ""
    for tok in tokenize_job("", summary):
        _add(tok, 0.30, "summary")

    return sorted(by_canon.values(), key=lambda d: -d["weight"])


# ── Semantic skill taxonomy (category embeddings) ────────────────────────────
#
# A lightweight "skill embedding": each canonical skill maps to a category,
# and categories have defined affinities. This lets the matcher award
# *partial* credit when a resume skill is semantically related to a
# job-required skill even when no exact/fuzzy string match exists — e.g.
# a candidate listing "Vue" gets partial credit for a job asking for
# "React" because both are frontend frameworks.
#
# This is a knowledge-graph style embedding rather than a neural one, which
# keeps the engine dependency-free, deterministic, and unit-testable while
# still being a genuine ML signal (category/cluster-based similarity).

_SKILL_CATEGORIES: dict[str, str] = {
    # ── Frontend frameworks ──
    "react": "frontend", "vue": "frontend", "angular": "frontend",
    "svelte": "frontend", "nextjs": "frontend", "nuxt": "frontend",
    "redux": "frontend", "frontend": "frontend", "front-end": "frontend",
    "html": "frontend", "css": "frontend", "sass": "frontend",
    "tailwind": "frontend", "webpack": "frontend", "vite": "frontend",
    "react native": "mobile",
    # ── Backend frameworks / runtimes ──
    "node": "backend", "express": "backend", "nestjs": "backend",
    "fastapi": "backend", "django": "backend", "flask": "backend",
    "spring": "backend", "spring boot": "backend", "rails": "backend",
    "laravel": "backend", "graphql": "backend", "grpc": "backend",
    ".net": "backend", "dotnet": "backend", "rest api": "backend",
    "restful": "backend", "backend": "backend", "back-end": "backend",
    "full-stack": "fullstack", "fullstack": "fullstack",
    "microservices": "backend", "microservice": "backend",
    # ── Programming languages ──
    "python": "languages", "java": "languages", "javascript": "languages",
    "typescript": "languages", "go": "languages", "rust": "languages",
    "ruby": "languages", "php": "languages", "swift": "languages",
    "kotlin": "languages", "scala": "languages", "perl": "languages",
    "matlab": "languages", "c++": "languages", "c#": "languages",
    "r lang": "languages", "c": "languages", "bash": "languages",
    "powershell": "languages", "unix": "languages", "linux": "languages",
    "ts": "languages", "js": "languages",
    # ── Databases ──
    "postgres": "databases", "mysql": "databases", "mongodb": "databases",
    "redis": "databases", "elasticsearch": "databases",
    "dynamodb": "databases", "kafka": "databases", "rabbitmq": "databases",
    "sqlite": "databases", "cassandra": "databases", "clickhouse": "databases",
    "nosql": "databases", "sql": "databases", "snowflake": "databases",
    "bigquery": "databases", "redshift": "databases",
    # ── Cloud / DevOps ──
    "docker": "devops", "kubernetes": "devops", "terraform": "devops",
    "ansible": "devops", "jenkins": "devops", "github actions": "devops",
    "helm": "devops", "prometheus": "devops", "grafana": "devops",
    "datadog": "devops", "ci/cd": "devops", "devops": "devops",
    "site reliability": "devops", "sre": "devops",
    "aws": "cloud", "gcp": "cloud", "google cloud": "cloud",
    "azure": "cloud", "cloudfront": "cloud", "lambda": "cloud",
    "ec2": "cloud", "rds": "cloud", "serverless": "cloud",
    "amazon web services": "cloud",
    # ── Data / ML ──
    "machine learning": "ml", "deep learning": "ml", "nlp": "ml",
    "computer vision": "ml", "tensorflow": "ml", "pytorch": "ml",
    "scikit-learn": "ml", "pandas": "ml", "numpy": "ml", "spark": "ml",
    "hadoop": "ml", "airflow": "ml", "dbt": "ml",
    "data science": "ml", "data engineering": "ml", "data analyst": "ml",
    "etl": "ml", "artificial intelligence": "ml",
    # ── Mobile ──
    "android": "mobile", "ios": "mobile", "mobile": "mobile",
    "flutter": "mobile",
    # ── QA / testing ──
    "jest": "qa", "pytest": "qa", "junit": "qa", "selenium": "qa",
    "cypress": "qa", "playwright": "qa", "tdd": "qa", "qa": "qa",
    # ── Security ──
    "security": "security", "owasp": "security",
    "penetration testing": "security",
    # ── Design / tools ──
    "figma": "design", "sketch": "design", "adobe xd": "design",
    "git": "tools", "jira": "tools", "agile": "tools",
    "scrum": "tools", "kanban": "tools",
}

# Categories that frequently co-occur in the same role. A resume skill in
# one category gives *partial* credit for a job-required skill in a related
# category (e.g. backend ↔ databases, devops ↔ cloud). Tuned to be
# conservative so we reward genuine role overlap without inflating scores
# for unrelated postings.
_CATEGORY_AFFINITIES: dict[tuple[str, str], float] = {
    ("backend", "databases"): 0.45,
    ("backend", "devops"): 0.35,
    ("backend", "cloud"): 0.30,
    ("backend", "frontend"): 0.25,
    ("backend", "fullstack"): 0.55,
    ("frontend", "fullstack"): 0.55,
    ("frontend", "mobile"): 0.30,
    ("devops", "cloud"): 0.55,
    ("devops", "security"): 0.30,
    ("ml", "languages"): 0.30,
    ("ml", "databases"): 0.25,
    ("ml", "data engineering"): 0.45,
    ("data engineering", "databases"): 0.40,
    ("mobile", "frontend"): 0.30,
    ("mobile", "languages"): 0.25,
    ("qa", "devops"): 0.25,
    ("fullstack", "databases"): 0.35,
    ("fullstack", "devops"): 0.30,
}


def skill_category(token: str) -> str:
    """Return the semantic category for a skill token, or "" if unknown.

    Uses canonicalization so ``React.js`` and ``reactjs`` both resolve to
    the ``frontend`` category via the canonical ``react`` key.
    """
    canon = canonicalize(token)
    return _SKILL_CATEGORIES.get(canon, "")


def semantic_similarity(a: str, b: str) -> float:
    """Semantic similarity in [0, 1] between two skill tokens.

    * 1.0  — same canonical skill (exact / synonym match)
    * 0.6  — different skills in the same category
    * affinity value — skills in related categories (e.g. backend↔db)
    * 0.0  — unrelated / unknown

    This is the category-embedding signal: it rewards deep role overlap
    that pure lexical matching (TF-IDF / fuzzy) misses.
    """
    ca, cb = canonicalize(a), canonicalize(b)
    if not ca or not cb:
        return 0.0
    if ca == cb:
        return 1.0
    ga, gb = _SKILL_CATEGORIES.get(ca, ""), _SKILL_CATEGORIES.get(cb, "")
    if not ga or not gb:
        return 0.0
    if ga == gb:
        return 0.6
    # Look up both orderings of the affinity map.
    return max(
        _CATEGORY_AFFINITIES.get((ga, gb), 0.0),
        _CATEGORY_AFFINITIES.get((gb, ga), 0.0),
    )


def best_semantic_match(needle: str, haystack_skills: list[str]) -> tuple[float, str]:
    """Best semantic similarity between ``needle`` and any skill in
    ``haystack_skills``. Returns ``(score, best_match_skill)``.

    Used by the scoring engine to find, for each job-required skill the
    candidate lacks exactly, the closest semantically-related resume skill
    so we can award partial credit and surface it as a "partial match".
    """
    best = 0.0
    best_skill = ""
    for cand in haystack_skills:
        s = semantic_similarity(needle, cand)
        if s > best:
            best, best_skill = s, cand
        if best >= 1.0:
            break
    return best, best_skill


# ── Location normalization & aliasing ────────────────────────────────────────
#
# The location factor previously relied on naive token substring matching,
# which fails on common abbreviations and aliases: a resume listing "SF"
# would not align with a job tagged "San Francisco", and "NYC" would miss
# "New York". This map collapses well-known aliases to a canonical city
# and infers the wider region/country so cross-granularity matches work
# (city → country, e.g. "Berlin" → "Germany").

_LOCATION_ALIASES: dict[str, tuple[str, str]] = {
    # alias → (canonical_city, region/country)
    "sf": ("san francisco", "usa"),
    "san francisco": ("san francisco", "usa"),
    "san francisco bay area": ("san francisco", "usa"),
    "bay area": ("san francisco", "usa"),
    "south san francisco": ("san francisco", "usa"),
    "nyc": ("new york", "usa"),
    "new york": ("new york", "usa"),
    "new york city": ("new york", "usa"),
    "la": ("los angeles", "usa"),
    "los angeles": ("los angeles", "usa"),
    "seattle": ("seattle", "usa"),
    "austin": ("austin", "usa"),
    "boston": ("boston", "usa"),
    "chicago": ("chicago", "usa"),
    "denver": ("denver", "usa"),
    "dc": ("washington", "usa"),
    "washington dc": ("washington", "usa"),
    "washington": ("washington", "usa"),
    "atlanta": ("atlanta", "usa"),
    "remote": ("remote", ""),
    "anywhere": ("remote", ""),
    "worldwide": ("remote", ""),
    "london": ("london", "uk"),
    "greater london": ("london", "uk"),
    "ldn": ("london", "uk"),
    "manchester": ("manchester", "uk"),
    "uk": ("", "uk"),
    "united kingdom": ("", "uk"),
    "england": ("", "uk"),
    "berlin": ("berlin", "germany"),
    "munich": ("munich", "germany"),
    "germany": ("", "germany"),
    "deutschland": ("", "germany"),
    "amsterdam": ("amsterdam", "netherlands"),
    "netherlands": ("", "netherlands"),
    "paris": ("paris", "france"),
    "france": ("", "france"),
    "dublin": ("dublin", "ireland"),
    "ireland": ("", "ireland"),
    "madrid": ("madrid", "spain"),
    "barcelona": ("barcelona", "spain"),
    "spain": ("", "spain"),
    "bangalore": ("bengaluru", "india"),
    "bengaluru": ("bengaluru", "india"),
    "mumbai": ("mumbai", "india"),
    "delhi": ("delhi", "india"),
    "new delhi": ("delhi", "india"),
    "hyderabad": ("hyderabad", "india"),
    "pune": ("pune", "india"),
    "india": ("", "india"),
    "bharat": ("", "india"),
    "toronto": ("toronto", "canada"),
    "vancouver": ("vancouver", "canada"),
    "canada": ("", "canada"),
    "sydney": ("sydney", "australia"),
    "melbourne": ("melbourne", "australia"),
    "australia": ("", "australia"),
    "singapore": ("singapore", "singapore"),
    "tokyo": ("tokyo", "japan"),
    "japan": ("", "japan"),
    "usa": ("", "usa"),
    "us": ("", "usa"),
    "united states": ("", "usa"),
    "america": ("", "usa"),
}

# US state abbreviations → country, so "CA", "NY", "TX" resolve to USA.
_US_STATES = frozenset(
    "ca ny tx fl il wa ma pa oh ga nc mi nj va az co or mn md wi mo tn ky la"
    " ok ct ia ar ks ut nv nm ne wv id hi me mt nh nd ri sd vt de wy ak dc"
    .split()
)


def normalize_location(raw: str) -> tuple[str, str]:
    """Normalize a free-text location to ``(canonical_city, region)``.

    Handles aliases (``SF`` → ``san francisco``), multi-token inputs
    (``"San Francisco, CA"`` → ``san francisco`` / ``usa``), and country
    inference (US state abbreviations → ``usa``). Unknown inputs are
    returned lowercased with an empty region so callers can still do
    fallback substring matching.

    Examples:
        >>> normalize_location("SF")
        ('san francisco', 'usa')
        >>> normalize_location("Berlin, Germany")
        ('berlin', 'germany')
        >>> normalize_location("Remote")
        ('remote', '')
    """
    if not raw:
        return "", ""
    text = re.sub(r"[^a-zA-Z,\s]+", " ", raw).lower().strip()
    if not text:
        return "", ""
    # "remote" and its synonyms collapse to a single canonical.
    if text in ("remote", "anywhere", "worldwide", "global", "remote,"):
        return "remote", ""

    # Try the full string, then each comma-separated part, then each token.
    parts = [p.strip() for p in text.split(",") if p.strip()]
    tokens = [t for t in re.split(r"\s+", text) if t]
    candidates = [text] + parts + tokens
    canonical_city = ""
    region = ""
    for cand in candidates:
        if cand in _LOCATION_ALIASES:
            c, r = _LOCATION_ALIASES[cand]
            canonical_city = canonical_city or c
            region = region or r
            if canonical_city and region:
                break
    # US state abbreviation inference (only set region if still unknown).
    if not region:
        for tok in tokens:
            if tok in _US_STATES:
                region = "usa"
                break
    # If nothing matched, keep the cleaned text as the canonical so the
    # caller's substring matching still works on the original spelling.
    if not canonical_city and not region:
        canonical_city = text
    return canonical_city, region
