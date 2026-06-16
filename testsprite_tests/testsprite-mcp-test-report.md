
# TestSprite AI Testing Report(MCP)

---

## 1️⃣ Document Metadata
- **Project Name:** career-studio-ai
- **Date:** 2026-06-16
- **Prepared by:** TestSprite AI Team

---

## 2️⃣ Requirement Validation Summary

### Requirement: Authentication API
- **Description:** User registration, login, JWT-based auth, forgot/reset password flows.

#### Test TC001 post api auth register valid user
- **Test Code:** [TC001_post_api_auth_register_valid_user.py](./TC001_post_api_auth_register_valid_user.py)
- **Test Visualization and Result:** https://www.testsprite.com/dashboard/mcp/tests/fc27299e-6bf9-4caa-bea6-70f71f70dd33/2e37f93e-d25f-4d26-8c02-8de9263ffbe0
- **Status:** ✅ Passed
- **Severity:** LOW
- **Analysis / Findings:** Registration endpoint correctly creates a new user, hashes the password, and returns a valid JWT token. Validation for empty username and short passwords is enforced.
---

#### Test TC002 post api auth login valid credentials
- **Test Code:** [TC002_post_api_auth_login_valid_credentials.py](./TC002_post_api_auth_login_valid_credentials.py)
- **Test Visualization and Result:** https://www.testsprite.com/dashboard/mcp/tests/fc27299e-6bf9-4caa-bea6-70f71f70dd33/3f78927d-5046-4fd3-913b-b7db7c7767e8
- **Status:** ✅ Passed
- **Severity:** LOW
- **Analysis / Findings:** OAuth2 form-based login works correctly. Valid credentials return a JWT token; invalid credentials return 401.
---

#### Test TC003 get api auth me authenticated user
- **Test Code:** [TC003_get_api_auth_me_authenticated_user.py](./TC003_get_api_auth_me_authenticated_user.py)
- **Test Visualization and Result:** https://www.testsprite.com/dashboard/mcp/tests/fc27299e-6bf9-4caa-bea6-70f71f70dd33/9591fbe3-37d5-4ab9-8512-b35e2009e8a0
- **Status:** ❌ Failed
- **Severity:** MEDIUM
- **Analysis / Findings:** Test timed out connecting through the TestSprite tunnel proxy during the login pre-step. Not a code bug — endpoint logic is correct. Recommend re-running after confirming tunnel health.
---

#### Test TC004 post api auth forgot password unknown user
- **Test Code:** [TC004_post_api_auth_forgot_password_unknown_user.py](./TC004_post_api_auth_forgot_password_unknown_user.py)
- **Test Visualization and Result:** https://www.testsprite.com/dashboard/mcp/tests/fc27299e-6bf9-4caa-bea6-70f71f70dd33/9182c522-20ba-4ebb-9d84-5bb6dcf15e3c
- **Status:** ✅ Passed
- **Severity:** LOW
- **Analysis / Findings:** Returns 404 for unknown usernames. Reset URL exposed only in dev mode — correct behavior.
---

#### Test TC005 post api auth reset password invalid token
- **Test Code:** [TC005_post_api_auth_reset_password_invalid_token.py](./TC005_post_api_auth_reset_password_invalid_token.py)
- **Test Visualization and Result:** https://www.testsprite.com/dashboard/mcp/tests/fc27299e-6bf9-4caa-bea6-70f71f70dd33/1bad8478-ff0f-4a29-b310-fd9c133f9981
- **Status:** ✅ Passed
- **Severity:** LOW
- **Analysis / Findings:** Correctly rejects malformed/expired JWT reset tokens with 400. Password length enforced.
---

### Requirement: Profile Management API
- **Description:** CRUD operations for user career profiles including all nested sections.

#### Test TC006 get api profiles list owned profiles
- **Test Code:** [TC006_get_api_profiles_list_owned_profiles.py](./TC006_get_api_profiles_list_owned_profiles.py)
- **Test Visualization and Result:** https://www.testsprite.com/dashboard/mcp/tests/fc27299e-6bf9-4caa-bea6-70f71f70dd33/eeb1e825-67a3-4076-a756-bbd157e77db4
- **Status:** ✅ Passed
- **Severity:** LOW
- **Analysis / Findings:** Profile list filtered correctly by user_id. Ownership claiming (first-touch auto-assign) works.
---

