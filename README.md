# AI Career Studio 🚀

<div align="center">

<img src="docs/logo.jpg" alt="AI Career Studio Logo" width="160" style="border-radius: 24px; margin-bottom: 15px; box-shadow: 0 4px 25px rgba(0,0,0,0.4);" />

### **A local-first, AI-ready career management platform.**
*Upload any resume format → parse it into a structured profile → edit everything locally → export to 7 formats.*

[![Python](https://img.shields.io/badge/Python-3.11+-3776ab?logo=python&logoColor=white)](https://python.org)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.115-009688?logo=fastapi&logoColor=white)](https://fastapi.tiangolo.com)
[![React](https://img.shields.io/badge/React-18-61dafb?logo=react&logoColor=white)](https://react.dev)
[![TypeScript](https://img.shields.io/badge/TypeScript-5-3178c6?logo=typescript&logoColor=white)](https://typescriptlang.org)
[![Tailwind CSS](https://img.shields.io/badge/Tailwind-3-06b6d4?logo=tailwindcss&logoColor=white)](https://tailwindcss.com)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

</div>

---


## ✨ What it does

Career Studio is a **full-stack desktop web app** that turns any resume file into a fully editable, exportable, AI-powered career profile — no cloud, no subscriptions, no data leaving your machine.

| Step | What happens |
|------|-------------|
| **Upload** | Drag & drop a `.json`, `.csv`, `.xml`, `.docx`, or `.pdf` resume |
| **Parse** | Backend extracts name, contact, skills, experience, projects, education, certifications |
| **Edit** | Tabbed CRUD editor — change anything in the browser |
| **AI Analysis** | Score your resume (0-100), get ATS keyword gaps, strengths & actionable suggestions |
| **Cover Letter** | AI-generated, personalized cover letters by job title + company — saved with history |
| **Roadmap** | Career roadmap, growth plan, or portfolio strategy for 1–10 year horizon |
| **Jobs** | Live job matching from Remotive + Adzuna, scored by skill keyword overlap |
| **Export** | One-click download in 7 formats: JSON, CSV, XML, DOCX, PDF, LaTeX, HTML Portfolio |
| **Logs** | Every action (import, export, analyze, etc.) logged with timestamps |
| **Settings** | Configure AI provider (OpenAI / Anthropic / OpenRouter), model, and API key |

---

## 📸 Screenshots

### Upload Screen
![Upload Screen](docs/screenshots/01-upload-screen.png)

### Profile Editor
![Profile Editor — Contact Tab](docs/screenshots/02-profile-editor.png)

### Export Panel
![Export Panel](docs/screenshots/03-export-panel.png)

---

## 🏗️ Architecture

```
career-studio/
├── backend/                  # FastAPI + SQLite
│   ├── models.py             # SQLModel ORM — 13 tables
│   ├── db.py                 # SQLite engine + session
│   ├── logger.py             # Python logging to stdout + file
│   ├── main.py               # FastAPI app with CORS
│   ├── parsers/              # Plugin registry — JSON, CSV, XML, DOCX, PDF
│   ├── exporters/            # Plugin registry — JSON, CSV, XML, DOCX, PDF, LaTeX, HTML
│   ├── services/
│   │   ├── activity.py       # Activity log writer
│   │   └── ai_service.py     # Unified OpenAI / Anthropic / OpenRouter interface
│   ├── routers/
│   │   ├── import_router.py  # POST /api/import
│   │   ├── profile_router.py # GET/PATCH/DELETE /api/profiles/{id}
│   │   ├── export_router.py  # GET /api/profiles/{id}/export/{fmt}
│   │   ├── analysis_router.py# POST /analyze /cover-letter /roadmap; GET /score
│   │   ├── jobs_router.py    # GET /api/profiles/{id}/jobs
│   │   ├── logs_router.py    # GET/DELETE /api/logs
│   │   └── settings_router.py# GET/PUT /api/settings
│   └── tests/                # 35 pytest tests (TDD throughout)
└── frontend/                 # React 18 + Vite + Tailwind CSS
    └── src/
        ├── api.ts            # Axios API client (all endpoints)
        ├── types.ts          # TypeScript interfaces
        ├── components/
        │   ├── UploadScreen.tsx
        │   ├── ProfileEditor.tsx  # 14-tab grouped navigation
        │   ├── ExportPanel.tsx    # 7 formats incl. LaTeX + Portfolio
        │   └── tabs/         # Contact, Summary, Skills, Experience, Projects,
        │                     #   Education, Certifications, Analysis, CoverLetter,
        │                     #   Roadmap, Jobs, Logs, Settings, Export
        └── App.tsx
```

---

## 🚀 Quick Start

### Prerequisites

- Python 3.11+
- Node.js 18+

### 1. Clone

```bash
git clone https://github.com/haseeb-heaven/career-studio.git
cd career-studio
```

### 2. Backend

```bash
cd backend

# Create virtual environment
python -m venv .venv

# Activate (Windows)
.venv\Scripts\activate
# Activate (macOS/Linux)
source .venv/bin/activate

# Install dependencies
pip install fastapi uvicorn sqlmodel pdfplumber python-docx reportlab

# Run
uvicorn main:app --reload --port 8000
```

Backend available at **http://localhost:8000**  
Interactive API docs at **http://localhost:8000/docs**

### 3. Frontend

```bash
cd frontend

npm install
npm run dev
```

Frontend available at **http://localhost:5173**

---

## 🧪 Tests

```bash
cd backend
.venv/Scripts/python -m pytest -v
```

```
35 passed in 1.85s
```

Tests cover: models, all 5 parsers, all 5 exporters, all API endpoints (import, CRUD, export).

---

## 📂 Supported Formats

| Format | Parse (import) | Export (download) |
|--------|:--------------:|:-----------------:|
| JSON   | ✅ Full fidelity | ✅ |
| CSV    | ✅ Full fidelity | ✅ |
| XML    | ✅ Full fidelity | ✅ |
| DOCX   | ✅ Best-effort  | ✅ Styled (blue/teal) |
| PDF    | ✅ Best-effort  | ✅ Styled (blue/teal) |
| LaTeX  | —               | ✅ Full `article` document |
| HTML   | —               | ✅ Styled portfolio page |

> **Best-effort** means the parser extracts what it can from design-heavy layouts. Always review the parsed profile and correct anything missed. JSON/CSV/XML imports are lossless.

---

## 🔌 API Reference

### Import

```http
POST /api/import
Content-Type: multipart/form-data

file: <binary>
```

```json
{ "profile_id": 1, "warnings": [] }
```

### Profile CRUD

```http
GET    /api/profiles              # List all profiles
GET    /api/profiles/{id}         # Full profile with all relations
PATCH  /api/profiles/{id}         # Update contact/summary/meta fields
DELETE /api/profiles/{id}         # Delete (cascades to all children)
```

### Export

```http
GET /api/profiles/{id}/export/{fmt}
# fmt ∈ { json | csv | xml | docx | pdf | latex | tex | html | portfolio }
# Returns file download with correct Content-Disposition header
```

### AI Analysis

```http
POST /api/profiles/{id}/analyze          # Returns score, strengths, weaknesses, suggestions, ats_keywords
GET  /api/profiles/{id}/score            # Same as analyze (GET shortcut)
POST /api/profiles/{id}/cover-letter     # body: { job_title, company, extra_notes }
GET  /api/profiles/{id}/cover-letters    # List saved cover letters
DELETE /api/profiles/{id}/cover-letters/{cl_id}
POST /api/profiles/{id}/roadmap          # body: { plan_type, target_role, years_horizon }
GET  /api/profiles/{id}/roadmaps         # List saved roadmaps
DELETE /api/profiles/{id}/roadmaps/{plan_id}
```

### Jobs

```http
GET /api/profiles/{id}/jobs?limit=20     # Live search Remotive + Adzuna, returns scored JobMatch list
```

### Logs & Settings

```http
GET    /api/logs?limit=100   # Activity log entries
DELETE /api/logs             # Clear all logs
GET    /api/settings         # Current AI provider config (keys masked)
PUT    /api/settings         # Update provider, model, api_key
```

---

## 🗂️ Data Model

```
Profile
  ├── ContactLink[]      label, url
  ├── Skill[]            name, category, years
  ├── Experience[]
  │     └── ExperienceBullet[]   text
  ├── Project[]          name, description, link, tech (JSON array)
  ├── Education[]        institution, degree, field, start, end
  ├── Certification[]    name, issuer, date
  ├── CoverLetter[]      job_title, company, content
  └── CareerPlan[]       plan_type, content

Settings              ai_provider, ai_model, api_key (per-provider)
ActivityLog           action, detail, profile_id, created_at
JobMatch              title, company, location, url, description, source, match_score
```

All profile-linked tables use cascade-delete so removing a profile cleans up every child record.

---

## 🛠️ Tech Stack

### Backend
| Library | Purpose |
|---------|---------|
| FastAPI | REST API framework |
| SQLModel | ORM (built on SQLAlchemy 2 + Pydantic) |
| SQLite | Local database (zero-config) |
| pdfplumber | PDF text extraction |
| python-docx | DOCX read/write |
| ReportLab | Styled PDF generation |

### Frontend
| Library | Purpose |
|---------|---------|
| React 18 | UI framework |
| TypeScript | Type safety |
| Vite | Build tool |
| Tailwind CSS 3 | Utility-first styling |
| Axios | HTTP client |

---

## 🌿 Branches

| Branch | Purpose |
|--------|---------|
| `main` | Stable releases |
| `develop` | Active development |

---

## 💡 Dev Note

> This project was **entirely built by [Claude Code](https://claude.ai/code)** — Anthropic's agentic coding CLI — using a test-driven, subagent-driven development workflow. Every file, test, fix, and architectural decision was driven through Claude Code with zero manual code written.
>
> Special love and gratitude to the teams behind **Claude Fable** and **Claude Mythos** — the models pushing the frontier of what AI-assisted engineering can be. This project is a testament to what's possible when great models meet great tooling.
>
> Built with ❤️ using Claude Code · Slice 2 complete — full AI-powered career platform.

---

## 🛠️ Tech Stack (added in Slice 2)

### Backend additions
| Library | Purpose |
|---------|---------|
| openai | OpenAI + OpenRouter API client |
| anthropic | Anthropic Claude API client |

### New API endpoints
15 REST endpoints total across import, profiles, export, analysis, jobs, logs, settings.

---

## 📋 Roadmap (Slice 3+)

- [x] ~~AI analysis — score resume, suggest improvements (OpenAI / Anthropic / OpenRouter)~~ ✅ Done
- [x] ~~Cover letter generator~~ ✅ Done
- [x] ~~Career roadmap & growth plan generator~~ ✅ Done
- [x] ~~Live job matching (Remotive + Adzuna)~~ ✅ Done
- [x] ~~LaTeX export~~ ✅ Done
- [x] ~~Portfolio HTML page generator~~ ✅ Done
- [x] ~~Activity logs~~ ✅ Done
- [ ] Multi-profile management UI (switch between profiles)
- [ ] LinkedIn / Indeed job matching (OAuth)
- [ ] AI interview prep (mock Q&A)
- [ ] Salary benchmarking

---

## 📝 Changelog

See the [Changelogs.md](Changelogs.md) file for the complete history of changes and updates.

---

## 📄 License

MIT © [Haseeb Mir](https://github.com/haseeb-heaven)

---

<div align="center">
  <sub>Made with ❤️ by <a href="https://github.com/haseeb-heaven">Haseeb Mir</a> · Built with <a href="https://claude.ai/code">Claude Code</a></sub>
</div>
