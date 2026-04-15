"""
Demo data seed - creates a realistic project with full data across all modules.
Run: cd backend && python seed_demo.py
"""

import asyncio
from datetime import date, datetime, timedelta
from decimal import Decimal

from app.database import engine, AsyncSessionLocal, Base
from app.models import *  # noqa
from app.models.user import UserRole
from app.models.project import ProjectPhase, BankName
from app.models.apartment import Ownership, UnitStatus, UnitType
from app.models.budget import CategoryType
from app.models.monthly_report import ReportStatus
from app.models.bank_statement import ParsingStatus, TransactionType, TransactionCategory
from app.models.sales import PaymentStatus

from sqlalchemy import select, delete


async def seed_demo():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    async with AsyncSessionLocal() as db:
        # Get firm
        firm = (await db.execute(select(Firm).where(Firm.name == "בלייר כץ-אהרונוב"))).scalar_one_or_none()
        if not firm:
            print("Error: Run seed.py first to create firm + admin.")
            return

        # Delete existing demo project if exists
        existing = (await db.execute(select(Project).where(Project.project_name == 'פרויקט "הנחלה" רחובות'))).scalar_one_or_none()
        if existing:
            # Cascade delete everything
            for Model in [
                SourcesUses, ProfitabilitySnapshot, GuaranteeSnapshot, EquityTracking,
                VatTracking, ConstructionProgress, BudgetTrackingLine, BudgetTrackingSnapshot,
                BankTransaction, BankStatement, PaymentScheduleItem, SalesContract,
                BudgetLineItem, BudgetCategory, Milestone, ContractorAgreement,
                ProjectFinancing, MonthlyReport, Apartment,
            ]:
                await db.execute(delete(Model).where(Model.project_id == existing.id))
            await db.execute(delete(Project).where(Project.id == existing.id))
            await db.commit()
            print("Cleared existing demo data.")

        # ── 1. Project ─────────────────────────────────────────────
        project = Project(
            firm_id=firm.id,
            project_name='פרויקט "הנחלה" רחובות',
            address="רחוב הנחלה 12-18",
            city="רחובות",
            neighborhood="נחלת יהודה",
            block="3845",
            parcel="55,56",
            developer_name='אלעזר נדל"ן בע"מ',
            developer_company_number="515678901",
            bank=BankName.LEUMI,
            bank_branch="783",
            project_account_number="12345678",
            escrow_account_number="87654321",
            phase=ProjectPhase.ACTIVE,
            report_0_date=date(2025, 6, 1),
            base_index=Decimal("127.3"),
            base_index_date=date(2025, 6, 1),
            contractor_base_index=Decimal("127.3"),
            total_units=42,
            total_buildings=2,
            project_type="land",
            current_report_number=3,
        )
        db.add(project)
        await db.flush()
        pid = project.id
        print(f"Created project: {project.project_name} (id={pid})")

        # ── 2. Financing ───────────────────────────────────────────
        financing = ProjectFinancing(
            project_id=pid,
            financing_type="banking",
            financing_body="בנק לאומי",
            agreement_date=date(2025, 5, 15),
            credit_limit_total=Decimal("45000000"),
            credit_limit_construction=Decimal("35000000"),
            credit_limit_land=Decimal("8000000"),
            credit_limit_guarantees=Decimal("2000000"),
            equity_required_amount=Decimal("5000000"),
            equity_required_percent=Decimal("12"),
            presale_units_required=8,
            presale_amount_required=Decimal("12000000"),
            interest_rate=Decimal("5.5"),
            guarantee_fee_percent=Decimal("1.2"),
        )
        db.add(financing)

        # ── 3. Contractor ──────────────────────────────────────────
        contractor = ContractorAgreement(
            project_id=pid,
            contractor_name="אופק בנייה בע\"מ",
            contractor_company_number="512345678",
            contract_amount_no_vat=Decimal("28000000"),
            contract_amount_with_vat=Decimal("33040000"),
            contract_date=date(2025, 7, 1),
            base_index_value=Decimal("127.3"),
            base_index_date=date(2025, 6, 1),
            guarantee_percent=Decimal("10"),
            guarantee_amount=Decimal("2800000"),
            retention_percent=Decimal("5"),
            construction_duration_months=24,
        )
        db.add(contractor)

        # ── 4. Milestones ──────────────────────────────────────────
        milestones_data = [
            ("היתר בנייה", date(2025, 6, 15), date(2025, 7, 1), 1),
            ("התחלת חפירה", date(2025, 7, 15), date(2025, 8, 1), 2),
            ("סיום יסודות", date(2025, 10, 1), date(2025, 11, 15), 3),
            ("סיום שלד", date(2026, 3, 1), date(2026, 3, 20), 4),
            ("סיום טיח חוץ", date(2026, 6, 1), None, 5),
            ("טופס 4", date(2026, 10, 1), None, 6),
            ("מסירת דירות", date(2026, 12, 1), None, 7),
        ]
        for name, planned, actual, order in milestones_data:
            db.add(Milestone(project_id=pid, name=name, planned_date=planned, actual_date=actual, display_order=order))

        # ── 5. Budget (5 categories, 20 line items) ───────────────
        budget_items = {
            CategoryType.TENANT_EXPENSES: [
                ("פינוי דיירים - משפחת כהן", Decimal("850000"), "ע\"פ הסכם"),
                ("פינוי דיירים - משפחת לוי", Decimal("720000"), "ע\"פ הסכם"),
                ("שכ\"ד מעבר לדיירים", Decimal("480000"), "אומדן"),
            ],
            CategoryType.LAND_AND_TAXES: [
                ("רכישת קרקע", Decimal("7500000"), "ע\"פ הסכם"),
                ("מס רכישה", Decimal("600000"), "אומדן"),
                ("היטל השבחה", Decimal("350000"), "אומדן"),
            ],
            CategoryType.INDIRECT_COSTS: [
                ("אדריכלות - א. כהן אדריכלים", Decimal("850000"), "ע\"פ הסכם"),
                ("הנדסה - מ. שרון מהנדסים", Decimal("420000"), "ע\"פ הסכם"),
                ("ייעוץ משפטי", Decimal("350000"), "אומדן"),
                ("שיווק ופרסום", Decimal("600000"), "אומדן"),
                ("ביטוח קבלנים", Decimal("180000"), "ע\"פ הסכם"),
                ("פיקוח הנדסי", Decimal("320000"), "ע\"פ הסכם"),
                ("ניהול פרויקט", Decimal("250000"), "אומדן"),
            ],
            CategoryType.DIRECT_CONSTRUCTION: [
                ("עבודות חפירה ותשתית", Decimal("2200000"), "ע\"פ הסכם"),
                ("שלד בטון", Decimal("8500000"), "ע\"פ הסכם"),
                ("אלומיניום וזיגוג", Decimal("3200000"), "ע\"פ הסכם"),
                ("חשמל ואינסטלציה", Decimal("2800000"), "ע\"פ הסכם"),
                ("ריצוף וחיפוי", Decimal("1900000"), "ע\"פ הסכם"),
                ("צבע וגבס", Decimal("1200000"), "ע\"פ הסכם"),
                ("מעליות", Decimal("1100000"), "ע\"פ הסכם"),
            ],
        }

        for cat_type, items in budget_items.items():
            total = sum(item[1] for item in items)
            cat = BudgetCategory(
                project_id=pid,
                category_type=cat_type,
                display_order=list(budget_items.keys()).index(cat_type),
                total_amount=total,
            )
            db.add(cat)
            await db.flush()
            for i, (desc, cost, source) in enumerate(items, 1):
                db.add(BudgetLineItem(
                    category_id=cat.id,
                    line_number=i,
                    description=desc,
                    cost_no_vat=cost,
                    source=source,
                ))

        # ── 6. Apartments (42 units: 30 developer, 12 resident) ──
        apt_data = []
        for bldg in ["A", "B"]:
            for floor in range(0, 8):
                for unit in range(1, 4):
                    apt_num = floor * 3 + unit
                    if apt_num > 21:
                        break
                    is_resident = (bldg == "A" and floor < 2)  # Ground floors of building A = residents
                    rooms = 3 if unit == 1 else 4 if unit == 2 else 5
                    area = 75 + (rooms - 3) * 20
                    price_sqm = 28000 if bldg == "A" else 26000
                    price_no_vat = area * price_sqm
                    price_with_vat = int(price_no_vat * 1.18)

                    apt_data.append(Apartment(
                        project_id=pid,
                        building_number=bldg,
                        floor=str(floor),
                        unit_number=str(apt_num),
                        unit_type=UnitType.PENTHOUSE if floor == 7 else UnitType.GARDEN if floor == 0 else UnitType.APARTMENT,
                        ownership=Ownership.RESIDENT if is_resident else Ownership.DEVELOPER,
                        unit_status=UnitStatus.COMPENSATION if is_resident else UnitStatus.FOR_SALE,
                        room_count=Decimal(str(rooms)),
                        net_area_sqm=Decimal(str(area)),
                        balcony_area_sqm=Decimal("12") if floor < 7 else Decimal("40"),
                        parking_count=1 if rooms <= 4 else 2,
                        storage_count=1,
                        list_price_with_vat=Decimal(str(price_with_vat)),
                        list_price_no_vat=Decimal(str(price_no_vat)),
                        report_0_price_no_vat=Decimal(str(int(price_no_vat * 0.95))),  # Report 0 was 5% lower
                    ))

        for apt in apt_data:
            db.add(apt)
        await db.flush()

        # Get developer apartments for sales
        dev_apts = [a for a in apt_data if a.ownership == Ownership.DEVELOPER]
        print(f"Created {len(apt_data)} apartments ({len(dev_apts)} developer, {len(apt_data) - len(dev_apts)} resident)")

        # ── 7. Sales (12 contracts with payment schedules) ────────
        buyers = [
            ("יוסי כהן", "302456789"), ("רונית לוי", "204567890"), ("אבי גולן", "305678901"),
            ("מיכל דהן", "207890123"), ("עמית שמש", "301234567"), ("דניאל אברהם", "208901234"),
            ("נועה ישראלי", "303456789"), ("יעל מזרחי", "209012345"), ("אלון ברק", "304567890"),
            ("שירה פרידמן", "200123456"), ("גיל רוזנברג", "306789012"), ("תמר חיימוב", "201234567"),
        ]

        sales_created = []
        for i, (name, id_num) in enumerate(buyers):
            apt = dev_apts[i]
            apt.unit_status = UnitStatus.SOLD
            # 5% discount on average
            discount = Decimal("0.95") + Decimal(str(i % 3)) * Decimal("0.02")
            final_no_vat = int(float(apt.list_price_no_vat) * float(discount))
            final_with_vat = int(final_no_vat * 1.18)

            sale = SalesContract(
                apartment_id=apt.id,
                project_id=pid,
                buyer_name=name,
                buyer_id_number=id_num,
                contract_date=date(2025, 7, 1) + timedelta(days=i * 15),
                original_price_with_vat=apt.list_price_with_vat,
                final_price_with_vat=Decimal(str(final_with_vat)),
                final_price_no_vat=Decimal(str(final_no_vat)),
                is_recognized_by_bank=(i < 8),  # First 8 are recognized
                is_non_linear=(i == 5),  # One non-linear
            )
            db.add(sale)
            await db.flush()
            sales_created.append(sale)

            # Payment schedule: 4-5 installments per sale
            schedule = [
                ("מקדמה", Decimal("0.15"), date(2025, 7, 15) + timedelta(days=i * 15), True),
                ("תשלום 2", Decimal("0.25"), date(2025, 10, 1) + timedelta(days=i * 10), i < 8),
                ("תשלום 3", Decimal("0.25"), date(2026, 1, 1) + timedelta(days=i * 10), i < 4),
                ("תשלום 4", Decimal("0.20"), date(2026, 4, 1) + timedelta(days=i * 10), False),
                ("גמר - מסירה", Decimal("0.15"), date(2026, 10, 1), False),
            ]

            for pnum, (desc, pct, sched_date, is_paid) in enumerate(schedule, 1):
                amount = int(final_with_vat * float(pct))
                item = PaymentScheduleItem(
                    contract_id=sale.id,
                    payment_number=pnum,
                    description=desc,
                    scheduled_amount=Decimal(str(amount)),
                    scheduled_date=sched_date,
                    status=PaymentStatus.PAID if is_paid else PaymentStatus.SCHEDULED,
                    actual_amount=Decimal(str(amount)) if is_paid else None,
                    actual_date=sched_date if is_paid else None,
                )
                db.add(item)

        print(f"Created {len(sales_created)} sales with payment schedules")

        # ── 8. Monthly Reports (3 reports) ─────────────────────────
        reports = []
        for rnum in range(1, 4):
            month = date(2025, 9 + rnum, 1)  # Oct, Nov, Dec 2025
            report = MonthlyReport(
                project_id=pid,
                report_month=month,
                report_number=rnum,
                status=ReportStatus.REVIEW if rnum < 3 else ReportStatus.DATA_ENTRY,
                current_index=Decimal("127.3") + Decimal(str(rnum * 0.4)),
                vat_rate=Decimal("0.18"),
            )
            db.add(report)
            await db.flush()
            reports.append(report)

        # ── 9. Bank Statements + Transactions ──────────────────────
        transaction_templates = [
            # Report 1 (Oct 2025)
            [
                (date(2025, 10, 3), "העברה מחשבון הון עצמי", 2500000, "credit", TransactionCategory.EQUITY_DEPOSIT),
                (date(2025, 10, 5), "תשלום קרקע - רשות מקרקעין", 3500000, "debit", TransactionCategory.LAND_AND_TAXES),
                (date(2025, 10, 8), "תקבול רוכש - יוסי כהן - דירה 1", 450000, "credit", TransactionCategory.SALE_INCOME),
                (date(2025, 10, 10), "תקבול רוכש - רונית לוי - דירה 2", 520000, "credit", TransactionCategory.SALE_INCOME),
                (date(2025, 10, 12), "שכ\"ד מעבר לדיירים", 40000, "debit", TransactionCategory.TENANT_EXPENSES),
                (date(2025, 10, 15), "אופק בנייה - חפירה ותשתית", 650000, "debit", TransactionCategory.DIRECT_CONSTRUCTION),
                (date(2025, 10, 18), "א. כהן אדריכלים", 120000, "debit", TransactionCategory.INDIRECT_COSTS),
                (date(2025, 10, 20), "תקבול רוכש - אבי גולן - דירה 3", 380000, "credit", TransactionCategory.SALE_INCOME),
                (date(2025, 10, 22), "ביטוח קבלנים", 45000, "debit", TransactionCategory.INDIRECT_COSTS),
                (date(2025, 10, 25), "ריבית חודשית", 22000, "debit", TransactionCategory.INTEREST_AND_FEES),
                (date(2025, 10, 28), "העברה ליווי בנקאי", 5000000, "credit", TransactionCategory.LOAN_RECEIVED),
                (date(2025, 10, 30), "עמלת ניהול חשבון", 3500, "debit", TransactionCategory.INTEREST_AND_FEES),
            ],
            # Report 2 (Nov 2025)
            [
                (date(2025, 11, 2), "תקבול רוכש - מיכל דהן - דירה 4", 490000, "credit", TransactionCategory.SALE_INCOME),
                (date(2025, 11, 5), "אופק בנייה - עבודות שלד", 1200000, "debit", TransactionCategory.DIRECT_CONSTRUCTION),
                (date(2025, 11, 7), "תקבול רוכש - עמית שמש - דירה 5", 410000, "credit", TransactionCategory.SALE_INCOME),
                (date(2025, 11, 10), "מ. שרון מהנדסים - פיקוח", 65000, "debit", TransactionCategory.INDIRECT_COSTS),
                (date(2025, 11, 12), "היטל השבחה - עירייה", 175000, "debit", TransactionCategory.LAND_AND_TAXES),
                (date(2025, 11, 15), "אופק בנייה - שלד בטון", 850000, "debit", TransactionCategory.DIRECT_CONSTRUCTION),
                (date(2025, 11, 18), "תקבול רוכש - דניאל אברהם - דירה 6", 530000, "credit", TransactionCategory.SALE_INCOME),
                (date(2025, 11, 20), "החזר מע\"מ", 320000, "credit", TransactionCategory.VAT_REFUNDS),
                (date(2025, 11, 22), "חשמל ואינסטלציה - מקדמה", 280000, "debit", TransactionCategory.DIRECT_CONSTRUCTION),
                (date(2025, 11, 25), "ריבית חודשית", 24000, "debit", TransactionCategory.INTEREST_AND_FEES),
                (date(2025, 11, 28), "שיווק ופרסום", 85000, "debit", TransactionCategory.INDIRECT_COSTS),
                (date(2025, 11, 30), "הפקדת הון עצמי", 1500000, "credit", TransactionCategory.EQUITY_DEPOSIT),
            ],
            # Report 3 (Dec 2025) - latest, some unclassified
            [
                (date(2025, 12, 2), "תקבול רוכש - נועה ישראלי", 470000, "credit", TransactionCategory.SALE_INCOME),
                (date(2025, 12, 5), "אופק בנייה - עבודות שלד המשך", 1400000, "debit", TransactionCategory.DIRECT_CONSTRUCTION),
                (date(2025, 12, 8), "תקבול רוכש - יעל מזרחי", 395000, "credit", TransactionCategory.SALE_INCOME),
                (date(2025, 12, 10), "העברה 123456", 150000, "debit", None),  # Unclassified!
                (date(2025, 12, 12), "אלומיניום הדרום - מקדמה", 450000, "debit", TransactionCategory.DIRECT_CONSTRUCTION),
                (date(2025, 12, 15), "שובר 98765", 75000, "debit", None),  # Unclassified!
                (date(2025, 12, 18), "תקבול רוכש - אלון ברק", 510000, "credit", TransactionCategory.SALE_INCOME),
                (date(2025, 12, 20), "ייעוץ משפטי - עו\"ד ברנשטיין", 45000, "debit", TransactionCategory.INDIRECT_COSTS),
                (date(2025, 12, 22), "ריבית חודשית + עמלה", 26500, "debit", TransactionCategory.INTEREST_AND_FEES),
                (date(2025, 12, 25), "החזר מע\"מ", 280000, "credit", TransactionCategory.VAT_REFUNDS),
                (date(2025, 12, 28), "פקדון זמני", 200000, "debit", None),  # Unclassified!
                (date(2025, 12, 30), "תקבול רוכש - שירה פרידמן", 440000, "credit", TransactionCategory.SALE_INCOME),
            ],
        ]

        for r_idx, report in enumerate(reports):
            stmt = BankStatement(
                monthly_report_id=report.id,
                project_id=pid,
                account_type="project",
                original_filename=f"תדפיס_לאומי_{report.report_month.strftime('%m_%Y')}.pdf",
                bank_name="בנק לאומי",
                account_number="12345678",
                statement_start_date=report.report_month,
                statement_end_date=date(report.report_month.year, report.report_month.month, 28),
                parsing_status=ParsingStatus.PARSED,
            )
            db.add(stmt)
            await db.flush()

            balance = Decimal("5000000")
            for tx_date, desc, amount, tx_type, category in transaction_templates[r_idx]:
                if tx_type == "credit":
                    balance += Decimal(str(amount))
                else:
                    balance -= Decimal(str(amount))

                tx = BankTransaction(
                    bank_statement_id=stmt.id,
                    monthly_report_id=report.id,
                    project_id=pid,
                    transaction_date=tx_date,
                    description=desc,
                    amount=Decimal(str(amount)),
                    balance=balance,
                    transaction_type=TransactionType.CREDIT if tx_type == "credit" else TransactionType.DEBIT,
                    category=category,
                    is_manually_classified=category is not None,
                    ai_suggested_category=category.value if category else None,
                )
                db.add(tx)

        print(f"Created 3 monthly reports with {sum(len(t) for t in transaction_templates)} transactions")

        # ── 10. Construction Progress ──────────────────────────────
        progress_data = [
            (reports[0].id, Decimal("15"), Decimal("15"), "סיום חפירה, התחלת יסודות. יציקת רפסודה בניין A."),
            (reports[1].id, Decimal("28"), Decimal("13"), "סיום יסודות שני הבניינים. התחלת שלד קומה 1 בניין A."),
            (reports[2].id, Decimal("42"), Decimal("14"), "שלד עד קומה 3 בניין A, קומה 2 בניין B. התחלת טיח פנים קומות תחתונות."),
        ]
        for rid, overall, delta, desc in progress_data:
            db.add(ConstructionProgress(
                monthly_report_id=rid,
                project_id=pid,
                overall_percent=overall,
                monthly_delta_percent=delta,
                description_text=desc,
                visitor_name="שמאי דוד אלעזר",
            ))

        # ── 11. Guarantees (for report 3) ──────────────────────────
        guarantee_items = [
            {"buyer_name": "יוסי כהן", "guarantee_type": "sale_law", "original_amount": 450000, "indexed_balance": 462000, "expiry_date": "2027-06-30", "apartment_number": "1", "notes": ""},
            {"buyer_name": "רונית לוי", "guarantee_type": "sale_law", "original_amount": 520000, "indexed_balance": 534000, "expiry_date": "2027-06-30", "apartment_number": "2", "notes": ""},
            {"buyer_name": "אבי גולן", "guarantee_type": "sale_law", "original_amount": 380000, "indexed_balance": 390000, "expiry_date": "2027-06-30", "apartment_number": "3", "notes": ""},
            {"buyer_name": "מיכל דהן", "guarantee_type": "sale_law", "original_amount": 490000, "indexed_balance": 503000, "expiry_date": "2027-06-30", "apartment_number": "4", "notes": ""},
            {"buyer_name": "עמית שמש", "guarantee_type": "sale_law", "original_amount": 410000, "indexed_balance": 421000, "expiry_date": "2027-06-30", "apartment_number": "5", "notes": ""},
            {"buyer_name": "אופק בנייה", "guarantee_type": "performance", "original_amount": 2800000, "indexed_balance": 2870000, "expiry_date": "2027-12-31", "apartment_number": "", "notes": "ערבות ביצוע קבלן"},
        ]
        db.add(GuaranteeSnapshot(
            monthly_report_id=reports[2].id,
            project_id=pid,
            total_balance=Decimal("5180000"),
            total_receipts=Decimal("3665000"),
            gap=Decimal("1515000"),
            items=guarantee_items,
            notes="",
        ))

        # ── 12. Equity Tracking ────────────────────────────────────
        equity_data = [
            (reports[0].id, Decimal("5000000"), Decimal("2500000"), Decimal("0"), Decimal("2500000"), Decimal("-2500000")),
            (reports[1].id, Decimal("5000000"), Decimal("4000000"), Decimal("0"), Decimal("4000000"), Decimal("-1000000")),
            (reports[2].id, Decimal("5000000"), Decimal("4000000"), Decimal("0"), Decimal("4000000"), Decimal("-1000000")),
        ]
        for rid, req, dep, wd, bal, gap in equity_data:
            db.add(EquityTracking(
                monthly_report_id=rid, project_id=pid,
                required_amount=req, total_deposits=dep, total_withdrawals=wd,
                current_balance=bal, gap=gap,
            ))

        # ── 13. VAT Tracking ──────────────────────────────────────
        vat_data = [
            (reports[0].id, Decimal("8330000"), Decimal("1499400"), Decimal("4380500"), Decimal("788490"), Decimal("-710910"), Decimal("-710910")),
            (reports[1].id, Decimal("1750000"), Decimal("315000"), Decimal("2655000"), Decimal("477900"), Decimal("162900"), Decimal("-548010")),
            (reports[2].id, Decimal("2095000"), Decimal("377100"), Decimal("2346500"), Decimal("422370"), Decimal("45270"), Decimal("-502740")),
        ]
        for rid, tx_total, output_v, inputs, input_v, balance, cum in vat_data:
            db.add(VatTracking(
                monthly_report_id=rid, project_id=pid,
                transactions_total=tx_total, output_vat=output_v,
                inputs_total=inputs, input_vat=input_v,
                vat_balance=balance, cumulative_vat_balance=cum,
            ))

        await db.commit()
        print("\nDemo data seeded successfully!")
        print(f"  Project: {project.project_name}")
        print(f"  Apartments: {len(apt_data)} ({len(dev_apts)} developer)")
        print(f"  Sales: {len(sales_created)} with payment schedules")
        print(f"  Monthly Reports: 3 (Oct-Dec 2025)")
        print(f"  Bank transactions: {sum(len(t) for t in transaction_templates)}")
        print(f"  Guarantees: {len(guarantee_items)} items")
        print(f"  Milestones: {len(milestones_data)}")
        print(f"\nLogin: admin@maakav.co.il / admin123")
        print(f"URL: http://localhost:4700")


if __name__ == "__main__":
    asyncio.run(seed_demo())
