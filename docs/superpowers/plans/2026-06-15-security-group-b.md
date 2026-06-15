# Security Group B Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Enforce authentication on all profile/analysis/jobs/sections routes and encrypt API keys at rest using Fernet symmetric encryption derived from `SECRET_KEY`.

**Architecture:** `crypto.py` provides Fernet helpers; all routers import `get_current_user` from `auth_utils.py` and define a local `_check_ownership` helper. `settings_router.py` runs an idempotent startup migration and encrypts keys on write. `ai_service._load_settings()` decrypts in-memory after loading from DB. The `conftest.py` test harness sets `DATABASE_URL` before imports so all `from db import engine` bindings pick up the test SQLite engine automatically — no extra patching needed.

**Tech Stack:** FastAPI, SQLModel, `python-jose[cryptography]` (JWT), `cryptography==49.0.0` (Fernet, already pinned in `requirements.txt`)

---

### Task 1: Create `backend/crypto.py` — Fernet helpers

**Files:**
- Create: `backend/crypto.py`
- Create: `tests/test_crypto.py`

- [ ] **Step 1: Write the failing tests**

Create `tests/test_crypto.py`:

```python
"""Tests for Fernet key encryption helpers."""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent / "backend"))

from crypto import _is_encrypted, encrypt_key, decrypt_key


def test_is_encrypted_false_for_plain_text():
    assert _is_encrypted("sk-abc123") is False


def test_is_encrypted_false_for_empty_string():
    assert _is_encrypted("") is False


def test_is_encrypted_false_for_none():
    assert _is_encrypted(None) is False


def test_is_encrypted_true_for_fernet_prefix():
    assert _is_encrypted("gAAAAAbunchofbase64==") is True


def test_encrypt_key_produces_fernet_token():
    ct = encrypt_key("my-secret-key")
    assert ct.startswith("gAAAAA")


def test_decrypt_key_round_trip():
    plain = "sk-test-12345"
    ct = encrypt_key(plain)
    assert decrypt_key(ct) == plain


def test_encrypt_key_idempotent_already_encrypted():
    ct = encrypt_key("original")
    ct2 = encrypt_key(ct)  # must not double-encrypt
    assert ct2 == ct
    assert decrypt_key(ct2) == "original"


def test_encrypt_key_empty_passthrough():
    assert encrypt_key("") == ""


def test_decrypt_key_plain_passthrough():
    assert decrypt_key("plain-text") == "plain-text"


def test_decrypt_key_empty_passthrough():
    assert decrypt_key("") == ""
```

- [ ] **Step 2: Run tests, confirm they fail**

```
cd backend && ../.venv/Scripts/python.exe -m pytest ../tests/test_crypto.py -v
```

Expected: `ModuleNotFoundError: No module named 'crypto'`

- [ ] **Step 3: Create `backend/crypto.py`**

```python
import base64
import hashlib
import os
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


def _is_encrypted(value) -> bool:
    """True only if value is already a Fernet v1 ciphertext (starts with 'gAAAAA')."""
    return bool(value) and isinstance(value, str) and value.startswith("gAAAAA")


def encrypt_key(val) -> str:
    """Encrypt a plain-text key. Returns val unchanged if empty or already encrypted."""
    if not val or _is_encrypted(val):
        return val
    return _get_fernet().encrypt(val.encode()).decode()


def decrypt_key(val) -> str:
    """Decrypt a Fernet ciphertext. Returns val unchanged if empty or not encrypted."""
    if not val or not _is_encrypted(val):
        return val
    try:
        return _get_fernet().decrypt(val.encode()).decode()
    except Exception:
        return val
```

- [ ] **Step 4: Run tests, confirm all pass**

```
cd backend && ../.venv/Scripts/python.exe -m pytest ../tests/test_crypto.py -v
```

Expected: all 10 tests PASS

- [ ] **Step 5: Commit**

```bash
git add backend/crypto.py tests/test_crypto.py
git commit -m "feat: add Fernet key encryption helpers in crypto.py"
```

---

### Task 2: Add `get_current_user` to `auth_utils.py`

**Files:**
- Modify: `backend/routers/auth_utils.py`

`get_current_user_optional` returns `None` for missing/invalid tokens. Add `get_current_user` that raises HTTP 401 instead. `auth_router.py`'s `/me` endpoint already uses `get_current_user` — if `/api/auth/me` already returns 401 without a token the function exists; just verify the signature matches exactly what's below.

- [ ] **Step 1: Check if `get_current_user` already exists**

```
cd backend && ../.venv/Scripts/python.exe -m pytest ../tests/test_auth.py::TestMeEndpoint -v
```

Expected: all 3 tests PASS (confirming the `/me` endpoint already enforces 401). If they fail, add the function below.

- [ ] **Step 2: Replace `backend/routers/auth_utils.py` with the final version**

```python
"""JWT + password utilities shared between auth_router and other routers."""
from __future__ import annotations
import os
from typing import Optional
from datetime import datetime, timedelta, timezone

from fastapi import Depends, HTTPException
from fastapi.security import OAuth2PasswordBearer
from passlib.context import CryptContext
from jose import jwt, JWTError
from sqlmodel import Session

import db
from models import User

SECRET_KEY = os.getenv("SECRET_KEY", "ai-career-studio-dev-secret-2026")
ALGORITHM = "HS256"
TOKEN_EXPIRE_HOURS = 24 * 7  # 1 week

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/auth/login", auto_error=False)


def make_token(user_id: int, username: str) -> str:
    expire = datetime.now(timezone.utc) + timedelta(hours=TOKEN_EXPIRE_HOURS)
    return jwt.encode(
        {"sub": str(user_id), "username": username, "exp": expire},
        SECRET_KEY,
        algorithm=ALGORITHM,
    )


def get_current_user_optional(
    token: Optional[str] = Depends(oauth2_scheme),
    session: Session = Depends(db.get_session_dep),
) -> Optional[User]:
    if not token:
        return None
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        user_id = int(payload["sub"])
        return session.get(User, user_id)
    except (JWTError, KeyError, ValueError):
        return None


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

- [ ] **Step 3: Run the existing auth test suite**

```
cd backend && ../.venv/Scripts/python.exe -m pytest ../tests/test_auth.py -v
```

Expected: all tests PASS

- [ ] **Step 4: Commit**

```bash
git add backend/routers/auth_utils.py
git commit -m "feat: add required get_current_user dependency (raises 401)"
```

---

### Task 3: Enforce auth on `profile_router.py`

**Files:**
- Modify: `backend/routers/profile_router.py`
- Modify: `tests/test_auth.py` (update one broken test + add new enforcement tests)

**Test breakage warning:** `TestProfileOwnership::test_unauthenticated_sees_all_profiles` currently asserts 200 for unauthenticated `GET /profiles`. After this task it must assert 401. Update that test in Step 1 BEFORE the implementation so the test suite reflects the new contract.

- [ ] **Step 1: Update `tests/test_auth.py` — fix the now-incorrect test and add enforcement tests**

In `TestProfileOwnership`, change `test_unauthenticated_sees_all_profiles`:

```python
    def test_unauthenticated_sees_all_profiles(self, client):
        """After auth enforcement, unauthenticated GET /profiles returns 401."""
        resp = client.get("/api/profiles")
        assert resp.status_code == 401
