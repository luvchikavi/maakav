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
│   │   ├── services/ # Business logic (incl. transaction_taxonomy, financing_bodies)
│   │   ├── core/     # Auth, security, constants
│   │   └── tests/    # pytest smoke tests
│   ├── start.py      # Entrypoint: idempotent ALTERs + uvicorn
│   ├── pytest.ini
│   ├── Dockerfile
│   └── requirements.txt
├── frontend/         # Next.js 16 + TypeScript + Tailwind
└── .github/workflows/ci.yml   # backend-test + frontend-build + backend-lint
```

## Common Commands

### Backend (`backend/`)
```bash
# Setup
python -m venv venv && source venv/bin/activate
pip install -r requirements.txt

# Run dev server
uvicorn app.main:app --reload --port 8000

# Smoke tests (gated in CI)
pytest app/tests

# Lint (informational, not gating)
ruff check . && black --check .
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
- **AI**: Claude Vision (Sonnet) for bank statement PDF parsing; Claude Haiku for transaction classification
- **Reports**: python-docx → LibreOffice headless → PDF
- **Deploy**: Railway (backend+DB) + Vercel (frontend), both auto-deploy from `main`

## Schema migrations — no Alembic in production
Despite `alembic.ini` being checked in, **production does not run alembic**. New columns are added via idempotent `ALTER TABLE ... ADD COLUMN IF NOT EXISTS` statements in `backend/start.py`'s `init_db()`. To add a new column:
1. Declare it on the SQLAlchemy model.
2. Add the matching `ALTER TABLE` to `column_additions` in `start.py`.
3. New tables are picked up automatically by `Base.metadata.create_all`.

## CI/CD pipeline
`.github/workflows/ci.yml` runs three jobs:
- `backend-test` — pytest smoke tests under `backend/app/tests`. **Required to merge.**
- `frontend-build` — `npx tsc --noEmit` + `npm run build`. **Required to merge.**
- `backend-lint` — ruff + black, informational only.

External required check: `Vercel` (preview deploy build status). Branch protection on `main` blocks merging until `backend-test`, `frontend-build`, and `Vercel` are all green. Force pushes blocked. Admin can bypass for hotfixes.

Workflow: feature branch → push → PR → 5 checks go green → squash-merge → Railway + Vercel auto-deploy production.

## Key Conventions
- Hebrew RTL UI throughout
- All monetary values stored as `Decimal(15, 2)`
- VAT rate stored as fraction (`0.18` = 18%) on `MonthlyReport.vat_rate` and snapshotted onto `SalesContract.vat_rate`. Forward-only — changing the project VAT does NOT retroactively shift past sales' no-VAT side.
- Budget tracking uses 15-column index-adjusted calculation (see `BudgetTrackingLine.calculate_all`)
- Monthly reports are the central entity — all monthly data links to `monthly_report_id`
- Bank-transaction classification is two-level: `category_primary` (broad bucket) + `subcategory` (specific item or budget-line id). Legacy flat `category` enum kept in parallel for backwards compat with `budget_calculator.py`. Source of truth: `app/services/transaction_taxonomy.py`.
