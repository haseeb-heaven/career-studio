# Security Group B — Auth Enforcement + API Key Encryption Design Spec
**Date:** 2026-06-15  
**Status:** Approved  
**Branch:** `refactor/pdf-stack`  
**Closes:** Issue #2 (Items 1 and 2)

---

## Problem

**Issue 1:** Every profile, analysis, jobs, and sections route accepts unauthenticated requests. `get_current_user_optional` silently passes `None` as the user; `GET /api/profiles` returns every profile in the database to anyone without a token; write and delete routes have no ownership check at all.

**Issue 2:** OpenAI, Anthropic, OpenRouter, Adzuna, LinkedIn, Indeed, and Glassdoor API keys are stored as plain-text strings in `Settings`. Any read of `career_studio.db` exposes all keys instantly. `ai_service.py` reads these fields directly.

---

## Scope

Seven files change. No schema migration, no new tables, no frontend changes.

| File | Change |
|---|---|
| `backend/routers/auth_utils.py` | Add `get_current_user` required dependency |
| `backend/crypto.py` | New module: Fernet helpers (`encrypt_key`, `decrypt_key`, `_is_encrypted`, `_get_fernet`) |
| `backend/routers/profile_router.py` | Enforce auth + ownership on all 4 routes |
| `backend/routers/analysis_router.py` | Enforce auth + ownership on all 8 routes |
| `backend/routers/jobs_router.py` | Enforce auth + ownership on 1 route |
| `backend/routers/sections_router.py` | Enforce auth + ownership on all 18 routes |
| `backend/routers/settings_router.py` | Encrypt keys on write; startup migration to encrypt existing plain-text keys |
| `backend/services/ai_service.py` | Decrypt key fields after loading Settings from DB |

`import_router.py`, `export_router.py`, `models.py`, all frontend files — **unchanged**.

---

## Architecture

```
Token → get_current_user() → User (raises 401 if missing/invalid)
                                    ↓
                        _check_ownership(profile, user)  → raises 403 if mismatch
                                    ↓
                              route handler

Settings write path:
  PUT /settings body → encrypt_key(val) for each KEY_FIELDS member → stored in DB

Settings read path (ai_service.py):
  _load_settings() → Settings object from DB
                    → for each KEY_FIELDS: decrypt_key(field) in-place
                    → return decrypted Settings (used only in memory, never persisted back)

Startup migration (runs once on first GET or PUT /settings after deploy):
  _migrate_encrypt_existing_keys(cfg, session):
    for each field in KEY_FIELDS:
      if not _is_encrypted(getattr(cfg, field)):
        setattr(cfg, field, encrypt_key(getattr(cfg, field)))
    session.commit()
```

---

## `backend/crypto.py` — new file

```python
import base64, hashlib, os
from cryptography.fernet import Fernet

_KEY_FIELDS: tuple[str, ...] = (
    "api_key",
    "anthropic_api_key",
    "openrouter_api_key",
    "adzuna_app_key",
    "linkedin_api_key",
    "indeed_api_key",
    "glassdoor_api_key",
)


def _get_fernet() -> Fernet:
    raw = os.getenv("SECRET_KEY", "ai-career-studio-dev-secret-2026")
    key = base64.urlsafe_b64encode(hashlib.sha256(raw.encode()).digest())
    return Fernet(key)


def _is_encrypted(value: str) -> bool:
    """True if value is already a Fernet ciphertext. Never double-encrypts."""
    return bool(value) and value.startswith("gAAAAA")


def encrypt_key(val: str) -> str:
    """Encrypt a plain-text key. Returns unchanged if empty or already encrypted."""
    if not val or _is_encrypted(val):
        return val
    return _get_fernet().encrypt(val.encode()).decode()


def decrypt_key(val: str) -> str:
    """Decrypt a Fernet ciphertext. Returns unchanged if empty or not encrypted."""
    if not val or not _is_encrypted(val):
        return val
    try:
        return _get_fernet().decrypt(val.encode()).decode()
    except Exception:
        return val
```

`_KEY_FIELDS` is defined here and imported by both `settings_router.py` and `ai_service.py` — single source of truth for which fields get encrypted.

---

## `backend/routers/auth_utils.py` — add `get_current_user`

Add this function after `get_current_user_optional`:

```python
from fastapi import HTTPException

def get_current_user(
    token: Optional[str] = Depends(oauth2_scheme),
    session: Session = Depends(db.get_session_dep),
) -> User:
    """Required auth dependency. Raises 401 if token is missing or invalid."""
    if not token:
        raise HTTPException(status_code=401, detail="Not authenticated")
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        user_id = int(payload["sub"])
        user = session.get(User, user_id)
        if not user:
            raise HTTPException(status_code=401, detail="User not found")
        return user
    except (JWTError, KeyError, ValueError):
        raise HTTPException(status_code=401, detail="Invalid token")
```

---

## Profile router — ownership enforcement

Add a helper at the top of `profile_router.py`:

```python
def _check_ownership(profile: Profile, user: User) -> None:
    """Raise 403 if profile belongs to a different user.
    Profiles with NULL user_id are accessible by any authenticated user
    (pre-auth data from before enforcement was added)."""
    if profile.user_id is not None and profile.user_id != user.id:
        raise HTTPException(status_code=403, detail="Forbidden")
```

Apply auth + ownership to every route:

| Route | Change |
|---|---|
| `GET /profiles` | `user: User = Depends(get_current_user)` — return only caller's profiles: `select(Profile).where((Profile.user_id == user.id) \| (Profile.user_id == None))` |
| `GET /profiles/{id}` | `user: User = Depends(get_current_user)` + `_check_ownership(p, user)` |
| `PATCH /profiles/{id}` | `user: User = Depends(get_current_user)` + `_check_ownership(p, user)` |
| `DELETE /profiles/{id}` | `user: User = Depends(get_current_user)` + `_check_ownership(p, user)` |

---

## Analysis, Jobs, Sections routers — ownership enforcement

All routes in these three routers follow the same pattern:

1. Add `user: User = Depends(get_current_user)` to the route signature.
2. After loading the profile, call `_check_ownership(profile, user)`.

The `_check_ownership` helper is defined once in `profile_router.py` and imported by analysis, jobs, and sections routers — avoids drift if the NULL-user_id policy ever changes.

```python
if profile.user_id is not None and profile.user_id != user.id:
    raise HTTPException(status_code=403, detail="Forbidden")
```

Routes affected:
- `analysis_router.py`: 8 routes (`analyze`, `score`, `cover-letter`, `cover-letters` GET/DELETE, `roadmap` POST/GET/DELETE)
- `jobs_router.py`: 1 route (`search_jobs`)
- `sections_router.py`: 18 routes (all skill/experience/bullet/project/education/certification CRUD)

---

## `backend/routers/settings_router.py` — encrypt keys on write

Import `_KEY_FIELDS`, `encrypt_key`, `decrypt_key`, `_is_encrypted` from `crypto`.

**Startup migration** — add `_migrate_encrypt_existing_keys` and call it inside `_get_or_create`:

```python
def _migrate_encrypt_existing_keys(cfg: Settings, session: Session) -> None:
    """Idempotent: encrypts any plain-text key fields. Safe to run every boot."""
    changed = False
    for field in _KEY_FIELDS:
        val = getattr(cfg, field, "")
        if val and not _is_encrypted(val):
            setattr(cfg, field, encrypt_key(val))
            changed = True
    if changed:
        session.add(cfg)
        session.commit()
        session.refresh(cfg)
```

Call it at the end of `_get_or_create`:
```python
def _get_or_create(session: Session) -> Settings:
    s = session.exec(select(Settings)).first()
    if not s:
        s = Settings()
        session.add(s)
        session.commit()
        session.refresh(s)
    _migrate_encrypt_existing_keys(s, session)
    return s
```

**Write path** — in `PUT /settings`, before `setattr(cfg, k, v)`, encrypt if the field is a key field and the incoming value is not the mask:

```python
if k in _KEY_FIELDS:
    if v == "***":
        continue          # sentinel → keep existing value
    v = encrypt_key(v)   # plain-text → Fernet ciphertext
setattr(cfg, k, v)
```

`GET /settings` response is unchanged — `_key_status` already returns `"***"` or `""`, never the raw (or encrypted) value. No decryption needed in the GET path.

---

## `backend/services/ai_service.py` — decrypt after load

Import `decrypt_key` and `_KEY_FIELDS` from `crypto`.