```

Then add this new class at the END of `tests/test_auth.py`:

```python
class TestProfileRouterAuth:
    """Profile routes must require auth after enforcement."""

    def test_list_profiles_no_token_returns_401(self, client):
        resp = client.get("/api/profiles")
        assert resp.status_code == 401

    def test_get_profile_no_token_returns_401(self, client):
        import json as _json
        headers = _auth_headers(client, "pauth_creator")
        data = _json.dumps({"full_name": "Auth Test Profile"}).encode()
        imp = client.post(
            "/api/import",
            files={"file": ("p.json", data, "application/json")},
            headers=headers,
        )
        pid = imp.json()["profile_id"]
        resp = client.get(f"/api/profiles/{pid}")
        assert resp.status_code == 401

    def test_patch_profile_no_token_returns_401(self, client):
        import json as _json
        headers = _auth_headers(client, "pauth_patcher")
        data = _json.dumps({"full_name": "Patch Test"}).encode()
        imp = client.post(
            "/api/import",
            files={"file": ("p.json", data, "application/json")},
            headers=headers,
        )
        pid = imp.json()["profile_id"]
        resp = client.patch(f"/api/profiles/{pid}", json={"full_name": "New Name"})
        assert resp.status_code == 401

    def test_delete_profile_no_token_returns_401(self, client):
        import json as _json
        headers = _auth_headers(client, "pauth_deleter")
        data = _json.dumps({"full_name": "Del Test"}).encode()
        imp = client.post(
            "/api/import",
            files={"file": ("p.json", data, "application/json")},
            headers=headers,
        )
        pid = imp.json()["profile_id"]
        resp = client.delete(f"/api/profiles/{pid}")
        assert resp.status_code == 401

    def test_wrong_user_get_profile_returns_403(self, client):
        import json as _json
        h_a = _auth_headers(client, "pauth_owner_a")
        h_b = _auth_headers(client, "pauth_owner_b")
        data = _json.dumps({"full_name": "A Profile"}).encode()
        imp = client.post(
            "/api/import",
            files={"file": ("p.json", data, "application/json")},
            headers=h_a,
        )
        pid = imp.json()["profile_id"]
        resp = client.get(f"/api/profiles/{pid}", headers=h_b)
        assert resp.status_code == 403

    def test_wrong_user_delete_profile_returns_403(self, client):
        import json as _json
        h_a = _auth_headers(client, "pauth_del_a")
        h_b = _auth_headers(client, "pauth_del_b")
        data = _json.dumps({"full_name": "A Profile 2"}).encode()
        imp = client.post(
            "/api/import",
            files={"file": ("p.json", data, "application/json")},
            headers=h_a,
        )
        pid = imp.json()["profile_id"]
        resp = client.delete(f"/api/profiles/{pid}", headers=h_b)
        assert resp.status_code == 403

    def test_owner_can_get_profile(self, client):
        import json as _json
        headers = _auth_headers(client, "pauth_own_get")
        data = _json.dumps({"full_name": "Owner Profile"}).encode()
        imp = client.post(
            "/api/import",
            files={"file": ("p.json", data, "application/json")},
            headers=headers,
        )
        pid = imp.json()["profile_id"]
        resp = client.get(f"/api/profiles/{pid}", headers=headers)
        assert resp.status_code == 200
        assert resp.json()["full_name"] == "Owner Profile"
```

- [ ] **Step 2: Run new tests, confirm they fail**

```
cd backend && ../.venv/Scripts/python.exe -m pytest ../tests/test_auth.py::TestProfileRouterAuth -v
```

Expected: tests expecting 401/403 fail (currently get 200/204)

- [ ] **Step 3: Rewrite `backend/routers/profile_router.py`**

```python
import db
from fastapi import APIRouter, HTTPException, Depends
from sqlmodel import Session, select
from models import (
    Profile, Skill, Experience, ExperienceBullet,
    Project, Education, Certification, ContactLink, User,
)
from logger import get_logger
from services.activity import log_activity
from routers.auth_utils import get_current_user

logger = get_logger(__name__)
router = APIRouter(prefix="/profiles", tags=["profiles"])


def _get_or_404(session: Session, profile_id: int) -> Profile:
    profile = session.get(Profile, profile_id)
    if not profile:
        raise HTTPException(404, f"Profile {profile_id} not found")
    return profile


def _check_ownership(profile: Profile, user: User) -> None:
    """Raise 403 if profile belongs to a different user.
    NULL user_id profiles are accessible by any authenticated user (pre-auth data)."""
    if profile.user_id is not None and profile.user_id != user.id:
        raise HTTPException(status_code=403, detail="Forbidden")


@router.get("")
def list_profiles(user: User = Depends(get_current_user)):
    with Session(db.engine) as session:
        profiles = session.exec(
            select(Profile).where(
                (Profile.user_id == user.id) | (Profile.user_id == None)  # noqa: E711
            )
        ).all()
        return [{"id": p.id, "full_name": p.full_name, "email": p.email} for p in profiles]


@router.get("/{profile_id}")
def get_profile(profile_id: int, user: User = Depends(get_current_user)):
    logger.info(f"GET profile {profile_id}")
    with Session(db.engine) as session:
        p = _get_or_404(session, profile_id)
        _check_ownership(p, user)
        skills = list(p.skills or [])
        experience = list(p.experience or [])
        projects = list(p.projects or [])
        education = list(p.education or [])
        certifications = list(p.certifications or [])
        links = list(p.links or [])
        return {
            "id": p.id,
            "full_name": p.full_name,
            "email": p.email,
            "phone": p.phone,
            "location": p.location,
            "summary": p.summary,
            "availability": p.availability,
            "compensation": p.compensation,
            "skills": [
                {"id": s.id, "name": s.name, "category": s.category, "years": s.years}
                for s in skills
            ],
            "experience": [
                {
                    "id": e.id, "company": e.company, "role": e.role,
                    "start": e.start, "end": e.end, "location": e.location,
                    "bullets": [{"id": b.id, "text": b.text} for b in (e.bullets or [])],
                }
                for e in experience
            ],
            "projects": [
                {
                    "id": pr.id, "name": pr.name, "description": pr.description,
                    "link": pr.link, "tech": pr.get_tech(),
                }
                for pr in projects
            ],
            "education": [
                {
                    "id": ed.id, "institution": ed.institution, "degree": ed.degree,
                    "field": ed.field, "start": ed.start, "end": ed.end,
                }
                for ed in education
            ],
            "certifications": [
                {"id": c.id, "name": c.name, "issuer": c.issuer, "date": c.date}
                for c in certifications
            ],
            "links": [{"id": lnk.id, "label": lnk.label, "url": lnk.url} for lnk in links],
        }


@router.patch("/{profile_id}")
def patch_profile(profile_id: int, body: dict, user: User = Depends(get_current_user)):
    ALLOWED = {"full_name", "email", "phone", "location", "summary", "availability", "compensation"}
    logger.info(f"PATCH profile {profile_id}: {list(body.keys())}")
    with Session(db.engine) as session:
        p = _get_or_404(session, profile_id)
        _check_ownership(p, user)
        for k, v in body.items():
            if k in ALLOWED:
                setattr(p, k, v)
        session.add(p)
        session.commit()
        session.refresh(p)
        log_activity("patch", f"profile #{profile_id} fields={list(body.keys())}", profile_id)
        return {"id": p.id, "full_name": p.full_name}


@router.delete("/{profile_id}", status_code=204)
def delete_profile(profile_id: int, user: User = Depends(get_current_user)):
    logger.info(f"DELETE profile {profile_id}")
    with Session(db.engine) as session:
        p = _get_or_404(session, profile_id)
        _check_ownership(p, user)
        session.delete(p)
        session.commit()
        log_activity("delete", f"profile #{profile_id}", profile_id)
