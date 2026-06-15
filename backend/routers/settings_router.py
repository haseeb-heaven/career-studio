import os
from fastapi import APIRouter
from sqlmodel import Session, select
from db import engine
from models import Settings
from services.ai_service import ollama_available, list_ollama_models
from crypto import encrypt_key, _KEY_FIELDS

router = APIRouter(prefix="/settings", tags=["settings"])

ALLOWED = {
    "ai_provider", "ai_model", "api_key", "anthropic_api_key", "openrouter_api_key",
    "use_local_ai", "ollama_base_url", "ollama_model", "local_for_simple",
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


def _get_or_create(session: Session) -> Settings:
    s = session.exec(select(Settings)).first()
    if not s:
        s = Settings()
        session.add(s)
        session.commit()
        session.refresh(s)
    _migrate_encrypt_existing_keys(session, s)
    return s


def _key_status(db_val: str, env_var: str) -> str:
    """Return '***' if key is set (DB or env), '' otherwise."""
    return "***" if (db_val or os.getenv(env_var, "")) else ""


@router.get("")
def get_settings():
    with Session(engine) as s:
        cfg = _get_or_create(s)
        return {
            "ai_provider": cfg.ai_provider,
            "ai_model": cfg.ai_model,
            "api_key": _key_status(cfg.api_key, "OPENAI_API_KEY"),
            "anthropic_api_key": _key_status(cfg.anthropic_api_key, "ANTHROPIC_API_KEY"),
            "openrouter_api_key": _key_status(cfg.openrouter_api_key, "OPENROUTER_API_KEY"),
            "use_local_ai": cfg.use_local_ai,
            "ollama_base_url": cfg.ollama_base_url,
            "ollama_model": cfg.ollama_model,
            "local_for_simple": cfg.local_for_simple,
            "adzuna_app_id": cfg.adzuna_app_id,
            "adzuna_app_key": _key_status(cfg.adzuna_app_key, "ADZUNA_APP_KEY"),
            "linkedin_api_key": _key_status(cfg.linkedin_api_key, "LINKEDIN_API_KEY"),
            "indeed_api_key": _key_status(cfg.indeed_api_key, "INDEED_API_KEY"),
            "glassdoor_api_key": _key_status(cfg.glassdoor_api_key, "GLASSDOOR_API_KEY"),
        }


@router.put("")
def update_settings(body: dict):
    with Session(engine) as session:
        cfg = _get_or_create(session)
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


@router.get("/ollama/status")
def ollama_status(base_url: str = "http://localhost:11434"):
    available = ollama_available(base_url)
    models = list_ollama_models(base_url) if available else []
    return {"available": available, "models": models}
