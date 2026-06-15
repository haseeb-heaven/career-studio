"""Unified AI provider interface with local (Ollama) and external (OpenAI/Anthropic/OpenRouter) support."""
import json
import os
import urllib.request
from sqlmodel import Session, select
from db import engine
from models import Settings


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
        return cfg


# ---------- Local AI (Ollama) ----------

def _call_ollama(base_url: str, model: str, system: str, user: str) -> str:
    payload = json.dumps({
        "model": model,
        "messages": [
            {"role": "system", "content": system},
            {"role": "user", "content": user},
        ],
        "stream": False,
    }).encode()
    req = urllib.request.Request(
        f"{base_url.rstrip('/')}/api/chat",
        data=payload,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=120) as resp:
        data = json.loads(resp.read())
    return data["message"]["content"]


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
    try:
        from openai import OpenAI
    except ImportError:
        raise RuntimeError(
            "openai package not installed. Run: pip install openai"
        )
    try:
        client = OpenAI(api_key=api_key)
        resp = client.chat.completions.create(
            model=model,
            messages=[{"role": "system", "content": system}, {"role": "user", "content": user}],
        )
        return resp.choices[0].message.content or ""
    except Exception as e:
        raise RuntimeError(_friendly_api_error(e, "OpenAI")) from e


def _call_anthropic(api_key: str, model: str, system: str, user: str) -> str:
    try:
        import anthropic
    except ImportError:
        raise RuntimeError(
            "anthropic package not installed. Run: pip install anthropic"
        )
    try:
        client = anthropic.Anthropic(api_key=api_key)
        resp = client.messages.create(
            model=model,
            max_tokens=4096,
            system=system,
            messages=[{"role": "user", "content": user}],
        )
        return resp.content[0].text if resp.content else ""
    except Exception as e:
        raise RuntimeError(_friendly_api_error(e, "Anthropic")) from e


def _call_openrouter(api_key: str, model: str, system: str, user: str) -> str:
    try:
        from openai import OpenAI
    except ImportError:
        raise RuntimeError(
            "openai package not installed. Run: pip install openai"
        )
    try:
        client = OpenAI(api_key=api_key, base_url="https://openrouter.ai/api/v1")
        resp = client.chat.completions.create(
            model=model,
            messages=[{"role": "system", "content": system}, {"role": "user", "content": user}],
        )
        return resp.choices[0].message.content or ""
    except Exception as e:
        raise RuntimeError(_friendly_api_error(e, "OpenRouter")) from e


def _call_external(cfg: Settings, system: str, user: str) -> str:
    provider = cfg.ai_provider
    model = cfg.ai_model
    if provider == "anthropic":
        key = cfg.anthropic_api_key or os.getenv("ANTHROPIC_API_KEY", "")
        if not key:
            raise ValueError("Anthropic API key not configured — set it in Settings or ANTHROPIC_API_KEY in .env")
        return _call_anthropic(key, model or "claude-haiku-4-5-20251001", system, user)
    elif provider == "openrouter":
        key = cfg.openrouter_api_key or os.getenv("OPENROUTER_API_KEY", "")
        if not key:
            raise ValueError("OpenRouter API key not configured — set it in Settings or OPENROUTER_API_KEY in .env")
        return _call_openrouter(key, model or "meta-llama/llama-3.1-8b-instruct:free", system, user)
    else:  # openai
        key = cfg.api_key or os.getenv("OPENAI_API_KEY", "")
        if not key:
            raise ValueError("OpenAI API key not configured — set it in Settings or OPENAI_API_KEY in .env")
        return _call_openai(key, model or "gpt-4o-mini", system, user)


# ---------- Public interface ----------

# Task complexity: "simple" = quick summaries / keyword extraction; "complex" = cover letters, roadmaps, full analysis
def complete(system: str, user: str, complexity: str = "complex") -> str:
    """Route to local or external AI based on settings and task complexity."""
    cfg = _load_settings()

    use_local = (
        cfg.use_local_ai
        and (complexity == "simple" or not cfg.local_for_simple or True)
        and ollama_available(cfg.ollama_base_url)
    )

    # Use local for simple tasks when both are configured
    if cfg.use_local_ai and cfg.local_for_simple and complexity == "simple":
        if ollama_available(cfg.ollama_base_url):
            return _call_ollama(cfg.ollama_base_url, cfg.ollama_model, system, user)

    # Use local for ALL tasks when set to local-only
    if cfg.use_local_ai and not cfg.local_for_simple:
        if ollama_available(cfg.ollama_base_url):
            return _call_ollama(cfg.ollama_base_url, cfg.ollama_model, system, user)

    # Fall through to external
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