```

- [ ] **Step 4: Run full auth test suite**

```
cd backend && ../.venv/Scripts/python.exe -m pytest ../tests/test_auth.py -v
```

Expected: all tests PASS. The updated `test_unauthenticated_sees_all_profiles` and all `TestProfileRouterAuth` tests pass. The existing `TestProfileOwnership` tests using authenticated requests continue to pass.

- [ ] **Step 5: Commit**

```bash
git add backend/routers/profile_router.py tests/test_auth.py
git commit -m "feat: enforce auth + ownership on all profile routes"
```

---

### Task 4: Enforce auth on `analysis_router.py`

**Files:**
- Modify: `backend/routers/analysis_router.py`
- Modify: `tests/test_auth.py` (add `TestAnalysisRouterAuth` class)

8 routes to protect: `analyze` (POST), `score` (GET), `generate_cover_letter` (POST), `list_cover_letters` (GET), `delete_cover_letter` (DELETE), `generate_roadmap` (POST), `list_roadmaps` (GET), `delete_roadmap` (DELETE).

- [ ] **Step 1: Write failing tests**

Add at the END of `tests/test_auth.py`:

```python
class TestAnalysisRouterAuth:
    """Analysis routes must require auth."""

    def _make_profile(self, client, username: str) -> tuple[dict, int]:
        import json as _json
        headers = _auth_headers(client, username)
        data = _json.dumps({"full_name": f"{username} Profile"}).encode()
        imp = client.post(
            "/api/import",
            files={"file": ("p.json", data, "application/json")},
            headers=headers,
        )
        return headers, imp.json()["profile_id"]

    def test_analyze_no_token_returns_401(self, client):
        _, pid = self._make_profile(client, "ana_creator_1")
        resp = client.post(f"/api/profiles/{pid}/analyze")
        assert resp.status_code == 401

    def test_cover_letter_no_token_returns_401(self, client):
        _, pid = self._make_profile(client, "ana_creator_2")
        resp = client.post(
            f"/api/profiles/{pid}/cover-letter",
            json={"job_title": "Dev", "company": "Acme"},
        )
        assert resp.status_code == 401

    def test_list_cover_letters_no_token_returns_401(self, client):
        _, pid = self._make_profile(client, "ana_creator_3")
        resp = client.get(f"/api/profiles/{pid}/cover-letters")
        assert resp.status_code == 401

    def test_roadmap_no_token_returns_401(self, client):
        _, pid = self._make_profile(client, "ana_creator_4")
        resp = client.post(f"/api/profiles/{pid}/roadmap", json={})
        assert resp.status_code == 401

    def test_list_roadmaps_no_token_returns_401(self, client):
        _, pid = self._make_profile(client, "ana_creator_5")
        resp = client.get(f"/api/profiles/{pid}/roadmaps")
        assert resp.status_code == 401

    def test_wrong_user_list_cover_letters_returns_403(self, client):
        h_a = _auth_headers(client, "ana_owner_a")
        h_b = _auth_headers(client, "ana_owner_b")
        import json as _json
        data = _json.dumps({"full_name": "CL Profile"}).encode()
        imp = client.post(
            "/api/import",
            files={"file": ("p.json", data, "application/json")},
            headers=h_a,
        )
        pid = imp.json()["profile_id"]
        resp = client.get(f"/api/profiles/{pid}/cover-letters", headers=h_b)
        assert resp.status_code == 403

    def test_wrong_user_list_roadmaps_returns_403(self, client):
        h_a = _auth_headers(client, "ana_rm_owner_a")
        h_b = _auth_headers(client, "ana_rm_owner_b")
        import json as _json
        data = _json.dumps({"full_name": "Roadmap Profile"}).encode()
        imp = client.post(
            "/api/import",
            files={"file": ("p.json", data, "application/json")},
            headers=h_a,
        )
        pid = imp.json()["profile_id"]
        resp = client.get(f"/api/profiles/{pid}/roadmaps", headers=h_b)
        assert resp.status_code == 403
```

- [ ] **Step 2: Run tests, confirm they fail**

```
cd backend && ../.venv/Scripts/python.exe -m pytest ../tests/test_auth.py::TestAnalysisRouterAuth -v
```

Expected: 401/403 tests fail (get 200 or 422 instead)

- [ ] **Step 3: Rewrite `backend/routers/analysis_router.py`**

```python
"""Analysis endpoints: resume score, AI suggestions, cover letter, career roadmap."""
from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel
from sqlmodel import Session, select
from db import engine
from models import Profile, CoverLetter, CareerPlan, User
from services import activity
from services.ai_service import complete_simple, complete_complex, profile_text_summary
from logger import get_logger
from routers.auth_utils import get_current_user
from routers.profile_router import _check_ownership

logger = get_logger(__name__)
router = APIRouter(prefix="/profiles", tags=["analysis"])


def _get_profile(pid: int, session: Session) -> Profile:
    p = session.get(Profile, pid)
    if not p:
        raise HTTPException(status_code=404, detail="Profile not found")
    session.refresh(p)
    return p


# ---------- /analyze ----------

@router.post("/{profile_id}/analyze")
def analyze(profile_id: int, user: User = Depends(get_current_user)):
    with Session(engine) as s:
        p = _get_profile(profile_id, s)
        _check_ownership(p, user)
        resume_text = profile_text_summary(p)

    system = (
        "You are a senior technical recruiter and career coach. "
        "Analyze the resume and return a JSON object with these keys:\n"
        '  "score": integer 0-100,\n'
        '  "strengths": list of 3-5 short strings,\n'
        '  "weaknesses": list of 3-5 short strings,\n'
        '  "suggestions": list of 5-7 specific, actionable improvement suggestions,\n'
        '  "ats_keywords": list of 10 ATS keywords missing from the resume.\n'
        "Return ONLY valid JSON. No prose."
    )
    user_msg = f"Resume:\n{resume_text}"

    try:
        raw = complete_simple(system, user_msg)
        import json
        raw = raw.strip()
        if raw.startswith("```"):
            raw = raw.split("```", 2)[1]
            if raw.startswith("json"):
                raw = raw[4:]
        result = json.loads(raw)
    except Exception as e:
        logger.error("AI analysis failed: %s", e)
        raise HTTPException(status_code=502, detail=f"AI error: {e}")

    activity.log_activity("analyze", f"score={result.get('score')}", profile_id)
    return result


# ---------- /score ----------

@router.get("/{profile_id}/score")
def score(profile_id: int, user: User = Depends(get_current_user)):
    """Quick score-only endpoint (same AI call, cheaper to display)."""
    return analyze(profile_id, user)


# ---------- /cover-letter ----------

class CoverLetterRequest(BaseModel):
    job_title: str
    company: str
    extra_notes: str = ""


@router.post("/{profile_id}/cover-letter")
def generate_cover_letter(
    profile_id: int,
    body: CoverLetterRequest,
    user: User = Depends(get_current_user),
):
    with Session(engine) as s:
        p = _get_profile(profile_id, s)
        _check_ownership(p, user)
        resume_text = profile_text_summary(p)

    system = (
        "You are an expert career coach. Write a professional, enthusiastic, "
        "and personalized cover letter in the first person. "
        "The letter should be 3-4 paragraphs: opening hook, skills/experience match, "
        "why this company, call to action. Do not add placeholders. "
        "Return ONLY the cover letter text, no subject line or date header."
    )
    user_msg = (
        f"Job Title: {body.job_title}\n"
        f"Company: {body.company}\n"
        f"Extra notes: {body.extra_notes}\n\n"
        f"Resume:\n{resume_text}"
    )

    try:
        content = complete_complex(system, user_msg)
    except Exception as e:
        logger.error("Cover letter generation failed: %s", e)
        raise HTTPException(status_code=502, detail=f"AI error: {e}")

    with Session(engine) as s:
        cl = CoverLetter(
            profile_id=profile_id,
            job_title=body.job_title,
            company=body.company,
            content=content,
        )
        s.add(cl)
        s.commit()
        s.refresh(cl)
        activity.log_activity("cover_letter", f"{body.job_title} @ {body.company}", profile_id)
        return {"id": cl.id, "content": cl.content, "job_title": cl.job_title, "company": cl.company}


