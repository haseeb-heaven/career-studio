# Deployment Guide — AI Career Studio

## Architecture

- **Frontend** (React/Vite) → static files, host on Vercel / Netlify / Hostinger Static
- **Backend** (FastAPI + SQLite) → server required, host on Hostinger VPS / Railway / Render / Fly.io

## Option A: Vercel (Frontend) + Railway (Backend)

### Backend on Railway
1. Create account at railway.app
2. New Project → Deploy from GitHub → select `career-studio/backend`
3. Set root directory to `backend/`
4. Railway auto-detects Python, add `Procfile`: `web: uvicorn main:app --host 0.0.0.0 --port $PORT`
5. Add env var: `CORS_ORIGINS=https://your-app.vercel.app`
6. Copy the Railway URL (e.g. `https://xyz.railway.app`)

### Frontend on Vercel
1. Import repo on vercel.com
2. Set root directory to `frontend/`
3. Build command: `npm run build`, Output: `dist`
4. Add env var: `VITE_API_BASE_URL=https://xyz.railway.app/api`
5. Deploy

## Option B: Netlify (Frontend) + Render (Backend)

### Backend on Render
1. New Web Service on render.com → connect GitHub
2. Root directory: `backend`, Runtime: Python 3.11
3. Build: `pip install -r requirements.txt`, Start: `uvicorn main:app --host 0.0.0.0 --port $PORT`
4. Add env var: `CORS_ORIGINS=https://your-app.netlify.app`
5. Copy the Render URL

### Frontend on Netlify
1. Import repo on netlify.com — it auto-reads `netlify.toml`
2. Add env var: `VITE_API_BASE_URL=https://xyz.render.com/api`
3. Deploy

## Option C: Hostinger VPS (Full Stack with Docker)

1. Get a VPS plan on hostinger.com (Ubuntu 22.04)
2. SSH in and install Docker + Docker Compose
3. Clone the repo: `git clone <repo-url> career-studio && cd career-studio`
4. Build frontend: `cd frontend && npm install && npm run build && cd ..`
5. Create `.env` from `.env.example`, set `CORS_ORIGINS=https://yourdomain.com`
6. Run: `docker-compose up -d`
7. Point your domain DNS A record to VPS IP
8. Add SSL: install certbot and update `nginx.conf` with SSL config

## Environment Variables

| Variable | Where | Description |
|---|---|---|
| `DATABASE_URL` | Backend | SQLite path or PostgreSQL URL |
| `CORS_ORIGINS` | Backend | Comma-separated allowed frontend origins |
| `VITE_API_BASE_URL` | Frontend build | Full URL to backend API |
