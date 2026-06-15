# Changelog

All notable changes to the **AI Career Studio** project will be documented in this file.

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