@router.get("/{profile_id}/cover-letters")
def list_cover_letters(profile_id: int, user: User = Depends(get_current_user)):
    with Session(engine) as s:
        p = _get_profile(profile_id, s)
        _check_ownership(p, user)
        rows = s.exec(select(CoverLetter).where(CoverLetter.profile_id == profile_id)).all()
        return [
            {
                "id": r.id, "job_title": r.job_title, "company": r.company,
                "content": r.content, "created_at": r.created_at.isoformat(),
            }
            for r in rows
        ]


@router.delete("/{profile_id}/cover-letters/{cl_id}")
def delete_cover_letter(
    profile_id: int,
    cl_id: int,
    user: User = Depends(get_current_user),
):
    with Session(engine) as s:
        p = _get_profile(profile_id, s)
        _check_ownership(p, user)
        cl = s.get(CoverLetter, cl_id)
        if not cl or cl.profile_id != profile_id:
            raise HTTPException(status_code=404)
        s.delete(cl)
        s.commit()
        return {"ok": True}


# ---------- /roadmap ----------

class RoadmapRequest(BaseModel):
    plan_type: str = "roadmap"   # roadmap | growth | portfolio
    target_role: str = ""
    years_horizon: int = 3


@router.post("/{profile_id}/roadmap")
def generate_roadmap(
    profile_id: int,
    body: RoadmapRequest,
    user: User = Depends(get_current_user),
):
    with Session(engine) as s:
        p = _get_profile(profile_id, s)
        _check_ownership(p, user)
        resume_text = profile_text_summary(p)

    plan_prompts = {
        "roadmap": (
            "Create a detailed {years}-year career roadmap targeting the role '{role}'. "
            "You must return a single JSON object with this exact structure:\n"
            "{{\n"
            "  \"title\": \"Career Roadmap to {role}\",\n"
            "  \"overview\": \"A 2-3 sentence overview of the starting point vs. target role.\",\n"
            "  \"timeline\": [\n"
            "    {{\n"
            "      \"period\": \"Year 1\",\n"
            "      \"milestones\": [\"milestone 1\", \"milestone 2\"],\n"
            "      \"skills\": [\"skill 1\", \"skill 2\"],\n"
            "      \"certifications\": [\"cert 1\"],\n"
            "      \"actions\": [\"networking action 1\", \"target company list\"]\n"
            "    }}\n"
            "  ],\n"
            "  \"projects\": [\n"
            "    {{\n"
            "      \"name\": \"Portfolio Project\",\n"
            "      \"description\": \"Description of what to build to show capability.\",\n"
            "      \"tech_stack\": [\"tech 1\", \"tech 2\"],\n"
            "      \"github_strategy\": \"How to structure/document the repo.\"\n"
            "    }}\n"
            "  ],\n"
            "  \"learning_resources\": [\n"
            "    {{\n"
            "      \"title\": \"Specific Course or Topic\",\n"
            "      \"platform\": \"YouTube / Coursera / Udemy / edX / Books\",\n"
            "      \"url\": \"https://www.youtube.com/results?search_query=advanced+typescript\",\n"
            "      \"description\": \"Why this resource is essential.\"\n"
            "    }}\n"
            "  ],\n"
            "  \"additional_strategy\": \"Salary progression expectations over {years} years.\"\n"
            "}}\n"
            "IMPORTANT: Return ONLY this JSON. Do not write any introduction or conclusion."
        ),
        "growth": (
            "Create a detailed {years}-year personal growth plan targeting the role '{role}'. "
            "Return a JSON object with keys: title, overview, timeline, projects, learning_resources, additional_strategy. "
            "IMPORTANT: Return ONLY this JSON."
        ),
        "portfolio": (
            "Create a detailed {years}-year portfolio strategy targeting the role '{role}'. "
            "Return a JSON object with keys: title, overview, timeline, projects, learning_resources, additional_strategy. "
            "IMPORTANT: Return ONLY this JSON."
        ),
    }

    template = plan_prompts.get(body.plan_type, plan_prompts["roadmap"])
    prompt_suffix = template.format(years=body.years_horizon, role=body.target_role or "senior engineer")

    system = "You are an expert career coach with 20 years of tech experience. Return ONLY valid JSON."
    user_msg = f"Resume:\n{resume_text}\n\nTask: {prompt_suffix}"

    try:
        content = complete_complex(system, user_msg)
        content_stripped = content.strip()
        if content_stripped.startswith("```"):
            parts = content_stripped.split("```")
            for part in parts:
                part = part.strip()
                if part.startswith("json"):
                    part = part[4:].strip()
                try:
                    import json
                    json.loads(part)
                    content = part
                    break
                except Exception:
                    pass
    except Exception as e:
        logger.error("Roadmap generation failed: %s", e)
        raise HTTPException(status_code=502, detail=f"AI error: {e}")

    with Session(engine) as s:
        plan = CareerPlan(
            profile_id=profile_id,
            content=content,
            plan_type=body.plan_type,
        )
        s.add(plan)
        s.commit()
        s.refresh(plan)
        activity.log_activity("roadmap", f"type={body.plan_type}", profile_id)
        return {"id": plan.id, "content": plan.content, "plan_type": plan.plan_type}


@router.get("/{profile_id}/roadmaps")
def list_roadmaps(profile_id: int, user: User = Depends(get_current_user)):
    with Session(engine) as s:
        p = _get_profile(profile_id, s)
        _check_ownership(p, user)
        rows = s.exec(select(CareerPlan).where(CareerPlan.profile_id == profile_id)).all()
        return [
            {
                "id": r.id, "plan_type": r.plan_type,
                "content": r.content, "created_at": r.created_at.isoformat(),
            }
            for r in rows
        ]


@router.delete("/{profile_id}/roadmaps/{plan_id}")
def delete_roadmap(
    profile_id: int,
    plan_id: int,
    user: User = Depends(get_current_user),
):
    with Session(engine) as s:
        p = _get_profile(profile_id, s)
        _check_ownership(p, user)
        plan = s.get(CareerPlan, plan_id)
        if not plan or plan.profile_id != profile_id:
            raise HTTPException(status_code=404)
        s.delete(plan)
        s.commit()
        return {"ok": True}
```

Note: the `score` route delegates to `analyze` directly, passing `user` through. The local `user_msg` variable replaces the original `user` variable name (which now shadows the `user: User` parameter).

- [ ] **Step 4: Run tests**

```
cd backend && ../.venv/Scripts/python.exe -m pytest ../tests/test_auth.py::TestAnalysisRouterAuth -v
```

Expected: all tests PASS

- [ ] **Step 5: Commit**

```bash
git add backend/routers/analysis_router.py tests/test_auth.py
git commit -m "feat: enforce auth + ownership on all analysis routes"
```

---

### Task 5: Enforce auth + decrypt keys on `jobs_router.py`

**Files:**
- Modify: `backend/routers/jobs_router.py`
- Modify: `tests/test_auth.py` (add `TestJobsRouterAuth`)

1 route to protect: `GET /{profile_id}/jobs`. Also replace the raw settings key reads at lines 325–330 with decrypted reads.

- [ ] **Step 1: Write failing tests**

Add at the END of `tests/test_auth.py`:

```python
class TestJobsRouterAuth:
    """Jobs route must require auth."""

    def test_search_jobs_no_token_returns_401(self, client):
        import json as _json
        headers = _auth_headers(client, "jobs_creator")
        data = _json.dumps({"full_name": "Jobs User"}).encode()
        imp = client.post(
            "/api/import",
            files={"file": ("p.json", data, "application/json")},
            headers=headers,
        )
        pid = imp.json()["profile_id"]
        resp = client.get(f"/api/profiles/{pid}/jobs")
        assert resp.status_code == 401

    def test_wrong_user_search_jobs_returns_403(self, client):
        import json as _json
        h_a = _auth_headers(client, "jobs_owner_a")
        h_b = _auth_headers(client, "jobs_owner_b")
        data = _json.dumps({"full_name": "Jobs A Profile"}).encode()
        imp = client.post(
            "/api/import",
            files={"file": ("p.json", data, "application/json")},
            headers=h_a,
        )
        pid = imp.json()["profile_id"]
        resp = client.get(f"/api/profiles/{pid}/jobs", headers=h_b)
        assert resp.status_code == 403
