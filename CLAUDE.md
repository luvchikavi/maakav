# CLAUDE.md - Maakav (מעקב)

## What Is This
Construction project tracking system for Israeli real estate appraisal firms. Replaces Excel-based workflow for producing monthly bank monitoring reports (דוחות מעקב).

## Repository Structure
```
Maakav/
├── backend/          # FastAPI + SQLAlchemy async + PostgreSQL
│   ├── app/
│   │   ├── api/v1/   # Route handlers
│   │   ├── models/   # SQLAlchemy models
│   │   ├── schemas/  # Pydantic schemas
│   │   ├── services/ # Business logic
│   │   ├── core/     # Auth, security, constants
│   │   └── migrations/ # Alembic
│   ├── requirements.txt
│   └── alembic.ini
└── frontend/         # Next.js 15 + TypeScript + Tailwind
```

## Common Commands

### Backend (`backend/`)
```bash
# Setup
python -m venv venv && source venv/bin/activate
pip install -r requirements.txt

# Run dev server
uvicorn app.main:app --reload --port 8000

# Migrations
alembic revision --autogenerate -m "description"
alembic upgrade head

# Lint
ruff check . && black --check .

# Test
pytest
```

### Frontend (`frontend/`)
```bash
npm install
npm run dev        # Dev server
npm run build      # Production build
npm run lint       # ESLint
```

## Architecture
- **Auth**: JWT (access 15min + refresh 7d) via python-jose
- **DB**: PostgreSQL with async SQLAlchemy (asyncpg driver)
- **Multi-tenant**: All queries filter by `firm_id` from JWT token
- **AI**: Claude Vision (Sonnet) for bank statement PDF parsing
- **Reports**: python-docx → LibreOffice headless → PDF
- **Deploy**: Railway (backend+DB) + Vercel (frontend)

## Key Conventions
- Hebrew RTL UI throughout
- All monetary values stored as Decimal(15,2)
- Budget tracking uses 15-column index-adjusted calculation (see BudgetTrackingLine.calculate_all)
- Monthly reports are the central entity - all monthly data links to monthly_report_id
