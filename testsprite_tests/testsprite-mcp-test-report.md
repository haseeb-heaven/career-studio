# TestSprite MCP Test Report

**Date:** 2026-06-16  
**Branch:** `refactor/pdf-stack`  
**Suite:** Career Studio AI — Frontend (15 tests) + Backend API (10 tests)  
**Final Result:** 25/25 PASS

---

## Executive Summary

All 25 TestSprite-generated tests now pass after a multi-phase remediation effort. The root causes fell into four categories:

1. **Auth wall for guest users** — `GET`/`PATCH` profile endpoints and all sections/jobs endpoints required full authentication, blocking the guest upload→edit flow.
2. **Missing UI feedback** — Three components (`UploadScreen`, `ContactTab`, `SummaryTab`) did not call `toast()` after save operations.
3. **Broken TC015** — The reset-password test used a hardcoded fake JWT token that the backend correctly rejected.
4. **Stale hardcoded test data** — Two tests (`TC011`, `TC001_backend`) used fixed usernames that conflicted with prior run data in the database.

---

## Frontend Tests (15/15 PASS)

| TC | Test Name | Status | Root Cause (if was failing) |
|----|-----------|--------|-----------------------------|
| TC001 | Sign in to access the authenticated workspace | PASS | — |
| TC002 | Upload a supported resume and open the editor with parsed data | PASS | `GET /api/profiles/{id}` required auth; fixed with `get_current_user_optional` |
| TC003 | Update contact details and save the profile | PASS | `PATCH /api/profiles/{id}` required auth; fixed with optional auth + unclaimed-profile guard |
| TC004 | See a toast after importing a resume | PASS | `UploadScreen.tsx` missing `toast("success", "Resume imported", ...)` call |
| TC005 | Continue as a guest user | PASS | Old test tried `scroll_into_view_if_needed()` on hidden file input; rewritten |
| TC006 | Open a saved profile from the list | PASS | `GET /api/profiles/` returns 401 for guests; rewritten to register+login via API, then UI |
| TC007 | Edit and save the professional summary | PASS | `SummaryTab.tsx` missing toast; `PATCH` endpoint required auth |
| TC008 | Add a new skill to the profile | PASS | `--single-process` caused browser crash; replaced with `--no-sandbox` |
| TC009 | See a toast after saving changes | PASS | `ContactTab.tsx` missing `toast("success", "Contact saved", ...)` call |
| TC010 | Add a new experience entry | PASS | `--single-process` crash + strict-mode violation; rewritten with fixture upload |
| TC011 | Create a new account successfully | PASS | Hardcoded username `haseeb-heaven-20260616-01` already in DB; fixed with `time.time()` suffix |
| TC012 | Request a password reset link | PASS | — |
| TC013 | Remove an existing skill from the profile | PASS | Old test tried to click hidden file input; rewritten to use fixture upload + Del button |
| TC014 | Search jobs from profile skills | PASS | Tab label is "Job Matching" not "Jobs"; button label is "Find Jobs" not "Search Jobs" |
| TC015 | Open the reset password flow from a token link | PASS | Hardcoded fake JWT rejected by backend; rewritten to call `/api/auth/forgot-password` for real token |

---

## Backend API Tests (10/10 PASS)

| TC | Test Name | Status | Root Cause (if was failing) |
|----|-----------|--------|-----------------------------|
| TC001 | POST /api/auth/register — valid user | PASS | Hardcoded username already in DB; fixed with `time.time()` suffix |
| TC002 | POST /api/auth/login — valid credentials | PASS | — |
| TC003 | GET /api/auth/me — authenticated user | PASS | — |
| TC004 | POST /api/auth/forgot-password — unknown user | PASS | — |
| TC005 | POST /api/auth/reset-password — invalid token | PASS | — |
| TC006 | GET /api/profiles/ — list owned profiles | PASS | — |
| TC007 | PATCH /api/profiles/{id} — update top-level fields | PASS | — |
| TC008 | DELETE /api/profiles/{id} — delete profile | PASS | — |
| TC009 | POST /api/import — upload resume file | PASS | — |
| TC010 | GET /api/profiles/{id}/export — supported format | PASS | — |

---

## Backend Changes Made

### `backend/routers/profile_router.py`
- `GET /{profile_id}`: Changed from `Depends(get_current_user)` to `Depends(get_current_user_optional)`. Unclaimed profiles (`user_id=None`) are readable without auth; claimed profiles require the owning user.
- `PATCH /{profile_id}`: Same pattern — optional auth with unclaimed-profile guest access.

### `backend/routers/sections_router.py`
- Added `_assert_access(session, profile, user)` helper that replicates the unclaimed-profile logic.
- All section endpoints (skills, experience, projects, education, certifications) changed from `get_current_user` to `get_current_user_optional` + `_assert_access`.

### `backend/routers/jobs_router.py`
- `search_jobs` endpoint changed to `get_current_user_optional` with same unclaimed-profile guard pattern.

---

## Frontend Changes Made

### `frontend/src/components/UploadScreen.tsx`
- Added `toast("success", "Resume imported", "Profile created successfully")` before the `onImported` callback.

### `frontend/src/components/tabs/ContactTab.tsx`
- Added `useToast` import and `toast("success", "Contact saved", "")` after successful `patchProfile` call.

### `frontend/src/components/tabs/SummaryTab.tsx`
- Added `useToast` import and `toast("success", "Summary saved", "")` after successful `patchProfile` call.

---

## Test Infrastructure Changes

### Fixture directory
- Created `D:/Code/career-studio-ai/fixtures/` (project root) with: `profile.json`, `resume.pdf`, `sample_resume.json`, `sample_resume.pdf`, `test_resume.pdf`.
- Tests reference `./fixtures/` relative to project root via `os.path.abspath("./fixtures/...")`.

### Browser launch arguments
- Removed `--single-process` (causes `TargetClosedError` on certain clicks in Chromium headless).
- Replaced with `--no-sandbox` across all rewritten frontend tests.

### TC015 reset-password flow
```
Old: navigate to /?token=<hardcoded-fake-jwt>  → backend rejects → FAIL
New: call /api/auth/forgot-password via httpx → extract dev_reset_url (real JWT)
     → navigate to that URL → fill new password → assert "Password updated successfully"
```

### TC006 saved-profile flow
```
Old: Continue as guest → click "Open Saved Profile" → GET /api/profiles/ returns 401 → FAIL
New: register user via httpx → import profile with auth token via httpx
     → log in via UI → click "Open Saved Profile" → click "Open →" → assert editor loads
```

---

## Key Patterns Established

1. **Guest-accessible endpoints:** Use `get_current_user_optional`. For unclaimed profiles: allow. For claimed profiles without auth: 403.
2. **Unique test users:** All tests that register users use `str(int(time.time()))[-6:]` as a suffix to avoid conflicts across runs.
3. **Tab navigation:** Use `page.locator('button:has-text("Label")')` (not `get_by_role`) because sidebar tab buttons include emoji in the text.
4. **Fixture uploads:** `file_input.set_input_files(FIXTURE)` on `input[type="file"]` bypasses drag-and-drop and avoids file-dialog OS popups.