```

- [ ] **Step 2: Run tests, confirm they fail**

```
cd backend && ../.venv/Scripts/python.exe -m pytest ../tests/test_auth.py::TestJobsRouterAuth -v
```

Expected: 401/403 tests fail (get 200 instead)

- [ ] **Step 3: Update the imports and `search_jobs` function in `backend/routers/jobs_router.py`**

Add these two imports at the top of the file (after the existing imports):

```python
from fastapi import APIRouter, HTTPException, Query, Depends
from models import Profile, JobMatch, Settings, User
from routers.auth_utils import get_current_user
from crypto import decrypt_key
```

The full import block becomes:

```python
import json
import re
import urllib.request
import urllib.parse
from fastapi import APIRouter, HTTPException, Query, Depends
from sqlmodel import Session, select
from db import engine
from models import Profile, JobMatch, Settings, User
from services import activity
from logger import get_logger
from routers.auth_utils import get_current_user
from routers.profile_router import _check_ownership
from crypto import decrypt_key
```

Update the `search_jobs` function signature and settings reads:

```python
@router.get("/{profile_id}/jobs")
def search_jobs(
    profile_id: int,
    limit: int = Query(default=20, le=50),
    job_title: str = Query(default=""),
    location: str = Query(default=""),
    portal: str = Query(default="all"),
    user: User = Depends(get_current_user),
):
    with Session(engine) as s:
        p = s.get(Profile, profile_id)
        if not p:
            raise HTTPException(status_code=404, detail="Profile not found")
        _check_ownership(p, user)
        s.refresh(p)
        query = job_title.strip() if job_title.strip() else _build_keywords(p)
        search_loc = location.strip() if location.strip() else (p.location or "Remote")

        cfg = s.exec(select(Settings)).first() or Settings()
        adzuna_id    = cfg.adzuna_app_id or ""
        adzuna_key   = decrypt_key(cfg.adzuna_app_key)   or ""
        linkedin_key = decrypt_key(cfg.linkedin_api_key) or ""
        indeed_key   = decrypt_key(cfg.indeed_api_key)   or ""
        glassdoor_key = decrypt_key(cfg.glassdoor_api_key) or ""
    # ... rest of function body is unchanged
```

The rest of `search_jobs` (from `logger.info(...)` onwards) stays exactly as it was. Only the function signature and the 5 settings-read lines change.

- [ ] **Step 4: Run tests**

```
cd backend && ../.venv/Scripts/python.exe -m pytest ../tests/test_auth.py::TestJobsRouterAuth -v
```

Expected: both tests PASS

- [ ] **Step 5: Commit**

```bash
git add backend/routers/jobs_router.py tests/test_auth.py
git commit -m "feat: enforce auth + ownership + decrypt keys on jobs route"
```

---

### Task 6: Enforce auth on `sections_router.py`

**Files:**
- Modify: `backend/routers/sections_router.py`
- Modify: `tests/test_auth.py` (add `TestSectionsRouterAuth`)

18 routes to protect across 6 section types. The pattern is identical on every route: add `user: User = Depends(get_current_user)` to the signature, then call `_check_ownership(profile, user)` after `_profile_or_404`.

- [ ] **Step 1: Write failing tests**

Add at the END of `tests/test_auth.py`:

```python
class TestSectionsRouterAuth:
    """Section routes must require auth (spot-check one per action type)."""

    def _owned_profile(self, client, username: str) -> tuple[dict, int]:
        import json as _json
        headers = _auth_headers(client, username)
        data = _json.dumps({"full_name": f"{username} Profile"}).encode()
        imp = client.post(
            "/api/import",
            files={"file": ("p.json", data, "application/json")},
            headers=headers,
        )
        return headers, imp.json()["profile_id"]

    def test_add_skill_no_token_returns_401(self, client):
        _, pid = self._owned_profile(client, "sec_skill_create")
        resp = client.post(f"/api/profiles/{pid}/skills", json={"name": "Python"})
        assert resp.status_code == 401

    def test_add_experience_no_token_returns_401(self, client):
        _, pid = self._owned_profile(client, "sec_exp_create")
        resp = client.post(f"/api/profiles/{pid}/experience", json={"company": "Acme"})
        assert resp.status_code == 401

    def test_add_project_no_token_returns_401(self, client):
        _, pid = self._owned_profile(client, "sec_proj_create")
        resp = client.post(f"/api/profiles/{pid}/projects", json={"name": "MyApp"})
        assert resp.status_code == 401

    def test_add_education_no_token_returns_401(self, client):
        _, pid = self._owned_profile(client, "sec_edu_create")
        resp = client.post(f"/api/profiles/{pid}/education", json={"institution": "MIT"})
        assert resp.status_code == 401

    def test_add_certification_no_token_returns_401(self, client):
        _, pid = self._owned_profile(client, "sec_cert_create")
        resp = client.post(f"/api/profiles/{pid}/certifications", json={"name": "AWS"})
        assert resp.status_code == 401

    def test_wrong_user_add_skill_returns_403(self, client):
        import json as _json
        h_a = _auth_headers(client, "sec_skill_owner_a")
        h_b = _auth_headers(client, "sec_skill_owner_b")
        data = _json.dumps({"full_name": "A Skill Profile"}).encode()
        imp = client.post(
            "/api/import",
            files={"file": ("p.json", data, "application/json")},
            headers=h_a,
        )
        pid = imp.json()["profile_id"]
        resp = client.post(
            f"/api/profiles/{pid}/skills",
            json={"name": "Python"},
            headers=h_b,
        )
        assert resp.status_code == 403

    def test_owner_can_add_skill(self, client):
        headers, pid = self._owned_profile(client, "sec_skill_happy")
        resp = client.post(
            f"/api/profiles/{pid}/skills",
            json={"name": "Python", "category": "Languages", "years": 3},
            headers=headers,
        )
        assert resp.status_code == 201
        assert resp.json()["name"] == "Python"
```

- [ ] **Step 2: Run tests, confirm they fail**

```
cd backend && ../.venv/Scripts/python.exe -m pytest ../tests/test_auth.py::TestSectionsRouterAuth -v
```

Expected: 401/403 tests fail

- [ ] **Step 3: Rewrite `backend/routers/sections_router.py`**

```python
"""CRUD endpoints for profile sub-sections: skills, experience, bullets, projects, education, certifications."""
from fastapi import APIRouter, HTTPException, Depends
from sqlmodel import Session, select
from db import engine
from models import (
    Profile, Skill, Experience, ExperienceBullet,
    Project, Education, Certification, User,
)
from services.activity import log_activity
from logger import get_logger
from routers.auth_utils import get_current_user
from routers.profile_router import _check_ownership
import json

logger = get_logger(__name__)
router = APIRouter(prefix="/profiles", tags=["sections"])


def _profile_or_404(session: Session, profile_id: int) -> Profile:
    p = session.get(Profile, profile_id)
    if not p:
        raise HTTPException(404, f"Profile {profile_id} not found")
    return p


# ──────────────────────────────────────────────
# SKILLS
# ──────────────────────────────────────────────

@router.post("/{profile_id}/skills", status_code=201)
def add_skill(profile_id: int, body: dict, user: User = Depends(get_current_user)):
    with Session(engine) as s:
        p = _profile_or_404(s, profile_id)
        _check_ownership(p, user)
        skill = Skill(
            profile_id=profile_id,
            name=body.get("name", ""),
            category=body.get("category", ""),
            years=float(body.get("years", 0) or 0),
        )
        s.add(skill)
        s.commit()
        s.refresh(skill)
        log_activity("patch", f"added skill '{skill.name}' to profile #{profile_id}", profile_id)
        return {"id": skill.id, "name": skill.name, "category": skill.category, "years": skill.years}


