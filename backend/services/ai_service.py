"""Unified AI provider interface with local (Ollama) and external (OpenAI/Anthropic/OpenRouter) support."""
import json
import os
import urllib.request
import httpx
from sqlmodel import Session, select
import db
from models import Settings
from security_crypto import decrypt_key, _KEY_FIELDS


def _extract_choice_content(resp, provider: str) -> str:
    """Safely pull message content from a chat-completion response, raising a
    friendly error instead of crashing with 'NoneType is not subscriptable'
    when the provider returns a response with no choices."""
    if not resp or not getattr(resp, "choices", None):
        raise RuntimeError(
            f"{provider} returned an empty response (no choices). "
            "The model may be unavailable or rate-limited — try again or switch models."
        )
    return resp.choices[0].message.content or ""


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
        return _extract_choice_content(resp, provider)
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
                return _extract_choice_content(resp, "OpenRouter")

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
                return _extract_choice_content(resp, provider)
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
        return _extract_choice_content(resp, "OpenAI")
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


def _call_openai_compatible(base_url: str, api_key: str, model: str, system: str, user: str, provider_label: str) -> str:
    """Shared call path for providers that expose an OpenAI-compatible
    /chat/completions endpoint (OpenRouter, Gemini, Cerebras, Groq, NVIDIA)."""
    try:
        from openai import OpenAI
    except ImportError:
        raise RuntimeError(
            "openai package not installed. Run: pip install openai"
        )
    try:
        client = OpenAI(api_key=api_key, base_url=base_url)
        resp = client.chat.completions.create(
            model=model,
            messages=[{"role": "system", "content": system}, {"role": "user", "content": user}],
        )
        return _extract_choice_content(resp, provider_label)
    except Exception as e:
        raise RuntimeError(_friendly_api_error(e, provider_label)) from e


def _call_openrouter(api_key: str, model: str, system: str, user: str) -> str:
    return _call_openai_compatible("https://openrouter.ai/api/v1", api_key, model, system, user, "OpenRouter")


def _call_gemini(api_key: str, model: str, system: str, user: str) -> str:
    return _call_openai_compatible(
        "https://generativelanguage.googleapis.com/v1beta/openai/", api_key, model, system, user, "Gemini"
    )


def _call_cerebras(api_key: str, model: str, system: str, user: str) -> str:
    return _call_openai_compatible("https://api.cerebras.ai/v1", api_key, model, system, user, "Cerebras")


def _call_groq(api_key: str, model: str, system: str, user: str) -> str:
    return _call_openai_compatible("https://api.groq.com/openai/v1", api_key, model, system, user, "Groq")


def _call_nvidia(api_key: str, model: str, system: str, user: str) -> str:
    return _call_openai_compatible("https://integrate.api.nvidia.com/v1", api_key, model, system, user, "NVIDIA")


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
        elif provider == "gemini":
            resp = httpx.get(
                "https://generativelanguage.googleapis.com/v1beta/openai/models",
                headers={"Authorization": f"Bearer {api_key}"},
                timeout=10,
            )
        elif provider == "cerebras":
            resp = httpx.get(
                "https://api.cerebras.ai/v1/models",
                headers={"Authorization": f"Bearer {api_key}"},
                timeout=10,
            )
        elif provider == "groq":
            resp = httpx.get(
                "https://api.groq.com/openai/v1/models",
                headers={"Authorization": f"Bearer {api_key}"},
                timeout=10,
            )
        elif provider == "nvidia":
            resp = httpx.get(
                "https://integrate.api.nvidia.com/v1/models",
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
_GEMINI_DEFAULT = "gemini-2.5-flash"
_CEREBRAS_DEFAULT = "llama-3.3-70b"
_GROQ_DEFAULT = "llama-3.3-70b-versatile"
_NVIDIA_DEFAULT = "nvidia/nemotron-3-super-120b-a12b"

_PROVIDER_DEFAULTS = {
    "anthropic":  _ANTHROPIC_DEFAULT,
    "openrouter": _OPENROUTER_DEFAULT,
    "gemini":     _GEMINI_DEFAULT,
    "cerebras":   _CEREBRAS_DEFAULT,
    "groq":       _GROQ_DEFAULT,
    "nvidia":     _NVIDIA_DEFAULT,
}

# Proper display names for error messages — str.title() mangles "openrouter"
# into "Openrouter" instead of the branded "OpenRouter", so this map is used
# instead wherever a provider name is shown to the user.
_PROVIDER_LABELS = {
    "openai":     "OpenAI",
    "anthropic":  "Anthropic",
    "openrouter": "OpenRouter",
    "gemini":     "Gemini",
    "cerebras":   "Cerebras",
    "groq":       "Groq",
    "nvidia":     "NVIDIA",
}


def _valid_model(model: str, provider: str) -> str:
    """Return model if it looks valid for the provider, else a safe default."""
    default = _PROVIDER_DEFAULTS.get(provider, _OPENAI_DEFAULT)
    if not model:
        return default
    if provider == "openrouter" and "/" not in model:
        return default
    if len(model) < 3 or (" " in model and "/" not in model):
        return default
    # A leftover OpenAI-style model id (e.g. the default "gpt-4o-mini") is
    # invalid for any other provider — fall back rather than forwarding an
    # OpenAI model name to a different provider's API.
    if provider != "openai" and model.startswith(("gpt-", "o1", "o3", "o4")):
        return default
    return model


_EXTERNAL_PROVIDERS = {
    # provider: (key_field, env_var, call_fn_name)
    # call_fn_name is looked up dynamically via globals() at call time (not
    # bound directly) so that @patch("services.ai_service._call_xxx") in
    # tests actually takes effect.
    "anthropic":  ("anthropic_api_key", "ANTHROPIC_API_KEY", "_call_anthropic"),
    "openrouter": ("openrouter_api_key", "OPENROUTER_API_KEY", "_call_openrouter"),
    "gemini":     ("gemini_api_key", "GEMINI_API_KEY", "_call_gemini"),
    "cerebras":   ("cerebras_api_key", "CEREBRAS_API_KEY", "_call_cerebras"),
    "groq":       ("groq_api_key", "GROQ_API_KEY", "_call_groq"),
    "nvidia":     ("nvidia_api_key", "NVIDIA_API_KEY", "_call_nvidia"),
}


def _call_external(cfg: Settings, system: str, user: str) -> str:
    provider = cfg.ai_provider
    model = _valid_model(cfg.ai_model, provider)
    if provider in _EXTERNAL_PROVIDERS:
        key_field, env_var, call_fn_name = _EXTERNAL_PROVIDERS[provider]
        key = getattr(cfg, key_field, "") or os.getenv(env_var, "")
        if not key:
            label = _PROVIDER_LABELS.get(provider, provider.title())
            raise ValueError(f"{label} API key not configured — set it in Settings or {env_var} in .env")
        call_fn = globals()[call_fn_name]
        return call_fn(key, model, system, user)
    # openai (default)
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
