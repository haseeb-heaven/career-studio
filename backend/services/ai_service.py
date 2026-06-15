"""Unified AI provider interface with local (Ollama) and external (OpenAI/Anthropic/OpenRouter) support."""
import json
import os
import urllib.request
from sqlmodel import Session, select
from db import engine
from models import Settings
from crypto import decrypt_key, _KEY_FIELDS


def _friendly_api_error(e: Exception, provider: str) -> str:
    """Return a human-readable error message for common API errors."""
    msg = str(e)
    if "401" in msg or "User not found" in msg or "Incorrect API key" in msg:
        return (
            f"{provider} API key is invalid or not found (401). "
            "Please set a valid API key in the Settings tab or .env file. "
            "Alternatively, use Ollama for local AI or switch to OpenRouter (free models available)."
        )
    if "429" in msg or "insufficient_quota" in msg or "exceeded your current quota" in msg:
        return (
            f"{provider} API quota exceeded (429). "
            "Please check your billing at platform.openai.com or switch to OpenRouter/Anthropic."
        )
    if "403" in msg:
        return f"{provider} access forbidden (403). Check your API key permissions."
    return f"{provider} API error: {msg}"


def _load_settings() -> Settings:
    with Session(engine) as s:
        cfg = s.exec(select(Settings)).first()
        if not cfg:
            cfg = Settings()
            s.add(cfg)
            s.commit()
            s.refresh(cfg)
    for field in _KEY_FIELDS:
        val = getattr(cfg, field, "")
        if val:
            setattr(cfg, field, decrypt_key(val))
    return cfg


# ---------- Local AI (Ollama) ----------

def _call_litellm(model: str, api_key: str | None, system: str, user: str, provider: str, api_base: str | None = None) -> str:
    try:
        import litellm
    except ImportError:
        raise RuntimeError(
            "litellm package not installed. Run: pip install litellm"
        )
    try:
        litellm.telemetry = False
        litellm.logging = False
        
        messages = [
            {"role": "system", "content": system},
            {"role": "user", "content": user},
        ]
        kwargs = {
            "model": model,
            "messages": messages,
        }
        if api_key:
            kwargs["api_key"] = api_key
        if api_base:
            kwargs["api_base"] = api_base.rstrip("/")
            
        resp = litellm.completion(**kwargs)
        return resp.choices[0].message.content or ""
    except Exception as e:
        raise RuntimeError(_friendly_api_error(e, provider)) from e


def _call_ollama(base_url: str, model: str, system: str, user: str) -> str:
    litellm_model = f"ollama/{model}" if not model.startswith("ollama/") else model
    return _call_litellm(
        model=litellm_model,
        api_key=None,
        system=system,
        user=user,
        provider="Ollama",
        api_base=base_url
    )


def ollama_available(base_url: str) -> bool:
    try:
        urllib.request.urlopen(f"{base_url.rstrip('/')}/api/tags", timeout=3)
        return True
    except Exception:
        return False


def list_ollama_models(base_url: str) -> list[str]:
    try:
        with urllib.request.urlopen(f"{base_url.rstrip('/')}/api/tags", timeout=5) as resp:
            data = json.loads(resp.read())
        return [m["name"] for m in data.get("models", [])]
    except Exception:
        return []


# ---------- External AI ----------

def _call_openai(api_key: str, model: str, system: str, user: str) -> str:
    litellm_model = f"openai/{model}" if not model.startswith("openai/") else model
    return _call_litellm(litellm_model, api_key, system, user, "OpenAI")


def _call_anthropic(api_key: str, model: str, system: str, user: str) -> str:
    litellm_model = f"anthropic/{model}" if not model.startswith("anthropic/") else model
    return _call_litellm(litellm_model, api_key, system, user, "Anthropic")


def _call_openrouter(api_key: str, model: str, system: str, user: str) -> str:
    litellm_model = f"openrouter/{model}" if not model.startswith("openrouter/") else model
    return _call_litellm(litellm_model, api_key, system, user, "OpenRouter")


