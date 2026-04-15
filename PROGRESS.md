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

## Phase 5: Report Generation ✅ COMPLETE (Word, PDF pending)
### Word Document Generator (python-docx)
- [x] Create report_templates/tracking_report.py (orchestrator)
- [x] RTL formatting setup (paragraph.bidi, Hebrew font David)
- [x] Cover page (project name, report number, date, developer)
- [x] Chapter 4: Budget tracking table (נספח א') + index data
- [ ] Chapter 4.3: Expense forecast for next month (Phase 6)
- [x] Chapter 5.1: Physical vs financial execution table
- [x] Chapter 5.2: Construction description
- [ ] Chapter 5.3: Milestones timeline (Phase 6)
- [ ] Chapter 6: Contractor agreement summary (Phase 6)
- [ ] Chapter 7.1: Full sales list table (Phase 6)
- [x] Chapter 7.2: Quarterly sales pace table
- [x] Chapter 7.3: Sales summary stats
- [ ] Chapter 7.4: Receipts summary (Phase 6)
- [x] Chapter 7.5: Payment arrears table
- [ ] Chapter 7.6: Guarantee status table (Phase 6)
- [x] Chapter 7.7: Non-linear sales mention
- [x] Chapter 8: VAT tracking table
- [x] Chapter 9: Equity balance
- [x] Chapter 10: Profitability comparison (Report 0 vs current)
- [x] Chapter 11: Sources & uses balance table

### PDF Conversion
- [ ] LibreOffice headless integration (Phase 6)
- [ ] Docker image with LibreOffice for Railway

### API + Frontend
- [ ] POST /projects/{id}/monthly-reports/{id}/generate
- [x] POST /projects/{id}/monthly-reports/{id}/generate endpoint
- [x] StreamingResponse with .docx download
- [x] Generate step: download button with success state
- [ ] S3 storage for generated files (Phase 6)
- [ ] PDF conversion (Phase 6)

---

## Phase 6: Dashboard & Polish ✅ CORE COMPLETE
- [x] Dashboard with 5 KPI metrics across all projects
  - Budget usage % (ניצול תקציב)
  - Construction progress % (ביצוע פיזי)
  - Signed contracts (חוזים חתומים)
  - Qualified sales (מכירות מוכרות >15%)
  - Active projects count
- [x] Projects table with progress bars + phase tags
- [x] Dockerfile for Railway
- [x] Procfile for Railway
- [x] GitHub Actions CI/CD (lint + build)
- [ ] Project-level dashboard with monthly trend charts
- [ ] Mobile responsiveness (site visits)
- [ ] Performance optimization (query caching)
- [ ] User management (invite users, roles)
- [ ] Railway + Vercel deployment execution
- [ ] PDF conversion (LibreOffice)
- [ ] AI auto-classification of transactions
- [ ] User documentation / onboarding

---

## Phase 7A: Sales & Payments ✅ COMPLETE
### Sales Entry (Wizard Step 2)
- [x] Frontend: Sales entry form with apartment dropdown (unsold only), buyer name/ID, date, prices
- [x] Frontend: Auto-fill prices from apartment list, auto-calc no-VAT (÷1.18)
- [x] Frontend: Sales list table with delete + payment schedule button
- [x] Backend: GET /projects/{id}/apartments/unsold endpoint
- [x] Backend: DELETE /projects/{id}/sales/{id} endpoint

### Payment Schedule
- [x] Backend: Full CRUD endpoints (GET/POST/PATCH/DELETE) for PaymentScheduleItem
- [x] Frontend: Payment schedule modal per sale (add, edit status, delete)
- [x] Frontend: Status indicators (scheduled/paid/partial/overdue) with color badges
- [x] Frontend: Summary cards (total scheduled, paid, remaining)

---

## Phase 7B: Guarantees ✅ COMPLETE
### Guarantee Processing (Wizard Step 5)
- [x] Backend: guarantee_parser_service.py (240 LOC) — AI-powered Excel/PDF parser
- [x] Backend: POST /guarantees/upload, GET /guarantees, PUT /guarantees/items
- [x] Frontend: Upload + parse → items table with type badges, amounts, expiry
- [x] Frontend: Delete individual items, re-upload replaces
- [x] Frontend: Summary cards (total count, sale_law count, total balance)

---

## Phase 7C: Missing Report Chapters ✅ COMPLETE
### Word Report Additions
- [x] Chapter 7.1: Full sales list table (#, building, unit, buyer, date, price, Report 0, diff) + totals row
- [x] Chapter 5.3: Milestones table (name, planned date, actual date, status)
- [x] Chapter 7.6: Guarantee items table (buyer, type, apartment, original, indexed, expiry)
- [x] Chapter 9.2: Equity per-report history table (report number, deposits, withdrawals, balance)
- [x] Updated tracking_report.py to pass milestones + guarantees to chapter generators
- [x] Updated calculations endpoint to include milestones, guarantees, equity history

---

## Phase 8: P2 Features ✅ COMPLETE
### AI Auto-Classification (#7)
- [x] transaction_classifier.py — rule-based + Claude Haiku fallback
- [x] Auto-classifies on bank statement upload (high-confidence auto-applied)
- [x] POST /transactions/auto-classify endpoint for manual trigger
- [x] Frontend: "סווג אוטומטי" button + AI badges on auto-classified rows

### PDF Report Conversion (#8)
- [x] pdf_converter.py — LibreOffice headless (Mac/Linux/Docker)
- [x] GET /reports/pdf-available health check
- [x] POST /generate?format=pdf|docx
- [x] Frontend: Word + PDF download buttons in generate step

### Exposure Report (#9)
- [x] exposure_calculator.py — sales %, construction %, credit utilization, net exposure
- [x] GET /exposure endpoint
- [x] Shown in review step with 7-stat card layout

### Cashflow Forecast (#10)
- [x] cashflow_calculator.py — 6-month projection from payment schedule + budget remaining
- [x] GET /cashflow?months=6 endpoint
- [x] Shown in review step with monthly table + summary totals

---

## Phase 9: Polish (P3) ✅ COMPLETE
### Hebrew Error Messages (#11)
- [x] 35 English error messages replaced with Hebrew across 13 API files

### Mobile Responsiveness (#12)
- [x] Collapsible sidebar: hamburger menu on mobile, slide-in overlay
- [x] Responsive layout padding (mobile top padding for hamburger)
- [x] CSS animation for sidebar slide-in

### User Management (#13)
- [x] Backend: 5 endpoints — list, create, update role, reset password, delete
- [x] Admin-only access control
- [x] Frontend: /users page with role dropdowns, status toggles, invite + reset modals
- [x] Sidebar: added users navigation link

---

## Phase 10: Deploy ⬜ NOT STARTED
- [ ] Railway backend deployment (see DEPLOYMENT.md)
- [ ] Vercel frontend deployment
- [ ] Environment variables configuration
- [ ] Domain setup (maakav.co.il or subdomain)
- [ ] SSL + health check verification
- [ ] Smoke test on production

---

## Summary Statistics
- **Commits:** 18+
- **Backend files:** ~98
- **Frontend pages:** 17
- **DB models:** 17
- **Calculator services:** 9
- **Report chapters:** 11
- **API endpoints:** ~70
- **Total lines of code:** ~17,500
- **Open P1 gaps:** 0 ✅
- **Open P2 gaps:** 0 ✅
- **Open P3 gaps:** 0 ✅
