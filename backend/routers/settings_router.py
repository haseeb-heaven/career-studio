from fastapi import APIRouter
from sqlmodel import Session, select
from db import engine
from models import Settings
from services.ai_service import ollama_available, list_ollama_models

router = APIRouter(prefix="/settings", tags=["settings"])

ALLOWED = {
    "ai_provider", "ai_model", "api_key", "anthropic_api_key", "openrouter_api_key",
    "use_local_ai", "ollama_base_url", "ollama_model", "local_for_simple",
}


def _get_or_create(session: Session) -> Settings:
    s = session.exec(select(Settings)).first()
    if not s:
        s = Settings()
        session.add(s)
        session.commit()
        session.refresh(s)
    return s


@router.get("")
def get_settings():
    with Session(engine) as s:
        cfg = _get_or_create(s)
        return {
            "ai_provider": cfg.ai_provider,
            "ai_model": cfg.ai_model,
            "api_key": "***" if cfg.api_key else "",
            "anthropic_api_key": "***" if cfg.anthropic_api_key else "",
            "openrouter_api_key": "***" if cfg.openrouter_api_key else "",
            "use_local_ai": cfg.use_local_ai,
            "ollama_base_url": cfg.ollama_base_url,
            "ollama_model": cfg.ollama_model,
            "local_for_simple": cfg.local_for_simple,
        }


@router.put("")
def update_settings(body: dict):
    with Session(engine) as session:
        cfg = _get_or_create(session)
        for k, v in body.items():
            if k in ALLOWED:
                setattr(cfg, k, v)
        session.add(cfg)
        session.commit()
        return {"ok": True}


@router.get("/ollama/status")
def ollama_status(base_url: str = "http://localhost:11434"):
    available = ollama_available(base_url)
    models = list_ollama_models(base_url) if available else []
    return {"available": available, "models": models}
