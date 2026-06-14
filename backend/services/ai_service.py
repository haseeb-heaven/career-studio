"""Unified AI provider interface. Reads Settings from DB to pick provider/model/key."""
import json
from sqlmodel import Session, select
from db import engine
from models import Settings


def _load_settings() -> Settings:
    with Session(engine) as s:
        cfg = s.exec(select(Settings)).first()
        if not cfg:
            cfg = Settings()
            s.add(cfg)
            s.commit()
            s.refresh(cfg)
        return cfg


def _call_openai(api_key: str, model: str, system: str, user: str) -> str:
    from openai import OpenAI
    client = OpenAI(api_key=api_key)
    resp = client.chat.completions.create(
        model=model,
        messages=[{"role": "system", "content": system}, {"role": "user", "content": user}],
    )
    return resp.choices[0].message.content or ""


def _call_anthropic(api_key: str, model: str, system: str, user: str) -> str:
    import anthropic
    client = anthropic.Anthropic(api_key=api_key)
    resp = client.messages.create(
        model=model,
        max_tokens=4096,
        system=system,
        messages=[{"role": "user", "content": user}],
    )
    return resp.content[0].text if resp.content else ""


def _call_openrouter(api_key: str, model: str, system: str, user: str) -> str:
    from openai import OpenAI
    client = OpenAI(api_key=api_key, base_url="https://openrouter.ai/api/v1")
    resp = client.chat.completions.create(
        model=model,
        messages=[{"role": "system", "content": system}, {"role": "user", "content": user}],
    )
    return resp.choices[0].message.content or ""


def complete(system: str, user: str) -> str:
    """Call the configured AI provider and return the text response."""
    cfg = _load_settings()
    provider = cfg.ai_provider
    model = cfg.ai_model

    if provider == "anthropic":
        key = cfg.anthropic_api_key
        if not key:
            raise ValueError("Anthropic API key not configured")
        return _call_anthropic(key, model or "claude-haiku-4-5-20251001", system, user)
    elif provider == "openrouter":
        key = cfg.openrouter_api_key
        if not key:
            raise ValueError("OpenRouter API key not configured")
        return _call_openrouter(key, model or "openai/gpt-4o-mini", system, user)
    else:  # openai (default)
        key = cfg.api_key
        if not key:
            raise ValueError("OpenAI API key not configured")
        return _call_openai(key, model or "gpt-4o-mini", system, user)


def profile_text_summary(profile) -> str:
    """Convert a Profile ORM object into a compact text block for AI prompts."""
    lines = [
        f"Name: {profile.full_name}",
        f"Email: {profile.email}",
        f"Phone: {profile.phone}",
        f"Location: {profile.location}",
        f"Summary: {profile.summary}",
    ]
    if profile.skills:
        skill_names = ", ".join(f"{s.name} ({s.years}y)" for s in profile.skills)
        lines.append(f"Skills: {skill_names}")
    for exp in profile.experience:
        lines.append(f"Experience: {exp.role} at {exp.company} ({exp.start}–{exp.end or 'present'})")
        for b in exp.bullets:
            lines.append(f"  - {b.text}")
    for proj in profile.projects:
        import json as _json
        tech = ", ".join(_json.loads(proj.tech)) if proj.tech else ""
        lines.append(f"Project: {proj.name} — {proj.description} [{tech}]")
    for edu in profile.education:
        lines.append(f"Education: {edu.degree} in {edu.field} at {edu.institution} ({edu.start}–{edu.end})")
    for cert in profile.certifications:
        lines.append(f"Certification: {cert.name} by {cert.issuer} ({cert.date})")
    return "\n".join(lines)
