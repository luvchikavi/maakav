# Maakav - Open Gaps & Next Steps

## Priority 1: Core Gaps (Must Fix Before Deploy)

### 1. Guarantees (ערבויות) - Currently Placeholder
- **What's missing:** Upload zone exists but doesn't process the file
- **What's needed:** Parse guarantee PDF/Excel, extract items (buyer, amount, type, expiry)
- **Also needed:** Guarantee vs receipts comparison table in report (Chapter 7.6)
- **Nectra has:** GuaranteeSnapshot + GuaranteeSnapshotItem models, guarantee_tracking service

### 2. Sales Entry in Monthly Wizard (Step 2)
- **What's missing:** Step 2 only shows summary, can't add new sales
- **What's needed:** Form to add new sale (select apartment, buyer name, price, date)
- **Also needed:** Payment schedule entry per sale (installments)

### 3. Payment Schedule UI
- **What's missing:** PaymentScheduleItem model exists but no UI to enter installments
- **What's needed:** Per-sale payment grid (date, amount, status)
- **Required for:** Arrears calculation, recognized sales (>15%), receipts tracking

### 4. Full Sales List in Report (Chapter 7.1)
- **What's missing:** Report only has summary, not the full apartment-by-apartment sales table
- **What's needed:** Table with: serial, building, unit, buyer, date, price with VAT, price no VAT, Report 0 price, difference

### 5. Milestones in Report (Chapter 5.3)
- **What's missing:** Milestones data exists but not included in Word report
- **What's needed:** Table with: milestone name, planned date, actual date

### 6. Equity Detail Table (Chapter 9.2)
- **What's missing:** Only shows totals, not per-report deposits/withdrawals
- **What's needed:** Table listing each deposit/withdrawal by report number (like the Excel)

## Priority 2: Important Features

### 7. AI Auto-Classification of Transactions
- **What's missing:** User must manually classify every transaction
- **What's needed:** After AI parsing, suggest category based on description
- **Approach:** Claude API with category taxonomy + project context
- **Nectra has:** Smart upload service with column mapping suggestions

### 8. PDF Report Conversion
- **What's missing:** Only Word output, no PDF
- **What's needed:** LibreOffice headless conversion (or alternative)
- **For deploy:** Need LibreOffice in Docker image

### 9. Exposure Report (דוח חשיפה)
- **What's missing:** Not implemented
- **What's needed:** Monthly tracking of bank exposure (sold %, construction %, credit used)
- **Nectra has:** Basic exposure tracking in BankTransactionsSection

### 10. Cashflow Forecast (תזרים מזומנים)
- **What's missing:** Not implemented
- **What's needed:** Monthly projected income vs expenses

## Priority 3: Polish

### 11. Hebrew Error Messages
- **What's missing:** Some API errors return English
- **What's needed:** Consistent Hebrew throughout

### 12. Mobile Responsiveness
- **What's missing:** Sidebar doesn't collapse on mobile
- **What's needed:** Responsive sidebar, touch-friendly progress slider

### 13. User Management
- **What's missing:** Only seed-created admin
- **What's needed:** Invite users, assign roles (admin/appraiser/viewer)

---

## Excel Upload Strategy (To Discuss)

### Current State:
- Budget upload: works, auto-detects sheet + header row
- Apartments upload: works, handles multiple sheets (developer + owner)
- Bank statement: AI parsing from PDF

### Questions to Resolve:
1. Should there be a single "bulk upload" Excel template for initial project setup?
2. Should the system accept the office's existing Excel format (21-tab workbook)?
3. How to handle monthly bank statement Excel vs PDF?
4. Should the system support importing from the existing monitoring Excel (מעקב חודשי)?

---

## Code to Port from Nectra

| Nectra File | Purpose | Port Status |
|-------------|---------|-------------|
| bank_statement_ai_parser.py | AI bank PDF parsing | ✅ Ported |
| excel_importer.py | Apartment Excel import | ✅ Adapted |
| file_upload_views.py | Sheet/header auto-detection | ✅ Adapted |
| excel_generator.py | Excel export | ⬜ Not yet |
| guarantee_tracking.py | Guarantee processing | ⬜ Needed |
| smart_upload_service.py | AI column mapping | ⬜ Could help with auto-classification |
