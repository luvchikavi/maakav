# Maakav - Open Gaps & Next Steps

## Priority 1: Core Gaps (Must Fix Before Deploy)

### 1. Sales Entry in Monthly Wizard (Step 2) ✅ DONE
- Full sales entry form: apartment dropdown (unsold only), buyer name/ID, date, price with/without VAT
- Auto-fill prices from apartment list, auto-calc no-VAT from with-VAT (÷1.18)
- Sales list table with delete + payment schedule link
- New endpoint: GET /projects/{id}/apartments/unsold
- New endpoint: DELETE /projects/{id}/sales/{id}

### 2. Payment Schedule UI ✅ DONE
- Per-sale payment schedule modal with add/edit/delete
- Status management: scheduled → paid/partial/overdue
- Auto-mark as paid with amount + date when status changes
- Totals: scheduled vs paid vs remaining
- Backend: Full CRUD endpoints (GET/POST/PATCH/DELETE) for PaymentScheduleItem

### 3. Guarantees (ערבויות) ✅ DONE
- AI-powered guarantee parser (Claude Vision for PDF, auto-detect columns for Excel)
- Upload + parse → items table with type badges, amounts, expiry
- Delete individual items, re-upload replaces
- New service: guarantee_parser_service.py (240 LOC)
- New endpoints: POST upload, GET snapshot, PUT items
- Frontend: full items table with summary cards

### 4. Full Sales List in Report (Chapter 7.1) ✅ DONE
- Table with: #, building, unit, buyer, date, sale price, Report 0 price, difference
- Totals row at bottom
- Uses report_0_comparison data from sales calculator

### 5. Milestones in Report (Chapter 5.3) ✅ DONE
- Table with: milestone name, planned date, actual date, status (✓ completed / waiting)
- Data loaded from milestones table via calculations endpoint

### 6. Guarantee Status + Equity Detail in Report (Chapters 7.6, 9.2) ✅ DONE
- **Ch 7.6:** Full guarantee items table with type labels, amounts, expiry, apartment number
- **Ch 9.2:** Per-report equity history table (report number, deposits, withdrawals, balance)

---

## Priority 2: Important Features (Post-Deploy)

### 7. AI Auto-Classification of Transactions ✅ DONE
- Two-phase classification: rule-based patterns (instant, 75% confidence) + Claude Haiku fallback
- Auto-classifies on upload (high-confidence applied automatically)
- Manual "auto-classify" button for remaining unclassified
- AI badge on auto-classified transactions, purple vs green for manual
- New service: transaction_classifier.py (190 LOC)

### 8. PDF Report Conversion ✅ DONE
- LibreOffice headless conversion (docx → pdf)
- Auto-detects LibreOffice on Mac/Linux/Docker
- Generate page shows Word + PDF buttons
- Graceful fallback: if LibreOffice unavailable, shows Word only
- New service: pdf_converter.py
- GET /reports/pdf-available endpoint for frontend check

### 9. Exposure Report (דוח חשיפה) ✅ DONE
- Calculates: sales %, construction %, credit utilization, net exposure
- Net exposure = credit used - receipts - equity
- Shown in review step after calculations run
- New service: exposure_calculator.py
- GET /exposure endpoint

### 10. Cashflow Forecast (תזרים מזומנים) ✅ DONE
- Projects 6 months ahead (configurable)
- Income: scheduled payment receipts from sales contracts
- Expenses: remaining budget spread evenly + monthly interest
- Monthly table with net flow + cumulative balance
- Shown in review step
- New service: cashflow_calculator.py
- GET /cashflow endpoint

---

## Priority 3: Polish ✅ COMPLETE

### 11. Hebrew Error Messages ✅ DONE
- 35 English error messages replaced with Hebrew across all 13 API files

### 12. Mobile Responsiveness ✅ DONE
- Sidebar: hidden on mobile, hamburger button opens overlay with slide-in animation
- Layout: responsive padding, mobile-safe top margin for hamburger
- Desktop: unchanged (fixed 256px sidebar)

### 13. User Management ✅ DONE
- Backend: 5 endpoints (list, create, update, reset-password, delete)
- Admin-only access for create/update/delete
- Frontend: /users page with table, role dropdowns, status toggles
- Invite modal: name, email, password, role selection
- Reset password modal
- Sidebar updated with users link

---

## Excel Upload Strategy ✅ RESOLVED

- **Bulk upload** works: 8-tab unified Excel → all data distributed automatically
- **Bank statement Excel**: smart fallback parser works for all 7 Israeli banks (no AI needed)
- **Bank statement PDF**: Claude Vision AI (requires ANTHROPIC_API_KEY with credits)
- **Individual uploads** still available for each section separately

## Overnight Fixes (Apr 15)

### Bank Statement Excel Parser ✅
- Smart column detection for all Israeli banks: לאומי, פועלים, דיסקונט, ירושלים, מזרחי, הבינלאומי, מרכנתיל
- Works WITHOUT AI — direct column mapping
- Tested: 4/4 Excel samples parsed correctly (27-47 transactions each)

### VAT Calculation Refinement ✅
- VAT-exempt categories properly excluded (land tax, equity, loans, interest)
- VAT extracted from amounts (÷1.18) instead of flat 18% multiplication
- Monthly VAT history table in report and review step

### Form 50 + Surplus Release ✅
- Fields added to MonthlyReport model
- Included in calculations endpoint and Word report (Chapter 10)

### Expense Forecast ✅
- Budget remaining + estimated monthly expense + expected receipts
- Shown in review step as "תחזית חודש הבא" card

### Guarantee Cross-Validation ✅
- GET /guarantees/validate endpoint
- Checks: sold apartments without guarantee, receipts vs guarantee gap
- Returns typed alerts with severity

## Implementation Status

```
All P1 + P2 + P3 gaps closed ✅
Overnight fixes applied ✅
Strategic roadmap: see ROADMAP.md
```