@router.patch("/{profile_id}/skills/{skill_id}")
def update_skill(profile_id: int, skill_id: int, body: dict, user: User = Depends(get_current_user)):
    with Session(engine) as s:
        p = _profile_or_404(s, profile_id)
        _check_ownership(p, user)
        skill = s.get(Skill, skill_id)
        if not skill or skill.profile_id != profile_id:
            raise HTTPException(404, "Skill not found")
        if "name" in body:
            skill.name = body["name"]
        if "category" in body:
            skill.category = body["category"]
        if "years" in body:
            skill.years = float(body["years"] or 0)
        s.add(skill)
        s.commit()
        s.refresh(skill)
        return {"id": skill.id, "name": skill.name, "category": skill.category, "years": skill.years}


@router.delete("/{profile_id}/skills/{skill_id}", status_code=204)
def delete_skill(profile_id: int, skill_id: int, user: User = Depends(get_current_user)):
    with Session(engine) as s:
        p = _profile_or_404(s, profile_id)
        _check_ownership(p, user)
        skill = s.get(Skill, skill_id)
        if not skill or skill.profile_id != profile_id:
            raise HTTPException(404, "Skill not found")
        s.delete(skill)
        s.commit()


# ──────────────────────────────────────────────
# EXPERIENCE
# ──────────────────────────────────────────────

def _exp_dict(e: Experience) -> dict:
    return {
        "id": e.id, "company": e.company, "role": e.role,
        "start": e.start, "end": e.end, "location": e.location,
        "bullets": [{"id": b.id, "text": b.text} for b in (e.bullets or [])],
    }


@router.post("/{profile_id}/experience", status_code=201)
def add_experience(profile_id: int, body: dict, user: User = Depends(get_current_user)):
    with Session(engine) as s:
        p = _profile_or_404(s, profile_id)
        _check_ownership(p, user)
        exp = Experience(
            profile_id=profile_id,
            company=body.get("company", ""),
            role=body.get("role", ""),
            start=body.get("start", ""),
            end=body.get("end", ""),
            location=body.get("location", ""),
        )
        s.add(exp)
        s.flush()
        for b in body.get("bullets", []):
            s.add(ExperienceBullet(
                experience_id=exp.id,
                text=b if isinstance(b, str) else b.get("text", ""),
            ))
        s.commit()
        s.refresh(exp)
        log_activity("patch", f"added experience '{exp.role}' to profile #{profile_id}", profile_id)
        return _exp_dict(exp)


@router.patch("/{profile_id}/experience/{exp_id}")
def update_experience(profile_id: int, exp_id: int, body: dict, user: User = Depends(get_current_user)):
    with Session(engine) as s:
        p = _profile_or_404(s, profile_id)
        _check_ownership(p, user)
        exp = s.get(Experience, exp_id)
        if not exp or exp.profile_id != profile_id:
            raise HTTPException(404, "Experience not found")
        for field in ("company", "role", "start", "end", "location"):
            if field in body:
                setattr(exp, field, body[field])
        s.add(exp)
        s.commit()
        s.refresh(exp)
        return _exp_dict(exp)


@router.delete("/{profile_id}/experience/{exp_id}", status_code=204)
def delete_experience(profile_id: int, exp_id: int, user: User = Depends(get_current_user)):
    with Session(engine) as s:
        p = _profile_or_404(s, profile_id)
        _check_ownership(p, user)
        exp = s.get(Experience, exp_id)
        if not exp or exp.profile_id != profile_id:
            raise HTTPException(404, "Experience not found")
        for b in list(exp.bullets or []):
            s.delete(b)
        s.delete(exp)
        s.commit()


# ──────────────────────────────────────────────
# EXPERIENCE BULLETS
# ──────────────────────────────────────────────

@router.post("/{profile_id}/experience/{exp_id}/bullets", status_code=201)
def add_bullet(profile_id: int, exp_id: int, body: dict, user: User = Depends(get_current_user)):
    with Session(engine) as s:
        p = _profile_or_404(s, profile_id)
        _check_ownership(p, user)
        exp = s.get(Experience, exp_id)
        if not exp or exp.profile_id != profile_id:
            raise HTTPException(404, "Experience not found")
        bullet = ExperienceBullet(experience_id=exp_id, text=body.get("text", ""))
        s.add(bullet)
        s.commit()
        s.refresh(bullet)
        return {"id": bullet.id, "text": bullet.text}


@router.patch("/{profile_id}/experience/{exp_id}/bullets/{bullet_id}")
def update_bullet(
    profile_id: int,
    exp_id: int,
    bullet_id: int,
    body: dict,
    user: User = Depends(get_current_user),
):
    with Session(engine) as s:
        p = _profile_or_404(s, profile_id)
        _check_ownership(p, user)
        bullet = s.get(ExperienceBullet, bullet_id)
        if not bullet or bullet.experience_id != exp_id:
            raise HTTPException(404, "Bullet not found")
        bullet.text = body.get("text", bullet.text)
        s.add(bullet)
        s.commit()
        s.refresh(bullet)
        return {"id": bullet.id, "text": bullet.text}


@router.delete("/{profile_id}/experience/{exp_id}/bullets/{bullet_id}", status_code=204)
def delete_bullet(
    profile_id: int,
    exp_id: int,
    bullet_id: int,
    user: User = Depends(get_current_user),
):
    with Session(engine) as s:
        p = _profile_or_404(s, profile_id)
        _check_ownership(p, user)
        bullet = s.get(ExperienceBullet, bullet_id)
        if not bullet or bullet.experience_id != exp_id:
            raise HTTPException(404, "Bullet not found")
        s.delete(bullet)
        s.commit()


# ──────────────────────────────────────────────
# PROJECTS
# ──────────────────────────────────────────────

def _proj_dict(p: Project) -> dict:
    return {
        "id": p.id, "name": p.name, "description": p.description,
        "link": p.link, "tech": p.get_tech(),
    }


@router.post("/{profile_id}/projects", status_code=201)
def add_project(profile_id: int, body: dict, user: User = Depends(get_current_user)):
    with Session(engine) as s:
        p = _profile_or_404(s, profile_id)
        _check_ownership(p, user)
        proj = Project(
            profile_id=profile_id,
            name=body.get("name", ""),
            description=body.get("description", ""),
            link=body.get("link", ""),
        )
        proj.set_tech(body.get("tech", []))
        s.add(proj)
        s.commit()
        s.refresh(proj)
        log_activity("patch", f"added project '{proj.name}' to profile #{profile_id}", profile_id)
        return _proj_dict(proj)


@router.patch("/{profile_id}/projects/{proj_id}")
def update_project(profile_id: int, proj_id: int, body: dict, user: User = Depends(get_current_user)):
    with Session(engine) as s:
        p = _profile_or_404(s, profile_id)
        _check_ownership(p, user)
        proj = s.get(Project, proj_id)
        if not proj or proj.profile_id != profile_id:
            raise HTTPException(404, "Project not found")
        for field in ("name", "description", "link"):
            if field in body:
                setattr(proj, field, body[field])
        if "tech" in body:
            proj.set_tech(body["tech"])
        s.add(proj)
        s.commit()
        s.refresh(proj)
        return _proj_dict(proj)


@router.delete("/{profile_id}/projects/{proj_id}", status_code=204)
def delete_project(profile_id: int, proj_id: int, user: User = Depends(get_current_user)):
    with Session(engine) as s:
        p = _profile_or_404(s, profile_id)
        _check_ownership(p, user)
        proj = s.get(Project, proj_id)
        if not proj or proj.profile_id != profile_id:
            raise HTTPException(404, "Project not found")
        s.delete(proj)
        s.commit()


# ──────────────────────────────────────────────
# EDUCATION
# ──────────────────────────────────────────────