# Valid model name prefixes per provider (to reject junk values like 'openrouter/free')
_OPENROUTER_DEFAULT = "meta-llama/llama-3.1-8b-instruct:free"
_OPENAI_DEFAULT = "gpt-4o-mini"
_ANTHROPIC_DEFAULT = "claude-haiku-4-5-20251001"


def _valid_model(model: str, provider: str) -> str:
    """Return model if it looks valid for the provider, else a safe default."""
    if not model:
        if provider == "anthropic":
            return _ANTHROPIC_DEFAULT
        if provider == "openrouter":
            return _OPENROUTER_DEFAULT
        return _OPENAI_DEFAULT
    # OpenRouter models always have a '/' like 'meta-llama/...' or 'google/...'
    if provider == "openrouter" and "/" not in model:
        return _OPENROUTER_DEFAULT
    # Reject obviously wrong values (shorter than 3 chars, or containing spaces)
    if len(model) < 3 or (" " in model and "/" not in model):
        if provider == "anthropic":
            return _ANTHROPIC_DEFAULT
        if provider == "openrouter":
            return _OPENROUTER_DEFAULT
        return _OPENAI_DEFAULT
    return model


def _call_external(cfg: Settings, system: str, user: str) -> str:
    provider = cfg.ai_provider
    model = _valid_model(cfg.ai_model, provider)
    if provider == "anthropic":
        key = cfg.anthropic_api_key or os.getenv("ANTHROPIC_API_KEY", "")
        if not key:
            raise ValueError("Anthropic API key not configured — set it in Settings or ANTHROPIC_API_KEY in .env")
        return _call_anthropic(key, model, system, user)
    elif provider == "openrouter":
        key = cfg.openrouter_api_key or os.getenv("OPENROUTER_API_KEY", "")
        if not key:
            raise ValueError("OpenRouter API key not configured — set it in Settings or OPENROUTER_API_KEY in .env")
        return _call_openrouter(key, model, system, user)
    else:  # openai
        key = cfg.api_key or os.getenv("OPENAI_API_KEY", "")
        if not key:
            raise ValueError("OpenAI API key not configured — set it in Settings or OPENAI_API_KEY in .env")
        return _call_openai(key, model, system, user)


# ---------- Public interface ----------

# Task complexity: "simple" = quick summaries / keyword extraction; "complex" = cover letters, roadmaps, full analysis
def complete(system: str, user: str, complexity: str = "complex") -> str:
    """Route to local or external AI based on settings and task complexity."""
    cfg = _load_settings()

    if cfg.use_local_ai:
        ollama_up = ollama_available(cfg.ollama_base_url)
        # local_for_simple=True  → use Ollama only for 'simple' tasks
        # local_for_simple=False → use Ollama for ALL tasks
        use_ollama = ollama_up and (
            not cfg.local_for_simple  # use for everything
            or complexity == "simple"  # or just simple tasks
        )
        if use_ollama:
            return _call_ollama(cfg.ollama_base_url, cfg.ollama_model, system, user)

    # Fall through to external provider
    return _call_external(cfg, system, user)


def complete_simple(system: str, user: str) -> str:
    return complete(system, user, complexity="simple")


def complete_complex(system: str, user: str) -> str:
    return complete(system, user, complexity="complex")


def profile_text_summary(profile) -> str:
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
        tech = ", ".join(json.loads(proj.tech)) if proj.tech else ""
        lines.append(f"Project: {proj.name} — {proj.description} [{tech}]")
    for edu in profile.education:
        lines.append(f"Education: {edu.degree} in {edu.field} at {edu.institution} ({edu.start}–{edu.end})")
    for cert in profile.certifications:
        lines.append(f"Certification: {cert.name} by {cert.issuer} ({cert.date})")
    return "\n".join(lines)
