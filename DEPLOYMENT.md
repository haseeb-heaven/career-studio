# 🚀 Deployment Guide — Career Studio AI

This guide covers one-click and manual deployment for all supported platforms.

> **Branch Strategy:** All deployment work should happen on `deploy/cloud` branch.
> ```bash
> git checkout -b deploy/cloud
> # Make any config changes here
> # Test → then merge to main
> ```

---

## ⚡ One-Click Deploy

| Platform | Type | Database | Click to Deploy |
|---|---|---|---|
| **Railway** ⭐ Recommended | Full-stack (Frontend + Backend) | SQLite persists ✅ | [![Deploy on Railway](https://railway.com/button.svg)](https://railway.com/template/deploy?repo=https://github.com/haseeb-heaven/career-studio-ai) |
| **Render** | Full-stack (Frontend + Backend) | SQLite persists ✅ | [![Deploy to Render](https://render.com/images/deploy-to-render-button.svg)](https://render.com/deploy?repo=https://github.com/haseeb-heaven/career-studio-ai) |
| **Vercel** | Frontend only | N/A | [![Deploy with Vercel](https://vercel.com/button)](https://vercel.com/new/clone?repository-url=https://github.com/haseeb-heaven/career-studio-ai) |

> ⚠️ **Vercel deploys frontend only.** Pair with Railway or Render for the backend.

---

## 📋 Required Environment Variables

Set these on whichever platform you deploy to:

### Backend
| Variable | Example | Required |
|---|---|---|
| `CORS_ORIGINS` | `https://your-frontend.vercel.app` | ✅ Yes |
| `DATABASE_URL` | `sqlite:////data/career_studio.db` | Optional (has default) |
| `SECRET_KEY` | `your-random-secret-key-32-chars` | ✅ Yes |

### Frontend
| Variable | Example | Required |
|---|---|---|
| `VITE_API_URL` | `https://your-backend.up.railway.app` | ✅ Yes |

---

## 🚂 Option 1 — Railway (Recommended)

**Best choice.** Docker-native, SQLite persists, free tier available. Zero code changes.

[![Deploy on Railway](https://railway.com/button.svg)](https://railway.com/template/deploy?repo=https://github.com/haseeb-heaven/career-studio-ai)

**Step-by-step:**

1. Click the Railway button above
2. Connect your GitHub account and select this repo
3. Railway auto-detects Docker — backend deploys immediately
4. In Railway dashboard → Variables tab, set:
   ```
   CORS_ORIGINS = https://your-frontend.vercel.app
   SECRET_KEY   = your-random-32-char-secret
   DATABASE_URL = sqlite:////data/career_studio.db
   ```
5. Add a Volume mount: `/data` (keeps SQLite data across deploys)
6. Deploy frontend separately on Vercel:
   - Connect same repo → Vercel auto-reads `vercel.json`
   - Set env var: `VITE_API_URL = https://your-app.up.railway.app`
7. Update `CORS_ORIGINS` on Railway with your actual Vercel URL
8. ✅ Done — visit your Vercel URL

**Cost:** Free tier available · $5/mo for always-on

---

## 🟦 Option 2 — Render

**Good alternative.** Full-stack on one platform, persistent disk for SQLite.

[![Deploy to Render](https://render.com/images/deploy-to-render-button.svg)](https://render.com/deploy?repo=https://github.com/haseeb-heaven/career-studio-ai)

**Step-by-step:**

1. Click the Render button above
2. Render auto-reads `render.yaml` — creates backend + frontend services automatically
3. In Render dashboard, set environment variables:
   ```
   Backend  → CORS_ORIGINS = https://career-studio-frontend.onrender.com
   Backend  → SECRET_KEY   = your-random-32-char-secret
   Frontend → VITE_API_URL = https://career-studio-backend.onrender.com
   ```
4. Render auto-provisions a 1GB disk for `/data` (SQLite persists) 
5. ✅ Done — visit your Render frontend URL

**Cost:** Free tier (spins down after 15min idle) · $7/mo for always-on

---

## 🪂 Option 3 — Fly.io

**Best performance for India.** Singapore region (`sin`) is closest, persistent volumes.

**Step-by-step:**

```bash
# 1. Install flyctl
curl -L https://fly.io/install.sh | sh
fly auth login

# 2. Launch app (generates fly.toml)
cd backend
fly launch --no-deploy --name career-studio-backend

# 3. Create persistent volume for SQLite
fly volumes create sqlite_data --size 1 --region sin

# 4. Set secrets
fly secrets set \
  CORS_ORIGINS=https://your-frontend.vercel.app \
  SECRET_KEY=your-random-32-char-secret \
  DATABASE_URL=sqlite:////data/career_studio.db

# 5. Deploy
fly deploy

# 6. Deploy frontend on Vercel
# Set VITE_API_URL=https://career-studio-backend.fly.dev
```

**Cost:** Free tier (3 shared VMs) · $1.94/mo for dedicated

---

## 🐳 Option 4 — Docker / Self-Hosted VPS

**Full control.** Works on any Linux VPS (DigitalOcean, Hetzner, Linode).

```bash
# 1. Clone repo on your VPS
git clone https://github.com/haseeb-heaven/career-studio-ai
cd career-studio-ai

# 2. Set environment variables
export CORS_ORIGINS=https://yourdomain.com
export SECRET_KEY=your-random-32-char-secret

# 3. Build frontend
cd frontend && npm install && npm run build && cd ..

# 4. Start everything
docker-compose up -d

# 5. App running at http://your-vps-ip
```

**Cost:** VPS cost only (~$5/mo on Hetzner)

---

## ❌ Not Recommended

| Platform | Why Not | Alternative |
|---|---|---|
| **Heroku** | SQLite wipes on every deploy | Use Railway instead |
| **Vercel (full-stack)** | Serverless — FastAPI + SQLite both broken | Vercel frontend + Railway backend |
| **Netlify (full-stack)** | Same as Vercel | Same as above |

---

## 🗄️ Database Notes

Current stack uses **SQLite** — perfect for personal use and small deployments.

- Railway, Render, Fly.io all support persistent SQLite via volume mounts ✅
- **No database changes needed** for any recommended platform
- **Future scaling (500+ users):** Migrate to PostgreSQL with one line in `backend/db.py`:

```python
# Only this line changes — all models, routers, queries stay the same
DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://user:pass@host/dbname")
```

Free PostgreSQL when ready: [Supabase](https://supabase.com) · [Neon](https://neon.tech) · Railway Postgres plugin

---

## ✅ Post-Deployment Checklist

- [ ] Backend health: `GET https://your-backend/docs` returns Swagger UI
- [ ] Frontend loads without CORS errors (check browser console → Network tab)
- [ ] Resume upload + parse works end-to-end
- [ ] AI analysis works (requires API key configured in Settings tab)
- [ ] Export downloads work (PDF, DOCX, JSON)
- [ ] Data persists after redeploy (upload resume → redeploy → resume still there)

---

## 🆘 Troubleshooting

| Symptom | Cause | Fix |
|---|---|---|
| CORS error in browser console | `CORS_ORIGINS` wrong/missing | Set `CORS_ORIGINS=https://exact-frontend-url` on backend |
| Frontend blank / API 404 errors | `VITE_API_URL` missing | Set `VITE_API_URL=https://your-backend-url` on frontend |
| SQLite data lost after redeploy | No volume/disk mounted | Mount `/data` volume on Railway · disk on Render |
| 500 error on AI analysis | API key missing | Add OpenAI/Anthropic key in app Settings tab |
| Backend 502 / not starting | Port mismatch | Ensure `uvicorn` binds to `0.0.0.0:$PORT` |
