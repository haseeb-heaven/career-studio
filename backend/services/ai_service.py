"""Unified AI provider interface with local (Ollama) and external (OpenAI/Anthropic/OpenRouter) support."""
import json
import os
import urllib.request
import httpx
from sqlmodel import Session, select
import db
from models import Settings
from security_crypto import decrypt_key, _KEY_FIELDS


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


def _load_settings(user_id: int | None = None) -> Settings:
    with Session(db.engine) as s:
        query = select(Settings)
        if user_id is not None:
            query = query.where(Settings.user_id == user_id)
        cfg = s.exec(query).first()
        if not cfg:
            cfg = Settings(user_id=user_id)
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
    except ImportError:
        # Fall back to using native libraries if litellm is not installed
        try:
            messages = [
                {"role": "system", "content": system},
                {"role": "user", "content": user},
            ]
            
            clean_model = model
            model_provider = provider.lower()
            if "/" in model:
                prefix, clean_model = model.split("/", 1)
                if prefix in ["openai", "anthropic", "openrouter", "ollama"]:
                    model_provider = prefix

            if model_provider == "anthropic":
                import anthropic
                client = anthropic.Anthropic(api_key=api_key)
                resp = client.messages.create(
                    model=clean_model,
                    max_tokens=4000,
                    system=system,
                    messages=[{"role": "user", "content": user}]
                )
                return "".join(block.text for block in resp.content if hasattr(block, "text"))

            elif model_provider == "openrouter":
                from openai import OpenAI
                client = OpenAI(
                    api_key=api_key,
                    base_url="https://openrouter.ai/api/v1"
                )
                resp = client.chat.completions.create(
                    model=clean_model,
                    messages=messages,
                )
                return resp.choices[0].message.content or ""

            elif model_provider == "ollama":
                import urllib.request
                import json
                url = f"{(api_base or 'http://localhost:11434').rstrip('/')}/api/chat"
                payload = {
                    "model": clean_model,
                    "messages": messages,
                    "stream": False
                }
                req = urllib.request.Request(
                    url,
                    data=json.dumps(payload).encode("utf-8"),
                    headers={"Content-Type": "application/json"}
                )
                with urllib.request.urlopen(req, timeout=120) as response:
                    res_data = json.loads(response.read().decode("utf-8"))
                    return res_data.get("message", {}).get("content", "")

            else:
                from openai import OpenAI
                client = OpenAI(api_key=api_key)
                resp = client.chat.completions.create(
                    model=clean_model,
                    messages=messages,
                )
                return resp.choices[0].message.content or ""
        except Exception as e:
            raise RuntimeError(_friendly_api_error(e, provider)) from e
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


def test_provider_key(provider: str, api_key: str) -> tuple[bool, str]:
    """Make a single zero-completion-cost request to verify an API key is accepted.
    Returns (ok, message)."""
    if not api_key:
        return False, f"No {provider} API key provided."

    try:
        if provider == "openai":
            resp = httpx.get(
                "https://api.openai.com/v1/models",
                headers={"Authorization": f"Bearer {api_key}"},
                timeout=10,
            )
        elif provider == "anthropic":
            resp = httpx.get(
                "https://api.anthropic.com/v1/models",
                headers={"x-api-key": api_key, "anthropic-version": "2023-06-01"},
                timeout=10,
            )
        elif provider == "openrouter":
            resp = httpx.get(
                "https://openrouter.ai/api/v1/auth/key",
                headers={"Authorization": f"Bearer {api_key}"},
                timeout=10,
            )
        else:
            return False, f"Unknown provider: {provider}"
    except Exception as e:
        return False, f"Could not reach {provider}: {e}"

    if resp.status_code == 200:
        return True, "Key is valid."
    if resp.status_code == 401:
        return False, f"{provider} rejected this key (401 unauthorized)."
    return False, f"{provider} returned HTTP {resp.status_code}."


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
    if provider == "openrouter" and "/" not in model:
        return _OPENROUTER_DEFAULT
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
def complete(system: str, user: str, complexity: str = "complex", user_id: int | None = None) -> str:
    """Route to local or external AI based on settings and task complexity."""
    cfg = _load_settings(user_id)

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


def complete_simple(system: str, user: str, user_id: int | None = None) -> str:
    return complete(system, user, complexity="simple", user_id=user_id)


def complete_complex(system: str, user: str, user_id: int | None = None) -> str:
    return complete(system, user, complexity="complex", user_id=user_id)


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