def _edu_dict(ed: Education) -> dict:
    return {
        "id": ed.id, "institution": ed.institution, "degree": ed.degree,
        "field": ed.field, "start": ed.start, "end": ed.end,
    }


@router.post("/{profile_id}/education", status_code=201)
def add_education(profile_id: int, body: dict, user: User = Depends(get_current_user)):
    with Session(engine) as s:
        p = _profile_or_404(s, profile_id)
        _check_ownership(p, user)
        ed = Education(
            profile_id=profile_id,
            institution=body.get("institution", ""),
            degree=body.get("degree", ""),
            field=body.get("field", ""),
            start=body.get("start", ""),
            end=body.get("end", ""),
        )
        s.add(ed)
        s.commit()
        s.refresh(ed)
        log_activity("patch", f"added education '{ed.institution}' to profile #{profile_id}", profile_id)
        return _edu_dict(ed)


@router.patch("/{profile_id}/education/{edu_id}")
def update_education(profile_id: int, edu_id: int, body: dict, user: User = Depends(get_current_user)):
    with Session(engine) as s:
        p = _profile_or_404(s, profile_id)
        _check_ownership(p, user)
        ed = s.get(Education, edu_id)
        if not ed or ed.profile_id != profile_id:
            raise HTTPException(404, "Education not found")
        for field in ("institution", "degree", "field", "start", "end"):
            if field in body:
                setattr(ed, field, body[field])
        s.add(ed)
        s.commit()
        s.refresh(ed)
        return _edu_dict(ed)


@router.delete("/{profile_id}/education/{edu_id}", status_code=204)
def delete_education(profile_id: int, edu_id: int, user: User = Depends(get_current_user)):
    with Session(engine) as s:
        p = _profile_or_404(s, profile_id)
        _check_ownership(p, user)
        ed = s.get(Education, edu_id)
        if not ed or ed.profile_id != profile_id:
            raise HTTPException(404, "Education not found")
        s.delete(ed)
        s.commit()


# ──────────────────────────────────────────────
# CERTIFICATIONS
# ──────────────────────────────────────────────

def _cert_dict(c: Certification) -> dict:
    return {"id": c.id, "name": c.name, "issuer": c.issuer, "date": c.date}


@router.post("/{profile_id}/certifications", status_code=201)
def add_certification(profile_id: int, body: dict, user: User = Depends(get_current_user)):
    with Session(engine) as s:
        p = _profile_or_404(s, profile_id)
        _check_ownership(p, user)
        cert = Certification(
            profile_id=profile_id,
            name=body.get("name", ""),
            issuer=body.get("issuer", ""),
            date=body.get("date", ""),
        )
        s.add(cert)
        s.commit()
        s.refresh(cert)
        log_activity("patch", f"added cert '{cert.name}' to profile #{profile_id}", profile_id)
        return _cert_dict(cert)


@router.patch("/{profile_id}/certifications/{cert_id}")
def update_certification(
    profile_id: int,
    cert_id: int,
    body: dict,
    user: User = Depends(get_current_user),
):
    with Session(engine) as s:
        p = _profile_or_404(s, profile_id)
        _check_ownership(p, user)
        cert = s.get(Certification, cert_id)
        if not cert or cert.profile_id != profile_id:
            raise HTTPException(404, "Certification not found")
        for field in ("name", "issuer", "date"):
            if field in body:
                setattr(cert, field, body[field])
        s.add(cert)
        s.commit()
        s.refresh(cert)
        return _cert_dict(cert)


@router.delete("/{profile_id}/certifications/{cert_id}", status_code=204)
def delete_certification(
    profile_id: int,
    cert_id: int,
    user: User = Depends(get_current_user),
):
    with Session(engine) as s:
        p = _profile_or_404(s, profile_id)
        _check_ownership(p, user)
        cert = s.get(Certification, cert_id)
        if not cert or cert.profile_id != profile_id:
            raise HTTPException(404, "Certification not found")
        s.delete(cert)
        s.commit()
```

- [ ] **Step 4: Run tests**

```
cd backend && ../.venv/Scripts/python.exe -m pytest ../tests/test_auth.py::TestSectionsRouterAuth -v
```

Expected: all 7 tests PASS

- [ ] **Step 5: Commit**

```bash
git add backend/routers/sections_router.py tests/test_auth.py
git commit -m "feat: enforce auth + ownership on all 18 sections routes"
```

---

### Task 7: Startup migration + encrypt on write in `settings_router.py`

**Files:**
- Modify: `backend/routers/settings_router.py`
- Create: `tests/test_settings_crypto.py`

`_get_or_create` gains a startup migration that encrypts any plain-text key fields already in the DB. The PUT handler encrypts before storing. GET is unchanged (already returns `***` masks).

- [ ] **Step 1: Write failing tests**

Create `tests/test_settings_crypto.py`:

```python
"""Tests for settings key encryption at rest."""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent / "backend"))


def test_put_settings_stores_encrypted_key(client):
    """PUT /settings stores Fernet ciphertext, not plain-text."""
    resp = client.put("/api/settings", json={"api_key": "sk-test-plain-key"})
    assert resp.status_code == 200

    # Read stored value directly from DB to verify encryption
    from db import engine
    from sqlmodel import Session, select
    from models import Settings
    with Session(engine) as s:
        cfg = s.exec(select(Settings)).first()
        assert cfg is not None
        assert cfg.api_key.startswith("gAAAAA"), (
            f"Expected Fernet ciphertext but got: {cfg.api_key!r}"
        )


def test_put_settings_mask_sentinel_leaves_key_unchanged(client):
    """PUT /settings with '***' as value does not overwrite the stored key."""
    client.put("/api/settings", json={"api_key": "sk-original-key"})

    from db import engine
    from sqlmodel import Session, select
    from models import Settings
    with Session(engine) as s:
        original_ct = s.exec(select(Settings)).first().api_key

    client.put("/api/settings", json={"api_key": "***"})

    with Session(engine) as s:
        after_ct = s.exec(select(Settings)).first().api_key

    assert after_ct == original_ct


def test_startup_migration_encrypts_plain_text(client):
    """_get_or_create encrypts a plain-text key written directly to DB."""
    from db import engine
    from sqlmodel import Session, select
    from models import Settings

    # Write plain-text directly to DB (simulating a pre-encryption deployment)
    with Session(engine) as s:
        cfg = s.exec(select(Settings)).first()
        if not cfg:
            cfg = Settings()
            s.add(cfg)
            s.commit()
            s.refresh(cfg)
        cfg.anthropic_api_key = "raw-plain-key-12345"
        s.add(cfg)
        s.commit()

    # Trigger _get_or_create via GET /settings — migration runs
    client.get("/api/settings")

    # Verify it's now encrypted
    with Session(engine) as s:
        cfg = s.exec(select(Settings)).first()
        assert cfg.anthropic_api_key.startswith("gAAAAA"), (
            f"Migration did not encrypt plain-text key: {cfg.anthropic_api_key!r}"
        )


def test_startup_migration_idempotent(client):
    """Running migration twice does not change an already-encrypted key."""
    from db import engine
    from sqlmodel import Session, select
    from models import Settings

    client.put("/api/settings", json={"openrouter_api_key": "sk-router-test"})

    with Session(engine) as s:
        ct1 = s.exec(select(Settings)).first().openrouter_api_key

    assert ct1.startswith("gAAAAA")

    # GET triggers migration again
    client.get("/api/settings")

    with Session(engine) as s:
        ct2 = s.exec(select(Settings)).first().openrouter_api_key

    assert ct1 == ct2, "Migration changed an already-encrypted key"
