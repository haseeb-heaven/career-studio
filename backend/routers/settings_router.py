import os
from fastapi import APIRouter, Depends
from sqlmodel import Session, select
import db
from models import Settings, User
from services.ai_service import ollama_available, list_ollama_models, test_provider_key
from security_crypto import encrypt_key, decrypt_key, _KEY_FIELDS
from routers.auth_utils import get_current_user

router = APIRouter(prefix="/settings", tags=["settings"])

ALLOWED = {
    "ai_provider", "ai_model", "api_key", "anthropic_api_key", "openrouter_api_key",
    "gemini_api_key", "cerebras_api_key", "groq_api_key", "nvidia_api_key",
    "use_local_ai", "ollama_base_url", "ollama_model", "local_for_simple",
    "use_deep_semantic_matching",
    "adzuna_app_id", "adzuna_app_key",
    "linkedin_api_key", "indeed_api_key", "glassdoor_api_key",
}


def _migrate_encrypt_existing_keys(session: Session, cfg: Settings) -> None:
    """Idempotent: encrypt any plain-text API keys that are already in the DB."""
    changed = False
    for field in _KEY_FIELDS:
        val = getattr(cfg, field, "")
        if val:
            encrypted = encrypt_key(val)
            if encrypted != val:
                setattr(cfg, field, encrypted)
                changed = True
    if changed:
        session.add(cfg)
        session.commit()
        session.refresh(cfg)


def _get_or_create(session: Session, user_id: int) -> Settings:
    s = session.exec(select(Settings).where(Settings.user_id == user_id)).first()
    if not s:
        s = Settings(user_id=user_id)
        session.add(s)
        session.commit()
        session.refresh(s)
    return s


def run_startup_migration() -> None:
    """Run once at startup: encrypt any plain-text API keys already in the DB.
    Must not be called on every request — idempotent but incurs a write per boot."""
    with Session(db.engine) as session:
        for cfg in session.exec(select(Settings)).all():
            _migrate_encrypt_existing_keys(session, cfg)


def _key_status(db_val: str, env_var: str) -> str:
    """Return '***' if key is set (DB or env), '' otherwise."""
    return "***" if (db_val or os.getenv(env_var, "")) else ""


@router.get("")
def get_settings(user: User = Depends(get_current_user)):
    with Session(db.engine) as s:
        cfg = _get_or_create(s, user.id)
        return {
            "ai_provider": cfg.ai_provider,
            "ai_model": cfg.ai_model,
            "api_key": _key_status(cfg.api_key, "OPENAI_API_KEY"),
            "anthropic_api_key": _key_status(cfg.anthropic_api_key, "ANTHROPIC_API_KEY"),
            "openrouter_api_key": _key_status(cfg.openrouter_api_key, "OPENROUTER_API_KEY"),
            "gemini_api_key": _key_status(cfg.gemini_api_key, "GEMINI_API_KEY"),
            "cerebras_api_key": _key_status(cfg.cerebras_api_key, "CEREBRAS_API_KEY"),
            "groq_api_key": _key_status(cfg.groq_api_key, "GROQ_API_KEY"),
            "nvidia_api_key": _key_status(cfg.nvidia_api_key, "NVIDIA_API_KEY"),
            "use_local_ai": cfg.use_local_ai,
            "ollama_base_url": cfg.ollama_base_url,
            "ollama_model": cfg.ollama_model,
            "local_for_simple": cfg.local_for_simple,
            "use_deep_semantic_matching": cfg.use_deep_semantic_matching,
            "adzuna_app_id": cfg.adzuna_app_id,
            "adzuna_app_key": _key_status(cfg.adzuna_app_key, "ADZUNA_APP_KEY"),
            "linkedin_api_key": _key_status(cfg.linkedin_api_key, "LINKEDIN_API_KEY"),
            "indeed_api_key": _key_status(cfg.indeed_api_key, "INDEED_API_KEY"),
            "glassdoor_api_key": _key_status(cfg.glassdoor_api_key, "GLASSDOOR_API_KEY"),
        }


@router.put("")
def update_settings(body: dict, user: User = Depends(get_current_user)):
    with Session(db.engine) as session:
        cfg = _get_or_create(session, user.id)
        for k, v in body.items():
            if k in ALLOWED:
                if k in _KEY_FIELDS and v == "***":
                    continue
                if k in _KEY_FIELDS and v:
                    v = encrypt_key(v)
                setattr(cfg, k, v)
        session.add(cfg)
        session.commit()
        return {"ok": True}


PROVIDER_KEY_FIELD = {
    "openai": "api_key",
    "anthropic": "anthropic_api_key",
    "openrouter": "openrouter_api_key",
    "gemini": "gemini_api_key",
    "cerebras": "cerebras_api_key",
    "groq": "groq_api_key",
    "nvidia": "nvidia_api_key",
}

PROVIDER_ENV_VAR = {
    "openai": "OPENAI_API_KEY",
    "anthropic": "ANTHROPIC_API_KEY",
    "openrouter": "OPENROUTER_API_KEY",
    "gemini": "GEMINI_API_KEY",
    "cerebras": "CEREBRAS_API_KEY",
    "groq": "GROQ_API_KEY",
    "nvidia": "NVIDIA_API_KEY",
}


@router.post("/test-key")
def test_key(body: dict, user: User = Depends(get_current_user)):
    provider = body.get("provider", "")
    api_key = body.get("api_key", "")
    field = PROVIDER_KEY_FIELD.get(provider)
    if field is None:
        return {"ok": False, "message": f"Unknown provider: {provider}"}

    if api_key == "***":
        with Session(db.engine) as session:
            cfg = _get_or_create(session, user.id)
            stored = getattr(cfg, field, "")
        api_key = decrypt_key(stored) if stored else ""
        if not api_key:
            api_key = os.getenv(PROVIDER_ENV_VAR[provider], "")

    ok, message = test_provider_key(provider, api_key)
    return {"ok": ok, "message": message}


@router.get("/ollama/status")
def ollama_status(base_url: str = "http://localhost:11434"):
    available = ollama_available(base_url)
    models = list_ollama_models(base_url) if available else []
    return {"available": available, "models": models}