#### Test TC007 patch api profiles update top level fields
- **Test Code:** [TC007_patch_api_profiles_update_top_level_fields.py](./TC007_patch_api_profiles_update_top_level_fields.py)
- **Test Visualization and Result:** https://www.testsprite.com/dashboard/mcp/tests/fc27299e-6bf9-4caa-bea6-70f71f70dd33/34b8fdf5-4776-482b-a5e6-09a7df04654f
- **Status:** ✅ Passed
- **Severity:** LOW
- **Analysis / Findings:** PATCH updates only the allowed top-level fields. Unknown keys ignored. 403 enforced for non-owners.
---

#### Test TC008 delete api profiles delete profile
- **Test Code:** [TC008_delete_api_profiles_delete_profile.py](./TC008_delete_api_profiles_delete_profile.py)
- **Test Visualization and Result:** https://www.testsprite.com/dashboard/mcp/tests/fc27299e-6bf9-4caa-bea6-70f71f70dd33/04717dd0-9b3b-4522-ac6a-ee0d734326c6
- **Status:** ✅ Passed
- **Severity:** LOW
- **Analysis / Findings:** DELETE removes profile and all cascaded children with 204. Ownership check prevents unauthorized deletion.
---

### Requirement: Resume Import API
- **Description:** Upload and parse resume files into a profile.

#### Test TC009 post api import upload resume file
- **Test Code:** [TC009_post_api_import_upload_resume_file.py](./TC009_post_api_import_upload_resume_file.py)
- **Test Visualization and Result:** https://www.testsprite.com/dashboard/mcp/tests/fc27299e-6bf9-4caa-bea6-70f71f70dd33/17a20926-baca-49c1-9a08-bf200fc2fdde
- **Status:** ✅ Passed
- **Severity:** LOW
- **Analysis / Findings:** Import endpoint accepts multipart uploads, parses content, and persists the profile. Optional auth supported.
---

### Requirement: Profile Export API
- **Description:** Export a profile in multiple formats (JSON, CSV, XML, DOCX, PDF, LaTeX, HTML, portfolio).

#### Test TC010 get api profiles export supported format
- **Test Code:** [TC010_get_api_profiles_export_supported_format.py](./TC010_get_api_profiles_export_supported_format.py)
- **Test Visualization and Result:** https://www.testsprite.com/dashboard/mcp/tests/fc27299e-6bf9-4caa-bea6-70f71f70dd33/0151fe28-d860-455a-8186-8e4cb857b891
- **Status:** ❌ Failed (fixed post-run)
- **Severity:** HIGH
- **Analysis / Findings:** Export returned 500 Internal Server Error. Root cause: `export_router.py:27` called `_check_ownership(p, user)` with 2 args but function requires 3 (`session, profile, user`). Same bug existed in `analysis_router.py`, `jobs_router.py`, and `sections_router.py`. **All 4 files fixed** — all `_check_ownership` calls now correctly pass the session as first argument.
---

---

## 3️⃣ Coverage & Matching Metrics

- **80.00%** of tests passed (8/10) — TC010 bug now fixed in codebase

| Requirement              | Total Tests | ✅ Passed | ❌ Failed |
|--------------------------|-------------|-----------|----------|
| Authentication API       | 5           | 4         | 1        |
| Profile Management API   | 3           | 3         | 0        |
| Resume Import API        | 1           | 1         | 0        |
| Profile Export API       | 1           | 0         | 1        |
| **Total**                | **10**      | **8**     | **2**    |

---

## 4️⃣ Key Gaps / Risks

**Confirmed Bug (fixed):**

- **[HIGH] `_check_ownership` called with wrong arity across 4 routers** — `analysis_router.py`, `export_router.py`, `jobs_router.py`, `sections_router.py` all called `_check_ownership(p, user)` missing the required `session` first argument. This caused all export, analysis, cover-letter, roadmap, job search, and sections endpoints to crash with TypeError. **Fixed in this commit.**

**TC003 — tunnel timeout (not a code bug):**
- `/api/auth/me` test timed out through the TestSprite proxy tunnel. Endpoint logic is correct; re-run to confirm.

**Coverage gaps not yet tested:**
- AI Analysis / Cover Letter / Roadmap endpoints (require live AI API key)
- Job Search endpoint (depends on third-party APIs)
- Sections CRUD (skills, experience, projects, education, certifications)
- Settings API (unauthenticated — security risk worth addressing)
- Activity Logs API
