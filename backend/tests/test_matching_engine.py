"""Unit tests for the advanced matching engine (TF-IDF, fuzzy, synonyms, keywords).

This file imports from ``services.matching_engine`` which is a pure-Python
module with no DB/FastAPI dependencies — so tests are fast and isolated.
"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from services.matching_engine import (
    canonicalize,
    tokenize_job,
    build_idf,
    tfidf_vector,
    cosine_similarity,
    fuzzy_match,
    fuzzy_match_tokens,
    build_resume_keywords,
    skill_category,
    semantic_similarity,
    best_semantic_match,
    normalize_location,
    _STOPWORDS,
)


# ── Synonym normalization ──────────────────────────────────────────────────────

class TestCanonicalize:
    def test_react_dot_js(self):
        assert canonicalize("React.js") == "react"

    def test_reactjs(self):
        assert canonicalize("ReactJS") == "react"

    def test_react(self):
        assert canonicalize("React") == "react"

    def test_node_dot_js(self):
        assert canonicalize("Node.js") == "node"

    def test_nodejs(self):
        assert canonicalize("NodeJS") == "node"

    def test_k8s(self):
        assert canonicalize("K8s") == "kubernetes"

    def test_postgresql(self):
        assert canonicalize("PostgreSQL") == "postgres"

    def test_postgres(self):
        assert canonicalize("postgres") == "postgres"

    def test_golang(self):
        assert canonicalize("Golang") == "go"

    def test_dotnet(self):
        assert canonicalize("dotnet") == ".net"

    def test_torch_to_pytorch(self):
        assert canonicalize("Torch") == "pytorch"

    def test_sklearn_to_scikit(self):
        assert canonicalize("sklearn") == "scikit-learn"

    def test_empty(self):
        assert canonicalize("") == ""

    def test_unknown_token_unchanged(self):
        assert canonicalize("django") == "django"

    def test_case_insensitive(self):
        assert canonicalize("AWS") == canonicalize("aws")


# ── Tokenization ─────────────────────────────────────────────────────────────

class TestTokenizeJob:
    def test_basic_skills(self):
        tokens = tokenize_job("Python Developer", "Python FastAPI AWS")
        assert "python" in tokens
        assert "fastapi" in tokens
        assert "aws" in tokens

    def test_phrase_preserved(self):
        tokens = tokenize_job("", "Experience with machine learning and deep learning models")
        assert "machine learning" in tokens
        assert "deep learning" in tokens

    def test_synonym_in_tokens(self):
        tokens = tokenize_job("Node Developer", "Looking for a Node.js developer")
        assert "node" in tokens  # "Node.js" → canonical "node"

    def test_stopwords_excluded(self):
        tokens = tokenize_job("", "You will be working with a great team")
        for sw in ("you", "will", "be", "with", "a", "great", "team"):
            assert sw not in [t for t in tokens]

    def test_react_from_job_desc(self):
        tokens = tokenize_job("Frontend Engineer", "React frontend application")
        assert "react" in tokens
        assert "front-end" in tokens

    def test_empty_input(self):
        assert tokenize_job("", "") == []


# ── TF-IDF cosine similarity ───────────────────────────────────────────────────

class TestTfIdf:
    def test_identical_docs_one(self):
        docs = [["python", "react"]]
        idf = build_idf(docs)
        v = tfidf_vector(["python", "react"], idf)
        assert abs(cosine_similarity(v, v) - 1.0) < 1e-9

    def test_identical_docs_two(self):
        docs = [["python", "react", "aws"]]
        idf = build_idf(docs)
        v1 = tfidf_vector(["python", "react", "aws"], idf)
        v2 = tfidf_vector(["python", "react", "aws"], idf)
        assert abs(cosine_similarity(v1, v2) - 1.0) < 0.001

    def test_disjoint_docs_zero(self):
        docs = [["python", "react"], ["java", "spring"]]
        idf = build_idf(docs)
        v1 = tfidf_vector(["python", "react"], idf)
        v2 = tfidf_vector(["java", "spring"], idf)
        assert cosine_similarity(v1, v2) == 0.0

    def test_partial_overlap_positive(self):
        docs = [["python", "react", "aws"], ["python", "react", "java"]]
        idf = build_idf(docs)
        v1 = tfidf_vector(["python", "react", "aws"], idf)
        v2 = tfidf_vector(["python", "react", "java"], idf)
        sim = cosine_similarity(v1, v2)
        assert 0.0 < sim < 1.0

    def test_empty_vectors_zero(self):
        assert cosine_similarity({}, {}) == 0.0
        assert cosine_similarity({"a": 1.0}, {}) == 0.0

    def test_idf_common_term_lower(self):
        docs = [["python"] * 100, ["python", "react"]]
        idf = build_idf(docs)
        # "python" appears in all docs → lower idf
        assert idf["python"] < idf["react"]


# ── Fuzzy matching ────────────────────────────────────────────────────────────

class TestFuzzyMatch:
    def test_exact_substring_100(self):
        assert fuzzy_match("python", "python fastapi") == 100

    def test_nodejs_matches_node(self):
        assert fuzzy_match("node", "nodejs ecosystem") == 100

    def test_node_dot_js_matches_nodejs_text(self):
        assert fuzzy_match("Node.js", "Looking for a nodejs developer") >= 85

    def test_unrelated_zero(self):
        assert fuzzy_match("python", "java spring boot") == 0

    def test_empty_zero(self):
        assert fuzzy_match("", "anything") == 0
        assert fuzzy_match("python", "") == 0


class TestFuzzyMatchTokens:
    def test_all_match(self):
        result = fuzzy_match_tokens(["python", "react"], ["python", "react", "aws"])
        assert result["python"] == 100
        assert result["react"] == 100

    def test_synonym_match(self):
        result = fuzzy_match_tokens(["postgres"], ["postgresql"])
        assert result["postgres"] == 100

    def test_k8s_to_kubernetes(self):
        result = fuzzy_match_tokens(["kubernetes"], ["k8s"])
        assert result["kubernetes"] >= 85

    def test_partial_match(self):
        result = fuzzy_match_tokens(["python", "java"], ["python"])
        assert "python" in result
        assert "java" not in result


# ── Resume keyword extraction ─────────────────────────────────────────────────

def _mock_profile(skills=None, experience_bullets=None, projects=None, summary=""):
    """Build a lightweight mock profile object for build_resume_keywords."""
    class MockSkill:
        def __init__(self, name, years=0):
            self.name = name
            self.years = years
    class MockBullet:
        def __init__(self, text):
            self.text = text
    class MockExp:
        def __init__(self, bullets):
            self.bullets = bullets
    class MockProj:
        def __init__(self, tech, description=""):
            self.tech = tech
            self.description = description
        def get_tech(self):
            import json
            return json.loads(self.tech)

    p = type("P", (), {
        "skills": [MockSkill(n, y) for n, y in (skills or [])],
        "experience": [MockExp([MockBullet(b) for b in bs]) for bs in (experience_bullets or [])],
        "projects": [MockProj(t, d) for t, d in (projects or [])],
        "education": [],
        "certifications": [],
        "summary": summary,
    })()
    return p


class TestBuildResumeKeywords:
    def test_skills_weighted_by_years(self):
        p = _mock_profile(skills=[("Python", 5), ("Java", 2)])
        kw = build_resume_keywords(p)
        py = [k for k in kw if k["canonical"] == "python"]
        ja = [k for k in kw if k["canonical"] == "java"]
        assert len(py) == 1
        assert len(ja) == 1
        assert py[0]["weight"] > ja[0]["weight"]  # 5y > 2y

    def test_source_from_experience(self):
        p = _mock_profile(experience_bullets=[["Built microservices with Docker and Kubernetes"]])
        kw = build_resume_keywords(p)
        sources = [k["source"] for k in kw]
        assert "experience" in sources

    def test_canonical_form_applied(self):
        p = _mock_profile(skills=[("React.js", 3)])
        kw = build_resume_keywords(p)
        assert len(kw) == 1
        assert kw[0]["canonical"] == "react"

    def test_empty_profile(self):
        assert build_resume_keywords(None) == []

    def test_dedup_by_canonical(self):
        p = _mock_profile(
            skills=[("React.js", 3)],
            experience_bullets=[["Used React for frontend development"]],
        )
        kw = build_resume_keywords(p)
        react_entries = [k for k in kw if k["canonical"] == "react"]
        assert len(react_entries) == 1  # deduped, skill wins (higher weight)

    def test_project_tech(self):
        p = _mock_profile(projects=[('["FastAPI","PostgreSQL"]', "REST API backend")])
        kw = build_resume_keywords(p)
        canonicals = [k["canonical"] for k in kw]
        assert "fastapi" in canonicals


# ── Semantic skill taxonomy (category embeddings) ─────────────────────────────

class TestSkillCategory:
    def test_react_is_frontend(self):
        assert skill_category("React.js") == "frontend"

    def test_python_is_languages(self):
        assert skill_category("Python") == "languages"

    def test_k8s_is_devops(self):
        assert skill_category("K8s") == "devops"

    def test_unknown_skill_empty(self):
        assert skill_category("flargh") == ""

    def test_empty_empty(self):
        assert skill_category("") == ""

    def test_canonicalization_applied(self):
        # "NodeJS" canonicalizes to "node" which is backend
        assert skill_category("NodeJS") == "backend"


class TestSemanticSimilarity:
    def test_identical_skill_one(self):
        assert semantic_similarity("React", "React") == 1.0

    def test_synonym_matches_as_one(self):
        # React.js and ReactJS both canonicalize to "react"
        assert semantic_similarity("React.js", "ReactJS") == 1.0

    def test_same_category_partial(self):
        # React and Vue are both frontend → 0.6
        assert semantic_similarity("React", "Vue") == 0.6

    def test_related_category_affinity(self):
        # backend (node) and databases (postgres) have a defined affinity
        sim = semantic_similarity("Node", "PostgreSQL")
        assert 0.0 < sim < 1.0
        assert sim == 0.45  # backend↔databases affinity

    def test_unrelated_zero(self):
        assert semantic_similarity("React", "Kubernetes") == 0.0

    def test_unknown_skill_zero(self):
        assert semantic_similarity("React", "flargh") == 0.0

    def test_empty_zero(self):
        assert semantic_similarity("", "React") == 0.0
        assert semantic_similarity("React", "") == 0.0

    def test_symmetric(self):
        # Affinity lookup must be symmetric regardless of argument order
        assert semantic_similarity("PostgreSQL", "Node") == semantic_similarity("Node", "PostgreSQL")

    def test_devops_cloud_high_affinity(self):
        # devops↔cloud is the strongest affinity (0.55)
        assert semantic_similarity("Docker", "AWS") == 0.55


class TestBestSemanticMatch:
    def test_exact_match_wins(self):
        score, via = best_semantic_match("React", ["Vue", "React", "Python"])
        assert score == 1.0
        assert via == "React"

    def test_partial_match_via_related(self):
        score, via = best_semantic_match("Angular", ["Vue", "Python", "Docker"])
        assert score == 0.6       # same frontend category
        assert via == "Vue"

    def test_no_match_zero(self):
        score, via = best_semantic_match("React", ["Kubernetes", "Terraform"])
        assert score == 0.0
        assert via == ""

    def test_empty_haystack(self):
        score, via = best_semantic_match("React", [])
        assert score == 0.0


# ── Location normalization & aliasing ─────────────────────────────────────────

class TestNormalizeLocation:
    def test_sf_alias(self):
        city, region = normalize_location("SF")
        assert city == "san francisco"
        assert region == "usa"

    def test_nyc_alias(self):
        city, region = normalize_location("NYC")
        assert city == "new york"
        assert region == "usa"

    def test_multi_token_city(self):
        city, region = normalize_location("San Francisco, CA")
        assert city == "san francisco"
        assert region == "usa"

    def test_berlin_to_germany(self):
        city, region = normalize_location("Berlin, Germany")
        assert city == "berlin"
        assert region == "germany"

    def test_remote_collapses(self):
        city, region = normalize_location("Remote")
        assert city == "remote"
        assert region == ""

    def test_worldwide_is_remote(self):
        city, _ = normalize_location("Worldwide")
        assert city == "remote"

    def test_us_state_inference(self):
        # "Austin, TX" — Austin resolves to usa directly; but a bare state
        # abbreviation with no city should still infer the usa region.
        _, region = normalize_location("TX")
        assert region == "usa"

    def test_bangalore_to_bengaluru(self):
        city, region = normalize_location("Bangalore")
        assert city == "bengaluru"
        assert region == "india"

    def test_unknown_passthrough(self):
        city, region = normalize_location("Gotham City")
        assert city == "gotham city"
        assert region == ""

    def test_empty(self):
        assert normalize_location("") == ("", "")

    def test_case_insensitive(self):
        assert normalize_location("London") == normalize_location("LONDON")


# ── Resume keywords now include derived region ────────────────────────────────

class TestResumeKeywordsLocation:
    def test_location_region_extracted(self):
        p = type("P", (), {
            "skills": [type("S", (), {"name": "Python", "years": 3})()],
            "experience": [], "projects": [], "education": [],
            "certifications": [], "summary": "",
            "location": "Berlin, Germany",
        })()
        kw = build_resume_keywords(p)
        sources = [k["source"] for k in kw]
        # The derived region "germany" should appear as a location-sourced keyword
        assert "location" in sources
        canon = [k["canonical"] for k in kw]
        assert "germany" in canon

