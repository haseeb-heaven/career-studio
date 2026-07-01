<div align="center">

<img src="docs/logo.jpg" alt="Career Studio AI" width="140" style="border-radius: 20px; box-shadow: 0 8px 32px rgba(0,0,0,0.3);" />

# Career Studio AI

**A local-first, AI-powered career management platform.**  
Upload any resume → parse → edit → analyze with AI → export in 7 formats → match live jobs.

<br/>

[![Python](https://img.shields.io/badge/Python-3.11+-3776ab?logo=python&logoColor=white&style=flat-square)](https://python.org)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.115-009688?logo=fastapi&logoColor=white&style=flat-square)](https://fastapi.tiangolo.com)
[![React](https://img.shields.io/badge/React-18-61dafb?logo=react&logoColor=white&style=flat-square)](https://react.dev)
[![TypeScript](https://img.shields.io/badge/TypeScript-5-3178c6?logo=typescript&logoColor=white&style=flat-square)](https://typescriptlang.org)
[![Tailwind CSS](https://img.shields.io/badge/Tailwind-3-06b6d4?logo=tailwindcss&logoColor=white&style=flat-square)](https://tailwindcss.com)
[![SQLite](https://img.shields.io/badge/SQLite-local--first-003b57?logo=sqlite&logoColor=white&style=flat-square)](https://sqlite.org)
[![Tests](https://img.shields.io/badge/tests-292%20backend%20%C2%B7%2010%2F30%20frontend-brightgreen?style=flat-square&logo=pytest&logoColor=white)](backend/tests/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow?style=flat-square)](LICENSE)

<br/>

**[⚡ Quick Start](#-quick-start-local) · [☁️ Deploy](#️-deploy) · [📖 API Docs](#-api-reference) · [🗺️ Roadmap](#️-roadmap)**

</div>

---

## 🚀 Latest Release: v2.5.0-gh

**What's new in v2.5.0-gh:**
- 🧠 **Advanced job-match engine** — synonym normalization, TF-IDF cosine similarity, and RapidFuzz fuzzy matching power richer per-skill match details, gap analysis, and hire-chance scoring
- 🔍 **Resume keywords endpoint** — extracts weighted keywords from a profile for matching and future search
- 🤖 **Deep Semantic Matching (local AI)** — optional `sentence-transformers`-powered embedding score alongside the lexical breakdown
- 🐛 **Fixed silent guest "Open Saved Profile" failure** — guests now see a clear toast explaining saved profiles require sign-in, instead of the button doing nothing
- 🧪 **292 backend tests passing** (was 188) — full coverage of the new matching engine and endpoints

See [Changelogs.md](Changelogs.md) for the full v2.5.0-gh entry.

---

## ✨ What It Does

Career Studio AI is a **full-stack web application** that turns any resume file into a fully editable, AI-powered career profile — with zero cloud dependency, zero subscriptions, and zero data leaving your machine.

| Step | What Happens |
|---|---|
| **📤 Upload** | Drag & drop `.json`, `.csv`, `.xml`, `.docx`, or `.pdf` resume |
| **🔍 Parse** | Extracts name, contact, skills, experience, projects, education, certifications |
| **✏️ Edit** | 14-tab CRUD editor — change everything in the browser |
| **🤖 AI Analysis** | Score resume (0–100), ATS keyword gaps, strengths & actionable suggestions |
| **📝 Cover Letter** | AI-generated cover letters by job title + company — saved with history |
| **🗺️ Roadmap** | Career roadmap and growth plan for 1–10 year horizon |
| **💼 Jobs** | Live job matching from Remotive + Adzuna, scored by skill overlap |
| **📦 Export** | One-click download in 7 formats: JSON, CSV, XML, DOCX, PDF, LaTeX, HTML Portfolio |
| **📋 Logs** | Every action logged with timestamps |
| **⚙️ Settings** | Configure AI provider: OpenAI, Anthropic, or OpenRouter |

---

## 📸 Screenshots

<div align="center">

**Upload Screen**

![Upload Screen](https://raw.githubusercontent.com/haseeb-heaven/career-studio-ai/develop/docs/screenshots/01-upload-screen.png)

<br/>

**Profile Editor — 14-Tab Navigation**

![Profile Editor](https://raw.githubusercontent.com/haseeb-heaven/career-studio-ai/develop/docs/screenshots/02-profile-editor.png)

<br/>

**Export Panel — 7 Formats**

![Export Panel](https://raw.githubusercontent.com/haseeb-heaven/career-studio-ai/develop/docs/screenshots/03-export-panel.png)

</div>

---

## ☁️ Deploy

> 📖 **Full platform-by-platform guide with step-by-step instructions → [DEPLOYMENT.md](DEPLOYMENT.md)**

### One-Click Deploy

> ℹ️ Railway and Render one-click buttons require a published template. Until then, use the direct deploy links below which open the platform's GitHub import flow with this repo pre-filled.

<div align="center">

| Platform | Best For | Click to Deploy |
|---|---|---|
| **Railway** ⭐ Recommended | Full-stack (backend + frontend) | [![Deploy on Railway](https://railway.com/button.svg)](https://railway.com/new?template=https://github.com/haseeb-heaven/career-studio-ai) |
| **Render** | Full-stack (backend + frontend) | [![Deploy to Render](https://render.com/images/deploy-to-render-button.svg)](https://render.com/deploy?repo=https://github.com/haseeb-heaven/career-studio-ai) |
| **Vercel** | Frontend only | [![Deploy with Vercel](https://vercel.com/button)](https://vercel.com/new/clone?repository-url=https://github.com/haseeb-heaven/career-studio-ai) |

</div>

> ⚠️ **Vercel hosts the frontend only.** Deploy the backend separately on Railway or Render.

### Required Environment Variables

Set these in your platform dashboard after deploying:

**Backend**
```bash
CORS_ORIGINS=https://your-frontend-url.vercel.app   # your frontend URL
SECRET_KEY=your-random-32-char-secret               # for JWT/session security
DATABASE_URL=sqlite:////data/career_studio.db       # optional, has default
```

**Frontend**
```bash
VITE_API_URL=https://your-backend.up.railway.app    # your backend URL
```

### Docker (Self-Hosted)

```bash
git clone https://github.com/haseeb-heaven/career-studio-ai.git
cd career-studio-ai

export CORS_ORIGINS=http://localhost
docker-compose up -d

# App running at http://localhost
```

### Settings Ownership Migration

For existing deployments created before per-user settings, run this once from the backend directory before restarting the server:

```bash
python scripts/migrate_settings_ownership.py
```

The script assigns the legacy settings row to the first user, or deletes legacy settings rows when no users exist.

---

## 🚀 Quick Start (Local)

### Prerequisites
- Python 3.11+
- Node.js 18+

### 1. Clone
```bash
git clone https://github.com/haseeb-heaven/career-studio-ai.git
cd career-studio-ai
```

### 2. Backend
```bash
cd backend
python -m venv .venv

# Windows
.venv\Scripts\activate
# macOS/Linux
source .venv/bin/activate

pip install -r requirements.txt
uvicorn main:app --reload --port 8000
```

> API at **http://localhost:8000** · Swagger docs at **http://localhost:8000/docs**

### 3. Frontend
```bash
cd frontend
npm install
npm run dev
```

> App at **http://localhost:5173**

---

## 🧪 Tests

### Backend (292 tests)

```bash
cd backend
python -m pytest -v
```

```
292 passed in 168s
```

Covers: models, all 5 parsers, all 5 exporters, all REST endpoints, scoring, filters, saved filters, the advanced matching engine, and the resume-keywords endpoint.

### Frontend (TestSprite — 10/30 passing)

```bash
# From project root
python run_testsprite_frontend.py
```

```
10 passed, 3 failed, 17 blocked
```

The TestSprite-generated frontend tests cover the full user journey: sign-in, resume upload, profile editing, AI analysis, cover letter generation, job matching, settings, and password reset. 16 of the 17 blocked cases stem from a single missing seeded test account (the account TestSprite logs in with doesn't exist in the target backend's database) rather than app defects; see [`testsprite_tests/testsprite-mcp-test-report.md`](testsprite_tests/testsprite-mcp-test-report.md) for the full breakdown, including one genuine UI bug found and fixed this release (guest "Open Saved Profile" giving no feedback).

---

## 🏗️ Architecture

```
career-studio-ai/
├── backend/                     # FastAPI + SQLite
│   ├── main.py                  # App entry — CORS, routers, startup
│   ├── models.py                # SQLModel ORM — 13 tables
│   ├── db.py                    # SQLite engine — DATABASE_URL from env
│   ├── parsers/                 # Plugin registry: JSON · CSV · XML · DOCX · PDF
│   ├── exporters/               # Plugin registry: JSON · CSV · XML · DOCX · PDF · LaTeX · HTML
│   ├── services/
│   │   ├── ai_service.py        # Unified OpenAI / Anthropic / OpenRouter interface
│   │   └── activity.py          # Activity log writer
│   ├── routers/
│   │   ├── import_router.py     # POST /api/import
│   │   ├── profile_router.py    # GET · PATCH · DELETE /api/profiles/{id}
│   │   ├── export_router.py     # GET /api/profiles/{id}/export/{fmt}
│   │   ├── analysis_router.py   # POST /analyze · /cover-letter · /roadmap
│   │   ├── jobs_router.py       # GET /api/profiles/{id}/jobs
│   │   ├── logs_router.py       # GET · DELETE /api/logs
│   │   └── settings_router.py   # GET · PUT /api/settings
│   └── tests/                   # 188 pytest tests (models, parsers, exporters, scoring, filters)
└── frontend/                    # React 18 + Vite + TypeScript + Tailwind
    └── src/
        ├── api.ts               # Axios client — all endpoints
        ├── types.ts             # TypeScript interfaces
        ├── App.tsx
        └── components/
            ├── UploadScreen.tsx
            ├── ProfileEditor.tsx  # 14-tab navigation
            ├── ExportPanel.tsx
            ├── ErrorBoundary.tsx # Graceful fallback for editor render errors
            └── tabs/            # Contact · Summary · Skills · Experience · Projects
                                 # Education · Certifications · Analysis · CoverLetter
                                 # Roadmap · Jobs · Logs · Settings · Export
```

---

## 📂 Supported Formats

| Format | Import | Export |
|---|:---:|:---:|
| JSON | ✅ Full fidelity | ✅ |
| CSV | ✅ Full fidelity | ✅ |
| XML | ✅ Full fidelity | ✅ |
| DOCX | ✅ Best-effort | ✅ Styled |
| PDF | ✅ Best-effort | ✅ Styled |
| LaTeX | — | ✅ Full `article` |
| HTML Portfolio | — | ✅ Styled page |

> **Best-effort** = parser extracts what it can from design-heavy files. JSON/CSV/XML imports are lossless.

---

## 🔌 API Reference

### Import
```http
POST /api/import
Content-Type: multipart/form-data
file: <binary>
→ { profile_id: 1, warnings: [] }
```

### Profile CRUD
```http
GET    /api/profiles           # List all profiles
GET    /api/profiles/{id}      # Full profile with all relations
PATCH  /api/profiles/{id}      # Update contact / summary / meta
DELETE /api/profiles/{id}      # Cascade-delete profile + all children
```

### Export
```http
GET /api/profiles/{id}/export/{fmt}
# fmt ∈ { json | csv | xml | docx | pdf | latex | html | portfolio }
```

### AI Analysis
```http
POST /api/profiles/{id}/analyze          # score, strengths, weaknesses, ats_keywords
POST /api/profiles/{id}/cover-letter     # body: { job_title, company, extra_notes }
GET  /api/profiles/{id}/cover-letters    # list saved
POST /api/profiles/{id}/roadmap          # body: { plan_type, target_role, years_horizon }
GET  /api/profiles/{id}/roadmaps         # list saved
```

### Jobs
```http
GET /api/profiles/{id}/jobs?limit=20     # Remotive + Adzuna · scored by skill overlap
```

### Settings & Logs
```http
GET    /api/settings    # AI config (keys masked)
PUT    /api/settings    # Update provider / model / api_key
GET    /api/logs        # Activity log
DELETE /api/logs        # Clear all
```

---

## 🗄️ Data Model

```
Profile
  ├── ContactLink[]       label, url
  ├── Skill[]             name, category, years
  ├── Experience[]
  │     └── ExperienceBullet[]   text
  ├── Project[]           name, description, link, tech[]
  ├── Education[]         institution, degree, field, start, end
  ├── Certification[]     name, issuer, date
  ├── CoverLetter[]       job_title, company, content
  └── CareerPlan[]        plan_type, content

Settings      ai_provider · ai_model · api_key (masked on GET)
ActivityLog   action · detail · profile_id · created_at
JobMatch      title · company · location · url · source · match_score
```

---

## 🛠️ Tech Stack

### Backend
| Library | Purpose |
|---|---|
| FastAPI | REST API framework |
| SQLModel | ORM (SQLAlchemy 2 + Pydantic) |
| SQLite | Zero-config local database |
| pdfplumber | PDF text extraction |
| python-docx | DOCX read/write |
| ReportLab | Styled PDF generation |
| openai | OpenAI + OpenRouter client |
| anthropic | Anthropic Claude client |

### Frontend
| Library | Purpose |
|---|---|
| React 18 | UI framework |
| TypeScript 5 | Type safety |
| Vite | Build tool |
| Tailwind CSS 3 | Utility-first styling |
| Axios | HTTP client |

---

## 🌿 Branches

| Branch | Purpose |
|---|---|
| `main` | Stable releases |
| `develop` | Active feature development |
| `deploy/cloud` | Cloud deployment configs (Railway · Render · Fly.io) |

---

## 🗺️ Roadmap

- [x] AI resume analysis — score, ATS keywords, suggestions ✅
- [x] Cover letter generator ✅
- [x] Career roadmap & growth plan ✅
- [x] Live job matching (Remotive + Adzuna) ✅
- [x] LaTeX + HTML portfolio export ✅
- [x] Activity logs ✅
- [ ] Multi-profile management UI
- [ ] AI interview prep — mock Q&A against your resume
- [ ] LinkedIn / Indeed OAuth job matching
- [ ] Salary benchmarking

---

## 📝 Changelog

See [Changelogs.md](Changelogs.md) for complete history.

---

## 📄 License

MIT © [Haseeb Mir](https://github.com/haseeb-heaven)

---

<div align="center">
  <sub>
    Made with ❤️ by <a href="https://github.com/haseeb-heaven">Haseeb Mir</a>
    &nbsp;·&nbsp;
    Built entirely with <a href="https://claude.ai/code">Claude Code</a>
    &nbsp;·&nbsp;
    <a href="DEPLOYMENT.md">🚀 Deploy Guide</a>
  </sub>
</div>
