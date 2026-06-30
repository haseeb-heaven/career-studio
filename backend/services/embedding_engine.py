"""Local, fully-offline neural semantic similarity for job matching.

Uses sentence-transformers (all-MiniLM-L6-v2) to embed resume and job text
and score their cosine similarity. The model is downloaded once from
Hugging Face on first use and cached locally (~/.cache/huggingface) —
after that, no network access is required. If the package is missing or
the model fails to load, every function here degrades gracefully and the
caller falls back to the existing category-embedding semantic factor.
"""
import logging

logger = logging.getLogger(__name__)

_MODEL_NAME = "all-MiniLM-L6-v2"
_model = None
_load_attempted = False


def is_available() -> bool:
    return get_model() is not None


def get_model():
    """Lazy singleton load. Returns None (and logs once) if the package is
    missing or the model fails to download/load."""
    global _model, _load_attempted
    if _model is not None:
        return _model
    if _load_attempted:
        return None
    _load_attempted = True
    try:
        from sentence_transformers import SentenceTransformer
        _model = SentenceTransformer(_MODEL_NAME)
        return _model
    except Exception as exc:
        logger.warning(
            "Deep semantic matching unavailable (sentence-transformers/model "
            "could not be loaded): %s. Falling back to category-embedding "
            "semantic matching only.", exc,
        )
        return None


def resume_embedding_text(profile) -> str:
    """Concatenate summary + skill names + experience bullets + project
    descriptions into one text blob for embedding."""
    parts = []
    if getattr(profile, "summary", ""):
        parts.append(profile.summary)
    for skill in getattr(profile, "skills", None) or []:
        if skill.name:
            parts.append(skill.name)
    for exp in getattr(profile, "experience", None) or []:
        if exp.role:
            parts.append(exp.role)
        for bullet in getattr(exp, "bullets", None) or []:
            if bullet.text:
                parts.append(bullet.text)
    for proj in getattr(profile, "projects", None) or []:
        if proj.description:
            parts.append(proj.description)
    return " ".join(parts)


def job_embedding_text(title: str, desc: str) -> str:
    return f"{title or ''} {desc or ''}".strip()


def embed_batch(texts):
    """Batch-encode; returns None if the model is unavailable."""
    model = get_model()
    if model is None:
        return None
    return model.encode(list(texts))


def cosine(a, b) -> float:
    dot = sum(x * y for x, y in zip(a, b))
    norm_a = sum(x * x for x in a) ** 0.5
    norm_b = sum(y * y for y in b) ** 0.5
    if norm_a == 0.0 or norm_b == 0.0:
        return 0.0
    return max(0.0, min(1.0, dot / (norm_a * norm_b)))


def neural_semantic_scores(resume_text: str, job_texts):
    """One resume embedding + one batched job-embedding call -> list of
    0-100 scores aligned to job_texts, or None if the model is unavailable."""
    model = get_model()
    if model is None:
        return None
    if not job_texts:
        return []
    resume_vec = model.encode([resume_text])[0]
    job_vecs = model.encode(list(job_texts))
    return [round(cosine(resume_vec, jv) * 100.0, 1) for jv in job_vecs]
