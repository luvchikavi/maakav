"""
VAT Calculator Service (מעקב מע"מ).

Calculates monthly:
- Transactions total (income) → output VAT
- Inputs total (expenses) → input VAT
- Balance = input - output
- Cumulative tracking

Handles:
- VAT-exempt categories (equity, loans, interest, tax refunds, VAT refunds)
- Separate output/input calculation
- Per-transaction actual VAT when available (future)
"""

from decimal import Decimal
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func

from ..models.monthly_report import MonthlyReport
from ..models.bank_statement import BankTransaction, TransactionType
from ..models.vat import VatTracking

# Categories subject to OUTPUT VAT (מע"מ עסקאות) — income from sales
OUTPUT_VAT_CATEGORIES = {
    "sale_income",       # הכנסה ממכירה
    "upgrades_income",   # הכנסה משידרוגים
    "other_income",      # הכנסה אחרת
}

# Categories subject to INPUT VAT (מע"מ תשומות) — expenses with VAT invoices
INPUT_VAT_CATEGORIES = {
    "tenant_expenses",       # הוצאות דיירים
    "indirect_costs",        # הוצאות עקיפות
    "direct_construction",   # בנייה ישירה
    "other_expense",         # הוצאה אחרת
}

# VAT-EXEMPT categories — no VAT calculated
# land_and_taxes — מס שבח, היטל השבחה, ארנונה (VAT exempt)
# equity_deposit — הון עצמי (not a transaction with VAT)
# loan_received / loan_repayment — הלוואה (financial, no VAT)
# interest_and_fees — ריביות ועמלות (financial services, mostly exempt)
# tax_refunds — החזרי מיסים (not subject to VAT)
# vat_refunds — החזרי מע"מ (the refund itself, not a new VAT event)
# deposit_to_savings — פקדון (transfer, no VAT)


async def calculate_vat(
    project_id: int,
    report_id: int,
    db: AsyncSession,
) -> VatTracking:
    """Calculate VAT tracking for a monthly report."""

    report = (await db.execute(
        select(MonthlyReport).where(MonthlyReport.id == report_id)
    )).scalar_one()

    vat_rate = report.vat_rate or Decimal("0.18")

    # Output VAT: income from sales (only categories that generate VAT invoices)
    income_total = (await db.execute(
        select(func.sum(BankTransaction.amount)).where(
            BankTransaction.monthly_report_id == report_id,
            BankTransaction.transaction_type == TransactionType.CREDIT,
            BankTransaction.category.in_(list(OUTPUT_VAT_CATEGORIES)),
        )
    )).scalar() or Decimal("0")

    # Input VAT: expenses with VAT invoices (construction, indirect, etc.)
    expense_total = (await db.execute(
        select(func.sum(BankTransaction.amount)).where(
            BankTransaction.monthly_report_id == report_id,
            BankTransaction.transaction_type == TransactionType.DEBIT,
            BankTransaction.category.in_(list(INPUT_VAT_CATEGORIES)),
        )
    )).scalar() or Decimal("0")

    # VAT-exempt totals (for reporting — land, interest, loans)
    exempt_income = (await db.execute(
        select(func.sum(BankTransaction.amount)).where(
            BankTransaction.monthly_report_id == report_id,
            BankTransaction.transaction_type == TransactionType.CREDIT,
            BankTransaction.category.in_(["equity_deposit", "loan_received", "tax_refunds", "vat_refunds"]),
        )
    )).scalar() or Decimal("0")

    exempt_expense = (await db.execute(
        select(func.sum(BankTransaction.amount)).where(
            BankTransaction.monthly_report_id == report_id,
            BankTransaction.transaction_type == TransactionType.DEBIT,
            BankTransaction.category.in_(["land_and_taxes", "loan_repayment", "interest_and_fees", "deposit_to_savings"]),
        )
    )).scalar() or Decimal("0")

    # Calculate VAT amounts
    # Output VAT = income × rate / (1 + rate) — amounts include VAT
    output_vat = (income_total * vat_rate / (1 + vat_rate)).quantize(Decimal("0.01"))
    # Input VAT = expense × rate / (1 + rate) — amounts include VAT
    input_vat = (expense_total * vat_rate / (1 + vat_rate)).quantize(Decimal("0.01"))

    balance = input_vat - output_vat  # Positive = refund, negative = pay

    # Get previous cumulative
    prev_cumulative = Decimal("0")
    if report.report_number > 1:
        prev_report = (await db.execute(
            select(MonthlyReport).where(
                MonthlyReport.project_id == project_id,
                MonthlyReport.report_number == report.report_number - 1,
            )
        )).scalar_one_or_none()

        if prev_report:
            prev_vat = (await db.execute(
                select(VatTracking).where(VatTracking.monthly_report_id == prev_report.id)
            )).scalar_one_or_none()
            if prev_vat:
                prev_cumulative = prev_vat.cumulative_vat_balance

    cumulative = prev_cumulative + balance

    # Upsert
    existing = (await db.execute(
        select(VatTracking).where(VatTracking.monthly_report_id == report_id)
    )).scalar_one_or_none()

    if existing:
        existing.transactions_total = income_total
        existing.output_vat = output_vat
        existing.inputs_total = expense_total
        existing.input_vat = input_vat
        existing.vat_balance = balance
        existing.cumulative_vat_balance = cumulative
        vat = existing
    else:
        vat = VatTracking(
            monthly_report_id=report_id,
            project_id=project_id,
            transactions_total=income_total,
            output_vat=output_vat,
            inputs_total=expense_total,
            input_vat=input_vat,
            vat_balance=balance,
            cumulative_vat_balance=cumulative,
        )
        db.add(vat)

    await db.commit()
    await db.refresh(vat)
    return vat
