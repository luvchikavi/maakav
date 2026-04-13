# Maakav - Progress Tracker

## Phase 1: Foundation (Weeks 1-3)

### Backend Scaffold
- [x] Project structure created
- [x] FastAPI app with CORS, health check
- [x] Pydantic Settings (config.py)
- [x] Async SQLAlchemy + PostgreSQL (database.py)
- [x] Alembic migration setup
- [x] JWT security (create/verify tokens, password hashing)
- [x] Auth endpoints (login, refresh, me)
- [x] Project CRUD endpoints (list, create, get, update, delete)
- [x] Multi-tenant isolation (firm_id filtering)

### Database Models (17 total)
- [x] Firm
- [x] User (with roles: admin, appraiser, viewer)
- [x] Project (with phase, bank, indexes)
- [x] ProjectFinancing (credit limits, equity requirements)
- [x] ContractorAgreement (contract amount, guarantees, retention)
- [x] Milestone (planned vs actual dates)
- [x] BudgetCategory (5 category types)
- [x] BudgetLineItem (individual budget items from Section 8)
- [x] Apartment (developer/resident, unit types, prices, report 0 price)
- [x] SalesContract (buyer, prices, recognized/non-linear flags)
- [x] PaymentScheduleItem (scheduled vs actual payments)
- [x] MonthlyReport (central entity, status workflow, completeness tracking)
- [x] BankStatement (PDF metadata, parsing status)
- [x] BankTransaction (16 categories, AI classification)
- [x] BudgetTrackingSnapshot + BudgetTrackingLine (15-column calculation with calculate_all)
- [x] ConstructionProgress (overall %, description, photos)
- [x] VatTracking (monthly transactions, inputs, outputs, balance)
- [x] EquityTracking (deposits, withdrawals, gap)
- [x] GuaranteeSnapshot (balance, items, gap)
- [x] ProfitabilitySnapshot (report 0 vs current)
- [x] SourcesUses (sources vs uses balance)

### Frontend Scaffold
- [x] Next.js 15 project initialization
- [x] Tailwind CSS + RTL setup
- [x] Hebrew font (Heebo)
- [x] Auth pages (login)
- [x] Dashboard layout (sidebar, header)
- [x] API client with JWT refresh
- [x] Project list page
- [x] Project creation page

### DevOps
- [x] Git repo initialized
- [x] GitHub repo created (luvchikavi/maakav)
- [x] .gitignore configured
- [x] CLAUDE.md created
- [ ] Railway backend deployment
- [ ] Vercel frontend deployment
- [ ] GitHub Actions CI/CD

---

## Phase 2: Project Setup (Weeks 4-6)
- [ ] Budget upload (Excel parser) + manual entry UI
- [ ] Apartment inventory CRUD + Excel import
- [ ] Financing terms form
- [ ] Contractor agreement form
- [ ] Milestones timeline
- [ ] Setup completion progress indicator
- [ ] Form validation on all setup pages

## Phase 3: Monthly Loop - Data Entry (Weeks 7-10)
- [ ] Monthly report creation with carry-forward service
- [ ] Bank statement PDF upload + AI parsing (port from Nectra)
- [ ] Transaction review & classification UI
- [ ] AI auto-classification service
- [ ] Sales entry/update with payment schedule
- [ ] Construction progress entry (% + description + photos)
- [ ] Index update (מדד תשומות)
- [ ] Guarantee upload
- [ ] 7-step wizard navigation in frontend

## Phase 4: Calculations Engine (Weeks 11-13)
- [ ] Budget calculator (calculate_all - already in model)
- [ ] Sales calculator (qualified >15%, quarterly pace, non-linear >40%)
- [ ] VAT calculator (monthly transactions/inputs/outputs)
- [ ] Equity calculator (deposits, withdrawals, gap)
- [ ] Profitability calculator (income vs costs, report 0 comparison)
- [ ] Sources & uses calculator (balance sheet)
- [ ] Guarantee vs receipts comparison
- [ ] Completeness validator (block report if data missing)
- [ ] Anomaly detector (budget overruns, unusual transactions)

## Phase 5: Report Generation (Weeks 14-16)
- [ ] Word document generator (python-docx)
- [ ] RTL formatting and Hebrew text in Word
- [ ] Chapter 4: Budget tracking table
- [ ] Chapter 5: Construction progress
- [ ] Chapter 6: Sales summary
- [ ] Chapter 7: Payment receipts & arrears
- [ ] Chapter 8: VAT tracking
- [ ] Chapter 9: Equity balance
- [ ] Chapter 10: Profitability
- [ ] Chapter 11: Sources & uses
- [ ] PDF conversion (LibreOffice headless)
- [ ] Download endpoints
- [ ] Report preview in frontend

## Phase 6: Dashboard & Polish (Weeks 17-18)
- [ ] Dashboard with 5 KPI metrics
- [ ] Cross-project overview
- [ ] Mobile responsiveness
- [ ] Performance optimization
- [ ] User documentation
