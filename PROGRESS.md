# Maakav (מעקב) - Full Development Progress Tracker

## Project Overview
**Purpose:** Construction project tracking system for Israeli appraisal firms
**Repo:** https://github.com/luvchikavi/maakav
**Local dir:** /Users/aviluvchik/app/Maakav
**Backend:** FastAPI + SQLAlchemy async + PostgreSQL (port 8700)
**Frontend:** Next.js 15 + TypeScript + Tailwind CSS RTL (port 4700)
**Database:** PostgreSQL local "maakav"
**Login:** admin@maakav.co.il / admin123

## Architecture Summary
- Multi-tenant: firms → users → projects → monthly_reports → all tracking data
- Monthly report is the central entity - all monthly data links to monthly_report_id
- Budget tracking uses 15-column index-adjusted calculation (BudgetTrackingLine.calculate_all)
- Bank statement parsing via Claude Vision AI (ported from Nectra, zero coupling)
- Report output: Word (python-docx) + PDF (LibreOffice headless)

## Key Files
- **Backend models:** backend/app/models/ (17 models)
- **Backend APIs:** backend/app/api/v1/ (auth, projects, setup/, monthly/)
- **Bank parser:** backend/app/services/bank_parser_service.py (596 LOC, ported from Nectra)
- **Budget calc:** backend/app/models/budget_tracking.py (calculate_all method)
- **Frontend pages:** frontend/src/app/(authenticated)/
- **API client:** frontend/src/lib/api.ts (JWT refresh queue)
- **Auth store:** frontend/src/lib/auth.ts (Zustand)
- **Formatters:** frontend/src/lib/formatters.ts (Hebrew currency/date/percent)
- **Seed script:** backend/seed.py (creates firm + admin user)

## Reusable Code from Nectra
| Source (Nectra) | Destination (Maakav) | Status |
|-----------------|---------------------|--------|
| core/services/bank_statement_ai_parser.py | services/bank_parser_service.py | ✅ Ported |
| budget/models/monthly_budget_tracking.py:413-469 | models/budget_tracking.py:calculate_all | ✅ Ported |
| sales/excel_importer.py (473 LOC) | setup/apartments.py (inline) | ✅ Adapted |
| frontend/src/services/api.js | lib/api.ts | ✅ Ported to TypeScript |
| reports/generators/excel_generator.py (340 LOC) | report_templates/ | ⬜ Not yet |

---

## Phase 1: Foundation ✅ COMPLETE
### Backend Scaffold
- [x] Project structure created
- [x] FastAPI app with CORS, health check, global error handler
- [x] Pydantic Settings (config.py)
- [x] Async SQLAlchemy + PostgreSQL (database.py)
- [x] Alembic migration setup
- [x] JWT security (create/verify tokens, password hashing)
- [x] Auth endpoints (login, refresh, me)
- [x] Project CRUD endpoints (list, create, get, update, delete)
- [x] Multi-tenant isolation (firm_id filtering)
- [x] Seed script for local dev (seed.py)

### Database Models (17 total)
- [x] Firm, User (roles: admin/appraiser/viewer)
- [x] Project (phase, bank, indexes), ProjectFinancing, ContractorAgreement, Milestone
- [x] BudgetCategory (5 types), BudgetLineItem
- [x] Apartment (developer/resident, unit types, prices, report_0_price)
- [x] SalesContract, PaymentScheduleItem
- [x] MonthlyReport (status workflow, completeness tracking)
- [x] BankStatement, BankTransaction (16 categories, AI classification)
- [x] BudgetTrackingSnapshot + BudgetTrackingLine (15 columns with calculate_all)
- [x] ConstructionProgress, VatTracking, EquityTracking
- [x] GuaranteeSnapshot, ProfitabilitySnapshot, SourcesUses

### Frontend Scaffold
- [x] Next.js 15 + TypeScript + Tailwind CSS + RTL (Heebo font)
- [x] Login page (clean, minimal)
- [x] Dashboard with KPI cards + project list
- [x] Sidebar navigation
- [x] AuthGuard + Zustand auth store
- [x] API client with JWT auto-refresh queue
- [x] Project creation form

