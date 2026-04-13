"""
VAT Calculator Service (מעקב מע"מ).

Calculates monthly:
- Transactions total (income) → output VAT
- Inputs total (expenses) → input VAT
- Balance = input - output
- Cumulative tracking
"""

from decimal import Decimal
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func

from ..models.monthly_report import MonthlyReport
from ..models.bank_statement import BankTransaction, TransactionType
from ..models.vat import VatTracking

# Categories that are income (output VAT)
INCOME_CATEGORIES = {
    "sale_income", "upgrades_income", "other_income",
}

# Categories that are expenses (input VAT)
EXPENSE_CATEGORIES = {
    "tenant_expenses", "land_and_taxes", "indirect_costs",
    "direct_construction", "deposit_to_savings", "other_expense",
}


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

    # Get income transactions (output VAT)
    income_total = Decimal("0")
    income_result = await db.execute(
        select(func.sum(BankTransaction.amount)).where(
            BankTransaction.monthly_report_id == report_id,
            BankTransaction.transaction_type == TransactionType.CREDIT,
            BankTransaction.category.in_([c for c in INCOME_CATEGORIES]),
        )
    )
    income_total = income_result.scalar() or Decimal("0")

    # Get expense transactions (input VAT)
    expense_total = Decimal("0")
    expense_result = await db.execute(
        select(func.sum(BankTransaction.amount)).where(
            BankTransaction.monthly_report_id == report_id,
            BankTransaction.transaction_type == TransactionType.DEBIT,
            BankTransaction.category.in_([c for c in EXPENSE_CATEGORIES]),
        )
    )
    expense_total = expense_result.scalar() or Decimal("0")

    output_vat = (income_total * vat_rate).quantize(Decimal("0.01"))
    input_vat = (expense_total * vat_rate).quantize(Decimal("0.01"))
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