In `_load_settings()`, after retrieving `cfg` from the DB, decrypt all key fields before returning:

```python
def _load_settings() -> Settings:
    with Session(engine) as s:
        cfg = s.exec(select(Settings)).first()
        if not cfg:
            cfg = Settings()
    # Decrypt in-memory only — never persist the decrypted object back to DB
    for field in _KEY_FIELDS:
        val = getattr(cfg, field, "")
        setattr(cfg, field, decrypt_key(val))
    return cfg
```

No other changes to `ai_service.py`. The rest of the service already reads `cfg.api_key`, `cfg.anthropic_api_key`, etc. — those now arrive decrypted.

---

## `backend/routers/jobs_router.py` — decrypt job-board keys

`jobs_router.py` reads settings directly at lines 325–330 (not via `ai_service._load_settings`). Replace those five assignment lines with:

```python
cfg = s.exec(select(Settings)).first() or Settings()
adzuna_id  = cfg.adzuna_app_id or ""                                  # plain app ID — no decrypt
adzuna_key = decrypt_key(cfg.adzuna_app_key)   or ""
linkedin_key  = decrypt_key(cfg.linkedin_api_key)  or ""
indeed_key    = decrypt_key(cfg.indeed_api_key)    or ""
glassdoor_key = decrypt_key(cfg.glassdoor_api_key) or ""
```

`adzuna_app_id` is a public application identifier (not a secret) and is NOT in `_KEY_FIELDS` — it is never encrypted and needs no decryption.

---

## NULL user_id policy (pre-auth profiles)

Profiles created before auth enforcement have `user_id = NULL`. The ownership check:

```python
if profile.user_id is not None and profile.user_id != user.id:
    raise HTTPException(403, "Forbidden")
```

This makes NULL-user_id profiles accessible to any authenticated user. This is correct for a single-user personal tool — the first logged-in user can access and interact with all pre-existing data. No auto-claim or migration is required.

---

## Error contract

| Condition | HTTP code |
|---|---|
| No token / expired token / invalid token | 401 `Not authenticated` |
| Valid token but profile belongs to different user | 403 `Forbidden` |
| Profile not found | 404 (unchanged) |
| Decrypt failure (corrupted ciphertext) | `decrypt_key` returns the raw value unchanged; key will fail at the provider, producing a normal API error — no crash |

---

## Dependency

`cryptography` is already present in `requirements.txt` as a transitive dependency of `passlib[bcrypt]`. Pin it explicitly to make the dep visible:

```
cryptography>=41.0.0
```

No new install needed; this is a documentation-only change to `requirements.txt`.

---

## Testing

New tests required (in `tests/test_api.py` or new `tests/test_auth.py`):

- `GET /api/profiles` without token → 401
- `GET /api/profiles/{id}` without token → 401
- `PATCH /api/profiles/{id}` with valid token but wrong user → 403
- `DELETE /api/profiles/{id}` with valid token but wrong user → 403
- `POST /api/auth/login` with valid credentials → token returned
- `GET /api/profiles` with valid token → only returns that user's profiles
- `PUT /api/settings` with a real key string → stored value in DB **starts with `gAAAAA`** (assert `stored.startswith("gAAAAA")`, matching the `_is_encrypted` contract exactly)
- `PUT /api/settings` then `ai_service._load_settings()` → key field is decrypted plain-text (does not start with `gAAAAA`)
- Startup migration: plain-text key in DB → `_get_or_create` encrypts it (value starts with `gAAAAA`); second call leaves it unchanged (idempotent)

---

## Known gap — `import_router.py` profile creation

`import_router.py` creates new profiles but has no auth. Under the NULL-user_id policy, every imported profile will have `user_id = NULL` and be accessible by any authenticated user. This is intentional and acceptable for a single-user personal tool. It is a **known gap, not an oversight** — adding auth to `import_router.py` is a separate follow-up task once the core auth enforcement is stable.

---

## What is explicitly out of scope

- `import_router.py` — profile creation auth is a tracked follow-up (see Known Gap above)
- `export_router.py` — reads profiles, does not mutate; not in Issue #2 scope
- `settings_router.py` auth enforcement (the Settings endpoints themselves) — not in the issue scope
- Frontend changes — zero
- Issue 3 (multi-profile UI) — separate spec
- PDF stack rewrite — separate plan already written