```

- [ ] **Step 2: Run tests, confirm they fail**

```
cd backend && ../.venv/Scripts/python.exe -m pytest ../tests/test_settings_crypto.py -v
```

Expected: `test_put_settings_stores_encrypted_key` fails (key stored as plain-text)

- [ ] **Step 3: Rewrite `backend/routers/settings_router.py`**

```python
import os
from fastapi import APIRouter
from sqlmodel import Session, select
from db import engine
from models import Settings
from services.ai_service import ollama_available, list_ollama_models
from crypto import _KEY_FIELDS, encrypt_key, _is_encrypted

router = APIRouter(prefix="/settings", tags=["settings"])

ALLOWED = {
    "ai_provider", "ai_model", "api_key", "anthropic_api_key", "openrouter_api_key",
    "use_local_ai", "ollama_base_url", "ollama_model", "local_for_simple",
    "adzuna_app_id", "adzuna_app_key",
    "linkedin_api_key", "indeed_api_key", "glassdoor_api_key",
}


def _migrate_encrypt_existing_keys(cfg: Settings, session: Session) -> None:
    """Idempotent: encrypts any plain-text key fields present in the DB."""
    changed = False
    for field in _KEY_FIELDS:
        val = getattr(cfg, field, "") or ""
        if val and not _is_encrypted(val):
            setattr(cfg, field, encrypt_key(val))
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
    _migrate_encrypt_existing_keys(s, session)
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
            if k not in ALLOWED:
                continue
            if k in _KEY_FIELDS:
                if v == "***":
                    continue          # sentinel — keep existing value
                v = encrypt_key(v)   # plain-text → Fernet ciphertext
            setattr(cfg, k, v)
        session.add(cfg)
        session.commit()
        return {"ok": True}


@router.get("/ollama/status")
def ollama_status(base_url: str = "http://localhost:11434"):
    available = ollama_available(base_url)
    models = list_ollama_models(base_url) if available else []
    return {"available": available, "models": models}
```

- [ ] **Step 4: Run tests**

```
cd backend && ../.venv/Scripts/python.exe -m pytest ../tests/test_settings_crypto.py -v
```

Expected: all 4 tests PASS

- [ ] **Step 5: Commit**

```bash
git add backend/routers/settings_router.py tests/test_settings_crypto.py
git commit -m "feat: encrypt API keys at rest + startup migration in settings_router"
```

---

### Task 8: Decrypt keys in `ai_service._load_settings()`

**Files:**
- Modify: `backend/services/ai_service.py`
- Create: `tests/test_ai_service_crypto.py`

`_load_settings()` returns raw DB values; after this task it decrypts `_KEY_FIELDS` in-memory. Callers (`complete_simple`, `complete_complex`) continue to work without change.

- [ ] **Step 1: Write failing tests**

Create `tests/test_ai_service_crypto.py`:

```python
"""Tests for ai_service decrypting key fields after loading from DB."""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent / "backend"))

from crypto import encrypt_key, _is_encrypted


def test_load_settings_returns_decrypted_key(client):
    """_load_settings() decrypts stored Fernet ciphertext before returning."""
    # Store an encrypted key via PUT /settings
    client.put("/api/settings", json={"api_key": "sk-should-be-decrypted"})

    # Verify it's encrypted in DB
    from db import engine
    from sqlmodel import Session, select
    from models import Settings
    with Session(engine) as s:
        cfg = s.exec(select(Settings)).first()
        assert cfg.api_key.startswith("gAAAAA")

    # Now call _load_settings() and verify the returned value is decrypted
    from services.ai_service import _load_settings
    loaded = _load_settings()
    assert loaded.api_key == "sk-should-be-decrypted", (
        f"Expected plain-text but got: {loaded.api_key!r}"
    )
    assert not _is_encrypted(loaded.api_key)


def test_load_settings_plain_key_passthrough(client):
    """_load_settings() passes through plain-text keys (not yet encrypted, edge case)."""
    from db import engine
    from sqlmodel import Session, select
    from models import Settings

    with Session(engine) as s:
        cfg = s.exec(select(Settings)).first()
        if not cfg:
            cfg = Settings()
            s.add(cfg)
            s.commit()
            s.refresh(cfg)
        cfg.anthropic_api_key = "plain-key-no-encrypt"
        s.add(cfg)
        s.commit()

    from services.ai_service import _load_settings
    loaded = _load_settings()
    assert loaded.anthropic_api_key == "plain-key-no-encrypt"
```

- [ ] **Step 2: Run tests, confirm they fail**

```
cd backend && ../.venv/Scripts/python.exe -m pytest ../tests/test_ai_service_crypto.py -v
```

Expected: `test_load_settings_returns_decrypted_key` fails (loaded value is Fernet ciphertext, not plain-text)

- [ ] **Step 3: Update `backend/services/ai_service.py` — add decrypt loop to `_load_settings`**

Add the imports at the top of `ai_service.py` (after the existing `from db import engine` line):

```python
from crypto import decrypt_key, _KEY_FIELDS
```

Replace the `_load_settings` function (lines 29–37) with:

```python
def _load_settings() -> Settings:
    with Session(engine) as s:
        cfg = s.exec(select(Settings)).first()
        if not cfg:
            cfg = Settings()
            s.add(cfg)
            s.commit()
            s.refresh(cfg)
    # Decrypt in-memory only — never persist the decrypted object back to DB
    for field in _KEY_FIELDS:
        val = getattr(cfg, field, "") or ""
        setattr(cfg, field, decrypt_key(val))
    return cfg
```

- [ ] **Step 4: Run tests**

```
cd backend && ../.venv/Scripts/python.exe -m pytest ../tests/test_ai_service_crypto.py -v
```

Expected: both tests PASS

- [ ] **Step 5: Commit**

```bash
git add backend/services/ai_service.py tests/test_ai_service_crypto.py
git commit -m "feat: decrypt API key fields in ai_service._load_settings()"
```

---

### Task 9: Full test suite verification

Run the complete test suite and verify nothing regressed.

- [ ] **Step 1: Run all tests**

```
cd backend && ../.venv/Scripts/python.exe -m pytest ../tests/ -v --tb=short
```

Expected output: all tests in these files PASS:
- `test_auth.py` — all original tests + new `TestProfileRouterAuth`, `TestAnalysisRouterAuth`, `TestJobsRouterAuth`, `TestSectionsRouterAuth`
- `test_crypto.py` — all 10 tests
- `test_settings_crypto.py` — all 4 tests
- `test_ai_service_crypto.py` — both tests
- `test_api_profiles.py` — all existing profile import/CRUD tests (these use authenticated requests already)
- `test_parsers.py` — unaffected (no auth changes)

If `test_api_profiles.py` tests fail, they likely call profile/section endpoints without a token. Fix them by adding `headers = _auth_headers(client, "legacy_user")` to any request that creates or reads a profile.

- [ ] **Step 2: Fix any regressions in existing tests**

If `test_api_profiles.py` has unauthenticated profile or section calls, wrap them with auth:

```python
# At top of the failing test function — add this pattern:
headers = _auth_headers(client, "legacy_unique_username")
# Then pass headers= to each profile/section API call
```

Use unique usernames per test to avoid conflicts (the test client is session-scoped).

- [ ] **Step 3: Final commit if any fixes were needed**

```bash
git add tests/
git commit -m "fix: update existing tests to use auth headers after enforcement"
```

- [ ] **Step 4: Create summary tag**

```bash
git tag security-group-b-done
```

---

## Error contract summary

| Condition | HTTP code |
|---|---|
| No token / expired / invalid | 401 |
| Valid token, wrong user's profile | 403 |
| Profile not found | 404 |
| Decrypt failure (corrupted ciphertext) | `decrypt_key` returns raw value unchanged; downstream API call fails with its own error |

## Known gap (tracked, not in scope)

`import_router.py` creates profiles without auth — imported profiles will have `user_id = NULL` and are accessible by any authenticated user under the NULL-user_id policy. This is intentional for the personal-tool use case. Auth on import is a separate follow-up.
