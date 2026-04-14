# Maakav - Deployment Guide

## Step 1: Railway (Backend + PostgreSQL)

### 1.1 Create Railway Project
1. Go to https://railway.app/new
2. Click "Deploy from GitHub repo"
3. Select `luvchikavi/maakav`
4. Railway will detect the Dockerfile in `backend/`

### 1.2 Set Root Directory
- In the service settings, set **Root Directory** to `backend`

### 1.3 Add PostgreSQL
1. Click "+ New" → "Database" → "PostgreSQL"
2. Railway auto-creates `DATABASE_URL` variable

### 1.4 Set Environment Variables
In the backend service, add these variables:

```
DATABASE_URL        → (auto from PostgreSQL, change prefix to postgresql+asyncpg://)
SECRET_KEY          → (generate: python -c "import secrets; print(secrets.token_urlsafe(32))")
FRONTEND_URL        → https://maakav.vercel.app (or your custom domain)
ANTHROPIC_API_KEY   → (your Claude API key for bank statement parsing)
DEBUG               → false
ENVIRONMENT         → production
```

**IMPORTANT:** Railway's DATABASE_URL uses `postgresql://`. You need to change it to `postgresql+asyncpg://` for async driver. Add a variable:
```
DATABASE_URL = ${RAILWAY_DATABASE_URL} but replace postgresql:// with postgresql+asyncpg://
```

Or add a start command that does the replacement:
```
web: python -c "import os; url=os.environ['DATABASE_URL'].replace('postgresql://', 'postgresql+asyncpg://'); os.environ['DATABASE_URL']=url" && uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8000}
```

### 1.5 Create Initial Data
After deployment, run in Railway CLI:
```bash
railway run python seed.py
```

### 1.6 Verify
- Health check: `https://your-railway-url.up.railway.app/health`
- API docs: `https://your-railway-url.up.railway.app/docs`

---

## Step 2: Vercel (Frontend)

### 2.1 Import Project
1. Go to https://vercel.com/new
2. Import `luvchikavi/maakav`
3. Set **Root Directory** to `frontend`
4. Framework: Next.js (auto-detected)

### 2.2 Set Environment Variables
```
NEXT_PUBLIC_API_URL → https://your-railway-url.up.railway.app
```

### 2.3 Deploy
Click "Deploy" - Vercel will build and deploy automatically.

### 2.4 Custom Domain (Optional)
1. Go to project settings → Domains
2. Add your domain (e.g., `maakav.co.il`)
3. Update DNS records as instructed

---

## Step 3: Connect Backend CORS

After both are deployed, update Railway backend:
```
FRONTEND_URL → https://your-vercel-url.vercel.app
```

---

## Step 4: Verify End-to-End

1. Open frontend URL
2. Login with `admin@maakav.co.il` / `admin123`
3. Create a project
4. Upload a bank statement PDF
5. Go through the 7-step wizard
6. Generate a Word report

---

## Auto-Deploy

Both Railway and Vercel auto-deploy on push to `main`:
- Push code → GitHub → Railway rebuilds backend
- Push code → GitHub → Vercel rebuilds frontend

CI/CD is configured in `.github/workflows/ci.yml`:
- Backend: ruff + black lint check
- Frontend: tsc + next build

---

## Quick Reference

| Service | URL | Config |
|---------|-----|--------|
| GitHub | https://github.com/luvchikavi/maakav | Source code |
| Railway | https://railway.app | Backend + PostgreSQL |
| Vercel | https://vercel.com | Frontend |
| Local Backend | http://localhost:8700 | `uvicorn app.main:app --port 8700` |
| Local Frontend | http://localhost:4700 | `NEXT_PUBLIC_API_URL=http://localhost:8700 npx next dev -p 4700` |
| Login | admin@maakav.co.il / admin123 | Default admin |