### DevOps
- [x] Git repo: https://github.com/luvchikavi/maakav
- [x] .gitignore, CLAUDE.md
- [ ] Railway backend deployment
- [ ] Vercel frontend deployment
- [ ] GitHub Actions CI/CD

---

## Phase 2: Project Setup ✅ COMPLETE
### Backend APIs
- [x] GET/POST /projects/{id}/setup/budget + Excel upload with auto-detect
- [x] GET/POST/DELETE /projects/{id}/setup/apartments + Excel upload
- [x] GET/PUT /projects/{id}/setup/financing (upsert)
- [x] GET/PUT /projects/{id}/setup/contractor (upsert)
- [x] CRUD /projects/{id}/setup/milestones
- [x] GET /projects/{id}/setup/status (completion checklist)

### Frontend Pages
- [x] Project detail page with 5 setup progress cards + completion bar
- [x] Budget page: drag-drop Excel + category/line item table
- [x] Apartments page: Excel upload + table with ownership badges
- [x] Financing page: credit limits, equity, interest rates form
- [x] Contractor page: contract amount, index, guarantees form
- [x] Milestones page: CRUD + quick-add defaults (היתר, יסודות, שלד, טופס 4)

---

## Phase 3: Monthly Loop - Data Entry ✅ COMPLETE
### Backend APIs
- [x] POST /projects/{id}/monthly-reports (auto-increment report number)
- [x] GET /projects/{id}/monthly-reports (list)
- [x] GET /projects/{id}/monthly-reports/{id}/completeness (validates what's filled/missing)
- [x] POST /projects/{id}/monthly-reports/{id}/bank-statements/upload (AI parsing)
- [x] GET /projects/{id}/monthly-reports/{id}/transactions (list parsed transactions)
- [x] PATCH /projects/{id}/monthly-reports/{id}/transactions/{id} (classify)
- [x] POST /projects/{id}/monthly-reports/{id}/transactions/bulk-classify
- [x] PUT /projects/{id}/monthly-reports/{id}/construction (progress entry)
- [x] PATCH /projects/{id}/monthly-reports/{id}/index (update construction index)
- [x] GET /projects/{id}/sales/summary

### Frontend Pages (7-step wizard)
- [x] Monthly reports list with create dialog
- [x] Wizard layout with horizontal stepper + completion indicators
- [x] Step 1: Bank statement upload → AI parse → transaction table with category dropdowns
- [x] Step 2: Sales summary (stats dashboard)
- [x] Step 3: Construction progress slider + description textarea
- [x] Step 4: Index update with ratio display
- [x] Step 5: Guarantees upload (placeholder)
- [x] Step 6: Review - completeness checklist (green/red) + missing items
- [x] Step 7: Generate report (placeholder for Phase 5)

---

## Phase 4: Calculations Engine ✅ COMPLETE
### Budget Calculator Service
- [x] Create services/budget_calculator.py
- [x] Wire calculate_all to bank transactions per category
- [x] Auto-populate K column (monthly_paid_actual) from classified transactions
- [x] Carry-forward F, J columns from previous month snapshot
- [x] POST /projects/{id}/monthly-reports/{id}/calculate endpoint
- [x] Return full נספח א' table data

### Sales Calculator Service
- [x] Create services/sales_calculator.py
- [x] Qualified sales count (תקבולים >15% ממחיר)
- [x] Quarterly sales pace (קצב מכירות רבעוני)
- [x] Non-linear sales detection (תקבול אחרון >40%)
- [x] Payment arrears (פיגורי רוכשים)
- [x] Sales vs Report 0 comparison (הפרש מחירים)

### VAT Calculator Service
- [x] Create services/vat_calculator.py
- [x] Monthly: transactions (income) → output VAT
- [x] Monthly: inputs (expenses) → input VAT
- [x] Balance: input - output
- [x] Cumulative tracking

### Equity Calculator Service
- [x] Create services/equity_calculator.py
- [x] Extract equity deposits/withdrawals from bank transactions
- [x] Calculate cumulative balance
- [x] Compare to required amount → gap

### Profitability Calculator Service
- [x] Create services/profitability_calculator.py
- [x] Income: receipts + inventory value
- [x] Costs: from budget tracking (נספח א')
- [x] Profit = income - costs
- [x] Comparison to Report 0

### Sources & Uses Calculator Service
- [x] Create services/sources_uses_calculator.py
- [x] Sources: equity, sales receipts, bank credit, VAT refunds
- [x] Uses: payments (from budget), surplus releases
- [x] Balance calculation

### Guarantee Calculator Service
- [ ] Create services/guarantee_calculator.py (Phase 5)
- [ ] Guarantee balance vs receipts comparison

### AI Auto-Classification Service
- [ ] Create services/transaction_classifier.py (Phase 6)
- [ ] Claude API with category taxonomy + project context

### Anomaly Detection
- [ ] Budget overrun alerts (Phase 6)
- [ ] Unusual transaction amounts
- [ ] Physical vs financial execution gap alerts

### Frontend - Review Step Enhancement
- [x] Show נספח א' table in review step
- [x] Show sales summary in review
- [x] Show VAT balance
- [x] Show equity status
- [x] Show profitability comparison (Report 0 vs current)

---

## Phase 5: Report Generation ⬜ NOT STARTED
### Word Document Generator (python-docx)
- [ ] Create report_templates/tracking_report.py (orchestrator)
- [ ] RTL formatting setup (paragraph.bidi, Hebrew font)
- [ ] Cover page (project name, report number, date, firm logo)
- [ ] Chapter 4: Budget tracking table (נספח א' - 15 columns)
- [ ] Chapter 4.3: Expense forecast for next month
- [ ] Chapter 5.1: Physical vs financial execution table
- [ ] Chapter 5.2: Construction description per report (cumulative table)
- [ ] Chapter 5.3: Milestones timeline (planned vs actual)
- [ ] Chapter 6: Contractor agreement summary
- [ ] Chapter 7.1: Sales list table (all sold apartments with prices)
- [ ] Chapter 7.2: Quarterly sales pace table
- [ ] Chapter 7.3: Sales summary stats
- [ ] Chapter 7.4: Receipts summary (cumulative + monthly)
- [ ] Chapter 7.5: Payment arrears table
- [ ] Chapter 7.6: Guarantee status table
- [ ] Chapter 7.7: Non-linear sales table
- [ ] Chapter 8: VAT tracking table (monthly rows)
- [ ] Chapter 9.1: Financing terms
- [ ] Chapter 9.2: Equity balance (cumulative deposits/withdrawals)
- [ ] Chapter 9.3: Profitability comparison (Report 0 vs current)
- [ ] Chapter 10: Form 50 + surplus releases
- [ ] Chapter 11: Sources & uses balance table

### PDF Conversion
- [ ] LibreOffice headless integration
- [ ] Docker image with LibreOffice for Railway

### API + Frontend
- [ ] POST /projects/{id}/monthly-reports/{id}/generate
- [ ] Return Word + PDF download URLs
- [ ] Generate step: preview + download buttons
- [ ] S3 storage for generated files

---

## Phase 6: Dashboard & Polish ⬜ NOT STARTED
- [ ] Dashboard with 5 KPI metrics across all projects
  - Budget usage % (ניצול תקציב)
  - Construction progress % (ביצוע פיזי)
  - Sales % (מכירות)
  - Signed contracts % (חוזים חתומים)
  - Qualified sales % (מכירות מוכרות >15%)
- [ ] Project-level dashboard with monthly trend charts
- [ ] Cross-project comparison view
- [ ] Mobile responsiveness (site visits)
- [ ] Performance optimization (query caching)
- [ ] Hebrew error messages throughout
- [ ] User management (invite users, roles)
- [ ] Deployment to Railway + Vercel
- [ ] GitHub Actions CI/CD
- [ ] User documentation / onboarding
