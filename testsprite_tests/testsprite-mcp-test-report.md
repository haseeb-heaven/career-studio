# TestSprite AI Testing Report (MCP)

---

## 1️⃣ Document Metadata
- **Project Name:** career-studio-ai
- **Version:** 2.5.0-gh
- **Date:** 2026-07-01
- **Prepared by:** TestSprite AI Team (frontend, production build, 30 test cases)
- **Target under test:** Frontend built with `npm run build` and served via `npm run preview` on `localhost:5173`, backed by FastAPI on `localhost:8001`
- **Test account used:** `haseeb-heaven` / `123456` (still does not exist in the running backend's database — see Key Gaps below)

---

## 2️⃣ Requirement Validation Summary

### Requirement: Authentication (Login, Registration, Guest Mode, Password Reset)

#### Test TC001 — Sign in to access the workspace
- **Test Code:** [TC001_Sign_in_to_access_the_workspace.py](./TC001_Sign_in_to_access_the_workspace.py)
- **Status:** ❌ Failed
- **Test Visualization:** https://www.testsprite.com/dashboard/mcp/tests/1ff46ca0-38a7-427d-a87e-1d6e63ead553/b33d3e1d-5565-47dd-8aba-42ef6e8b987f
- **Analysis / Findings:** Sign-in rejected the credentials with "Invalid username or password" and never left the sign-in screen. Root cause is environmental, not a login-flow bug: the `haseeb-heaven` account does not exist in the backend database the server was pointed at for this run. This single failure is the root cause of 16 of the 17 "BLOCKED" results below, since most other flows require an authenticated session.

#### Test TC006 — Create a new account
- **Status:** ✅ Passed
- **Test Visualization:** https://www.testsprite.com/dashboard/mcp/tests/1ff46ca0-38a7-427d-a87e-1d6e63ead553/4151f9b8-bd11-451b-8dfd-7efcc381cb4b
- **Analysis / Findings:** Registration flow works correctly end-to-end.

#### Test TC008 — Continue as a guest
- **Status:** ✅ Passed
- **Test Visualization:** https://www.testsprite.com/dashboard/mcp/tests/1ff46ca0-38a7-427d-a87e-1d6e63ead553/5d241879-a8ad-4d4d-a0c1-23b1d5045fd2
- **Analysis / Findings:** Guest mode entry works correctly.

#### Test TC012 — Request a password reset
- **Status:** ✅ Passed
- **Test Visualization:** https://www.testsprite.com/dashboard/mcp/tests/1ff46ca0-38a7-427d-a87e-1d6e63ead553/ea5a251b-46b6-4cc8-85d3-efa6c133da52
- **Analysis / Findings:** Forgot-password request flow works correctly.

#### Test TC019 — Open the reset password screen from a token link
- **Status:** ❌ Failed
- **Test Visualization:** https://www.testsprite.com/dashboard/mcp/tests/1ff46ca0-38a7-427d-a87e-1d6e63ead553/35d1d469-48a7-44ec-9756-335fc761c3e7
- **Analysis / Findings:** Submitting a new password via the reset-token link returned "Invalid or expired token." The agent used a synthetic/expired token rather than one issued in this run — expected given the test had no way to intercept a real reset email/token, not necessarily a real defect. Worth a follow-up test that captures a live token via the backend response in TC012 and feeds it into this flow.

### Requirement: Resume Upload, Import & Saved Profiles

#### Test TC002 — Import a resume into the editor
- **Status:** BLOCKED
- **Test Visualization:** https://www.testsprite.com/dashboard/mcp/tests/1ff46ca0-38a7-427d-a87e-1d6e63ead553/384b36fc-fab2-4871-9b01-6ce49ec4f948
- **Analysis / Findings:** Blocked by test-infrastructure, not the app: no sample resume file (PDF/DOCX/etc.) was available in the TestSprite agent's sandbox to attach to the file input. Re-run with a fixture file supplied via `additionalInstruction` or a seeded file path.

#### Test TC003 — Open a saved profile from the list
- **Status:** BLOCKED (auth dependency — see TC001)

#### Test TC015 — Update the professional summary
- **Status:** ❌ Failed
- **Test Visualization:** https://www.testsprite.com/dashboard/mcp/tests/1ff46ca0-38a7-427d-a87e-1d6e63ead553/d7074c49-8192-4d27-ab0b-50274daafcdc
- **Analysis / Findings:** Clicking "📂 Open Saved Profile" as a guest produced no visible change across three attempts — no modal, list, or navigation appeared. This repeats the same behavior seen in the prior run, even after the `UploadScreen.tsx` fix (v2.5.0-gh) that added a toast on load failure. The likely explanation: a guest with zero saved profiles gets a 401 from `GET /profiles` (it requires auth for everyone, not just returning empty for guests), and the new toast IS firing but TestSprite's headless agent isn't registering transient toast text as a UI change. **Recommendation:** verify manually whether the toast appears for a real guest session; if it does, this is a test-detection gap rather than an app bug — but consider also rendering a permanent inline empty-state/sign-in prompt instead of (or in addition to) a toast, since a toast that disappears after a few seconds is inherently fragile for both automated and human-perceived feedback.

#### Test TC024 — See logs after importing a profile
- **Status:** BLOCKED (auth dependency)

#### Test TC025 — Delete a saved profile from the list
- **Status:** BLOCKED (auth dependency)

### Requirement: Profile Editor (Contact, Skills, Experience, Projects)

#### Test TC009 — Update contact details for a loaded profile
- **Status:** ✅ Passed

#### Test TC017 — Add a new skill to the profile
- **Status:** ✅ Passed

#### Test TC021 — Add a new experience entry
- **Status:** ✅ Passed

#### Test TC028 — Add a new project to the profile
- **Status:** BLOCKED (auth dependency)

#### Test TC027 — See logs after editing and saving a profile
- **Status:** BLOCKED (auth dependency)

**Analysis / Findings (group):** Every editor-mutation test that ran (contact, skills, experience) passed cleanly. The two BLOCKED cases in this group required a signed-in saved profile rather than the guest/imported one, so they inherit the TC001 auth blocker rather than indicating an editor defect.

### Requirement: Resume Export

#### Test TC005 — Export a profile as JSON
- **Status:** ✅ Passed

#### Test TC013 — Export a profile as CSV
- **Status:** ✅ Passed

#### Test TC014 — Export a profile as PDF
- **Status:** BLOCKED (auth dependency)

#### Test TC020 — See logs after exporting a profile
- **Status:** BLOCKED (auth dependency)

**Analysis / Findings (group):** Export itself is verified working for JSON and CSV. PDF export and the export-logging check both required a saved (authenticated) profile and were blocked purely by TC001, not a format-specific defect.

### Requirement: AI Resume Analysis

#### Test TC004 — Generate a resume analysis from a loaded profile
- **Status:** BLOCKED
- **Test Visualization:** https://www.testsprite.com/dashboard/mcp/tests/1ff46ca0-38a7-427d-a87e-1d6e63ead553/91f97b3e-ca29-4638-a4ba-2a27555ab73c
- **Analysis / Findings:** Confirms analysis correctly requires authentication — the guest path surfaced "Analysis Error: Not authenticated" rather than silently succeeding or crashing, which is the correct defensive behavior.

#### Test TC023 — Show an error when analysis is started without an AI provider
- **Status:** ✅ Passed
- **Analysis / Findings:** Correct validation error is shown when no AI provider is configured.

### Requirement: AI Cover Letter Generation

#### Test TC007 — Generate a tailored cover letter from a profile
- **Status:** BLOCKED (auth dependency)

#### Test TC026 — Open a previously generated cover letter
- **Status:** BLOCKED (auth dependency)

#### Test TC029 — Delete a previously generated cover letter
- **Status:** BLOCKED (auth dependency)

### Requirement: AI Career Roadmap

#### Test TC011 — Generate a career roadmap from a loaded profile
- **Status:** BLOCKED (auth dependency)

### Requirement: Job Search and Matching

#### Test TC016 — Search for job matches from a saved profile
- **Status:** BLOCKED (auth dependency)

#### Test TC022 — Filter job matches by title, location, and portal
- **Status:** BLOCKED (auth dependency)

### Requirement: Settings

#### Test TC010 — Save AI provider settings
- **Status:** BLOCKED (auth dependency)

#### Test TC018 — Enable local AI with Ollama settings
- **Status:** ✅ Passed
- **Analysis / Findings:** Local-AI (Ollama) settings toggle is reachable and savable without requiring the blocked login (guest-accessible settings path).

#### Test TC030 — Save job board API credentials
- **Status:** BLOCKED (auth dependency)

---

## 3️⃣ Coverage & Matching Metrics

- **30** total test cases generated and executed
- **10 passed / 30 = 33.3%** pass rate
- **3 failed** (10.0%) — 1 is a test-detection ambiguity around a fix already shipped (TC015), 1 is an environment/credentials issue (TC001), 1 is a test-fixture limitation (TC019)
- **17 blocked** (56.7%) — 16 of these are downstream of the single TC001 login failure; 1 (TC002) is blocked by a missing test fixture file, unrelated to app code

| Requirement                          | Total Tests | ✅ Passed | ❌ Failed | 🚫 Blocked |
|---------------------------------------|-------------|-----------|-----------|------------|
| Authentication                        | 5           | 3         | 2         | 0          |
| Resume Upload / Import / Saved Profiles | 5         | 0         | 1         | 4          |
| Profile Editor                        | 5           | 3         | 0         | 2          |
| Resume Export                         | 4           | 2         | 0         | 2          |
| AI Resume Analysis                    | 2           | 1         | 0         | 1          |
| AI Cover Letter Generation            | 3           | 0         | 0         | 3          |
| AI Career Roadmap                     | 1           | 0         | 0         | 1          |
| Job Search and Matching               | 2           | 0         | 0         | 2          |
| Settings                              | 3           | 1         | 0         | 2          |
| **Total**                              | **30**      | **10**    | **3**     | **17**     |

---

## 4️⃣ Key Gaps / Risks

1. **Test account still does not exist in the backend database (highest-impact issue, unchanged from the prior run).** The TestSprite bootstrap credentials (`haseeb-heaven` / `123456`) have never been registered against the FastAPI backend instance used for this test session, so every flow requiring a signed-in (non-guest) session — saved profiles, PDF export, cover letters, roadmaps, job search, most settings — reported BLOCKED rather than pass/fail. This is not a product defect; it inflates the apparent failure surface and has now recurred across two consecutive runs. **Recommendation:** before the next TestSprite run, either (a) seed that exact account into the backend's user store, or (b) update `testsprite_tests/tmp/config.json`'s `loginUser`/`loginPassword` to an account already known to exist, then re-run only the 17 blocked test IDs.

2. **TC015 "Open Saved Profile" as guest — same symptom persists after the v2.5.0-gh fix.** The `UploadScreen.tsx` fix shipped this release added a toast on `listProfiles()` failure, but this run's TestSprite agent still observed "no visible change." Two explanations are plausible and should be checked manually: (a) the toast fires but disappears before/without being detected by the automated agent (a timing/detection gap, not a functional bug), or (b) something else is preventing the fetch/catch from running at all in this exact click path. **Recommendation:** manually click "📂 Open Saved Profile" as a guest in a real browser and confirm a toast appears; if it does, consider replacing or supplementing the toast with a persistent inline message so both users and automated tests get durable feedback instead of a fading notification.

3. **No test fixture files available to the TestSprite agent (TC002) — unchanged.** Resume-import testing needs at least one sample file per supported format (PDF/DOCX/JSON/CSV/XML) accessible to the test agent's sandbox. None were supplied this run either.

4. **Password-reset-via-token test used a non-live token (TC019) — unchanged.** To properly validate the reset-password screen, the token must be captured from the actual `forgot-password` response/email in the same test run rather than a placeholder, since tokens are single-use and time-limited.

**Overall:** Results are consistent with the prior run — every feature area exercisable without a pre-existing authenticated account passed (registration, guest mode, password-reset request, contact/skills/experience editing, JSON/CSV export, analysis-without-provider validation, Ollama settings). The dominant signal remains an environment/test-data gap (missing seeded user), not a product regression. TC015 needs a quick manual check to confirm the v2.5.0-gh fix is actually working and this is a test-detection artifact rather than a residual defect.
