"""Unit tests for the local neural-embedding semantic matching engine.
The real sentence-transformers model is never loaded in tests — get_model()
is monkeypatched with a deterministic fake encoder so tests run fast with
no network access or model download."""
import sys
import math
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from models import Profile, Skill, Experience, ExperienceBullet, Project
from services import embedding_engine as ee


class _FakeModel:
    """Deterministic fake encoder: each text maps to a fixed-length vector
    derived from a hash of its words, so cosine similarity is reproducible
    and identical/near-identical texts score highest."""

    def encode(self, texts, **kwargs):
        vectors = []
        for t in texts:
            words = sorted(set(t.lower().split()))
            vec = [0.0] * 16
            for w in words:
                vec[hash(w) % 16] += 1.0
            norm = math.sqrt(sum(v * v for v in vec)) or 1.0
            vectors.append([v / norm for v in vec])
        return vectors


def test_cosine_identical_vectors_is_one():
    a = [1.0, 0.0, 0.0]
    assert ee.cosine(a, a) == 1.0


def test_cosine_orthogonal_vectors_is_zero():
    a = [1.0, 0.0]
    b = [0.0, 1.0]
    assert ee.cosine(a, b) == 0.0


def test_resume_embedding_text_includes_skills_and_summary():
    p = Profile(full_name="Jane", summary="Backend engineer")
    p.skills = [Skill(name="Python", years=5)]
    p.experience = [Experience(company="A", role="Engineer", start="2020")]
    p.experience[0].bullets = [ExperienceBullet(text="Built data pipelines")]
    p.projects = [Project(name="API", description="REST API service")]
    text = ee.resume_embedding_text(p)
    assert "Backend engineer" in text
    assert "Python" in text
    assert "Built data pipelines" in text
    assert "REST API service" in text


def test_job_embedding_text_combines_title_and_description():
    text = ee.job_embedding_text("Data Engineer", "Build ETL pipelines")
    assert "Data Engineer" in text
    assert "Build ETL pipelines" in text


def test_neural_semantic_scores_returns_none_when_model_unavailable(monkeypatch):
    monkeypatch.setattr(ee, "get_model", lambda: None)
    result = ee.neural_semantic_scores("resume text", ["job text 1", "job text 2"])
    assert result is None


def test_neural_semantic_scores_aligned_and_scaled(monkeypatch):
    monkeypatch.setattr(ee, "get_model", lambda: _FakeModel())
    scores = ee.neural_semantic_scores(
        "python backend engineer",
        ["python backend engineer needed", "completely unrelated topic xyz"],
    )
    assert scores is not None
    assert len(scores) == 2
    for s in scores:
        assert 0.0 <= s <= 100.0
    # The near-identical text must score higher than the unrelated one.
    assert scores[0] > scores[1]
