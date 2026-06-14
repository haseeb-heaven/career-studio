from fastapi import APIRouter
from sqlmodel import Session, select
from db import engine
from models import Settings

router = APIRouter(prefix="/settings", tags=["settings"])

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
        }

@router.put("")
def update_settings(body: dict):
    ALLOWED = {"ai_provider", "ai_model", "api_key", "anthropic_api_key", "openrouter_api_key"}
    with Session(engine) as session:
        cfg = _get_or_create(session)
        for k, v in body.items():
            if k in ALLOWED:
                setattr(cfg, k, v)
        session.add(cfg)
        session.commit()
        return {"ok": True}
