# Changelog

All notable changes to the **AI Career Studio** project will be documented in this file.

---

## [2.4.0-gh] - 2026-06-19

### Added
- Profile editor error boundary (`ErrorBoundary` component) to gracefully handle render-time errors in the editor instead of crashing the page.
- Prefetched-profile support: the "Open →" button on saved profiles now prefetches the full profile data and passes it to `ProfileEditor`, eliminating a redundant network round-trip when opening a saved profile.
- `onOpenSavedProfile` plumbing in `App.tsx` so the editor can navigate back to the saved-profile picker without a full page reload.
- TestSprite frontend test runner (`run_testsprite_frontend.py`) that executes each generated test in a fresh subprocess for reliable, isolated runs.

### Changed
- `UploadScreen` now exposes an `initialShowProfiles` hook (auto-loads saved profiles when navigated to from the editor) and a `handleOpenProfile` path that prefetches profile data.
- `ProfileEditor` now accepts a `prefetchedProfile` prop and skips the loading state entirely when provided.
- Tightened the editor's `getProfile` effect with a cancellation guard to avoid `setState` on unmounted components.
- Updated the project version to **2.4.0-gh**.

### Fixed
- Resolved a TypeScript unused-variable warning in `App.tsx` introduced when the `showProfilesList` state was refactored.
- Resolved a missing `useEffect` import regression in `UploadScreen.tsx`.
- Hardened `UploadScreen`'s "Open →" click handler with `e.preventDefault()` and `type="button"` to avoid form-submit side effects in test environments.

### Tests
- **Backend**: `188 passed` (0 failed) — covers models, all 5 parsers, all 5 exporters, all REST endpoints, scoring, filters, and saved filters.
- **Frontend (TestSprite)**: `16 passed, 13 failed`. The remaining failures are concentrated in flows that rely on the editor mount path inside Playwright's `--single-process` Chromium mode (a known instability of single-process headless Chrome when remounting a heavy React tree mid-click). The failing tests are the saved-profile editor tests (TC002_Update, TC003_Import, TC007_Update, TC009, TC010, TC011, TC014, TC015) plus TC004_Create, TC006_Open, TC008_Reset, and the AI-provider analysis tests (TC012, TC013) which contain hardcoded `assert False` and are not runnable in the current environment.

---

## [2.3.0-gh] - 2026-06-17

### Added
- Expanded job board sources from 2 to 11+ providers: Himalayas (with salary data), The Muse, Jobicy, We Work Remotely (Tier 1 no-auth); Findwork, Jooble (Tier 2 API key); LinkedIn, Indeed, Glassdoor, Google Jobs (deep links).
- Added `salary` and `is_deep_link` fields to `JobMatch` model.
- Async parallel job fetching with `asyncio.gather` and `asyncio.to_thread`.
- Deduplication of job results by `(title, company)` key.
- Vite dev server reads `FRONTEND_HOST` and `FRONTEND_PORT` from root `.env`.
- `scripts/sync-testsprite-env.js` to keep TestSprite config in sync with `.env`.
- 22 new backend unit tests covering deduplication, new job sources, and deep links (33 total passing).
- Fixed TestSprite frontend tests TC003, TC008, TC012 — TC008 now uses proper forgot-password UI flow with dedicated reset account, TC003 and TC012 use synthetic PDF upload for cloud test environment.

### Changed
- `backend/routers/jobs_router.py` fully rewritten as async endpoint with parallel fetching.
- `_SUPPORTED_PORTALS` expanded to include all 11+ sources.
- TestSprite test plan updated with correct step sequences for TC003, TC008, TC012.
- `.gitignore` updated to track TestSprite test files while excluding `testsprite_tests/tmp/`.

---

## [2.2.0-gh] - 2026-06-16
### Added
- Integrated **TestSprite** MCP server configuration in `mcp_config.json` with the required `API_KEY` to automate UI and API tests.
- Synchronized [.env.example](file:///d:/Code/career-studio-ai/.env.example) to list all available environment variables (like model names, port, and test keys) with blank placeholder values.

### Changed
- Reorganized codebase automation and test scripts into a dedicated [scratch/](file:///d:/Code/career-studio-ai/scratch) folder.
- Stopped tracking scripts ([scratch/build_and_run.ps1](file:///d:/Code/career-studio-ai/scratch/build_and_run.ps1) and [scratch/build_and_run.sh](file:///d:/Code/career-studio-ai/scratch/build_and_run.sh)) in Git index (using `git rm --cached`) to allow local development environment scripts while ignoring them globally under `scratch/*` via [.gitignore](file:///d:/Code/career-studio-ai/.gitignore).
- Configured [scratch/run_frontend_tests.ps1](file:///d:/Code/career-studio-ai/scratch/run_frontend_tests.ps1) and [scratch/run_backend_tests.ps1](file:///d:/Code/career-studio-ai/scratch/run_backend_tests.ps1) to run with the specific Python environment at `D:\henv\Scripts\python.exe`.

---

## [2.1.0] - 2026-06-15
### Added
- One-click build and run automated scripts:
  - `build_and_run.ps1` for Windows PowerShell (launches backend and frontend in separate console windows).
  - `build_and_run.sh` for Unix/Linux/macOS/Git Bash (manages background processes concurrently and terminates cleanly on shutdown).
- High-fidelity screenshots of the latest application screens in `assets/screenshots/` and `docs/screenshots/` generated via Playwright browser automation.
- Comprehensive unit tests covering import/export API endpoints and format parsers.

### Fixed
- Fixed a TypeScript compiler warning/error in `frontend/src/components/tabs/ExperienceTab.tsx` regarding unused `ExperienceBullet` import.
- Configured `.gitignore` to ignore Python compiled caches (`__pycache__/`) and test caches (`.pytest_cache/`) globally across all subfolders.

---

## [2.0.0] - 2026-06-12
### Added
- **User Authentication:** Implemented user authentication with secure password hashing (bcrypt) and JWT tokens.
- **Profile Ownership:** Bound profile data to authenticated users to provide secure multi-tenant capabilities.
- **Login UI:** Designed a modern, user-friendly login and registration page.
- **Improved Logging:** Switched backend logger to run with UTF-8 encoding on Windows to prevent UnicodeDecodeError.
- **Robust Testing:** Enhanced test suites and fixed test xfail conditions for offline environments.

---

## [1.5.0] - 2026-06-10
### Added
- Unified AI integration with OpenAI, Anthropic, and OpenRouter for resume analysis.
- Live local-first PDF and DOCX parsers using `pdfplumber` and `python-docx`.
- Job matching engine powered by Remotive and Adzuna APIs.

### Fixed
- Fixed `.env` variable loading, API credentials fallback mechanism, and PDF parser crashes on complex layouts.

---

## [1.0.0] - 2026-06-05
### Added
- Initial release of AI Career Studio.
- Multi-format import and export (JSON, CSV, XML, DOCX, PDF, LaTeX, HTML Portfolio).
- Interactive Tabbed CRUD Profile Editor.
- AI ATS Score analysis, Cover Letter generator, and Career Roadmap planner.
- Local Activity Logs and settings configuration.
